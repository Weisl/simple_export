"""Orchestrates a single post-export engine-verification run.

`run_verification` is a pure function: plain values in, plain dataclasses
out. It MUST NOT touch bpy.data/bpy.context - it's designed to run on a
background thread, and Blender's Python API is not thread-safe. The caller
(operators/engine_verify_ops.py) runs it in a worker thread and only touches
bpy state once the result comes back on the main thread.
"""

from dataclasses import dataclass, field

from .mcp_client import MCPClient
from .unity_adapter import UnityAdapter

_ADAPTERS = {
    "UNITY": UnityAdapter,
    # 'GODOT': GodotAdapter,   # added in Phase 2
    # 'UNREAL': UnrealAdapter, # added in Phase 3
}

# Preset-name prefix (before the first '-') -> engine_id, matching the
# convention already used by real preset names such as "Unity-fbx",
# "Godot-gltf", "UE-fbx".
_PRESET_PREFIX_TO_ENGINE = {
    "unity": "UNITY",
    "godot": "GODOT",
    "ue": "UNREAL",
    "unreal": "UNREAL",
}


class VerificationCancelled(Exception):
    """Raised internally when the caller's cancel_event is set mid-flight."""


@dataclass
class EngineVerificationResult:
    engine_id: str
    collection_name: str
    import_ok: bool
    screenshot_bytes: bytes = b""
    issues: list = field(default_factory=list)


def get_adapter_class(engine_id):
    return _ADAPTERS.get(engine_id)


def available_engine_ids():
    return list(_ADAPTERS.keys())


def guess_engine_for_collection(collection):
    """Reads collection.simple_export_export_preset (e.g. 'Unity-fbx') and
    returns the matching engine_id, or None if no prefix matches."""
    if collection is None:
        return None
    preset_name = getattr(collection, "simple_export_export_preset", "") or ""
    prefix = preset_name.split("-", 1)[0].lower()
    return _PRESET_PREFIX_TO_ENGINE.get(prefix)


def _check_cancelled(cancel_event):
    if cancel_event is not None and cancel_event.is_set():
        raise VerificationCancelled()


def run_verification(engine_id, host, port, timeout, filepath, collection_name,
                      progress_callback=None, cancel_event=None):
    """Connect to `engine_id`'s MCP server at host:port, import `filepath`,
    capture a screenshot, and read back console messages - converting import
    failures and ERROR/WARNING console messages into
    validation.checks.ValidationIssue instances so they can be shown
    alongside the addon's existing pre-export validation results.

    Raises MCPError subclasses on connection/protocol failure, and
    VerificationCancelled if cancel_event is set between stages.
    """
    # Imported lazily: validation.checks imports bpy at module scope, and
    # engine_bridge otherwise stays bpy-free for headless unit testing.
    from ..validation.checks import ValidationIssue

    adapter_class = get_adapter_class(engine_id)
    if adapter_class is None:
        raise ValueError(f"No adapter registered for engine '{engine_id}'.")

    def report(text):
        if progress_callback is not None:
            progress_callback(text)

    report("connecting...")
    _check_cancelled(cancel_event)
    client = MCPClient(f"http://{host}:{port}/mcp", timeout=timeout)
    adapter = adapter_class(client)
    adapter.connect()

    report("importing asset...")
    _check_cancelled(cancel_event)
    import_result = adapter.import_asset(filepath)

    issues = []
    if not import_result.success:
        issues.append(ValidationIssue(
            check_id="engine_import_failed",
            collection_name=collection_name,
            object_name="",
            severity="ERROR",
            message=f"{adapter.display_name} import failed: {import_result.message}",
        ))

    report("capturing screenshot...")
    _check_cancelled(cancel_event)
    screenshot_bytes = b""
    if import_result.success:
        screenshot_result = adapter.capture_screenshot()
        if screenshot_result.success:
            screenshot_bytes = screenshot_result.image_bytes
        else:
            issues.append(ValidationIssue(
                check_id="engine_screenshot_failed",
                collection_name=collection_name,
                object_name="",
                severity="WARNING",
                message=f"{adapter.display_name} screenshot failed: {screenshot_result.message}",
            ))

    report("checking console...")
    _check_cancelled(cancel_event)
    for console_message in adapter.get_console_messages():
        if console_message.level not in ("ERROR", "WARNING"):
            continue
        issues.append(ValidationIssue(
            check_id="engine_console_message",
            collection_name=collection_name,
            object_name="",
            severity=console_message.level,
            message=f"{adapter.display_name} console: {console_message.text}",
        ))

    return EngineVerificationResult(
        engine_id=engine_id,
        collection_name=collection_name,
        import_ok=import_result.success,
        screenshot_bytes=screenshot_bytes,
        issues=issues,
    )
