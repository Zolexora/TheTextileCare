# Phase 7 — Order Database Schema

## Models
1. **Order**: Represents the parent commercial transaction. Contains pre-calculated sum totals, a generated `order_number`, state machine fields (`status`, timestamps), and JSON snapshots (`pricing_snapshot`, `catalog_snapshot`, `customer_snapshot`, `customer_address_snapshot`).
2. **OrderItem**: Represents a single service item ordered (e.g., "1x Cotton Shirt with Shirt Cleaning"). Stores its own price calculation results and catalog snapshots.
3. **OrderItemAddon**: Links add-ons to specific order line items.
4. **OrderStatusHistory**: An append-only log tracking lifecycle transitions, who made them, and the reason.

## Constraints & Sequences
- `order_number_seq`: Custom PostgreSQL sequence.
- `uq_order_order_number`: Unique order number across the entire platform.
- `uq_order_customer_idempotency`: Uniqueness on `customer_id` + `idempotency_key`.
