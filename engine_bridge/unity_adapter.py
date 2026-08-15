"""Adapter for Unity's official first-party MCP server (part of the
com.unity.ai.assistant package, Project Settings > AI > Unity MCP).

The tool names/argument shapes below are placeholders pending a live spike
against a running Unity Editor's `tools/list` response - Unity's public docs
describe capability categories ("scene management, asset operations, script
editing, console access") without listing exact tool names. Verify and
correct these constants against a real editor before relying on this adapter;
`discover_tools()` (inherited from EngineAdapter) is kept around specifically
for that purpose.
"""

from .engine_adapter import ConsoleMessage, EngineAdapter, ImportResult, ScreenshotResult
from .mcp_client import MCPProtocolError, first_image_bytes, first_text

# TODO(unity-spike): confirm against a running Unity Editor's tools/list.
_TOOL_IMPORT_ASSET = "assets_import"
_TOOL_CAPTURE_SCREENSHOT = "editor_capture_screenshot"
_TOOL_GET_CONSOLE_MESSAGES = "console_get_messages"


class UnityAdapter(EngineAdapter):
    engine_id = "UNITY"
    display_name = "Unity"
    is_experimental = False

    def import_asset(self, filepath):
        # A tool-level failure (isError=true, e.g. "unsupported format") is a
        # normal outcome to report as ImportResult(success=False), not an
        # exception - MCPProtocolError here must not propagate and crash the
        # verification run, only a genuine transport/protocol problem should.
        try:
            content = self.client.call_tool(_TOOL_IMPORT_ASSET, {"path": filepath})
        except MCPProtocolError as exc:
            return ImportResult(success=False, message=str(exc))
        text = first_text(content)
        return ImportResult(success=True, message=text or "Import reported success.")

    def capture_screenshot(self):
        try:
            content = self.client.call_tool(_TOOL_CAPTURE_SCREENSHOT)
        except MCPProtocolError as exc:
            return ScreenshotResult(success=False, message=str(exc))
        image_bytes = first_image_bytes(content)
        if not image_bytes:
            return ScreenshotResult(success=False, message="No image returned by the engine.")
        return ScreenshotResult(success=True, image_bytes=image_bytes)

    def get_console_messages(self):
        content = self.client.call_tool(_TOOL_GET_CONSOLE_MESSAGES)
        text = first_text(content)
        if not text:
            return []
        messages = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            level = "INFO"
            upper = line.upper()
            if upper.startswith("ERROR") or "[ERROR]" in upper:
                level = "ERROR"
            elif upper.startswith("WARNING") or "[WARNING]" in upper:
                level = "WARNING"
            messages.append(ConsoleMessage(level=level, text=line))
        return messages
