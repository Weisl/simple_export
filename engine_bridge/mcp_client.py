"""Minimal stdlib-only MCP (Model Context Protocol) client.

Only implements the JSON-RPC subset simple_export's engine-verification
feature actually needs - `initialize`, `tools/list`, `tools/call` over the
MCP "Streamable HTTP" transport - not the full protocol (resources, prompts,
sampling, roots, bidirectional notifications). This keeps the addon free of
third-party dependencies, which matters for distributing it through the
Blender extension platform.
"""

import base64
import json
import urllib.error
import urllib.request


class MCPError(Exception):
    """Base class for every error this client raises."""


class MCPTransportError(MCPError):
    """The engine's MCP server could not be reached (not running, wrong
    host/port, timed out, connection refused)."""


class MCPProtocolError(MCPError):
    """The engine's MCP server responded, but with an HTTP error status or a
    JSON-RPC/tool-call error."""


_JSONRPC_VERSION = "2.0"
_PROTOCOL_VERSION = "2025-06-18"


class MCPClient:
    """A synchronous, blocking JSON-RPC-over-HTTP MCP client for a single
    engine connection. Every method may raise MCPTransportError or
    MCPProtocolError - callers are expected to catch these and translate them
    into a user-facing message rather than letting them propagate as generic
    exceptions.
    """

    def __init__(self, base_url, timeout=10.0, headers=None, client_name="simple_export",
                 client_version="0.0.0"):
        self.base_url = base_url
        self.timeout = timeout
        self._extra_headers = dict(headers or {})
        self.client_name = client_name
        self.client_version = client_version
        self._session_id = None
        self._request_id = 0

    def _next_id(self):
        self._request_id += 1
        return self._request_id

    def _post(self, payload):
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        headers.update(self._extra_headers)
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id

        request = urllib.request.Request(self.base_url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                session_id = response.headers.get("Mcp-Session-Id")
                if session_id:
                    self._session_id = session_id
                content_type = response.headers.get("Content-Type", "")
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            raise MCPProtocolError(f"HTTP {exc.code} from MCP server: {detail or exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise MCPTransportError(str(exc.reason)) from exc
        except (TimeoutError, ConnectionError, OSError) as exc:
            raise MCPTransportError(str(exc)) from exc

        return self._parse_body(raw, content_type)

    @staticmethod
    def _parse_body(raw, content_type):
        """Response body may be a plain JSON object, or an SSE stream (one or
        more `data: <json>` lines) - the spec leaves the choice to the server."""
        if "text/event-stream" in content_type:
            for line in raw.splitlines():
                line = line.strip()
                if line.startswith("data:"):
                    raw = line[len("data:"):].strip()
                    break
        try:
            return json.loads(raw)
        except (ValueError, TypeError) as exc:
            raise MCPProtocolError(f"Could not parse MCP server response as JSON: {exc}") from exc

    def _request(self, method, params=None):
        payload = {"jsonrpc": _JSONRPC_VERSION, "id": self._next_id(), "method": method}
        if params is not None:
            payload["params"] = params

        message = self._post(payload)
        if "error" in message:
            error = message["error"]
            raise MCPProtocolError(f"{method} failed: {error.get('message', error)}")
        return message.get("result", {})

    def _notify(self, method, params=None):
        """Fire-and-forget JSON-RPC notification (no `id`, no response expected)."""
        payload = {"jsonrpc": _JSONRPC_VERSION, "method": method}
        if params is not None:
            payload["params"] = params
        try:
            self._post(payload)
        except MCPError:
            pass

    def initialize(self):
        result = self._request("initialize", {
            "protocolVersion": _PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": self.client_name, "version": self.client_version},
        })
        self._notify("notifications/initialized")
        return result

    def list_tools(self):
        result = self._request("tools/list")
        return result.get("tools", [])

    def call_tool(self, name, arguments=None):
        result = self._request("tools/call", {"name": name, "arguments": arguments or {}})
        content = result.get("content", [])
        if result.get("isError"):
            raise MCPProtocolError(f"tool '{name}' reported an error: {first_text(content) or result}")
        return content


def first_text(content_blocks):
    """Return the text of the first 'text' content block, or '' if none."""
    for block in content_blocks:
        if block.get("type") == "text":
            return block.get("text", "")
    return ""


def first_image_bytes(content_blocks):
    """Return the decoded bytes of the first 'image' content block, or b'' if none."""
    for block in content_blocks:
        if block.get("type") == "image" and block.get("data"):
            return base64.b64decode(block["data"])
    return b""
