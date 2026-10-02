"""Integration tests: the built image serving MCP over HTTP.

Nothing here imports server.py. tests/ drives the MCPServer in-process; this suite only knows a
URL, so it exercises the image's own CMD — python:3.14-slim, the locked install, uvicorn, and
the http transport — the way a deployed client does. Hermetic by design: tools/list never
contacts the Redux backend, so there is nothing else to stand up.

`rbs integration-test` reaches the container by its network alias, so every request here
arrives with a non-localhost Host header. That is the case mcp 2.x's DNS-rebinding protection
answers 421 to when `streamable_http_app()` is left on its 127.0.0.1 default — the regression
test_image_smoke.sh was written for — and this suite fails the same way.
"""

import httpx
import pytest
from mcp import Client

TIMEOUT = 20

# The tools a client has to be able to see for the server to be any use at all.
REQUIRED_TOOLS = {"list_problems", "solve_problem", "verify_solution", "reduce_problem"}

INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "integration", "version": "0"},
    },
}


def test_health(base_url):
    """GET /health answers ok — the same route rbs polls for readiness."""
    resp = httpx.get(f"{base_url}/health", timeout=TIMEOUT)
    assert resp.status_code == 200
    assert resp.text == "ok"


def test_external_host_header_is_accepted(base_url):
    """A 421 here means the server is back on its localhost default and locked out."""
    resp = httpx.post(
        f"{base_url}/mcp",
        headers={
            "Host": "mcpredux.example.test",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
        json=INITIALIZE,
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, resp.text


@pytest.mark.anyio
async def test_tools_are_listed_over_http(base_url):
    """A real MCP client session, end to end through the streamable-http transport."""
    async with Client(f"{base_url}/mcp") as session:
        tools = {t.name for t in (await session.list_tools()).tools}
    missing = REQUIRED_TOOLS - tools
    assert not missing, f"missing expected tools: {sorted(missing)}"
