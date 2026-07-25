"""
Headless Blender tests for the background version-check thread lifecycle.

Run with:
    blender --background --python tests/blender/test_version_check.py

Regression coverage for https://github.com/Weisl/simple_export/issues/306,
issue 6: start_version_check() fires a daemon thread that writes module-level
globals (update_available, latest_version_str). Before the fix there was no
way to tell that thread to stop, so it could still write those globals after
the addon was unregistered (e.g. during rapid enable/disable or test
teardown).

Covers:
  TestFetchRespectsCancelEvent
    - _fetch() must not write globals once the cancel event is set, even when
      the (mocked) HTTP response reports a newer version.
    - _fetch() must still update globals normally when never cancelled
      (regression guard for the happy path).

  TestStartStopVersionCheck
    - start_version_check() launches exactly one background thread.
    - stop_version_check() signals a fetch that is already blocked inside
      urlopen(); once the mocked response unblocks, the thread must not have
      written to the module globals.
"""

import json
import os
import sys
import threading
import unittest
from unittest import mock

import bpy  # noqa: F401  (kept for consistency with the other headless suites)

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
_TESTS_DIR = os.path.dirname(_FILE_DIR)
_ADDON_ROOT = os.path.dirname(_TESTS_DIR)
_EXTENSIONS_ROOT = os.path.dirname(_ADDON_ROOT)
if _EXTENSIONS_ROOT not in sys.path:
    sys.path.insert(0, _EXTENSIONS_ROOT)
if _ADDON_ROOT not in sys.path:
    sys.path.insert(0, _ADDON_ROOT)

import simple_export.operators.version_check as vc  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FakeResponse:
    """Minimal stand-in for the object returned by urllib.request.urlopen()."""

    def __init__(self, payload, on_enter=None):
        self._payload = payload
        self._on_enter = on_enter

    def __enter__(self):
        if self._on_enter:
            self._on_enter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def read(self):
        return self._payload


def _payload(tag):
    return json.dumps({"tag_name": tag}).encode()


class _VersionCheckTestBase(unittest.TestCase):
    """Snapshot and restore the module globals mutated by _fetch()."""

    def setUp(self):
        self._orig_update_available = vc.update_available
        self._orig_latest_version_str = vc.latest_version_str
        self._orig_cancel_event = vc._cancel_event
        vc.update_available = False
        vc.latest_version_str = ""

    def tearDown(self):
        vc.update_available = self._orig_update_available
        vc.latest_version_str = self._orig_latest_version_str
        vc._cancel_event = self._orig_cancel_event


# ---------------------------------------------------------------------------
# _fetch() honours the cancel event
# ---------------------------------------------------------------------------

class TestFetchRespectsCancelEvent(_VersionCheckTestBase):
    def test_fetch_does_not_write_globals_once_cancelled(self):
        """A response that would normally report an update must be ignored once cancelled."""
        event = threading.Event()
        event.set()  # simulate unregister() having already happened

        with mock.patch("urllib.request.urlopen", return_value=_FakeResponse(_payload("v999.0.0"))):
            vc._fetch(event)

        self.assertFalse(vc.update_available, "update_available must not be set after cancellation")
        self.assertEqual(vc.latest_version_str, "", "latest_version_str must not be written after cancellation")

    def test_fetch_updates_globals_when_not_cancelled(self):
        """Regression guard: the happy path must still work when the event is never set."""
        event = threading.Event()

        with mock.patch("urllib.request.urlopen", return_value=_FakeResponse(_payload("v999.0.0"))):
            vc._fetch(event)

        self.assertTrue(vc.update_available)
        self.assertEqual(vc.latest_version_str, "999.0.0")


# ---------------------------------------------------------------------------
# start_version_check() / stop_version_check() wiring
# ---------------------------------------------------------------------------

class TestStartStopVersionCheck(_VersionCheckTestBase):
    def test_stop_prevents_write_from_thread_blocked_in_flight(self):
        """A fetch already inside urlopen() must not write after stop_version_check()."""
        reached_urlopen = threading.Event()
        release_response = threading.Event()

        def _on_enter():
            reached_urlopen.set()
            release_response.wait(timeout=5)

        response = _FakeResponse(_payload("v999.0.0"), on_enter=_on_enter)

        threads_before = set(threading.enumerate())
        with mock.patch("urllib.request.urlopen", return_value=response):
            vc.start_version_check()

            new_threads = set(threading.enumerate()) - threads_before
            self.assertEqual(len(new_threads), 1, "start_version_check() must launch exactly one thread")
            worker = new_threads.pop()

            self.assertTrue(reached_urlopen.wait(timeout=5), "fetch thread never reached urlopen()")

            # Simulate the addon being unregistered while the request is in flight.
            vc.stop_version_check()
            release_response.set()

            worker.join(timeout=5)
            self.assertFalse(worker.is_alive(), "fetch thread did not finish in time")

        self.assertFalse(
            vc.update_available,
            "background thread wrote update_available after stop_version_check() was called",
        )
        self.assertEqual(vc.latest_version_str, "")

    def test_start_version_check_updates_globals_when_never_stopped(self):
        """Regression guard: without a stop signal, the thread must still report an update."""
        with mock.patch("urllib.request.urlopen", return_value=_FakeResponse(_payload("v999.0.0"))):
            threads_before = set(threading.enumerate())
            vc.start_version_check()
            worker = (set(threading.enumerate()) - threads_before).pop()
            worker.join(timeout=5)

        self.assertTrue(vc.update_available)
        self.assertEqual(vc.latest_version_str, "999.0.0")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
