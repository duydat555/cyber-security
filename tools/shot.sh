#!/usr/bin/env bash
# Usage: shot.sh <url> <output.png> [wait_ms] [width] [height]
URL="$1"; OUT="$2"; WAIT="${3:-5000}"; W="${4:-1366}"; H="${5:-900}"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
"$CHROME" --headless=new --disable-gpu --no-sandbox --hide-scrollbars \
  --force-device-scale-factor=1 --window-size="${W},${H}" \
  --virtual-time-budget="${WAIT}" --screenshot="$OUT" "$URL" >/dev/null 2>&1
if [ -s "$OUT" ]; then echo "OK -> $OUT ($(du -h "$OUT" | cut -f1))"; else echo "FAILED: $OUT"; fi
