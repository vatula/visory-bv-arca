# ARCRA Architecture: Docker Containerization Plan

**ATTENTION AI CODING AGENT:** This plan details how to package the ARCRA Backend (FastAPI/Pydantic Graph) and Frontend (Next.js) into isolated Docker containers. You must strictly adhere to the infrastructure boundaries and networking rules defined here, as they are designed to support asynchronous FSMs and Server-Sent Events (SSE).

## 1. System Infrastructure Overview

The application will run via `docker-compose` utilizing two custom-built images. The goal is local deployment parity with a production-ready MLOps environment.

* **Backend (`arcra_backend`):** A stateless Python container that relies on external volume mounts for both its state checkpointer (SQLite) and local evidence fixtures (`resources/`).  
* **Frontend (`arcra_frontend`):** A Node.js container running Next.js in standalone mode, serving both the React client and the Backend-for-Frontend (BFF) proxy.

## 2. Backend Containerization Constraints (Python)

* **Base Image:** Must use a slim Python 3.12+ base (e.g., `python:3.12-slim`) to minimize the attack surface.  
* **SQLite WAL & Volume Management:** The FSM uses SQLite with Write-Ahead Logging (WAL) for concurrent writes. The database MUST be stored in `/app/data` inside the container. This directory is mapped to a named volume (`arcra_db_data`) via docker-compose. **Do not** bake a SQLite file into the Docker image itself.  
* **AWS Credential Injection:**  
  The `pydantic-ai` `BedrockModel` requires AWS credentials. The container will run in read-only mode against the host machine's `~/.aws` directory. Do not write logic to copy `.env` files containing AWS keys into the image.
* **Dependency Installation (CRITICAL — avoid dev-dep re-sync at startup):**  
  Run `uv sync --no-dev --no-editable && uv cache clean` during the build step to install only production dependencies and discard the uv package cache from the image layer. **Do NOT use `CMD ["uv", "run", "uvicorn", ...]`** as `uv run` triggers a full environment re-sync at container startup (including `[dependency-groups] dev` tools such as `ruff` and `mypy`). Instead, invoke the pre-built venv binary directly: `CMD ["/app/.venv/bin/uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]`.

## 3. Frontend Containerization Constraints (Next.js)

* **Build Optimization:** Next.js must be configured in `next.config.ts` to use `output: 'standalone'`. The Dockerfile must be a multi-stage build that only copies the minimal `standalone` server and `static` assets into the final runner image to dramatically reduce image size.
* **`public/` Directory (CRITICAL — must exist before build):**  
  Next.js standalone builds always attempt to copy the `public/` directory into the output. If `frontend/public/` does not exist, the final `COPY --from=builder /app/public ./public` step in the runner stage will fail with a "not found" error. Always ensure `frontend/public/` exists (create it with a `.gitkeep` placeholder if the project has no static assets). Additionally, add `RUN mkdir -p ./public` in the runner stage immediately before the `COPY` as a defensive guard.  
* **Dual-Network Routing (CRITICAL):**  
  The Next.js architecture operates across two network namespaces. Your code must respect these environment variables injected by docker-compose:  
  1. `INTERNAL_API_URL=http://backend:8000` - Used by Next.js Server Components (BFF) to fetch data directly within the internal Docker bridge network.  
  2. `NEXT_PUBLIC_API_URL=http://localhost:8000` - Used by the browser (Client Components) for the Server-Sent Events (SSE) stream. The browser operates outside the Docker network, hence `localhost`.

## 4. Resource Fixture Mounting

Both containers mount the `./resources` directory as read-only (`:ro`). The backend reads `xero_api_feed.json` and Markdown policies directly from this mount. Do not `COPY` the `resources` directory into the Dockerfiles.