# Phase 7 — Order Foundation Architecture

## Core Architectural Principle
**An Order must be historically immutable with respect to its commercial definition.**

This is achieved via "Snapshots". When an order is placed, the catalog configuration, pricing calculations, and customer profile/address are copied into JSON structures directly on the `Order` and `OrderItem` models.

## Idempotency
Order creation requires an `Idempotency-Key` header from the client (mapped to a `UniqueConstraint` on `customer_id` + `idempotency_key`). This prevents duplicate orders from network retries.

## Order Number Generation
TTC order numbers are formatted as `TTC-YYYY-XXXXXX`. To guarantee uniqueness without race conditions, a PostgreSQL sequence `order_number_seq` is used rather than querying `MAX(id)`.

## Status Transitions
The Order Service acts as a strict state machine:
- Customers can cancel from `PENDING`
- Sellers can transition `PENDING` -> `CONFIRMED` -> `IN_PROGRESS` -> `COMPLETED`
- Sellers can cancel from `PENDING` or `CONFIRMED`
- `OrderService._transition()` handles these changes and stores an `OrderStatusHistory` record.
