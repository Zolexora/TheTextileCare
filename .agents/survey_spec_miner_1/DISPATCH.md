# Dispatch Task: Survey Spec Miner — Driver Assignment & Notifications (Q51–Q100)

## Working Directory
/workspaces/TheTextileCare/.agents/survey_spec_miner_1

## Objective
Thoroughly examine user requirements, specifications, and business decision records related to Q51–Q100 and requirements R1–R4.

## Inputs
- /workspaces/TheTextileCare/.agents/ORIGINAL_REQUEST.md
- /workspaces/TheTextileCare/.agents/orchestrator_3/DISPATCH.md
- Repository docs: `docs/decisions/`, `docs/architecture/`, `docs/database/`, and any Q51–Q100 documentation.

## Requirements to Investigate
1. **R1. Driver Assignment & Eligibility**:
   - Strict eligibility rules: active, authorized, available, compliance valid.
   - Authoritative assignment: NO accept/reject workflow.
   - Priority order: exact address familiarity > customer familiarity > workload > distance.
   - Concurrency-safe assignment: PostgreSQL row-locking (`SELECT ... FOR UPDATE`), exactly one active driver.
2. **R2. Reassignment & Unavailable Drivers**:
   - Manual reassignment: authorized seller staff with order access, mandatory reason required.
   - Pre-duty unavailability: automatic reassignment attempt to next eligible driver + operations alert.
   - Post-duty unavailability or late start: manual intervention ONLY, trigger operations alert, NO automatic reassignment.
   - Auditable history: historical drivers deactivated operationally, complete audit trail preserved.
3. **R3. Driver & Customer Notifications**:
   - Immediate notification delivery upon assignment/reassignment.
   - Customer notification payload: active driver's name, vehicle details, actual phone number.
   - Failure resilience: notification failure MUST NOT rollback or cancel assignment; retry mechanisms used.
   - Configurable channels: Push, In-App, SMS, WhatsApp (controlled by platform admin or full-access seller capabilities).
4. **R4. Security & Architectural Boundaries**:
   - Strict tenant/seller isolation: Seller A cannot reassign or access Seller B drivers.
   - Payment decoupling: driver assignment eligibility not equated with full payment unless configured.
   - Explicit domain actions (`assign`, `reassign`) vs generic mutations.
   - Shared platform infra / single driver app (ADR-009); no custom external broker (Kafka/Redis) for this phase.

## Output Requirements
Write a complete, structured report in `/workspaces/TheTextileCare/.agents/survey_spec_miner_1/handoff.md` with sections:
- Executive Summary
- Q51–Q100 Decision Mapping
- Detailed Requirements Analysis (R1–R4)
- Domain Invariants & Business Rules
- Edge Cases & Boundary Conditions
- Recommendation for Feature Inventory

## 2026-09-20T08:04:34Z
You are survey_spec_miner_1. Your working directory is /workspaces/TheTextileCare/.agents/survey_spec_miner_1.
Read your instructions in /workspaces/TheTextileCare/.agents/survey_spec_miner_1/DISPATCH.md and /workspaces/TheTextileCare/.agents/ORIGINAL_REQUEST.md.
Investigate repository docs, specs, and business decisions around Q51–Q100 and requirements R1–R4.
Write your complete handoff report to /workspaces/TheTextileCare/.agents/survey_spec_miner_1/handoff.md and notify parent when done.
