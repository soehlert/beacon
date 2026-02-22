# Build stage
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /app

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen --no-install-project --no-dev

# Final stage
FROM python:3.13-slim-bookworm

WORKDIR /app

# Copy the environment from the builder
COPY --from=builder /app/.venv /app/.venv

# Copy the application code
COPY app /app/app

# Place executable on path
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 7867

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7867"]
