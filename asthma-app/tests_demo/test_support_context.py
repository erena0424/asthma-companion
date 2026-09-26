"""Isolated route tests: no legacy conftest, real JWT, disposable SQLite only.

Run from asthma-app: python -B -m unittest discover -s tests_demo -v
Does not validate Postgres DDL, full app startup, or providers.
"""
import os
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['DATABASE_URL_DIRECT'] = 'sqlite://'
os.environ['JWT_SECRET'] = 'isolated-demo-test-secret-not-for-runtime'
os.environ['PYTHON_DOTENV_DISABLED'] = '1'

import sys
import types
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

# Only legacy forecast orchestration is replaced; these routes must not need it.
forecast_stub = types.ModuleType('services.forecast_service')
forecast_stub.refresh_forecast_after_check_in = AsyncMock(return_value=None)
sys.modules['services.forecast_service'] = forecast_stub

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, JSON, select, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from api import users, check_ins
from api.errors import APIError, api_error_handler, validation_exception_handler
from db.database import get_db
from db.models import User, CheckIn
from services.auth_service import create_access_token

# Test-only portability; never connect the configured engine or create all tables.
for table in (User.__table__, CheckIn.__table__):
    for column in table.columns:
        if isinstance(column.type, (ARRAY, JSONB)):
            column.type = JSON()


class SupportContextTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', poolclass=StaticPool,
                                    connect_args={'check_same_thread': False})
        User.__table__.create(self.engine)
        CheckIn.__table__.create(self.engine)
        self.ids = [uuid.uuid4(), uuid.uuid4()]
        with Session(self.engine) as db:
            for n, uid in enumerate(self.ids):
                db.add(User(id=uid, email=f'demo{n}@example.com', password_hash='unused'))
            db.commit()
        app = FastAPI()
        app.add_exception_handler(APIError, api_error_handler)
        app.add_exception_handler(RequestValidationError, validation_exception_handler)
        app.include_router(users.router, prefix='/v1')
        app.include_router(check_ins.router, prefix='/v1')
        def isolated_db():
            with Session(self.engine) as db:
                yield db
        app.dependency_overrides[get_db] = isolated_db
        self.client = TestClient(app)
        forecast_stub.refresh_forecast_after_check_in.reset_mock()
        self.path = '/v1/users/me/support-memory'

    def tearDown(self):
        self.client.close()
        self.engine.dispose()

    def headers(self, index=0):
        return {'Authorization': 'Bearer ' + create_access_token(str(self.ids[index]))}

    def test_authentication(self):
        expired = create_access_token(str(self.ids[0]), {'exp': datetime.now(timezone.utc)-timedelta(days=1)})
        for token in (None, 'invalid', expired, create_access_token('not-a-uuid')):
            headers = {} if token is None else {'Authorization': 'Bearer '+token}
            for method in ('get', 'put', 'delete'):
                kwargs = {'json': {'text':'test','approved':True}} if method == 'put' else {}
                self.assertEqual(getattr(self.client, method)(self.path, headers=headers, **kwargs).status_code, 401)

    def test_approval_and_validation_never_persist(self):
        for body in ({'text':'test'}, {'text':'test','approved':False},
                     {'text':'test','approved':1}, {'text':'test','approved':'true'},
                     {'text':' '*2,'approved':True}, {'text':'x'*501,'approved':True},
                     {'text':'test','approved':True,'user_id':str(self.ids[1])}):
            self.assertEqual(self.client.put(self.path, headers=self.headers(), json=body).status_code, 400)
        self.assertIsNone(self.client.get(self.path,headers=self.headers()).json()['summary'])
        self.client.patch('/v1/users/me',headers=self.headers(),json={'support_memory':{'text':'bypass'}})
        self.assertIsNone(self.client.get(self.path,headers=self.headers()).json()['summary'])

    def test_durable_correct_delete_and_isolation(self):
        saved = self.client.put(self.path, headers=self.headers(), json={'text':'x'*500,'approved':True}).json()['summary']
        self.assertEqual(saved['source'],'user-reported')
        self.assertIsNone(saved['check_in_date'])
        self.assertIsNotNone(datetime.fromisoformat(saved['saved_at']).tzinfo)
        self.assertEqual(self.client.get(self.path,headers=self.headers()).json()['summary'],saved)
        self.assertIsNone(self.client.get(self.path,headers=self.headers(1)).json()['summary'])
        self.client.delete(self.path,headers=self.headers(1))
        self.assertEqual(self.client.get(self.path,headers=self.headers()).json()['summary'],saved)
        changed = self.client.put(self.path,headers=self.headers(),json={'text':'Corrected','check_in_date':'2026-09-26','approved':True})
        self.assertEqual(changed.status_code,200)
        with Session(self.engine) as db:
            self.assertEqual(db.get(User,self.ids[0]).support_memory['text'],'Corrected')
            self.assertEqual(db.scalar(select(func.count()).select_from(CheckIn)),0)
        for _ in range(2):
            self.assertEqual(self.client.delete(self.path,headers=self.headers()).status_code,204)
        with Session(self.engine) as db:
            self.assertIsNone(db.get(User,self.ids[0]).support_memory)
        forecast_stub.refresh_forecast_after_check_in.assert_not_called()

    def test_contacts_preferences_and_clear(self):
        path='/v1/users/me'
        response=self.client.patch(path,headers=self.headers(),json={
            'emergency_contacts':[{'firstName':'Demo','phone':'555-0100'}],
            'care_goal':'Take breaks', 'accessibility_needs':'Large text'})
        self.assertEqual(response.status_code,200)
        self.assertIn('Demo',response.json()['emergency_contact'])
        self.assertEqual(self.client.get(path,headers=self.headers()).json()['care_goal'],'Take breaks')
        self.assertEqual(self.client.get(path,headers=self.headers(1)).json()['emergency_contacts'],[])
        cleared=self.client.patch(path,headers=self.headers(),json={'emergency_contacts':[], 'emergency_contact':'stale'})
        self.assertIsNone(cleared.json()['emergency_contact'])
        self.assertEqual(self.client.get(path,headers=self.headers()).json()['emergency_contacts'],[])

    def test_profile_write_validation_and_legacy_reads(self):
        for contact in ({}, {'firstName':' ','phone':'555-0100'},
                        {'firstName':'Demo','phone':'call me'},
                        {'firstName':'Demo','phone':'555-0100','unexpected':{}},
                        {'firstName':'x'*101,'phone':'555-0100'}):
            self.assertEqual(self.client.patch('/v1/users/me',headers=self.headers(),json={'emergency_contacts':[contact]}).status_code,400)
        self.assertEqual(self.client.patch('/v1/users/me',headers=self.headers(),json={'care_goal':'x'*1001}).status_code,400)
        with Session(self.engine) as db:
            db.get(User,self.ids[0]).emergency_contacts=[{'email':'old@example.com'}]
            db.commit()
        self.assertEqual(self.client.get('/v1/users/me',headers=self.headers()).status_code,200)

    def test_checkin_optout_and_legacy_default(self):
        body={'date':'2026-09-26','daily_day_symp':True,'daily_night_symp':False,'daily_limit_activity':True}
        response=self.client.post('/v1/check-ins?refresh_forecast=false',headers=self.headers(),json=body)
        self.assertEqual(response.status_code,201)
        self.assertFalse(response.json()['forecast_refreshed'])
        forecast_stub.refresh_forecast_after_check_in.assert_not_called()
        self.assertIsNone(self.client.get(self.path,headers=self.headers()).json()['summary'])
        body['daily_day_symp']=False
        self.client.post('/v1/check-ins',headers=self.headers(),json=body)
        forecast_stub.refresh_forecast_after_check_in.assert_awaited_once()
        rows=self.client.get('/v1/check-ins',headers=self.headers()).json()['items']
        self.assertEqual(len(rows),1)
        self.assertFalse(rows[0]['daily_day_symp'])
        self.assertEqual(self.client.get('/v1/check-ins',headers=self.headers(1)).json()['items'],[])

if __name__ == '__main__':
    unittest.main()
