FROM python:3.14-slim

WORKDIR /app

# Install the fully-pinned, hashed lock rather than requirements.txt so the
# image is reproducible and the weekly rebuild picks up base-image updates
# only. Regenerate the lock with `make lock`.
COPY requirements-lock.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements-lock.txt

COPY server.py .

# Fail the build if the entrypoint can't import — a pip install that resolves
# cleanly is not evidence the server runs.
RUN python -c "import server"

ENTRYPOINT ["python", "-u", "server.py"]
CMD ["--mode", "http", "--host", "0.0.0.0"]
