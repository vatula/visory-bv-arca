FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Copy dependency manifests first for layer caching
COPY pyproject.toml ./

# Install production dependencies only (no dev group)
RUN uv sync --no-dev --no-editable

# Create the database directory for SQLite WAL (mapped to named volume at runtime)
RUN mkdir -p /app/data

# Copy application source
COPY src/ ./src/

# Expose FastAPI port
EXPOSE 8000

# Launch via uvicorn; DATABASE_URL should point to /app/data/arcra.db via env
CMD ["uv", "run", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
