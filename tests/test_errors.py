"""The load-bearing contract (see CLAUDE.md, "Don't absorb error signals"):
a backend error must reach the client as a tool result with isError=True and
the backend body intact. A well-meaning try/except that returns the body as a
plain string would keep the text but drop the signal; these tests fail on it.
"""
import json

import pytest

from _util import text_of

pytestmark = pytest.mark.anyio


# Shape of the structured 400 Redux returns for a malformed reduction input
# (TODO.md §4). The content is the contract: the LLM needs `expected_example`
# and `hint` verbatim to self-correct.
INPUT_SHAPE_MISMATCH = json.dumps({
    "error": "input_shape_mismatch",
    "reduction": "SipserReduceToCliqueStandard",
    "expected_example": "(x1:True,x2:False,...)",
    "received": "{x1_0,x2_1,!x3_3}",
    "hint": "This input looks like a CLIQUE certificate. "
            "Use reduction=SipserReduceToSAT3 to map in that direction.",
})


async def test_backend_400_is_a_tool_error_with_body(mcp_client, redux):
    redux.respond(400, INPUT_SHAPE_MISMATCH)

    result = await mcp_client.call_tool("reduce_certificate", {
        "reduction": "SipserReduceToCliqueStandard",
        "certificate": "{x1_0,x2_1,!x3_3}",
        "instance": "(x1 | !x2 | x3)",
    })

    assert result.isError
    assert INPUT_SHAPE_MISMATCH in text_of(result)


async def test_backend_500_is_a_tool_error_with_body(mcp_client, redux):
    redux.respond(500, "System.NullReferenceException: Object reference not set")

    result = await mcp_client.call_tool("solve_problem",
                                        {"solver": "CliqueBruteForce", "instance": "{}"})

    assert result.isError
    assert "NullReferenceException" in text_of(result)


@pytest.mark.parametrize("status", [400, 404, 500, 502])
async def test_get_tools_surface_errors_too(mcp_client, redux, status):
    redux.respond(status, f"backend said {status}")

    result = await mcp_client.call_tool("get_info", {"interface": "NOPE"})

    assert result.isError
    assert f"backend said {status}" in text_of(result)


async def test_success_is_not_an_error(mcp_client, redux):
    redux.respond(200, "true")

    result = await mcp_client.call_tool("verify_solution", {
        "verifier": "CliqueVerifier", "certificate": "{1,2}", "problem_instance": "{}"})

    assert not result.isError
    assert text_of(result) == "true"


async def test_helpers_raise_rather_than_return(redux):
    # The unit-level half of the contract: the helpers themselves raise.
    import server
    redux.respond(400, "bad request body")

    with pytest.raises(RuntimeError, match="bad request body"):
        await server._get("/x")
    with pytest.raises(RuntimeError, match="bad request body"):
        await server._post("/x", "body")


async def test_bad_arguments_never_reach_the_backend(mcp_client, redux):
    # FastMCP validates the schema before the tool body runs.
    result = await mcp_client.call_tool("solve_problem", {"solver": "X"})  # missing instance

    assert result.isError
    assert redux.requests == []
