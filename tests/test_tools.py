"""Every tool is a thin mapping from arguments to a Redux request. These tests
pin that mapping: path, query parameters, and body. Tools are called through
the MCP client so the argument names under test are the ones the LLM uses.
"""
import json

import pytest

from _util import text_of

pytestmark = pytest.mark.anyio


GET_CASES = [
    ("list_problems", {}, "/Navigation/ALL_ProblemsRefactor", {}),
    ("list_solvers", {"problem": "CLIQUE"},
     "/Navigation/Problem_SolversRefactor", {"chosenProblem": "CLIQUE"}),
    ("list_verifiers", {"problem": "CLIQUE"},
     "/Navigation/Problem_VerifiersRefactor", {"chosenProblem": "CLIQUE"}),
    ("list_visualizations", {"problem": "CLIQUE"},
     "/Navigation/Problem_VisualizationsRefactor", {"chosenProblem": "CLIQUE"}),
    ("list_reductions", {}, "/Navigation/Reductions", {}),
    ("list_reductions", {"source": "SAT3"},
     "/Navigation/Reductions", {"source": "SAT3"}),
    ("list_reductions", {"target": "CLIQUE"},
     "/Navigation/Reductions", {"target": "CLIQUE"}),
    ("list_reductions", {"source": "SAT3", "target": "CLIQUE"},
     "/Navigation/Reductions", {"source": "SAT3", "target": "CLIQUE"}),
    ("find_reduction_path", {"reducing_from": "SAT3", "reducing_to": "CLIQUE"},
     "/Navigation/NPC_NavGraph/reductionPath",
     {"reducingFrom": "SAT3", "reducingTo": "CLIQUE"}),
    ("get_info", {"interface": "SAT3"}, "/ProblemProvider/info", {"interface": "SAT3"}),
    # generate_problem: defaults, explicit args, case-insensitive type, k=0 kept.
    ("generate_problem", {}, "/ProblemGenerator/UndirectedGraph",
     {"n": "5", "density": "50", "k": "-1"}),
    ("generate_problem", {"problem_type": "directed-graph", "n": 8, "density": 30, "k": 0},
     "/ProblemGenerator/DirectedGraph", {"n": "8", "density": "30", "k": "0"}),
    ("generate_problem", {"problem_type": "SAT3", "n": 4, "c": 7},
     "/ProblemGenerator/Sat3", {"n": "4", "c": "7"}),
    ("generate_problem", {"problem_type": "sat3"},
     "/ProblemGenerator/Sat3", {"n": "3", "c": "3"}),
]


@pytest.mark.parametrize("tool,args,path,params", GET_CASES,
                         ids=[f"{c[0]}:{c[1]}" for c in GET_CASES])
async def test_get_tools_send_expected_request(mcp_client, redux, tool, args, path, params):
    result = await mcp_client.call_tool(tool, args)

    assert not result.is_error
    req = redux.last
    assert req.method == "GET"
    assert req.url.path == path
    assert dict(req.url.params) == params


INSTANCE = "{{1,2,3},{{1,2},{2,3}}}"

POST_CASES = [
    ("solve_problem", {"solver": "CliqueBruteForce", "instance": INSTANCE},
     "/ProblemProvider/solve", {"solver": "CliqueBruteForce"}, INSTANCE),
    ("reduce_problem", {"reduction": "SipserReduceToCliqueStandard", "instance": INSTANCE},
     "/ProblemProvider/reduce", {"reduction": "SipserReduceToCliqueStandard"}, INSTANCE),
    ("visualize_problem", {"visualization": "CliqueGraph", "instance": INSTANCE},
     "/ProblemProvider/visualize", {"visualization": "CliqueGraph"}, INSTANCE),
    # The certificate travels as the `solution` query param; the instance is the body.
    ("reduce_certificate",
     {"reduction": "SipserReduceToCliqueStandard", "certificate": "(x1:True)", "instance": INSTANCE},
     "/ProblemProvider/mapSolution",
     {"reduction": "SipserReduceToCliqueStandard", "solution": "(x1:True)"}, INSTANCE),
    # verify wraps both inputs in a camelCase JSON object.
    ("verify_solution",
     {"verifier": "CliqueVerifier", "certificate": "{1,2}", "problem_instance": INSTANCE},
     "/ProblemProvider/verify", {"verifier": "CliqueVerifier"},
     {"certificate": "{1,2}", "problemInstance": INSTANCE}),
]


@pytest.mark.parametrize("tool,args,path,params,body", POST_CASES,
                         ids=[c[0] for c in POST_CASES])
async def test_post_tools_send_expected_request(mcp_client, redux, tool, args, path, params, body):
    result = await mcp_client.call_tool(tool, args)

    assert not result.is_error
    req = redux.last
    assert req.method == "POST"
    assert req.url.path == path
    assert dict(req.url.params) == params
    assert req.headers["content-type"] == "application/json"
    assert json.loads(req.content) == body


async def test_backend_body_passes_through_unchanged(mcp_client, redux):
    redux.respond(200, '{"problems": ["SAT3", "CLIQUE"]}')

    result = await mcp_client.call_tool("list_problems", {})

    assert not result.is_error
    assert text_of(result) == '{"problems": ["SAT3", "CLIQUE"]}'


async def test_each_call_makes_exactly_one_request(mcp_client, redux):
    await mcp_client.call_tool("list_problems", {})
    await mcp_client.call_tool("get_info", {"interface": "SAT3"})

    assert [r.url.path for r in redux.requests] == [
        "/Navigation/ALL_ProblemsRefactor",
        "/ProblemProvider/info",
    ]
