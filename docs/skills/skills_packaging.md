# Required Skills Profile: Docker & Infrastructure

## Core Competencies Required

### MLOps Containerization & Volume Management

* **Skill:** Writing secure, minimal-layer Dockerfiles for stateful Python applications.  
* **Application:** Ensuring the backend container safely mounts the `arcra_db_data` named volume to preserve SQLite WAL integrity across container restarts, and correctly maps the host's AWS credentials for Bedrock LLM access without leaking secrets into the image layers.

### Multi-Stage Node.js Build Optimization

* **Skill:** Next.js `standalone` output and Docker multi-stage builds.  
* **Application:** Preventing bloated 2GB+ Node.js images by compiling the Next.js frontend into a standalone Node server. The agent must understand how to isolate build dependencies from runtime dependencies, copying only the necessary `server.js`, `public`, and `.next/static` directories.

### Container Network Bridging & BFF Architecture

* **Skill:** Resolving DNS and API routing across segregated Docker networks and host machines.  
* **Application:** Correctly wiring the application to support the `docker-compose` topology. The agent must implement logic that uses the internal DNS (`http://backend:8000`) for server-to-server fetches, while allowing the external host browser to connect to the SSE streams via mapped ports (`http://localhost:8000`).