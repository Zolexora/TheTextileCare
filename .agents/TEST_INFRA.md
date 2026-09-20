# E2E Test Infra: TTC Driver Assignment, Reassignment & Notifications (Q51–Q100 / R1–R4)

## Test Philosophy
- **Opaque-box, Requirement-Driven**: Test cases are derived strictly from `ORIGINAL_REQUEST.md` (R1–R4) and business specifications Q51–Q100, treating implementation details as a black box.
- **Methodology**: Category-Partition + Boundary Value Analysis (BVA) + Pairwise Combinatorial Testing + Real-World Workload Testing.
- **Progressive Testability**: Verification uses public REST endpoints and database state assertions without requiring features more complex than what is under test.

## Feature Inventory & Test Coverage Goals
| # | Feature | Source | Tier 1 (Coverage ≥5) | Tier 2 (Boundaries ≥5) | Tier 3 (Pairwise) |
|---|---------|--------|:-------------------:|:---------------------:|:----------------:|
| 1 | Driver Profile, Shifts & Vehicle Registration | Q51–Q54, R1 | 5 | 5 | ✓ |
| 2 | Driver Compliance Verification (DL, RC, Insurance, BGC) | Q55–Q56, R1 | 5 | 5 | ✓ |
| 3 | Driver Eligibility Gate (Active, Shift, Capacity, Compliance) | Q53, Q57-Q58, R1 | 5 | 5 | ✓ |
| 4 | 4-Tier Algorithmic Familiarity & Priority Engine | Q71–Q80, R1 | 5 | 5 | ✓ |
| 5 | Authoritative Duty Assignment (No Accept/Reject) | Q61–Q64, R1 | 5 | 5 | ✓ |
| 6 | Concurrency-Safe PostgreSQL Locking (`FOR UPDATE` & Partial Unique Index) | Q65, R1 | 5 | 5 | ✓ |
| 7 | Assignment Fallback, Pool Expansion & Exhaustion Handling | Q69–Q70, R1 | 5 | 5 | ✓ |
| 8 | Manual Driver Reassignment with Mandatory Reason | Q81–Q82, R2 | 5 | 5 | ✓ |
| 9 | Pre-Duty Driver Unavailability (Auto-Reassign + Ops Alert) | Q83–Q84, R2 | 5 | 5 | ✓ |
| 10 | Post-Duty Unavailability & Late Start SLA (Manual Intervention Only) | Q85–Q87, R2 | 5 | 5 | ✓ |
| 11 | Immutable Assignment History & Operational Deactivation | Q88–Q89, R2 | 5 | 5 | ✓ |
| 12 | Immediate Multi-Channel Notifications (Driver & Customer) | Q91, Q95, R3 | 5 | 5 | ✓ |
| 13 | Customer Notification Payload (Driver Name, Vehicle, Unmasked Phone) | Q92–Q93, R3 | 5 | 5 | ✓ |
| 14 | Decoupled Notification Failure Resilience & Retry Queue | Q94, R3 | 5 | 5 | ✓ |
| 15 | Multi-Tenant & Seller Security Isolation | Q60, Q99, R4 | 5 | 5 | ✓ |
| 16 | Payment Decoupling Architectural Boundary | Q68, R4 | 5 | 5 | ✓ |

## Test Architecture
- **Test Runner**: Pytest executing in test environment (`APP_ENV=test`).
- **Invocation**: `pytest -v backend/tests/e2e/test_driver_*.py`
- **Pass/Fail Semantics**: All assertions must pass with exit code 0; zero regressions across existing test suite (`pytest backend/tests/`).
- **Isolation**: Each test operates within an isolated tenant/seller context with automatic schema reset via `conftest.py`.

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | Standard High-Volume Peak Pickup Dispatch | F1, F3, F4, F5, F12, F13 | High |
| 2 | Driver Pre-Duty Flat Tire Automatic Reassignment | F3, F4, F8, F9, F11, F12, F13 | High |
| 3 | Post-Duty Mid-Route Van Breakdown Emergency Intervention | F8, F10, F11, F12, F13 | High |
| 4 | High-Concurrency Flash Sale Multiple Duty Assignment Race | F5, F6, F11, F15 | Critical |
| 5 | Network Outage During Assignment with Retry Queue Verification | F5, F12, F14, F16 | High |
| 6 | Cross-Tenant Malicious Reassignment & Data Leakage Prevention | F8, F13, F15 | Critical |

## Coverage Thresholds
- **Tier 1 (Feature Coverage)**: 16 features × 5 = 80 test cases minimum.
- **Tier 2 (Boundary & Corner Cases)**: 16 features × 5 = 80 test cases minimum.
- **Tier 3 (Cross-Feature Combinations)**: 16 pairwise interaction test cases minimum.
- **Tier 4 (Real-World Workloads)**: 6 comprehensive end-to-end scenarios.
- **Total Suite Minimum**: ~182 rigorous test cases.
