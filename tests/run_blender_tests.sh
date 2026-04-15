#!/usr/bin/env bash
# Run all headless Blender tests for simple_export.
#
# Usage (from the addon root):
#   ./tests/run_blender_tests.sh
#   ./tests/run_blender_tests.sh /path/to/blender   # override Blender path
#
# Each test file in tests/blender/ is executed in its own Blender process so
# that module-level registration side-effects cannot leak between suites.
# Exit code is non-zero if any suite fails.

set -euo pipefail

ADDON_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# ---------------------------------------------------------------------------
# Locate Blender
# ---------------------------------------------------------------------------

BLENDER="${1:-}"

if [ -z "$BLENDER" ]; then
    # Common install locations — try them in order.
    for candidate in \
        blender \
        /usr/bin/blender \
        "/home/$USER/Applications/blender-5.1.0/blender" \
        "/home/$USER/Applications/blender-5.0.1/blender" \
        "/Applications/Blender.app/Contents/MacOS/Blender" \
        "/snap/bin/blender"
    do
        if command -v "$candidate" &>/dev/null 2>&1 || [ -x "$candidate" ]; then
            BLENDER="$candidate"
            break
        fi
    done
fi

if [ -z "$BLENDER" ] || ! { command -v "$BLENDER" &>/dev/null 2>&1 || [ -x "$BLENDER" ]; }; then
    echo "ERROR: Blender not found. Pass the path as the first argument:" >&2
    echo "  $0 /path/to/blender" >&2
    exit 1
fi

echo "Using Blender: $BLENDER"
echo "Addon root:    $ADDON_ROOT"
echo ""

# ---------------------------------------------------------------------------
# Run each test file
# ---------------------------------------------------------------------------

PASS=0
FAIL=0
FAILED_FILES=()

for test_file in "$ADDON_ROOT/tests/blender"/test_*.py; do
    rel="${test_file#"$ADDON_ROOT/"}"
    echo "──────────────────────────────────────────────"
    echo "  Running: $rel"
    echo "──────────────────────────────────────────────"

    if "$BLENDER" \
        --background \
        --factory-startup \
        --python "$test_file" \
        2>&1; then
        PASS=$((PASS + 1))
    else
        FAIL=$((FAIL + 1))
        FAILED_FILES+=("$rel")
    fi
    echo ""
done

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

echo "══════════════════════════════════════════════"
echo "  Headless Blender test summary"
echo "  Passed: $PASS   Failed: $FAIL"
if [ ${#FAILED_FILES[@]} -gt 0 ]; then
    echo ""
    echo "  FAILED suites:"
    for f in "${FAILED_FILES[@]}"; do
        echo "    • $f"
    done
fi
echo "══════════════════════════════════════════════"

[ $FAIL -eq 0 ]
