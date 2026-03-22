# Tasks: Backend API & Telemetry Implementation (FastAPI)

- [ ] **Setup:** Initialize FastAPI application. Configure CORS to allow requests strictly from the Next.js frontend IP/Domain.
- [ ] **Data Layer (Read Model):** Update `db.py` to include schema definitions for `arcra_ui_read_model` and `arcra_audit_events`.
- [ ] **Graph Telemetry Hooks:** Modify the Pydantic Graph node implementations. At the end of every node execution, emit an event to insert a row into `arcra_audit_events` (e.g., "Notion policy queried").
- [ ] **Slack Node Telemetry:** Specifically update the `CheckSlackNode` and the Webhook endpoint to write the exact message text and exact reply text to the `arcra_audit_events` table.
- [ ] **Endpoint Implementation:**  Implement `GET /api/v1/transactions/active`. Query `arcra_ui_read_model` where status is in `('pending', 'processing', 'suspended')` ordered by `last_updated` DESC limit 10. 
- [ ] **Endpoint Implementation:** Implement `GET /api/v1/transactions/processed`. Query where status is in `('resolved', 'escalated')` limit 10.
- [ ] **Endpoint Implementation:** Implement `GET /api/v1/transactions/{id}/audit`. Return a composite Pydantic response containing the Read Model details and the array of associated `arcra_audit_events`.
