#!/bin/sh
# Run all simple_export unit tests.
#
# Linux / macOS (from the addon root):
#   python3 -m unittest discover -s tests -v

cd "$(dirname "$0")/.."
python3 -m unittest discover -s tests -v