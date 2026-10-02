"""/health is what a compose healthcheck and `rbs integration-test` poll before
sending real traffic. It must answer without the Redux backend, so the fake
`redux` fixture is deliberately not requested here.
"""

import httpx
import pytest

import server

pytestmark = pytest.mark.anyio


async def test_health_answers_without_the_backend():
    app = server.mcp.streamable_http_app(host="0.0.0.0")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://mcpredux"
    ) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.text == "ok"
