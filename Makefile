# Dependency lock maintenance. The Docker image installs requirements-lock.txt
# (fully pinned, hashed); requirements.txt is the human-edited input.

# lock-check uses process substitution.
SHELL := /bin/bash

# Targets linux/3.14 to match the Dockerfile base image, not the host —
# several deps ship compiled wheels.
UV = uv
LOCKFLAGS = --generate-hashes --python-version 3.14 --python-platform linux

.PHONY: lock lock-check

# Regenerate requirements-lock.txt from requirements.txt. Run after editing
# requirements.txt; commit both together.
lock: requirements-lock.txt

requirements-lock.txt: requirements.txt
	$(UV) pip compile $< -o $@ $(LOCKFLAGS)

# Fail if the lock is stale with respect to requirements.txt. Used by CI.
# The temp file is seeded with the current lock so uv keeps existing pins
# that still satisfy requirements.txt (as `make lock` would). Without the
# seed uv resolves everything to latest, and any upstream release would fail
# the check. Compiles to a temp file rather than `-o -`: uv treats `-` as a
# literal filename and litters the tree with it. The output path is echoed
# into the generated header, so that line is filtered from both sides.
lock-check:
	@tmp=$$(mktemp); trap 'rm -f "$$tmp"' EXIT; \
	 cp requirements-lock.txt "$$tmp"; \
	 $(UV) pip compile -q requirements.txt -o "$$tmp" $(LOCKFLAGS) || exit 1; \
	 diff -u <(grep -v '^#  *uv pip compile' requirements-lock.txt) \
	         <(grep -v '^#  *uv pip compile' "$$tmp") \
	   || { echo "requirements-lock.txt is stale — run 'make lock'"; exit 1; }
