# Marketplace Public Boundary

The primary security responsibility of Phase 6 is distinguishing between **Tenant Private Data** and **Marketplace Public Data**.

## Rules Enforced

1. **Explicit Publication**: A seller is not public merely because they exist. They must have `marketplace_status = 'PUBLISHED'`.
2. **Explicit Branch Visibility**: A branch must explicitly have `is_marketplace_visible = True` to appear in location searches.
3. **Draft Exclusion**: Catalog entities in a `DRAFT` or `INACTIVE` state are strictly excluded from marketplace endpoints, preventing enumeration.
4. **No Customer Cross-Pollination**: Customer profiles and addresses are scoped strictly to the `X-User-Id` making the request. A customer cannot read another customer's `CustomerAddress`.
5. **Preview Safety**: Pricing calculation previews do not mutate state. They simply construct an ephemeral `PricingCalculationRequest` and pass it to the Phase 5 engine.
