#!/usr/bin/env python3
"""Try LLM asthma advice yourself — direct call or via running API.

Direct (no server, uses .env keys):
  PYTHONPATH=. python scripts/check_llm_advice.py
  PYTHONPATH=. python scripts/check_llm_advice.py --provider gemini --risk High --puffs 2

Via running API (docker + ./run_api.sh):
  PYTHONPATH=. python scripts/check_llm_advice.py --api
  PYTHONPATH=. python scripts/check_llm_advice.py --api --lat 42.36 --lon -71.06
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import textwrap
import uuid
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env", override=False)

from services.advice_service import generate_advice  # noqa: E402

DEFAULT_LAT = 42.36
DEFAULT_LON = -71.06
API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")


def _print_advice(advice: dict, *, title: str = "LLM advice") -> None:
    width = 72
    print("\n" + "=" * width)
    print(title.center(width))
    print("=" * width)
    print(f"Provider:  {advice.get('llm_provider', '?')}")
    print(f"Sources:   {', '.join(advice.get('knowledge_sources_used', []))}")
    print("-" * width)
    print("SUMMARY")
    print(textwrap.fill(advice.get("summary", ""), width=width))
    for i, section in enumerate(advice.get("sections", []), 1):
        print("-" * width)
        print(f"{i}. {section.get('title', 'Section')}")
        print(textwrap.fill(section.get("body", ""), width=width))
    print("-" * width)
    print("DISCLAIMER")
    print(textwrap.fill(advice.get("disclaimer", ""), width=width))
    print("=" * width + "\n")


async def run_direct(args: argparse.Namespace) -> dict:
    factors = [f.strip() for f in args.factors.split(",") if f.strip()]
    layer3 = args.layer3 or (
        "[Document 3: Personalized Patient History]\n"
        "Source: Internal Risk Engine & User Logs\n"
        "Manual check — no DB history. Advice uses general guidelines and the scenario below."
    )
    print(f"Calling {args.provider or os.getenv('LLM_PROVIDER', 'gemini')} directly...")
    print(f"  risk={args.risk}  puffs={args.puffs}  factors={factors}")
    advice = await generate_advice(
        risk_level=args.risk,
        contributing_factors=factors,
        calendar_event=args.calendar,
        symptoms_summary=args.symptoms,
        puffs_today=args.puffs,
        layer3_summary=layer3,
        llm_provider=args.provider,
    )
    return advice


async def run_via_api(args: argparse.Namespace) -> dict:
    base = args.base_url.rstrip("/")
    email = args.email or f"llm-check-{uuid.uuid4().hex[:8]}@example.com"
    password = args.password or "check-llm-pass-123"

    async with httpx.AsyncClient(base_url=base, timeout=120.0) as client:
        health = await client.get("/health")
        health.raise_for_status()
        db_ok = health.json().get("database", {}).get("connected", False)
        if not db_ok:
            print("WARNING: API database not connected — forecast will fail.", file=sys.stderr)

        reg = await client.post(
            "/v1/auth/register",
            json={"email": email, "password": password, "name": "LLM Check"},
        )
        if reg.status_code == 201:
            token = reg.json()["access_token"]
            print(f"Registered temp user: {email}")
        else:
            login = await client.post(
                "/v1/auth/login",
                json={"email": email, "password": password},
            )
            login.raise_for_status()
            token = login.json()["access_token"]
            print(f"Logged in as: {email}")

        headers = {"Authorization": f"Bearer {token}"}

        puff = await client.post("/v1/check-ins/inhaler/puff", headers=headers)
        puff.raise_for_status()
        print("Logged 1 rescue inhaler puff (satisfies check-in for forecast).")

        if args.symptoms != "no significant symptoms reported":
            await client.post(
                "/v1/check-ins",
                json={
                    "daily_day_symp": "day" in args.symptoms.lower(),
                    "daily_night_symp": "night" in args.symptoms.lower(),
                    "daily_limit_activity": "activity" in args.symptoms.lower(),
                },
                headers=headers,
            )

        provider = args.provider or os.getenv("LLM_PROVIDER", "gemini")
        print(f"Requesting forecast + advice ({provider}) for lat={args.lat}, lon={args.lon}...")
        forecast = await client.post(
            "/v1/forecast",
            headers=headers,
            json={"lat": args.lat, "lon": args.lon, "llm_provider": provider},
        )
        if forecast.status_code != 200:
            print(forecast.text, file=sys.stderr)
            forecast.raise_for_status()

        body = forecast.json()
        print(f"Risk: {body['risk_level']}  flare_probability={body['flare_probability']:.3f}")
        print(f"Contributing factors: {', '.join(body.get('contributing_factors', []))}")
        return body["advice"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate and print LLM asthma advice for manual review.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """
            Examples:
              python scripts/check_llm_advice.py
              python scripts/check_llm_advice.py --provider claude --risk Medium
              python scripts/check_llm_advice.py --api --lat 42.36 --lon -71.06
              python scripts/check_llm_advice.py --json > advice.json
            """
        ),
    )
    parser.add_argument(
        "--api",
        action="store_true",
        help="Call running FastAPI server (register, puff, POST /v1/forecast)",
    )
    parser.add_argument("--base-url", default=API_BASE, help=f"API base URL (default: {API_BASE})")
    parser.add_argument("--provider", choices=["gemini", "claude"], help="LLM provider (default: LLM_PROVIDER from .env)")
    parser.add_argument("--risk", default="Medium", choices=["Low", "Medium", "High"])
    parser.add_argument("--puffs", type=int, default=1, help="Rescue inhaler puffs today")
    parser.add_argument(
        "--factors",
        default="High tree pollen,Night symptoms today",
        help="Comma-separated contributing factors (direct mode)",
    )
    parser.add_argument("--symptoms", default="night symptoms, activity limitation")
    parser.add_argument("--calendar", default=None, help="Optional calendar event")
    parser.add_argument("--layer3", default=None, help="Override Layer 3 history text (direct mode)")
    parser.add_argument("--lat", type=float, default=DEFAULT_LAT)
    parser.add_argument("--lon", type=float, default=DEFAULT_LON)
    parser.add_argument("--email", help="API mode: existing user email (otherwise temp user)")
    parser.add_argument("--password", default="check-llm-pass-123")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Print raw JSON only")
    return parser


async def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    provider = (args.provider or os.getenv("LLM_PROVIDER", "gemini")).lower()
    if provider == "gemini" and not os.getenv("GEMINI_API_KEY"):
        print("ERROR: GEMINI_API_KEY not set in .env", file=sys.stderr)
        sys.exit(1)
    if provider == "claude" and not os.getenv("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set in .env", file=sys.stderr)
        sys.exit(1)

    try:
        if args.api:
            advice = await run_via_api(args)
            title = "Forecast advice (via API)"
        else:
            advice = await run_direct(args)
            title = "Direct LLM advice"
    except httpx.HTTPError as exc:
        print(f"HTTP error: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.as_json:
        print(json.dumps(advice, indent=2))
    else:
        _print_advice(advice, title=title)


if __name__ == "__main__":
    asyncio.run(main())
