FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Copy dependency manifests first for layer caching
COPY pyproject.toml ./

# Install production dependencies only (no dev group), into a fixed venv path
RUN uv sync --no-dev --no-editable && uv cache clean

# Create the database directory for SQLite WAL (mapped to named volume at runtime)
RUN mkdir -p /app/data

# Copy application source
COPY src/ ./src/

# Expose FastAPI port
EXPOSE 8000

# Launch via the pre-built venv binary — avoids uv re-syncing dev deps at startup
CMD ["/app/.venv/bin/uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
