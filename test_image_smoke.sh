#!/usr/bin/env bash
#
# test_image_smoke.sh — prove a built image actually starts and serves MCP.
#
# A clean `pip install` is not evidence the server runs: mcp 2.0.0 removed
# `mcp.server.fastmcp`, which resolved and installed fine, then failed at
# import. This speaks MCP to the container and confirms it enumerates tools.
#
# Both transports are checked. stdio alone is not enough: mcp 2.x auto-enables
# DNS-rebinding protection when `streamable_http_app()` keeps its 127.0.0.1
# default, which answers 421 to every request carrying a non-localhost Host
# header — invisible to a stdio test, fatal to the image's own CMD.
#
# Hermetic by design — tools/list never contacts the Redux backend, so this is
# safe to gate CI on. For end-to-end coverage against a live Redux, use
# test_docker.sh instead.
#
# Usage:
#   ./test_image_smoke.sh [IMAGE]      # IMAGE defaults to mcpredux

set -euo pipefail

IMAGE="${1:-mcpredux}"

echo "==> Smoke testing $IMAGE"

RESPONSE=$( { printf '%s\n%s\n%s\n' \
    '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke","version":"0.1"}}}' \
    '{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}' \
    '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
    # keep stdin open long enough for asyncio to drain its write buffer
    sleep 3; } | docker run -i --rm "$IMAGE" --mode stdio 2>/dev/null )

# The checker reads the captured responses on stdin, so its source has to come
# from -c rather than a heredoc (which would occupy stdin itself).
echo "$RESPONSE" | python3 -c "$(cat <<'PY'
import json
import sys

REQUIRED = ("list_problems", "solve_problem", "verify_solution", "reduce_problem")

tools = None
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        msg = json.loads(line)
    except json.JSONDecodeError:
        sys.exit(f"FAIL: non-JSON line from container: {line[:200]}")
    if msg.get("id") == 2:
        if "error" in msg:
            sys.exit(f"FAIL: tools/list returned an error: {msg['error']}")
        tools = msg["result"]["tools"]

if not tools:
    sys.exit("FAIL: no tools/list response — the container did not start")

names = sorted(t["name"] for t in tools)
print(f"{len(names)} tools: {', '.join(names)}")

missing = [t for t in REQUIRED if t not in names]
if missing:
    sys.exit(f"FAIL: missing expected tools: {', '.join(missing)}")

print("PASS: image starts and serves tools/list")
PY
)"


# ── http mode ─────────────────────────────────────────────────────────────────
#
# The image's CMD binds 0.0.0.0, so the request that matters is one arriving
# with somebody else's Host header. A 421 here means streamable_http_app() is
# back on its localhost default and external clients are locked out.

echo "==> Smoke testing $IMAGE in http mode"

CID=$(docker run -d --rm -p 127.0.0.1:0:8000 "$IMAGE" --mode http --host 0.0.0.0 --port 8000)
trap 'docker rm -f "$CID" >/dev/null 2>&1 || true' EXIT

PORT=$(docker port "$CID" 8000/tcp | head -n1 | sed 's/.*://')
[ -n "$PORT" ] || { echo "FAIL: container published no port"; exit 1; }

for _ in $(seq 1 40); do
    curl -sf -o /dev/null "http://127.0.0.1:$PORT/mcp" && break
    sleep 0.25
done

INIT='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke","version":"0.1"}}}'

CODE=$(curl -s -o /dev/null -w '%{http_code}' -X POST "http://127.0.0.1:$PORT/mcp" \
    -H 'Host: mcpredux.example.test' \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json, text/event-stream' \
    -d "$INIT")

if [ "$CODE" = "421" ]; then
    echo "FAIL: http mode returned 421 to an external Host header."
    echo "      streamable_http_app() needs host=args.host — see server.py main()."
    exit 1
fi

[ "$CODE" = "200" ] || { echo "FAIL: http initialize returned HTTP $CODE, want 200"; exit 1; }

echo "PASS: http mode accepts an external Host header"
