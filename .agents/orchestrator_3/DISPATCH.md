# Dispatch Log — Orchestrator 3 (Driver Assignment, Reassignment, & Notifications)

## 2026-09-20T08:01:28Z

You are the Project Orchestrator for the TTC (TheTextileCare) Driver Assignment, Reassignment, and Notification behaviors project (Q51–Q100).
Your working directory is: /workspaces/TheTextileCare/.agents/orchestrator_3
Your task is defined authoritatively in /workspaces/TheTextileCare/.agents/ORIGINAL_REQUEST.md and /workspaces/TheTextileCare/ORIGINAL_REQUEST.md.

Requirements summary:
R1. Driver Assignment & Eligibility:
- Implement automatic and manual driver assignment logic based on strict eligibility rules (active, authorized, available, compliance valid).
- Do not use an accept/reject workflow; assignment is authoritative.
- Driver preference must follow the established priority order (exact address familiarity > customer familiarity > workload > distance).
- Implement concurrency-safe assignment logic using PostgreSQL locking, ensuring exactly one active driver at a time.

R2. Reassignment & Unavailable Drivers:
- Support manual reassignment for seller staff with order access (requires a mandatory reason).
- If a driver is unavailable before duty starts: Automatically attempt reassignment to another eligible driver and alert operations.
- If a driver is unavailable after duty starts, or fails to start on time: Do not automatically reassign; trigger an operations alert requiring manual intervention.
- Preserve an auditable assignment history; historical drivers are no longer operationally active.

R3. Driver & Customer Notifications:
- Implement immediate notification delivery upon assignment/reassignment.
- Provide the customer with the active driver's name, vehicle details, and actual phone number.
- Do not roll back or cancel an assignment due to a notification delivery failure; use retry mechanisms instead.
- Support configurable notification channels (Push, In-App, SMS, WhatsApp) controlled by platform admin (Marketplace) or within platform capabilities (Full-Access Seller).

R4. Security & Architectural Boundaries:
- Enforce strict tenant/seller isolation for all assignment operations.
- Do not equate driver assignment eligibility with full payment unless configured.
- Extend existing explicit domain action APIs (e.g., assign, reassign) rather than generic status mutations.
- Rely on the shared platform infrastructure and single driver app; do not build seller-specific custom apps or distributed infrastructure (Kafka/Redis) for this checkpoint.

Acceptance Criteria:
- Automatic Assignment tests: preferred driver selection, timeout fallback, expanded pool usage, operations alerts if no driver available without order cancellation.
- Driver Unavailability tests: automatic reassignment before duty starts, manual-only reassignment if unavailable after duty start or late.
- Manual Reassignment tests: authorized staff reassign with mandatory reason, history reflects change with only one active driver.
- Notifications & Information tests: immediate notification triggers for driver & customer, exposure of driver actual phone number, notification failures do not invalidate assignments.
- Isolation & Concurrency tests: Tenant/Seller A cannot reassign Tenant/Seller B drivers, concurrency tests prevent multiple active assignments for the same duty.
- Regression & CI: full existing test suite passes without regressions (`pytest`). Fresh DB migrations succeed (`alembic upgrade head`). Backend linting and typechecking pass.

Please initialize your BRIEFING.md, plan, and keep progress.md updated in /workspaces/TheTextileCare/.agents/orchestrator_3/.
When complete, notify the Sentinel.
