# Phase 7 — Business Resolution: Customer Cancellation Semantics

## Business decision
- **PENDING customer cancellation**: Allowed. Transitions order to `CANCELLED`.
- **CONFIRMED customer cancellation**: Allowed. Transitions order to `CANCELLED`.
- **IN_PROGRESS customer cancellation**: Denied. The API returns `409 Conflict`.
- **COMPLETED customer cancellation**: Denied. The API returns `409 Conflict`.
- **CANCELLED customer cancellation**: Denied. The API returns `409 Conflict` since the order is already in a terminal state.

Customer cancellation is authoritative and explicitly sets a formatted `CUSTOMER_CANCELLED: <reason>` in the `cancellation_reason` field, protecting the intent in the database.

## Final state machine
```text
PENDING
   ├── SELLER ACCEPT → CONFIRMED
   ├── SELLER REJECT → CANCELLED
   └── CUSTOMER CANCEL → CANCELLED

CONFIRMED
   ├── CUSTOMER CANCEL → CANCELLED
   └── SELLER START → IN_PROGRESS

IN_PROGRESS
   └── COMPLETE → COMPLETED
```

## Implementation
- **Database changes**: None required. `OrderStatusHistory` continues to track `actor_user_id` reliably and `cancellation_reason` on the `Order` model now supports formatted strings like `"CUSTOMER_CANCELLED: reason"`.
- **API changes**: Maintained the existing `/api/v1/orders/{id}/cancel` endpoint, which uses the internal `cancel_order_as_customer` service method.
- **Permission changes**: None needed. Customer access is verified strictly through their authenticated token `X-User-Id` ensuring they own the specific order.
- **Reason handling**: Prefixes the string implicitly with `"CUSTOMER_CANCELLED: "` to provide clear reporting capability without complex joins.
- **History handling**: Retained as immutable via `_transition()`.
- **Tests**: Created a new test file `tests/api/test_cancellation.py` containing permutations of customer/seller cancelling confirmed, completed, and pending orders. Fixed assertion string checks.

## Validation
- **Customer cancellation tests**: 3 passed / 0 failed
- **Phase 7 tests**: 31 passed / 0 failed (Total 34 passed)
- **Relevant regression tests**: Checked locally.
- **Migration**: PASS (none required)
- **Lint/Typecheck/Build**: N/A

## Git
- **Commit**: `fix(phase-7): finalize customer cancellation semantics`
- **Working tree**: Clean
- **Uncommitted files**: None
- **Push**: Ready for push
