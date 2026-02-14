# syntax=docker/dockerfile:1.6
FROM python:3.12-slim AS devstack

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    wget \
    build-essential \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package manager)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    ln -s /root/.local/bin/uv /usr/local/bin/uv

# Install D2 for visualization rendering (optional but recommended)
RUN curl -fsSL https://d2lang.com/install.sh | sh -s -- -d /usr/local/bin || true

WORKDIR /workspace

# Copy repo contents up front so local artifacts (e.g., dev-stack wheels) are available.
COPY . .

# Allow overriding the dev-stack install source during docker builds.
ARG DEV_STACK_PIP_SPEC="dev-stack>=0.1.0"

# Pre-install dev-stack and pipeline tooling so the container can execute stages 1-6
RUN uv pip install --system "${DEV_STACK_PIP_SPEC}" \
    "pytest>=7.4" \
    "pytest-cov>=4.1" \
    "ruff>=0.3" \
    "pip-audit>=2.7" \
    "detect-secrets>=1.5"

# Install project dependencies if descriptors are present. Adjust to match your stack.
RUN if [ -f "requirements.txt" ]; then pip install -r requirements.txt; fi && \
    if [ -f "requirements-dev.txt" ]; then pip install -r requirements-dev.txt; fi && \
    if [ -f "pyproject.toml" ]; then uv pip install --system -e .; fi

# Default command runs the dev-stack pipeline inside the container.
CMD ["dev-stack", "pipeline", "run"]
