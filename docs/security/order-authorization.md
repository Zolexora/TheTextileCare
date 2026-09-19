# Phase 7 — Order Authorization

## Role-Based Access Control
Phase 7 adds 5 new permissions to `PermissionName`:
- `order.read`
- `order.manage`
- `order.confirm`
- `order.process`
- `order.cancel`

These permissions are granted to tenant roles:
- **TENANT_OWNER, TENANT_ADMIN**: All `order.*`
- **SELLER_OWNER, SELLER_ADMIN**: All `order.*`
- **STAFF**: `order.read`, `order.process`
- **VIEWER**: `order.read`

## Multi-Tenant Isolation
- Customer routes (`/api/v1/orders/*`) isolate by `X-User-Id` mapping directly to a Customer model.
- Seller routes (`/api/v1/seller/orders/*`) isolate by `X-Tenant-Id` + Permission context.
- Cross-tenant reads are prevented because the `OrderRepository` explicitly filters by `tenant_id` for all seller operations and by `customer_id` for all customer operations.
