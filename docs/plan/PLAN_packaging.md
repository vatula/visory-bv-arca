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

## 3. Frontend Containerization Constraints (Next.js)

* **Build Optimization:** Next.js must be configured in `next.config.ts` to use `output: 'standalone'`. The Dockerfile must be a multi-stage build that only copies the minimal `standalone` server and `static` assets into the final runner image to dramatically reduce image size.  
* **Dual-Network Routing (CRITICAL):**  
  The Next.js architecture operates across two network namespaces. Your code must respect these environment variables injected by docker-compose:  
  1. `INTERNAL_API_URL=http://backend:8000` - Used by Next.js Server Components (BFF) to fetch data directly within the internal Docker bridge network.  
  2. `NEXT_PUBLIC_API_URL=http://localhost:8000` - Used by the browser (Client Components) for the Server-Sent Events (SSE) stream. The browser operates outside the Docker network, hence `localhost`.

## 4. Resource Fixture Mounting

Both containers mount the `./resources` directory as read-only (`:ro`). The backend reads `xero_api_feed.json` and Markdown policies directly from this mount. Do not `COPY` the `resources` directory into the Dockerfiles.