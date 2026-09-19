# Phase 7 — Business Resolution: Seller Order Acceptance & Rejection Semantics

## Business decision
Seller acceptance transitions the order from `PENDING` to `CONFIRMED`.
Seller rejection explicitly aborts the order. Rather than creating a new `REJECTED` state, it leverages the `CANCELLED` state, keeping the overall state machine minimal and focused. 
A rejection is strictly defined as a seller terminating a `PENDING` order, whereas a cancellation is terminating a `CONFIRMED` order.

Order terminal state for rejection is `CANCELLED`.

Reason handling uses the existing string-based `cancellation_reason` field alongside `OrderStatusHistory`. 

## Final transition
```
PENDING
   ├── ACCEPT → CONFIRMED
   ├── REJECT → CANCELLED (via specialized /reject endpoint)
   └── CUSTOMER CANCEL → CANCELLED
```

## Implementation impact
- **Database changes**: ZERO database migrations required. The existing `OrderStatusHistory` combined with explicit context handles tracking unambiguous actor logic. Reporting can be accurately performed by analyzing `from_status=PENDING` and `to_status=CANCELLED` for a seller-executed action versus a customer-executed action.
- **API changes**: Added `POST /api/v1/seller/orders/{order_id}/reject` to explicitly handle rejections. Re-scoped `POST /api/v1/seller/orders/{order_id}/cancel` to only allow cancelling `CONFIRMED` orders.
- **Permission changes**: None needed. The existing `order.cancel` permission correctly guards both rejection and cancellation from unauthorized access, retaining strict tenant isolation.
- **Tests**: Created new targeted test suite `tests/api/test_rejection.py` handling valid/invalid transitions.
- **Documentation**: Logged this resolution directly into the architectural docs.

## Validation
- **Phase 7 tests**: 31 passed / 0 failed
- **Relevant regression tests**: Tested successfully locally.
- **Migration**: PASS (none required)
- **Frontend lint**: N/A
- **Frontend typecheck**: N/A
- **Frontend build**: N/A

## Git
- **Commit**: `fix(phase-7): finalize seller order acceptance semantics`
- **Working tree**: Clean
- **Uncommitted files**: None
- **Push**: N/A (local repo)
