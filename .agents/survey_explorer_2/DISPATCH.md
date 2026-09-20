# Dispatch Task: Survey Explorer — Backend Domain Models & Architecture

## Working Directory
/workspaces/TheTextileCare/.agents/survey_explorer_2

## Objective
Analyze the existing backend codebase to map out current driver, order, duty/assignment, and notification implementations, identifying required schema changes, models, and service architectures.

## Inputs
- /workspaces/TheTextileCare/.agents/ORIGINAL_REQUEST.md
- /workspaces/TheTextileCare/.agents/orchestrator_3/DISPATCH.md
- Backend code: `backend/app/models/`, `backend/app/schemas/`, `backend/app/services/`, `backend/app/api/`, `backend/alembic/versions/`

## Areas of Investigation
1. **Existing Driver Models**:
   - Inspect existing driver entities: drivers, driver profiles, vehicles, documents/compliance, shifts, availability (`backend/app/models/driver.py`, etc.).
   - Are there existing fields for driver availability, active status, compliance status, assigned branches/tenants?
2. **Order & Pickup/Delivery Domain**:
   - Inspect `backend/app/models/order.py`, `backend/app/models/pickup.py` (or `order_pickups`), delivery tasks/duties.
   - How are duties/tasks currently structured? Is there a driver assignment table or relation?
   - How are historical assignments preserved?
3. **Notification Models & Services**:
   - Inspect `backend/app/services/notification.py` or existing notification infrastructure.
   - What channels currently exist (SMS, WhatsApp, Push, In-App)? How are notifications logged/retried?
4. **Database & Migrations**:
   - What is the latest Alembic revision in `backend/alembic/versions`?
   - What new tables, columns, indexes, foreign keys, or enum types will be required for R1–R4?
5. **Architecture & Service Boundaries**:
   - How should the Assignment Service, Priority Resolution Engine, and Reassignment Handlers be structured?

## Output Requirements
Write a complete, structured report in `/workspaces/TheTextileCare/.agents/survey_explorer_2/handoff.md` with sections:
- Executive Summary
- Current Codebase Architecture & Entities
- Gap Analysis for R1–R4
- Proposed Schema & Model Additions (SQLAlchemy 2.0 / Alembic)
- Proposed Service Architecture & API Endpoints
- Dependencies & Technical Risks

## 2026-09-20T08:04:34Z
You are survey_explorer_2. Your working directory is /workspaces/TheTextileCare/.agents/survey_explorer_2.
Read your instructions in /workspaces/TheTextileCare/.agents/survey_explorer_2/DISPATCH.md and /workspaces/TheTextileCare/.agents/ORIGINAL_REQUEST.md.
Investigate the existing backend codebase for driver models, order/pickup models, notification services, migrations, and gap analysis for R1–R4.
Write your complete handoff report to /workspaces/TheTextileCare/.agents/survey_explorer_2/handoff.md and notify parent when done.

