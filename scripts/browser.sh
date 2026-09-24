#!/bin/bash
set -e
BIN=$(find ~/.cache/ms-playwright -maxdepth 3 -name chrome -type f | grep -v headless_shell | head -1)
if [ -z "$BIN" ]; then
  BIN=$(find ~/.cache/ms-playwright -maxdepth 3 -type f \( -name chrome -o -name headless_shell \) | head -1)
fi
if [ -z "$BIN" ]; then echo "chromium not found; rerun: python -m playwright install chromium"; exit 1; fi
echo "browser: $BIN"
exec "$BIN" --headless=new --headless=new --no-first-run --no-default-browser-check --remote-debugging-port=9223 --remote-debugging-address=127.0.0.1 --user-data-dir=/tmp/airtel-collect-profile about:blank
