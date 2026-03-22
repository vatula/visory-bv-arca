# Tasks: Docker Containerization

* [x] **Backend Prep (`backend/.dockerignore`):** Create an ignore file preventing `__pycache__`, `.pytest_cache`, `.env`, virtual environments, and `tests/` from being copied into the container context.
* [x] **Backend Dockerfile (`backend/Dockerfile`):**
  * Use python:3.12-slim (or similar).  
  * Set `WORKDIR /app`.  
  * Install dependencies (via `uv`).  
  * Explicitly create the database directory: `RUN mkdir -p /app/data`.  
  * Copy the `src` code.  
  * Set the startup command to launch FastAPI via `uvicorn` on `0.0.0.0:8000`.  
* [x] **Frontend Prep (`frontend/.dockerignore`):** Create an ignore file preventing `node_modules/`, `.next/`, and local `.env` files from being copied.
* [x] **Frontend Config (`frontend/next.config.ts`):** Modify the Next.js configuration file to include `output: 'standalone'`.
* [x] **Frontend Dockerfile (`frontend/Dockerfile`):**
  * Implement a multi-stage build (deps, builder, runner) using `node:18-alpine` (or newer).  
  * In the builder stage, run the Next.js build.  
  * In the runner stage, copy the `.next/standalone` directory and `.next/static` assets.  
  * Set the startup command to `node server.js` exposing port `3000`.  
* [x] **Networking Verification:** Search the frontend codebase to ensure server-side API calls use `process.env.INTERNAL_API_URL` and client-side SSE/fetches use `process.env.NEXT_PUBLIC_API_URL`.
* [x] **Orchestration:** Place the provided `docker-compose.yaml` in the root directory and ensure the relative paths (`./backend`, `./frontend`, `./resources`) resolve correctly.
* [x] **Runtime Fix — Backend dev-dep re-sync:** Replace `CMD ["uv", "run", "uvicorn", ...]` with `CMD ["/app/.venv/bin/uvicorn", ...]` and add `uv cache clean` to the build step to prevent `uv run` from re-syncing dev dependencies (`ruff`, `mypy`) at every container startup.
* [x] **Runtime Fix — Frontend missing `public/` directory:** Create `frontend/public/.gitkeep` so the builder stage always has a `public/` directory to copy. Add `RUN mkdir -p ./public` in the runner stage before the `COPY` as a defensive guard against empty-directory COPY failures.
* [x] **Runtime Fix — Backend response shape mismatch:** `GET /transactions/active` and `GET /transactions/processed` returned plain arrays but the frontend Zod schemas expected `{ active: [...] }` and `{ processed: [...] }`. Added `ActiveTransactionsResponse` and `ProcessedTransactionsResponse` Pydantic models and wrapped the return values accordingly.
* [x] **Runtime Fix — Frontend status enum incomplete:** `TransactionStatusSchema` was missing `"suspended"`, `"resolved"`, and `"evidence_found"` — all of which are written to `arcra_ui_read_model` by backend graph nodes. Added all three values to the Zod enum and added corresponding cases to the exhaustive `getStatusMeta` switch.
* [x] **Runtime Fix — Next.js proxy baking `localhost` at build time:** `next.config.ts` `rewrites()` evaluates `process.env.INTERNAL_API_URL` at build time (inside Docker with no env set), silently falling back to `http://localhost:8000`. Replaced the rewrite with a runtime catch-all App Router Route Handler (`src/app/api/[...path]/route.ts`) that reads `INTERNAL_API_URL` at request time.