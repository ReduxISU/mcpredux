FROM python:3.14-slim

# uv is copied in rather than pip-installed so its version is pinned to a
# specific image digest lineage. Bump the tag to upgrade.
COPY --from=ghcr.io/astral-sh/uv:0.12.17 /uv /bin/uv

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

# Install from uv.lock only. --locked fails the build if the lock is out of
# date with pyproject.toml, so a dependency edit committed without `uv lock`
# can't silently ship the old pins. Hashes in uv.lock are verified on install.
# Dependencies are layered before server.py so a code change doesn't
# invalidate the install layer.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

COPY server.py .

ENV PATH="/app/.venv/bin:$PATH"

# Fail the build if the entrypoint can't import — a sync that resolves
# cleanly is not evidence the server runs.
RUN python -c "import server"

ENTRYPOINT ["python", "-u", "server.py"]
CMD ["--mode", "http", "--host", "0.0.0.0"]
