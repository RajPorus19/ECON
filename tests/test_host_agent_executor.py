import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

from core.execution import ExecuteRequest
from core.execution.host_agent import HostAgentExecutor


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers["Content-Length"])
        body = json.loads(self.rfile.read(length))
        assert self.headers.get("Authorization") == "Bearer test-token"
        payload = json.dumps(
            {
                "success": True,
                "exit_code": 0,
                "stdout": " ".join(body["argv"]),
                "stderr": "",
                "error": "",
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def test_host_agent_executor_posts_argv() -> None:
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        executor = HostAgentExecutor(f"http://{host}:{port}", "test-token")
        result = executor.execute(ExecuteRequest(argv=["echo", "from-agent"]))
        assert result.success
        assert result.stdout == "echo from-agent"
    finally:
        server.shutdown()
