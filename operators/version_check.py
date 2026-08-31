import threading
import urllib.request
import urllib.error
import json

# Module-level state — read by the panel draw function
update_available = False
latest_version_str = ""

_RELEASES_URL = "https://api.github.com/repos/Weisl/simple_export/releases/latest"

# Set by unregister() so an in-flight background thread stops writing to the
# module globals above once the addon has been torn down.
_cancel_event = threading.Event()


def _parse_version(version_str):
    """Convert '2.1.4' or 'v2.1.4' to (2, 1, 4)."""
    return tuple(int(x) for x in version_str.lstrip("v").split("."))


def _fetch(cancel_event):
    global update_available, latest_version_str
    try:
        req = urllib.request.Request(
            _RELEASES_URL,
            headers={"User-Agent": "simple-export-addon"},
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())

        if cancel_event.is_set():
            return

        tag = data.get("tag_name", "")
        if not tag:
            return

        latest = _parse_version(tag)

        # Read current version from blender_manifest.toml at the addon root
        import os
        manifest_path = os.path.join(os.path.dirname(__file__), "..", "blender_manifest.toml")
        current_str = ""
        with open(manifest_path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("version"):
                    current_str = line.split("=")[1].strip().strip('"')
                    break

        if not current_str:
            return

        current = _parse_version(current_str)

        if cancel_event.is_set():
            return

        if latest > current:
            update_available = True
            latest_version_str = tag.lstrip("v")
        else:
            print(f"[Simple Export] Addon is up to date (v{current_str})")

    except Exception as exc:
        print(f"[Simple Export] version check failed: {exc}")


def start_version_check():
    """Fire a background thread to check for a newer release on GitHub."""
import bpy
if not bpy.app.online_access:
    return
global _cancel_event
_cancel_event = threading.Event()
t = threading.Thread(target=_fetch, args=(_cancel_event,), daemon=True)

    t.start()


def stop_version_check():
    """Signal any in-flight background thread to stop writing module globals."""
    _cancel_event.set()
