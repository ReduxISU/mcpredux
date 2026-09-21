# mcpredux

A [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server
that exposes the [Redux](https://redux.portneuf.cose.isu.edu/) algorithms
API as tools for AI assistants. Redux provides solvers, verifiers, and
polynomial reductions for a wide range of computational complexity
problems including NP-Complete, NP-Hard, and P-class problems.

## Tools

| Tool | Description |
|---|---|
| `list_problems` | List all problems, regardless of complexity class |
| `list_solvers` | List solvers available for a given problem |
| `list_verifiers` | List verifiers available for a given problem |
| `list_reductions` | List reductions available from a given problem |
| `list_visualizations` | List visualizations available for a given problem |
| `find_reduction_path` | Find the chain of reductions between two NP-Complete problems |
| `get_info` | Get detailed info about any named object (problem, solver, verifier, reduction) |
| `generate_problem` | Generate a random problem instance (undirected graph, directed graph, or 3SAT) |
| `solve_problem` | Solve a problem instance using a named solver |
| `verify_solution` | Check whether a solution certificate is valid for a problem instance |
| `reduce_problem` | Reduce a problem instance to another problem via a named reduction |
| `reduce_certificate` | Map a solution certificate through a reduction (source → target direction) |
| `visualize_problem` | Get the visualization of a problem instance |

## Setup

Requires [uv](https://docs.astral.sh/uv/). It installs a Python interpreter
if needed (the version in `.python-version`) and creates `.venv` from the
lock file:

```sh
uv sync
```

Dependencies are declared in `pyproject.toml` and pinned in `uv.lock`. After
changing `pyproject.toml`, run `uv lock` and commit both files together; CI
and the Docker build fail if the lock is stale.

## Modes

### stdio (default)

Runs as a local MCP server over stdin/stdout. Used when the client and
server are on the same machine.

```sh
uv run server.py [--base-url URL]
```

Claude Desktop / Claude Code config:

```json
{
  "mcpServers": {
    "redux": {
      "command": "uv",
      "args": ["--directory", "/path/to/mcpredux", "run", "server.py"]
    }
  }
}
```

### http

Runs as an HTTP server (streamable-HTTP MCP transport) suitable for
deployment behind a reverse proxy such as nginx.

```sh
uv run server.py --mode http [--host 127.0.0.1] [--port 8000]
```

Claude Code config (supports remote HTTP natively):

```json
{
  "mcpServers": {
    "redux": {
      "type": "http",
      "url": "https://your-server/mcp"
    }
  }
}
```

### proxy

Bridges Claude Desktop (stdio only) to a remote HTTP MCP server.
Claude Desktop spawns this process locally; it forwards all traffic
to the remote server.

```sh
uv run server.py --mode proxy --proxy-url https://your-server/mcp
```

Claude Desktop config:

```json
{
  "mcpServers": {
    "redux": {
      "command": "uv",
      "args": [
        "--directory", "/path/to/mcpredux", "run", "server.py",
        "--mode", "proxy",
        "--proxy-url", "https://your-server/mcp"
      ]
    }
  }
}
```

## Dependencies

- [mcp](https://github.com/modelcontextprotocol/python-sdk) — official Python MCP SDK (FastMCP)
- [httpx](https://www.python-httpx.org) — async HTTP client
- [uvicorn](https://www.uvicorn.org) — ASGI server (http mode)
