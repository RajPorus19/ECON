"""econom CLI: start, run, doctor."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


def _load_env() -> None:
    load_dotenv(ROOT / ".env")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
    sys.path.insert(0, str(ROOT))


def cmd_start(_args: argparse.Namespace) -> int:
    _load_env()
    from django.core.management import execute_from_command_line

    bind = os.environ.get("ECON_BIND", "127.0.0.1:8000")
    execute_from_command_line(["manage.py", "runserver", bind])
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    _load_env()
    import httpx

    base = os.environ.get("ECON_API_URL", "http://127.0.0.1:8000").rstrip("/")
    params = {"debug": "true"} if args.debug else None
    response = httpx.post(
        f"{base}/api/v1/execute",
        json={"text": args.text, "confirm": args.confirm},
        params=params,
        timeout=60.0,
    )
    try:
        print(json.dumps(response.json(), indent=2))
    except ValueError:
        print(response.text)
    return 0 if response.is_success else 1


def _check(name: str, ok: bool, detail: str) -> None:
    mark = "ok" if ok else "FAIL"
    print(f"  [{mark}] {name}: {detail}")


def cmd_doctor(_args: argparse.Namespace) -> int:
    _load_env()
    import django

    django.setup()
    from django.conf import settings
    from django.db import connection

    print("ECON Doctor")
    failed = 0

    try:
        connection.ensure_connection()
        _check("PostgreSQL", True, f"{settings.DATABASES['default'].get('HOST', 'sqlite')}")
    except Exception as exc:  # noqa: BLE001
        failed += 1
        _check("PostgreSQL", False, str(exc))

    try:
        import redis

        client = redis.from_url(os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0"))
        client.ping()
        _check("Redis", True, os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0"))
    except Exception as exc:  # noqa: BLE001
        failed += 1
        _check("Redis", False, str(exc))

    from core.llm.ollama import OllamaProvider

    llm = OllamaProvider(
        base_url=str(settings.ECON["LLM_BASE_URL"]),
        model=str(settings.ECON["LLM_MODEL"]),
    )
    llm_ok = llm.ping()
    if not llm_ok:
        failed += 1
    _check(
        "Ollama/Hermes",
        llm_ok,
        f"{settings.ECON['LLM_BASE_URL']} model={settings.ECON['LLM_MODEL']}",
    )

    mode = settings.ECON.get("EXECUTION_MODE", "local")
    if mode == "host_agent":
        from core.execution.host_agent import HostAgentExecutor

        agent = HostAgentExecutor(
            str(settings.ECON["HOST_AGENT_URL"]),
            str(settings.ECON["HOST_AGENT_TOKEN"]),
        )
        agent_ok = agent.ping()
        if not agent_ok:
            failed += 1
        _check("Host agent", agent_ok, str(settings.ECON["HOST_AGENT_URL"]))
    else:
        _check("Executor", True, "local subprocess")

    print()
    if failed:
        print(f"{failed} check(s) failed.")
        return 1
    print("Everything looks good.")
    return 0


def cmd_host_agent(_args: argparse.Namespace) -> int:
    _load_env()
    from host_agent.server import serve

    serve()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="econom", description="ECON local automation runtime")
    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser("start", help="Run the Django development server")
    start.set_defaults(func=cmd_start)

    run = sub.add_parser("run", help="Send a natural-language request to a running API")
    run.add_argument("text", help="Utterance to execute")
    run.add_argument("--debug", action="store_true")
    run.add_argument("--confirm", action="store_true")
    run.set_defaults(func=cmd_run)

    doctor = sub.add_parser("doctor", help="Check Postgres, Redis, Hermes, and the host agent")
    doctor.set_defaults(func=cmd_doctor)

    agent = sub.add_parser("host-agent", help="Run the host command daemon")
    agent.set_defaults(func=cmd_host_agent)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    raise SystemExit(args.func(args))
