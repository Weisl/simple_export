@echo off
:: Run all simple_export unit tests.
::
:: Windows (from any directory):
::   tests\run_tests.bat
::
:: Windows (from the addon root):
::   python -m unittest discover -s tests -v
::
:: Linux / macOS (from the addon root):
::   python3 -m unittest discover -s tests -v

cd /d "%~dp0\.."
python -m unittest discover -s tests -v
