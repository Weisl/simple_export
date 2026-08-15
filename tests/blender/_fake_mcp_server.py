"""A real, local stdlib HTTP server speaking a minimal MCP JSON-RPC subset,
for testing engine_bridge.mcp_client.MCPClient and the per-engine adapters
without a live game engine running.

Usage:

    def handle_tools_call(params):
        assert params['name'] == 'assets_import'
        return {"content": [{"type": "text", "text": "ok"}]}

    with FakeMCPServer({'tools/call': handle_tools_call}) as server:
        client = MCPClient(server.url)
        ...
"""

import http.server
import json
import threading


class RouteError(Exception):
    """Raised by a route handler to simulate a JSON-RPC error response."""


class FakeMCPServer:
    def __init__(self, routes):
        self.routes = dict(routes)
        self._server = http.server.HTTPServer(('127.0.0.1', 0), self._make_handler())
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)

    @property
    def url(self):
        _, port = self._server.server_address
        return f"http://127.0.0.1:{port}/mcp"

    def _make_handler(self):
        routes = self.routes

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass  # keep test output quiet

            def do_POST(self):
                length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(length)
                try:
                    message = json.loads(body.decode('utf-8'))
                except ValueError:
                    self.send_response(400)
                    self.end_headers()
                    return

                method = message.get('method')
                msg_id = message.get('id')

                if msg_id is None:
                    # Notification (e.g. notifications/initialized) - no response body.
                    self.send_response(200)
                    self.end_headers()
                    return

                handler = routes.get(method)
                if handler is None:
                    response = {
                        "jsonrpc": "2.0", "id": msg_id,
                        "error": {"code": -32601, "message": f"Method not found: {method}"},
                    }
                else:
                    try:
                        result = handler(message.get('params') or {})
                        response = {"jsonrpc": "2.0", "id": msg_id, "result": result}
                    except RouteError as exc:
                        response = {
                            "jsonrpc": "2.0", "id": msg_id,
                            "error": {"code": -32000, "message": str(exc)},
                        }

                payload = json.dumps(response).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        return Handler
