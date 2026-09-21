"""The tool list and the docstrings are the LLM-facing interface. A tool that
vanishes or loses its description is a regression even if every request it
makes is still correct.
"""
import pytest

pytestmark = pytest.mark.anyio


EXPECTED_TOOLS = sorted([
    "list_problems",
    "list_solvers",
    "list_verifiers",
    "list_reductions",
    "list_visualizations",
    "find_reduction_path",
    "get_info",
    "generate_problem",
    "solve_problem",
    "verify_solution",
    "reduce_problem",
    "reduce_certificate",
    "visualize_problem",
])


async def test_tool_names(mcp_client):
    tools = (await mcp_client.list_tools()).tools
    assert sorted(t.name for t in tools) == EXPECTED_TOOLS


async def test_every_tool_has_a_description(mcp_client):
    tools = (await mcp_client.list_tools()).tools
    missing = [t.name for t in tools if not (t.description or "").strip()]
    assert not missing, f"tools without a docstring: {missing}"


async def test_every_tool_argument_is_in_the_schema(mcp_client):
    # Sanity check that MCPServer exposed the Python signatures as input schemas.
    tools = {t.name: t for t in (await mcp_client.list_tools()).tools}
    assert set(tools["verify_solution"].input_schema["properties"]) == {
        "verifier", "certificate", "problem_instance"}
    assert set(tools["reduce_certificate"].input_schema["properties"]) == {
        "reduction", "certificate", "instance"}
    assert set(tools["list_reductions"].input_schema.get("required", [])) == set()
