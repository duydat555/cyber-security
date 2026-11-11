#!/usr/bin/env bash
# Render a text file as a terminal-style screenshot PNG (height auto-fit to content).
# Usage: term2png.sh <input.txt> <output.png> "<title>"
IN="$1"; OUT="$2"; TITLE="${3:-Terminal}"
# estimate height: count display lines (wrap long lines at ~110 cols)
LINES=$(awk '{n=int((length($0))/110)+1; t+=n} END{print t+4}' "$IN")
H=$(( LINES * 22 + 90 )); [ "$H" -lt 160 ] && H=160; [ "$H" -gt 4000 ] && H=4000
HTML="$(mktemp /tmp/term2png.XXXXXX.html)"
{
  echo '<!doctype html><html><head><meta charset="utf-8"><style>'
  echo 'html,body{margin:0;background:#1e1e1e;font-family:"SFMono-Regular",Menlo,Consolas,monospace}'
  echo '.win{margin:14px;border-radius:8px;overflow:hidden;border:1px solid #333}'
  echo '.bar{background:#323233;padding:8px 12px;color:#ccc;font:13px sans-serif}'
  echo '.dot{height:12px;width:12px;border-radius:50%;display:inline-block;margin-right:6px;vertical-align:middle}'
  echo 'pre{margin:0;padding:14px 16px;background:#1e1e1e;color:#d4d4d4;font-size:13px;line-height:1.45;white-space:pre-wrap;word-break:break-word}'
  echo '</style></head><body><div class="win"><div class="bar">'
  echo '<span class="dot" style="background:#ff5f56"></span><span class="dot" style="background:#ffbd2e"></span><span class="dot" style="background:#27c93f"></span>'
  printf '  %s</div><pre>' "$(printf '%s' "$TITLE" | sed 's/&/\&amp;/g;s/</\&lt;/g;s/>/\&gt;/g')"
  sed 's/&/\&amp;/g;s/</\&lt;/g;s/>/\&gt;/g' "$IN"
  echo '</pre></div></body></html>'
} > "$HTML"
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu \
  --hide-scrollbars --force-device-scale-factor=2 --window-size="1120,${H}" \
  --virtual-time-budget=1500 --screenshot="$OUT" "file://$HTML" >/dev/null 2>&1
rm -f "$HTML"
[ -s "$OUT" ] && echo "OK -> $OUT (${H}px, $(du -h "$OUT"|cut -f1))" || echo "FAILED -> $OUT"
