"""Proxy mode bridges a stdio client to a remote HTTP MCP server, one JSON-RPC
line at a time. `_proxy_forward` handles a single line; these tests drive it
with a scripted HTTP endpoint and a BytesIO standing in for stdout.
"""
import io
import json

import httpx
import pytest

from server import _proxy_forward

pytestmark = pytest.mark.anyio


URL = "http://mcp.test/mcp"
REQUEST = b'{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'


class FakeEndpoint:
    def __init__(self):
        self.requests: list[httpx.Request] = []
        self.response = httpx.Response(200, content=b'{"jsonrpc":"2.0","id":1,"result":{}}')
        self.raise_exc = None

    def handler(self, request):
        self.requests.append(request)
        if self.raise_exc:
            raise self.raise_exc
        return self.response


@pytest.fixture
def endpoint():
    return FakeEndpoint()


@pytest.fixture
async def client(endpoint):
    async with httpx.AsyncClient(transport=httpx.MockTransport(endpoint.handler)) as c:
        yield c


def lines(out: io.BytesIO) -> list[bytes]:
    return out.getvalue().split(b"\n")[:-1]


async def test_json_response_is_written_as_one_line(client, endpoint):
    out = io.BytesIO()

    sid = await _proxy_forward(client, URL, REQUEST, None, out)

    assert lines(out) == [b'{"jsonrpc":"2.0","id":1,"result":{}}']
    assert sid is None
    req = endpoint.requests[0]
    assert req.method == "POST" and str(req.url) == URL
    assert req.content == REQUEST
    assert req.headers["content-type"] == "application/json"
    assert "text/event-stream" in req.headers["accept"]
    assert "mcp-session-id" not in req.headers


async def test_session_id_is_captured_then_echoed(client, endpoint):
    endpoint.response = httpx.Response(
        200, content=b"{}", headers={"Mcp-Session-Id": "abc123"})
    out = io.BytesIO()

    sid = await _proxy_forward(client, URL, REQUEST, None, out)
    assert sid == "abc123"

    await _proxy_forward(client, URL, REQUEST, sid, out)
    assert endpoint.requests[1].headers["mcp-session-id"] == "abc123"


async def test_accepted_notification_writes_nothing(client, endpoint):
    endpoint.response = httpx.Response(202, headers={"Mcp-Session-Id": "keep-me"})
    out = io.BytesIO()

    sid = await _proxy_forward(client, URL, REQUEST, "keep-me", out)

    assert out.getvalue() == b""
    assert sid == "keep-me"


async def test_sse_data_lines_are_unwrapped(client, endpoint):
    sse = (
        b"event: message\n"
        b'data: {"jsonrpc":"2.0","id":1,"result":{"a":1}}\n'
        b"\n"
        b": keep-alive comment\n"
        b'data: {"jsonrpc":"2.0","method":"notifications/progress"}\n'
        b"\n"
        b"data: [DONE]\n"
    )
    endpoint.response = httpx.Response(
        200, content=sse, headers={"content-type": "text/event-stream"})
    out = io.BytesIO()

    await _proxy_forward(client, URL, REQUEST, None, out)

    assert lines(out) == [
        b'{"jsonrpc":"2.0","id":1,"result":{"a":1}}',
        b'{"jsonrpc":"2.0","method":"notifications/progress"}',
    ]


async def test_transport_failure_becomes_jsonrpc_error(client, endpoint):
    endpoint.raise_exc = httpx.ConnectError("connection refused")
    out = io.BytesIO()

    sid = await _proxy_forward(client, URL, REQUEST, "s1", out)

    assert sid == "s1"
    [line] = lines(out)
    err = json.loads(line)
    assert err["jsonrpc"] == "2.0"
    assert err["error"]["code"] == -32603
    assert "connection refused" in err["error"]["message"]


async def test_empty_body_writes_nothing(client, endpoint):
    endpoint.response = httpx.Response(200, content=b"  \n")
    out = io.BytesIO()

    await _proxy_forward(client, URL, REQUEST, None, out)

    assert out.getvalue() == b""
