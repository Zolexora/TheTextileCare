# Phase 6: Marketplace and Customer Foundation

## Architecture Overview

Phase 6 introduces the customer-facing discovery and public catalog API to TTC, creating a unified `Marketplace`. It connects the Phase 4 Catalog and Phase 5 Pricing Engine securely to a customer profile model without creating an "Order" or duplicating logic.

### Core Flows

1. **Customer Identity**: A `Customer` record is uniquely linked to a platform `User`. Customers own `CustomerAddress`es which enforce a strict "one-or-zero default address" rule.
2. **Seller Marketplace Publication**: A `Seller` object has an internal `status` and an external `marketplace_status`. Only a `PUBLISHED` seller with active branches will appear in discovery.
3. **Marketplace APIs**:
   - `/api/v1/marketplace/sellers`: Simple PostgreSQL ILIKE-based search against active/published sellers.
   - `/api/v1/marketplace/sellers/{id}/services`: Respects Phase 4 `ServiceBranchAvailability` and Phase 4 activation statuses.
   - `/api/v1/marketplace/pricing/preview`: Delegates to the Phase 5 Pricing Engine after verifying the entities are publicly accessible.

### Invariants
- Marketplace API requests for draft or inactive catalogs return 404/422.
- The Pricing Preview endpoint performs zero DB writes (no orders, carts, checkout).
