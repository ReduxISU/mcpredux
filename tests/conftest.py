"""Shared fixtures.

`redux` replaces the server's HTTP client with one whose transport is a
scripted stand-in for the Redux backend: no network, every request recorded,
one configurable canned response. `mcp_client` connects a real MCP client
session to the MCPServer in-process, so tool calls go through the same
argument validation and exception-to-is_error conversion the LLM sees.
"""
import httpx
import pytest
from mcp import Client

import server


@pytest.fixture
def anyio_backend():
    return "asyncio"


class FakeRedux:
    """Records requests and returns a canned response.

    The response body is deliberately a sentinel by default: the server passes
    backend bodies through untouched, so tests assert on what was *sent*, and
    only set a realistic body where its content is the contract (errors).
    """

    def __init__(self):
        self.requests: list[httpx.Request] = []
        self.status = 200
        self.text = "canned-redux-response"

    def respond(self, status: int, text: str) -> None:
        self.status = status
        self.text = text

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(self.status, text=self.text)

    @property
    def last(self) -> httpx.Request:
        assert self.requests, "no request reached the fake backend"
        return self.requests[-1]


@pytest.fixture
async def redux(monkeypatch):
    fake = FakeRedux()
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(fake.handler),
        base_url="http://redux.test",
    ) as client:
        monkeypatch.setattr(server, "_client", client)
        yield fake


@pytest.fixture
async def mcp_client(redux):
    async with Client(server.mcp) as session:
        yield session
