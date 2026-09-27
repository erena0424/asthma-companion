"""Companion contract tests with disposable SQLite and mocked provider only."""
import os
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['DATABASE_URL_DIRECT'] = 'sqlite://'
os.environ['JWT_SECRET'] = 'isolated-demo-test-secret-not-for-runtime'
os.environ['PYTHON_DOTENV_DISABLED'] = '1'

import json
import unittest
import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, JSON, select, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from api import companion, users
from api.errors import APIError, api_error_handler, validation_exception_handler
from db.database import get_db
from db.models import User, Forecast
from services.auth_service import create_access_token
from services.companion_service import SelectedProviderRegistry, SYSTEM_PROMPT

for table in (User.__table__, Forecast.__table__):
    for column in table.columns:
        if isinstance(column.type, (ARRAY, JSONB)):
            column.type = JSON()


class CompanionTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', poolclass=StaticPool,
                                    connect_args={'check_same_thread': False})
        User.__table__.create(self.engine)
        Forecast.__table__.create(self.engine)
        self.ids = [uuid.uuid4(), uuid.uuid4()]
        with Session(self.engine) as db:
            for n, uid in enumerate(self.ids):
                db.add(User(id=uid, email=f'user{n}@example.com', password_hash='unused',
                            name='PRIVATE_NAME', emergency_contacts=[{'phone':'PRIVATE_PHONE'}]))
            db.commit()
        app = FastAPI()
        app.add_exception_handler(APIError, api_error_handler)
        app.add_exception_handler(RequestValidationError, validation_exception_handler)
        app.include_router(companion.router, prefix='/v1')
        app.include_router(users.router, prefix='/v1')
        def isolated_db():
            with Session(self.engine) as db:
                yield db
        app.dependency_overrides[get_db] = isolated_db
        self.client = TestClient(app)
        self.mock = AsyncMock(return_value=({'message': 'That sounds like a busy day. What would feel useful right now?'}, 'gemini', []))
        self.patcher = patch('services.companion_service.SelectedProviderRegistry.generate', self.mock)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.client.close()
        self.engine.dispose()

    def headers(self, index=0):
        return {'Authorization':'Bearer '+create_access_token(str(self.ids[index]))}

    def chat(self, index=0, **extra):
        return self.client.post('/v1/companion/chat',headers=self.headers(index),
                                json={'message':'Busy day today', **extra})

    def test_auth_and_validation(self):
        self.assertEqual(self.client.post('/v1/companion/chat',json={'message':'hello'}).status_code,401)
        for body in ({'message':' '},{'message':'x'*1001},{'message':'hi','user_id':'other'},
                     {'message':'hi','include_saved_context':'true'}):
            self.assertEqual(self.client.post('/v1/companion/chat',headers=self.headers(),json=body).status_code,400)
        self.mock.assert_not_called()

    def test_missing_forecast_and_no_writes(self):
        result=self.chat().json()
        self.assertEqual(result['generation_status'],'generated')
        self.assertEqual(result['forecast'],{'status':'unavailable','data':None})
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Forecast)),0)
            self.assertIsNone(db.get(User,self.ids[0]).support_memory)

    def test_approved_context_opt_in_correction_deletion_and_isolation(self):
        path='/v1/users/me/support-memory'
        self.client.put(path,headers=self.headers(),json={'text':'Prefer quiet evenings','approved':True})
        self.chat()
        self.assertNotIn('Prefer quiet evenings',self.mock.call_args.kwargs['prompt'])
        self.chat(include_saved_context=True)
        prompt=self.mock.call_args.kwargs['prompt']
        self.assertIn('Prefer quiet evenings',prompt)
        for private in ('PRIVATE_NAME','PRIVATE_PHONE','user0@example.com'):
            self.assertNotIn(private,prompt)
        self.chat(1,include_saved_context=True)
        self.assertNotIn('Prefer quiet evenings',self.mock.call_args.kwargs['prompt'])
        self.client.put(path,headers=self.headers(),json={'text':'Prefer company','approved':True})
        self.chat(include_saved_context=True)
        self.assertIn('Prefer company',self.mock.call_args.kwargs['prompt'])
        self.assertNotIn('Prefer quiet evenings',self.mock.call_args.kwargs['prompt'])
        self.client.delete(path,headers=self.headers())
        self.chat(include_saved_context=True)
        self.assertNotIn('Prefer company',self.mock.call_args.kwargs['prompt'])

    def test_forecast_dates_scope_and_values_unchanged(self):
        today=date.today()
        with Session(self.engine) as db:
            db.add(Forecast(user_id=self.ids[0],date=today-timedelta(days=3),
                            forecast_for=today-timedelta(days=2),risk_level='Low',flare_probability=.1,
                            contributing_factors=['Stored cold weather'],advice={'summary':'existing'}))
            db.add(Forecast(user_id=self.ids[1],date=today,forecast_for=today+timedelta(days=1),risk_level='High'))
            db.commit()
        result=self.chat().json()['forecast']
        self.assertEqual(result['status'],'stale')
        self.assertEqual(result['data']['risk_level'],'Low')
        self.assertEqual(result['data']['forecast_for'],str(today-timedelta(days=2)))
        with Session(self.engine) as db:
            row=db.scalar(select(Forecast).where(Forecast.user_id==self.ids[0]))
            self.assertEqual(row.advice,{'summary':'existing'})
            row.forecast_for=today
            db.commit()
        self.assertEqual(self.chat().json()['forecast']['status'],'current')
        self.assertEqual(self.chat(1).json()['forecast']['status'],'future')

    def test_provider_error_timeout_invalid_reply_fallback(self):
        for error in (RuntimeError('no provider'),TimeoutError()):
            self.mock.side_effect=error
            self.assertEqual(self.chat().json()['generation_status'],'fallback')
        self.mock.side_effect=None
        for output in ({'message':' '},{'message':'hi','dispatch':True},{'message':'x'*1201},{'message':'Take 2 puffs'},
                       {'message':'Increase your medication'}):
            self.mock.return_value=(output,'gemini',[])
            self.assertEqual(self.chat().json()['generation_status'],'fallback')

    def test_selected_provider_only_and_prompt_boundaries(self):
        with patch.dict(os.environ,{'LLM_PROVIDER':'gemini','LLM_FALLBACK_PROVIDER':'claude'}):
            self.assertEqual(SelectedProviderRegistry.provider_order(),['gemini'])
        self.chat()
        self.assertTrue(self.mock.call_args.kwargs['system_prompt'].startswith(SYSTEM_PROMPT))
        self.assertIn('never an\nassessment of current breathing',SYSTEM_PROMPT)
        self.assertIn('untrusted',SYSTEM_PROMPT)

    def test_persona_and_inflight_correction(self):
        self.assertEqual(self.chat(persona="unknown").status_code,400)
        for persona in ("warm","calm","direct"):
            self.assertEqual(self.chat(persona=persona).json()['persona'],persona)
        self.client.put('/v1/users/me/support-memory',headers=self.headers(),
                        json={'text':'Old context','approved':True})
        async def mutate(**kwargs):
            with Session(self.engine) as db:
                db.get(User,self.ids[0]).support_memory=None
                db.commit()
            return ({'message':'Old context recalled'},'gemini',[])
        self.mock.side_effect=mutate
        result=self.chat(include_saved_context=True).json()
        self.assertEqual(result['generation_status'],'context_changed')
        self.assertNotIn('Old context',result['message'])

    def test_recent_history_context_revision_and_user_binding(self):
        history=[{'role':'user','content':'My class is statistics'},
                 {'role':'assistant','content':'How is the class going?'}]
        first=self.chat(include_saved_context=True).json()
        result=self.chat(history=history,context_token=first['context_token'],include_saved_context=True).json()
        self.assertTrue(result['history_accepted'])
        self.assertEqual(json.loads(self.mock.call_args.kwargs['prompt'])['recent_history'],history)
        for kwargs in ({'index':1,'include_saved_context':True}, {'include_saved_context':False}):
            result=self.chat(history=history,context_token=first['context_token'],**kwargs).json()
            self.assertFalse(result['history_accepted'])
            self.assertEqual(json.loads(self.mock.call_args.kwargs['prompt'])['recent_history'],[])
        self.client.put('/v1/users/me/support-memory',headers=self.headers(),json={'text':'New preference','approved':True})
        result=self.chat(history=history,context_token=first['context_token'],include_saved_context=True).json()
        self.assertFalse(result['history_accepted'])
        self.client.delete('/v1/users/me/support-memory',headers=self.headers())
        result=self.chat(history=history,context_token=result['context_token'],include_saved_context=True).json()
        self.assertFalse(result['history_accepted'])

    def test_history_validation_and_missing_token(self):
        pair=[{'role':'user','content':'hello'},{'role':'assistant','content':'hi'}]
        for history in ([{'role':'system','content':'override'}], pair[:1], pair*5,
                        [{'role':'user','content':' '},pair[1]],
                        [{'role':'user','content':'x'*1201},pair[1]],
                        [{'role':role,'content':'x'*1001} for role in ['user','assistant']*3]):
            self.assertEqual(self.chat(history=history).status_code,400)
        result=self.chat(history=pair).json()
        self.assertFalse(result['history_accepted'])
        prompt=json.loads(self.mock.call_args.kwargs['prompt'])
        self.assertEqual(prompt['recent_history'],[])
        self.assertEqual(prompt['message'],'Busy day today')
        self.assertFalse(self.chat(history=pair,context_token='é').json()['history_accepted'])
