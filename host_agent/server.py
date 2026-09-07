"""Host-side command daemon.

Runs on the Mac/Linux host so a Dockerized ECON API can still launch
desktop applications. Binds loopback by default; Docker Desktop forwards
host.docker.internal to that loopback port.
"""

from __future__ import annotations

import json
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from core.config import env_int, env_str


def _check_token(header_value: str, expected: str) -> bool:
    if not expected:
        return False
    prefix = "Bearer "
    if not header_value.startswith(prefix):
        return False
    provided = header_value[len(prefix) :].encode()
    wanted = expected.encode()
    if len(provided) != len(wanted):
        return False
    result = 0
    for left, right in zip(provided, wanted, strict=True):
        result |= left ^ right
    return result == 0


class HostAgentHandler(BaseHTTPRequestHandler):
    token = ""

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return

    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _unauthorized(self) -> None:
        self._send(401, {"error": "unauthorized"})

    def do_GET(self) -> None:  # noqa: N802
        if not _check_token(self.headers.get("Authorization", ""), self.token):
            self._unauthorized()
            return
        path = urlparse(self.path).path
        if path == "/v1/health":
            self._send(200, {"status": "ok", "service": "econom-host-agent"})
            return
        self._send(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if not _check_token(self.headers.get("Authorization", ""), self.token):
            self._unauthorized()
            return
        path = urlparse(self.path).path
        if path != "/v1/exec":
            self._send(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode() or "{}")
        except json.JSONDecodeError:
            self._send(400, {"error": "invalid json"})
            return
        argv = data.get("argv")
        valid_argv = isinstance(argv, list) and argv and all(isinstance(p, str) and p for p in argv)
        if not valid_argv:
            self._send(400, {"error": "argv must be a non-empty list of strings"})
            return
        timeout_s = float(data.get("timeout_s") or 30)
        cwd = data.get("cwd")
        if cwd is not None and not isinstance(cwd, str):
            self._send(400, {"error": "cwd must be a string"})
            return
        try:
            completed = subprocess.run(  # noqa: S603
                argv,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                cwd=cwd,
                shell=False,
                check=False,
            )
        except FileNotFoundError:
            self._send(
                200,
                {
                    "success": False,
                    "exit_code": 127,
                    "stdout": "",
                    "stderr": "",
                    "error": f"executable not found: {argv[0]}",
                },
            )
            return
        except subprocess.TimeoutExpired:
            self._send(
                200,
                {
                    "success": False,
                    "exit_code": None,
                    "stdout": "",
                    "stderr": "",
                    "error": "timeout",
                },
            )
            return
        self._send(
            200,
            {
                "success": completed.returncode == 0,
                "exit_code": completed.returncode,
                "stdout": completed.stdout[-8000:],
                "stderr": completed.stderr[-8000:],
                "error": "",
            },
        )


def serve(bind: str | None = None, port: int | None = None, token: str | None = None) -> None:
    bind = bind or env_str("ECON_HOST_AGENT_BIND", "127.0.0.1")
    port = port if port is not None else env_int("ECON_HOST_AGENT_PORT", 8765)
    token = token if token is not None else env_str("ECON_HOST_AGENT_TOKEN")
    if not token:
        raise SystemExit("ECON_HOST_AGENT_TOKEN is required")
    HostAgentHandler.token = token
    server = ThreadingHTTPServer((bind, port), HostAgentHandler)
    print(f"econom-host-agent listening on {bind}:{port}", flush=True)
    server.serve_forever()


def main() -> None:
    from dotenv import load_dotenv

    load_dotenv()
    serve()
