"""econom CLI: start, run, doctor, flows, entities, graph, learn, test, host-agent."""

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


def _setup_django() -> None:
    _load_env()
    import django

    django.setup()


def cmd_start(_args: argparse.Namespace) -> int:
    _load_env()
    import uvicorn

    bind = os.environ.get("ECON_BIND", "127.0.0.1:8000")
    host, _, port = bind.rpartition(":")
    uvicorn.run(
        "config.asgi:application",
        host=host or "127.0.0.1",
        port=int(port or "8000"),
        reload=os.environ.get("ECON_RELOAD", "1") not in {"0", "false", "False"},
    )
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


def cmd_test(args: argparse.Namespace) -> int:
    args.debug = True
    return cmd_run(args)


def _check(name: str, ok: bool, detail: str) -> None:
    mark = "ok" if ok else "FAIL"
    print(f"  [{mark}] {name}: {detail}")


def cmd_doctor(_args: argparse.Namespace) -> int:
    _setup_django()
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

    from core.stt import UnavailableSTT, load_stt

    stt = load_stt()
    if isinstance(stt, UnavailableSTT) or not stt.ping():
        _check("STT", False, "not installed")
    else:
        _check("STT", True, type(stt).__name__)

    from core.execution import ping_shell_executor

    shell_ok, shell_detail = ping_shell_executor()
    if not shell_ok:
        failed += 1
    _check("Shell executor", shell_ok, shell_detail)

    mode = settings.ECON.get("EXECUTION_MODE", "local")
    from core.execution.host_agent import HostAgentExecutor

    agent = HostAgentExecutor(
        str(settings.ECON["HOST_AGENT_URL"]),
        str(settings.ECON["HOST_AGENT_TOKEN"]),
    )
    agent_ok = agent.ping()
    if mode == "host_agent":
        if not agent_ok:
            failed += 1
        _check("Host agent", agent_ok, str(settings.ECON["HOST_AGENT_URL"]))
    else:
        _check("Host agent", True, f"optional ({'up' if agent_ok else 'down'})")

    jellyfin_url = os.environ.get("JELLYFIN_URL", "").strip()
    if jellyfin_url:
        jelly_ok = bool(os.environ.get("JELLYFIN_API_KEY", "").strip())
        if not jelly_ok:
            failed += 1
        key_note = "present" if jelly_ok else "missing"
        _check("Jellyfin", jelly_ok, f"JELLYFIN_URL set; API key {key_note}")
    steam_key = os.environ.get("STEAM_API_KEY", "").strip()
    if steam_key:
        _check("Steam API", True, "STEAM_API_KEY set (library lookup enabled)")

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


def cmd_flows_list(_args: argparse.Namespace) -> int:
    _setup_django()
    from apps.flows.models import Flow

    for flow in Flow.objects.all().order_by("name", "-version"):
        flag = "on" if flow.enabled else "off"
        print(
            f"{flow.pk}\t{flow.name}\tv{flow.version}\t{flag}\t"
            f"conf={flow.confidence:.2f}\tuse={flow.usage_count}"
        )
    return 0


def cmd_entities_list(_args: argparse.Namespace) -> int:
    _setup_django()
    from apps.knowledge.models import Entity

    for entity in Entity.objects.all().order_by("name"):
        print(f"{entity.pk}\t{entity.name}\t{entity.type}\tconf={entity.confidence:.2f}")
    return 0


def cmd_graph(args: argparse.Namespace) -> int:
    _setup_django()
    from apps.knowledge.models import Entity

    qs = Entity.objects.all()
    if args.query:
        qs = qs.filter(name__icontains=args.query)
    for entity in qs:
        aliases = ", ".join(entity.aliases.values_list("alias", flat=True)) or "-"
        print(f"{entity.name} ({entity.type})")
        print(f"  confidence={entity.confidence:.2f} usage={entity.usage_count}")
        print(f"  aliases: {aliases}")
        for node in entity.flow_nodes.select_related("flow", "action")[:8]:
            print(
                f"  flow: {node.flow.name} v{node.flow.version} → {node.action or node.node_type}"
            )
        print()
    return 0


def cmd_learn(_args: argparse.Namespace) -> int:
    _setup_django()
    from apps.analytics.tasks import recompute_daily_metrics
    from apps.plugins.registry import discover_and_sync

    plugins = discover_and_sync()
    recompute_daily_metrics.delay()
    print(f"Discovered plugins: {', '.join(p.name for p in plugins) or '(none)'}")
    print("Queued daily metric recompute.")
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

    test = sub.add_parser("test", help="Execute with debug=true")
    test.add_argument("text")
    test.add_argument("--confirm", action="store_true")
    test.set_defaults(func=cmd_test)

    doctor = sub.add_parser("doctor", help="Check Postgres, Redis, Hermes, STT, host agent, shell")
    doctor.set_defaults(func=cmd_doctor)

    agent = sub.add_parser("host-agent", help="Run the host command daemon")
    agent.set_defaults(func=cmd_host_agent)

    flows = sub.add_parser("flows", help="Flow commands")
    flows_sub = flows.add_subparsers(dest="flows_cmd", required=True)
    flows_list = flows_sub.add_parser("list", help="List flows")
    flows_list.set_defaults(func=cmd_flows_list)

    entities = sub.add_parser("entities", help="Entity commands")
    entities_sub = entities.add_subparsers(dest="entities_cmd", required=True)
    entities_list = entities_sub.add_parser("list", help="List entities")
    entities_list.set_defaults(func=cmd_entities_list)

    graph = sub.add_parser("graph", help="Print entity/flow neighborhood")
    graph.add_argument("query", nargs="?", default="")
    graph.set_defaults(func=cmd_graph)

    learn = sub.add_parser("learn", help="Discover plugins and recompute metrics")
    learn.set_defaults(func=cmd_learn)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    raise SystemExit(args.func(args))
