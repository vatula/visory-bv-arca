# Phase 7 — E2E Prompt Evaluation & LLM Testing Tasks

Bound to: `PLAN_OVERRIDE.md §7`

---

## Infrastructure

- [x] Create `backend/tests_e2e/` directory isolated from `backend/tests/` (unit suite)
- [x] Create `backend/tests_e2e/__init__.py`
- [x] Create `backend/pytest_e2e.ini` with `testpaths = tests_e2e`, `asyncio_mode = auto`, `pythonpath = .`
- [x] Confirm `backend/pyproject.toml` `testpaths = ["tests"]` remains unchanged (e2e suite not picked up by default `pytest` run)

## Shared Utilities

- [x] Create `backend/tests_e2e/helpers.py` with pure helper functions:
  - [x] `load_all_transactions()` — flattens `resources/xero_api_feed.json`
  - [x] `find_transaction(txs, tx_id)` — returns typed `XeroTransaction`
  - [x] `load_policy_content(filename)` — reads `resources/policies/<filename>`
  - [x] `build_transaction_prompt(tx)` — renders canonical vagueness-analysis prompt

## Fixtures (`conftest.py`)

- [x] `settings` fixture (session-scoped) — loads `Settings` from env / `.env`
- [x] `require_aws_credentials` autouse fixture — skips session if AWS creds absent
- [x] `all_transactions` fixture — loads and flattens xero feed
- [x] `travel_policy_content` fixture — reads `travel.md`
- [x] `cloud_policy_content` fixture — reads `cloud_and_finops_allocation.md`
- [x] `entertainment_policy_content` fixture — reads `client_entertainment.md`
- [x] `vagueness_agent` fixture — real `BedrockConverseModel`, no mock
- [x] `policy_extraction_agent` fixture — real `BedrockConverseModel`, no mock
- [x] `synthesis_agent` fixture — real `BedrockConverseModel`, no mock

## Vagueness Agent Tests (`test_e2e_vagueness_agent.py`)

- [x] `test_airbnb_non_standard_provider_flagged_as_vague`
  - [x] `tx_100043` AIRBNB -680.0 AUD → `is_vague=True`
  - [x] `extracted_entities` contains 'airbnb'
- [x] `test_google_cloud_without_project_code_flagged_as_vague`
  - [x] `tx_100008` GOOGLE CLOUD -890.1 AUD → `is_vague=True`
  - [x] `missing_context` references project code / cost centre
- [x] `test_entertainment_without_attendees_flagged_as_vague`
  - [x] `tx_100045` CAFE SYDNEY -120.0 AUD → `is_vague=True`
  - [x] `missing_context` references attendees / FBT

## Policy Extraction Agent Tests (`test_e2e_policy_agent.py`)

- [x] `test_travel_policy_extracts_airbnb_blocking_rule`
  - [x] `travel.md` → `len(rules) >= 1`
  - [x] At least one `is_blocking=True` rule mentioning Airbnb / non-standard lodging
- [x] `test_cloud_finops_policy_extracts_threshold_and_required_fields`
  - [x] `cloud_and_finops_allocation.md` → `len(rules) >= 1`
  - [x] At least one rule with `threshold_amount=500.0`
  - [x] At least one rule with 'project_code' / 'cost_center' in `required_fields`

## Synthesis Agent Tests (`test_e2e_synthesis_agent.py`)

- [x] `test_synthesis_with_complete_context_returns_valid_score`
  - [x] `tx_100042` QANTAS AIRWAYS full context → `confidence_score` in [0.0, 1.0]
  - [x] `reasoning` is non-empty string
  - [x] `key_risks` is a list
- [x] `test_synthesis_with_vague_context_identifies_risks`
  - [x] `tx_100043` AIRBNB vague context → `confidence_score < 1.0`
  - [x] `len(key_risks) >= 1`
  - [x] `key_risks` text references Airbnb / approval gap / policy violation

## How to Run

```bash
# From the backend/ directory:
cd backend
pytest -c pytest_e2e.ini -v

# With coverage (optional):
pytest -c pytest_e2e.ini -v --cov=src --cov-report=term-missing
```

> **Prerequisites:** AWS credentials must be set (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`,
> `AWS_DEFAULT_REGION`) or present in a `backend/.env` file.  Without credentials the entire
> suite is skipped with a clear message rather than failing.
