"""Common interface every per-engine MCP adapter implements.

Keeps engine-specific tool names/argument shapes isolated in one adapter
module per engine, so the orchestration code in verification.py and the
Blender-facing operator/UI code never need to know which engine they're
talking to.
"""

from dataclasses import dataclass, field


@dataclass
class ImportResult:
    success: bool
    message: str = ""
    imported_path: str = ""  # engine-side identifier, if the tool returns one


@dataclass
class ScreenshotResult:
    success: bool
    image_bytes: bytes = b""
    mime_type: str = "image/png"
    message: str = ""


@dataclass
class ConsoleMessage:
    level: str  # 'ERROR' | 'WARNING' | 'INFO'
    text: str


@dataclass
class EngineAdapter:
    """Base class for a single engine's MCP tool mapping. Subclasses only need
    to override the three methods below plus the class attributes."""

    client: object = field(repr=False)

    engine_id = ""
    display_name = ""
    is_experimental = False

    def connect(self):
        self.client.initialize()

    def import_asset(self, filepath):
        raise NotImplementedError

    def capture_screenshot(self):
        raise NotImplementedError

    def get_console_messages(self):
        raise NotImplementedError

    def discover_tools(self):
        """Diagnostic helper - dumps the engine's actual tools/list response.
        Useful when a vendor renames/changes a tool this adapter relies on."""
        return self.client.list_tools()
