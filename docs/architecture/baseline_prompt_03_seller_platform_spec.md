# TTC Baseline Prompt 03 — Seller Platform Business & Product Specification

## Purpose

Define the complete business and product behavior of the **TTC Seller Platform**.

This prompt covers:

* Seller onboarding
* Seller types
* Seller profile
* Seller branches
* Seller users
* Seller RBAC
* Seller catalog configuration
* Seller service configuration
* Seller pricing configuration
* Seller operational configuration
* Seller marketplace participation
* Full-Access Seller behavior
* White-label readiness
* Seller order operations
* Seller pickup/fulfillment configuration
* Seller payment/commercial configuration
* Seller restrictions
* Seller suspension
* Seller auditability

This is a **baseline product/business specification**, not an implementation instruction for a single phase.

Do not invent additional business rules where the established TTC decisions already define behavior.

---

# 1. Seller Platform Position

The Seller Platform is the operational control surface through which a laundry business manages the capabilities TTC makes available to it.

The architecture supports two principal seller operating models:

```text
                    TTC
                     │
             ┌───────┴────────┐
             │                │
     Marketplace Seller   Full-Access Seller
             │                │
       TTC Marketplace    Own branded
                           customer experience
```

Both use the same TTC platform foundation.

They do not receive separate backend implementations.

---

# 2. Marketplace Seller

A Marketplace Seller participates in the shared TTC marketplace.

The seller can configure supported business capabilities such as:

```text
branches
services
service items
pricing
availability
pickup configuration
operational settings
supported payment behavior
commercial configuration
```

However:

```text
TTC controls marketplace governance.
TTC controls master catalog.
TTC controls platform security.
TTC controls platform-level rules.
```

The seller does not create arbitrary platform capabilities.

---

# 3. Full-Access Seller

A Full-Access Seller operates through a seller-specific branded customer experience.

This may include:

```text
seller website
seller mobile application
seller domain
seller branding
seller customer experience
```

The seller receives broader supported configuration than a Marketplace Seller.

The seller can manage supported:

```text
users
roles
permissions
services
pricing
operations
customer experience
branding
payment configuration
workflow configuration
```

But:

> Full-Access does not mean arbitrary software development.

The seller still operates inside TTC's supported configuration-driven platform.

---

# 4. Seller Is a Tenant

Seller tenancy follows the established TTC architecture.

Conceptually:

```text
Tenant
   ↓
Seller
   ↓
Branches
   ↓
Seller Users
   ↓
Seller Configuration
   ↓
Seller Orders
```

The seller must never access another seller's data.

Every seller-scoped operation must resolve and validate:

```text
tenant
seller
branch
resource
```

using authenticated server-side context.

---

# 5. Seller Identity

Seller is a business/domain entity.

It is not a duplicate authentication system.

Authentication identifies the user.

Seller tenancy identifies the business the user operates within.

Conceptually:

```text
User
 ↓
Membership
 ↓
Tenant/Seller
 ↓
Roles
 ↓
Permissions
```

Do not create a second independent seller authentication database.

---

# 6. Seller Profile

A seller profile contains supported business information such as:

```text
business name
display name
legal/business identity where required
contact information
business description
branding
support information
operational information
```

The exact fields follow repository conventions and actual product requirements.

Do not store unnecessary sensitive information.

---

# 7. Seller Lifecycle

Seller onboarding should have an explicit lifecycle.

The platform must distinguish between:

```text
seller being onboarded
seller active
seller restricted
seller suspended
```

The exact implementation should reuse existing platform status conventions where available.

Do not create unnecessary seller states.

---

# 8. Seller Activation

A seller becomes operational only after required onboarding conditions are satisfied.

Activation may depend on:

```text
required seller information
branch configuration
catalog/service configuration
pricing configuration
platform approval where applicable
commercial configuration
domain/app configuration for Full-Access
```

Do not allow incomplete seller configuration to appear as fully operational.

---

# 9. Marketplace Eligibility

Marketplace participation is separate from simply being an active seller.

A seller may exist on TTC without being eligible for marketplace discovery.

Marketplace eligibility should validate relevant conditions such as:

```text
seller active
branch active
service active
catalog configured
marketplace participation enabled
required operational configuration available
```

The marketplace must revalidate these conditions at order creation.

---

# 10. Seller Branches

A seller may have multiple branches.

Conceptually:

```text
Seller
 ├── Branch A
 ├── Branch B
 └── Branch C
```

Each branch belongs to exactly one seller.

A branch must not be usable under another seller.

---

# 11. Branch Configuration

Branch configuration may include supported information such as:

```text
branch name
address
contact details
operating status
service availability
marketplace availability
operational settings
```

Do not duplicate seller-level configuration unnecessarily.

Use inheritance/resolution where the existing customization architecture supports it.

---

# 12. Branch Isolation

Every branch operation must verify:

```text
branch.seller_id == authenticated seller context
```

and:

```text
branch.tenant_id == authenticated tenant context
```

Never trust a client-supplied seller or tenant identifier.

---

# 13. Seller Users

Full-Access Sellers can manage supported seller users.

Marketplace Sellers do not receive arbitrary internal staff-management capabilities for marketplace operations unless TTC explicitly exposes them.

The platform distinguishes:

```text
TTC/platform users
Seller users
Customers
Drivers
```

Do not merge these identity domains.

---

# 14. Seller RBAC

Seller RBAC follows:

```text
Roles
+
Permissions
+
User-level additions/removals
```

Effective access:

```text
Available Permissions
        ↓
Role Permissions
        ↓
User
        ↓
Individual additions/removals
        ↓
Effective Permissions
```

Role changes apply immediately.

User-level permission changes apply immediately.

---

# 15. Seller Roles

Established seller roles include:

```text
SELLER_OWNER
SELLER_ADMIN
SELLER_STAFF
SELLER_VIEWER
```

These are baseline roles.

Do not invent a large role hierarchy unless required by an actual capability.

---

# 16. Seller Owner

The Seller Owner represents the highest seller-level administrative authority.

Subject to platform permissions, the owner can manage:

```text
seller configuration
users
roles
permissions
branches
services
pricing
orders
operational settings
commercial configuration
white-label configuration
```

The platform still controls capabilities that are globally restricted by TTC.

---

# 17. Seller Admin

Seller Admin manages day-to-day seller administration within the permissions granted by TTC.

Typical capabilities include:

```text
catalog/service configuration
pricing
branches
orders
operations
customer-facing configuration
```

Do not automatically grant platform-level administrative powers.

---

# 18. Seller Staff

Seller Staff receives operational access according to assigned permissions.

Examples:

```text
order.read
order.confirm
order.process
order.cancel
pickup.manage
price.adjust
```

Staff must not automatically receive:

```text
user management
permission management
commercial administration
platform configuration
```

unless explicitly authorized.

---

# 19. Seller Viewer

Seller Viewer is read-only where supported.

The viewer must not be able to:

```text
modify configuration
change prices
change order state
manage users
modify permissions
```

unless an explicit permission is later introduced.

---

# 20. Permission Management

Seller users cannot invent permissions.

TTC defines the available permission vocabulary.

Seller administrators can assign only permissions that the platform makes available to that seller type.

Permission management itself is permission-controlled.

---

# 21. Permission Dependencies

Some permissions may depend on other permissions.

For example:

```text
price.adjust
```

is an independent sensitive capability.

Locked-price correction uses:

```text
price.adjust_locked
```

This capability is not automatically available to every Full-Access Seller.

TTC must explicitly enable it.

---

# 22. Immediate Permission Revocation

If TTC revokes a seller capability:

```text
effective access
```

must change immediately.

For example:

```text
price.adjust_locked
```

being revoked means all affected seller users immediately lose that capability.

An in-progress exception workflow must not bypass the revocation.

A fresh authorization is required.

---

# 23. Master Catalog Boundary

TTC owns the master catalog.

Seller does not create arbitrary master catalog items.

The seller selects from TTC-supported master catalog entities.

Conceptually:

```text
TTC Master Catalog
        ↓
Seller selects supported items
        ↓
Seller configures presentation/service usage
```

---

# 24. Missing Catalog Item

If a seller requires an item that does not exist:

```text
Seller
   ↓
Request new master item
   ↓
TTC reviews
   ↓
TTC adds master catalog item
   ↓
Seller selects it
```

Do not allow sellers to bypass the master catalog.

---

# 25. Master Catalog Updates

When TTC changes a master catalog entity:

```text
future seller configuration
```

may receive the new capability according to eligibility rules.

However:

> Existing seller configuration and historical orders must not be silently corrupted.

Historical orders remain protected by snapshots.

---

# 26. Seller Presentation Customization

Sellers may customize supported presentation fields.

Examples:

```text
name
image
description
```

A seller may use:

```text
TTC default
```

or:

```text
seller-customized value
```

Customization is field-specific.

Therefore:

```text
custom name
+
TTC image
+
custom description
```

may coexist.

---

# 27. Resetting Customization

Each customizable field should be independently resettable.

Example:

```text
Custom name
Custom image
TTC description
```

The seller can reset only the name:

```text
name → TTC default
image → remains custom
description → remains TTC default
```

Do not force all fields back to TTC defaults when one field is reset.

---

# 28. Seller Services

A seller configures which supported services it offers.

Conceptually:

```text
Master Service
      ↓
Seller Service Configuration
      ↓
Branch availability
```

The seller does not invent an entirely independent service definition outside the master platform model.

---

# 29. Service Item Configuration

Seller services can expose supported master catalog items.

The seller can configure:

```text
availability
presentation
pricing
measurement
pickup configuration
```

according to platform capabilities.

---

# 30. Service Add-ons

Supported master add-ons may be enabled for seller services.

The same add-on can have seller-specific pricing/configuration.

Historical orders retain the original add-on snapshot.

---

# 31. Billing Measurement

The seller determines the billing measurement supported by a service from TTC-supported options.

Examples:

```text
PER_PIECE
PER_KG
```

Billing measurement is separate from pickup capture.

Do not infer billing method from the driver's captured data.

---

# 32. Pickup Capture Configuration

A seller can configure supported pickup capture behavior.

Examples:

```text
weight
item count
condition
damage evidence
notes
photos
```

The driver follows the configured workflow.

The driver does not invent billing rules.

---

# 33. Pickup Templates

Supported pickup templates can include:

```text
weight only
count only
weight + count
condition
damage photos/evidence
notes
```

The exact required fields are configuration-driven.

Marketplace behavior is governed by TTC.

Full-Access Sellers may configure supported behavior.

---

# 34. Customer Approval

Customer approval for pickup discrepancies or final pricing is configuration-driven.

For Marketplace Sellers:

```text
TTC marketplace configuration
```

controls the behavior.

For Full-Access Sellers:

```text
seller configuration
```

controls supported options within TTC boundaries.

---

# 35. Pricing Configuration

Seller pricing is configured through the TTC Pricing Engine.

The seller does not directly calculate order totals.

The Pricing Engine remains authoritative.

Conceptually:

```text
Seller Pricing Configuration
          ↓
Pricing Engine
          ↓
Authoritative Calculation
          ↓
Order Snapshot
```

---

# 36. No Duplicate Pricing Logic

Seller Web, Seller Mobile, Marketplace Web, Marketplace Mobile, Driver Mobile, and backend services must not independently calculate commercial totals.

They consume authoritative Pricing Engine results.

---

# 37. Price Policies

TTC supports configurable price-change policies.

Both seller types can configure supported price-change policy behavior.

However:

> Sellers do not define arbitrary policy eligibility conditions.

TTC defines eligibility rules.

---

# 38. Policy Assignment

The seller does not manually select which price-change policy applies to every transaction.

The platform automatically determines the applicable policy based on TTC-defined eligibility.

---

# 39. Policy Visibility

Seller users can see full applicable policy details, including:

```text
policy name
description
eligibility
existing-order behavior
recalculation behavior
customer approval
price rejection behavior
```

This is transparency, not arbitrary policy creation.

---

# 40. Policy Versioning

Price policy versions are immutable once published.

New behavior requires:

```text
new version
```

Published versions are retained permanently.

A newer published version supersedes an older version.

---

# 41. Existing Unlocked Orders

When a new applicable price policy version is published:

```text
existing order
+
not final-price-approved
```

automatically moves to the new applicable policy.

The current policy snapshot updates.

The previous application remains in immutable history/audit.

---

# 42. Immediate Recalculation

When an unlocked order moves to a new price policy:

```text
new policy
+
latest pickup data
+
Pricing Engine
```

produces the current calculation.

If the price changes, customer approval is required again.

If the price does not change, the system does not require approval solely because the policy version changed.

---

# 43. Lower Price

A lower recalculated price also requires explicit customer approval.

The platform must not silently lock a new lower commercial value.

---

# 44. Price Rejection

If the customer rejects the recalculated price:

```text
configured price-rejection behavior
```

is applied.

Possible supported outcomes include:

```text
PRICE_DISPUTE
REVIEW
CANCEL
```

The platform must never silently restore the previously unapproved price.

---

# 45. Price Dispute

Once an order enters:

```text
PRICE_DISPUTE / REVIEW
```

the current price policy is frozen for that dispute.

Later policy publications must not silently alter the active dispute.

---

# 46. Manual Price Adjustment

Both seller types may support controlled manual price adjustment.

Permission:

```text
price.adjust
```

The resolver may:

```text
accept calculated price
```

or:

```text
make controlled manual adjustment
```

The original calculation is never overwritten.

Every adjustment requires:

```text
reason code
audit
```

and customer approval.

---

# 47. Manual Adjustment Limits

TTC defines supported adjustment limits.

Limits may vary by:

- seller
- service

The seller may configure a limit only within TTC-supported boundaries.

---

# 48. Adjustment Limit Types

Supported limits may be:

- percentage

or:

- fixed amount

If both are configured:

```text
effective limit
=
smaller/safer permitted limit
```

---

# 49. Adjustment Direction

Seller configuration may specify whether supported adjustments can:

- increase price
- decrease price

or both.

The configuration remains bounded by TTC limits.

---

# 50. Customer Approval

Every manual price adjustment requires explicit customer approval.

No manual adjustment becomes final merely because a seller user entered it.

---

# 51. Price Approval Timeout

If the customer does not respond:

```text
configured timeout
↓
PRICE_EXPIRED
↓
configured closure/cancellation behavior
```

Do not auto-accept the price.

Do not silently restore the old price.

---

# 52. Locked Price

Once the customer approves the final commercial price:

```text
PRICE LOCKED
```

The price becomes historically immutable.

Normal seller configuration changes must not modify it.

---

# 53. Locked Price Exception

Exceptional corrections after price lock require a dedicated workflow.

Permission:

```text
price.adjust_locked
```

Requirements:

- authorized actor
- mandatory reason
- full audit
- new price version/history
- customer approval

The original locked calculation remains preserved.

---

# 54. Locked Adjustment Authorization

Marketplace Seller:

```text
TTC-authorized marketplace operations
```

Full-Access Seller:

```text
seller-authorized user
+
price.adjust_locked
```

TTC explicitly enables this capability for Full-Access Sellers.

---

# 55. Locked Price History

Every locked-price correction creates:

```text
new immutable price version/history entry
```

The original locked price is never overwritten.

---

# 56. Customer Price History

Customer-facing history contains only customer-safe information.

It may show:

- previous price
- new price
- customer-safe reason

It must not expose:

- internal authorization data
- internal audit details
- internal reason codes

---

# 57. Adjustment Reasons

TTC maintains standardized reason definitions.

A price adjustment contains:

- primary reason
- optional secondary reasons
- approved explanatory text

The internal reason code is not directly exposed to the customer.

---

# 58. Reason Versioning

Customer-facing reason definitions are versioned.

Lifecycle:

```text
DRAFT
   ↓
PUBLISHED
   ↓
ACTIVE
   ↓
RETIRED
```

Published definitions are immutable.

Retirement requires a replacement version.

Historical orders retain the historical description.

---

# 59. Reason Selection

The platform automatically selects the current published version.

The resolver selects:

```text
reason code
```

not a reason version.

---

# 60. Reason Structure

Multiple reasons may be active.

An adjustment contains:

- one primary reason
- optional secondary reasons

Customer-facing wording uses TTC-controlled templates.

---

# 61. Resolver Explanation

Resolver-entered explanatory text is not arbitrary customer-facing content.

It is validated/sanitized and populated only into TTC-approved placeholders.

This prevents internal or unsafe content from being exposed to customers.

---

# 62. Seller Order Operations

Seller users with appropriate permissions can operate orders.

Core order lifecycle:

```text
PENDING
   ↓
CONFIRMED
   ↓
IN_PROGRESS
   ↓
COMPLETED
```

Seller rejection:

```text
PENDING
   ↓
CANCELLED
reason = SELLER_REJECTED
```

Customer cancellation:

```text
PENDING / CONFIRMED
   ↓
CANCELLED
reason = CUSTOMER_CANCELLED
```

Seller cancellation after confirmation:

```text
CONFIRMED
   ↓
CANCELLED
reason = SELLER_CANCELLED
```

---

# 63. Seller Order Acceptance

Authorized seller users can accept:

```text
PENDING → CONFIRMED
```

Acceptance must be:

- permission-controlled
- tenant-scoped
- seller-scoped
- audited
- concurrency-safe

Repeated acceptance must not create duplicate successful transitions.

---

# 64. Seller Order Rejection

Authorized seller users can reject:

```text
PENDING → CANCELLED
```

with:

```text
actor_type = SELLER
reason_code = SELLER_REJECTED
```

Do not create a separate top-level `REJECTED` order state unless a future business requirement explicitly changes this decision.

---

# 65. Seller Cancellation

Seller cancellation after acceptance may occur:

```text
CONFIRMED → CANCELLED
```

with:

```text
reason_code = SELLER_CANCELLED
```

Do not allow arbitrary cancellation from:

- IN_PROGRESS
- COMPLETED

under the current Phase 7 baseline.

---

# 66. Order Start

Authorized seller operations can move:

```text
CONFIRMED → IN_PROGRESS
```

This action is explicit.

It is not an arbitrary status PATCH.

Where an exceptional reverse transition is supported:

```text
IN_PROGRESS → CONFIRMED
```

requires:

- mandatory reason
- audit
- authorization

---

# 67. Order Completion

Normal completion is tied to operational fulfillment.

The normal flow is:

```text
driver delivery/drop-off
↓
delivery verification
↓
COMPLETED
```

Seller staff/admin may have an exception completion capability where explicitly authorized.

Exception completion requires:

- mandatory reason
- audit

---

# 68. Reservice Boundary

Reservice is a separate case/job associated with the original completed order.

The original order remains:

```text
COMPLETED
```

Reservice must not mutate the original order back into an active operational state.

---

# 69. Driver Assignment

Seller operations participate in driver assignment where the workflow requires it.

Rules established by TTC include:

- assignment is authoritative
- driver does not accept/reject

If a driver becomes unavailable before duty starts:

```text
automatic reassignment attempt
+
seller operations alert
```

If an assigned driver becomes unavailable after assignment:

```text
manual seller-operations intervention
```

---

# 70. Manual Driver Reassignment

Authorized seller staff can manually reassign.

A manual reassignment requires:

- previous driver
- new driver
- actor
- timestamp
- mandatory reason

The previous assignment remains in history.

The newest assignment is the active assignment.

---

# 71. Driver Notification

Driver assignment generates an immediate informational notification.

Supported channels may include:

- Push
- In-app
- SMS
- WhatsApp

according to configuration.

Notification failure does not invalidate the assignment.

---

# 72. Customer Driver Visibility

After assignment, customer may see:

- driver name
- vehicle details
- contact option
- actual driver phone

This follows established customer-facing operational behavior.

---

# 73. Driver Customer Visibility

After assignment, driver receives the operational information required to perform the duty, including:

- customer name
- customer phone
- customer address
- order details
- current applicable amount

Access remains limited to the assigned operational context.

---

# 74. Pickup Verification

Seller configuration determines supported pickup verification.

Driver may capture:

- item type
- quantity
- weight
- condition
- damage
- photos
- notes

Only permitted master catalog entries may be selected.

---

# 75. New Pickup Item

If the driver discovers an item not originally included:

```text
driver selects supported master catalog item
```

If the item is not available:

```text
seller requests master catalog addition
↓
TTC adds item
↓
seller enables/selects item
```

Driver does not create arbitrary catalog definitions.

---

# 76. Pickup Quantity Changes

Quantity changes follow configured customer-approval behavior.

Default baseline:

```text
customer approval required
```

for material pickup changes unless configuration explicitly supports another behavior.

---

# 77. Pickup Item Removal

Removing an originally ordered item follows configured customer-approval behavior.

Default baseline:

```text
customer approval required
```

---

# 78. Pickup Dispute

If customer does not approve a pickup discrepancy:

```text
PICKUP DISPUTE / REVIEW
```

may be entered according to configured behavior.

The order must not silently continue using an unapproved commercial interpretation.

---

# 79. Damage Evidence

If damage reporting is enabled:

```text
photos/evidence
```

are mandatory by default.

The exact requirement can be configured within TTC-supported boundaries.

---

# 80. Payment Configuration

Seller payment configuration uses TTC's payment architecture.

Supported methods can include:

- online gateway
- cash
- mixed payment

The seller does not implement payment processing independently inside the seller application.

The platform/payment domain remains authoritative.

---

# 81. Payment Policy

Payment policy determines when payment is due.

Payment occurs after pickup/final pricing according to the applicable policy.

Seller configuration may select supported policy behavior.

TTC controls policy eligibility.

---

# 82. Driver Assignment and Payment

Driver assignment eligibility may depend on payment status.

Conceptually:

```text
UNPAID
PARTIALLY_PAID
PAID
      ↓
Assignment eligibility
```

The seller does not bypass platform payment-policy rules through frontend manipulation.

---

# 83. Commercial Seller Models

Marketplace Sellers use one of two mutually exclusive TTC commercial models:

- Percentage Commission

or:

- Monthly Subscription / Platform Fee

A seller cannot simultaneously operate under both models for the same applicable commercial period/transaction.

---

# 84. Percentage Commission

Commission is based on:

```text
final customer transaction amount actually paid
```

after seller discounts/promotions.

Commission is created when payment succeeds.

TTC commission GST:

```text
18%
```

Refunds reverse commission/GST proportionally.

Commercial configuration is snapshotted for historical transactions.

---

# 85. Monthly Subscription

Under subscription model:

```text
fixed monthly platform fee
```

applies.

There is:

```text
no per-transaction TTC commission
```

GST:

```text
18%
```

Auto-recurring billing is the default where supported, with manual fallback.

---

# 86. Seller Model Switching

A seller may switch commercial models later.

The new model applies to future applicable transactions.

Historical commercial records retain the model under which they were created.

Do not retroactively rewrite commercial history.

---

# 87. Gateway Fees

Gateway fees are separate from TTC commission.

They may be deducted from seller settlement.

For TTC gateway:

- 15-day cooling period
- settlement every Monday

For seller's own gateway:

- direct/instant
- no TTC hold

The exact gateway integration belongs to the payment/settlement implementation.

---

# 88. Settlement Boundary

Seller Platform may expose settlement information when supported, but settlement calculations belong to the commercial/payment domains.

Do not duplicate settlement calculations inside Seller UI.

---

# 89. Monthly Billing

Seller monthly platform billing baseline:

- invoice: 1st
- due: 5th
- default grace/due window: 5 days

Penalty default:

```text
₹1,000/day
```

Configuration may change supported values.

---

# 90. Seller Restriction Levels

Overdue seller billing may progress:

```text
WARNING
   ↓
MARKETPLACE_RESTRICTED
   ↓
WHITE_LABEL_RESTRICTED
   ↓
FULL_SUSPENSION
```

The restriction level is a platform-controlled business state.

---

# 91. Marketplace Restriction

When marketplace access is restricted:

```text
new marketplace activity
```

is restricted according to platform policy.

Existing operational orders continue.

PENDING marketplace orders may be cancelled with:

```text
SELLER_RESTRICTED
```

and the customer may select another seller.

---

# 92. White-Label Restriction

When white-label access is restricted:

```text
white-label customer experience
```

may be restricted according to the applicable seller billing policy.

Do not automatically treat white-label restriction as marketplace reselection.

---

# 93. Full Suspension

Full suspension prevents normal seller operation according to platform policy.

Existing operational orders are handled according to their current lifecycle rather than being arbitrarily destroyed.

---

# 94. Marketplace Reselection

When a marketplace seller becomes restricted while a PENDING marketplace order exists:

```text
old order
→ CANCELLED
reason = SELLER_RESTRICTED
```

The customer may select another seller.

Reselection creates:

- new order ID
- new order number

The previous order remains preserved.

Optional relationship:

```text
reselected_from_order_id
```

may connect the new order to the previous order.

---

# 95. White-Label Pending Orders

A Full-Access Seller's PENDING order does not enter marketplace reselection.

The customer remains within the seller-specific customer experience.

The applicable seller restriction workflow determines what happens.

---

# 96. No Refund for Pre-Payment Restriction

Because payment occurs after pickup/final pricing under the established payment flow:

```text
PENDING marketplace order
→ SELLER_RESTRICTED
```

does not require a payment refund where no payment has occurred.

---

# 97. Restriction History

The platform must preserve restriction history containing relevant information such as:

- restriction level
- reason
- overdue amount
- penalties
- effective time
- payment/recovery time
- restoration actor
- restoration timestamp

Audit requirements apply.

---

# 98. Seller Recovery

Recovery may be:

- automatic

or:

- manual approval

according to platform configuration.

Restoration must preserve the historical restriction record.

---

# 99. Seller Configuration Principle

Seller configuration is bounded configuration.

The seller can configure:

```text
supported TTC capabilities
```

but cannot redefine:

- platform architecture
- security model
- master catalog ownership
- permission vocabulary
- core domain invariants

---

# 100. No Seller-Specific Code Forks

Do not create:

- seller-a backend
- seller-b backend
- seller-c frontend fork

The platform uses:

```text
shared code
+
tenant configuration
+
seller configuration
+
application configuration
```

White-label behavior is runtime/configuration-driven.

---

# 101. Seller-Web

`apps/seller-web` is the primary seller administration surface.

It should provide supported areas such as:

- Dashboard
- Orders
- Branches
- Services
- Catalog Configuration
- Pricing
- Customers
- Pickup/Operations
- Users
- Roles
- Permissions
- Commercial
- Payment Configuration
- Branding
- White-Label Configuration
- Settings
- Audit/History

Exact navigation should follow implemented capabilities and permissions.

---

# 102. Seller-Mobile

`apps/seller-mobile` provides mobile access to appropriate seller operations.

It uses the same backend APIs and shared types.

It must not implement a separate seller business model.

---

# 103. Seller UI Authorization

Seller UI may hide unavailable actions, but frontend visibility is not authorization.

Every operation must be authorized server-side.

Example:

```text
Hide price.adjust button
```

does not replace backend:

```text
permission check
```

---

# 104. Seller API Boundary

Seller APIs should follow:

```text
authenticated user
↓
TenantContext
↓
SellerContext
↓
permission check
↓
resource validation
↓
domain service
↓
repository
```

Never trust:

- client seller_id
- client tenant_id
- client role
- client permission

as authorization.

---

# 105. Seller Auditability

Important seller actions must be auditable.

Examples:

- seller created
- seller activated
- branch created
- branch disabled
- service enabled
- pricing changed
- user added
- role changed
- permission changed
- order accepted
- order rejected
- order cancelled
- price adjusted
- locked price adjusted
- driver reassigned
- restriction applied
- restriction removed

Audit must follow platform redaction/security rules.

---

# 106. Seller Data Isolation

Test at minimum:

- Seller A → Seller A resources = allowed
- Seller A → Seller B resources = denied
- Tenant A → Tenant B resources = denied
- Seller user → unrelated customer data = denied
- Customer → seller administration = denied

Test direct-ID injection.

---

# 107. Historical Integrity

Seller configuration changes must never silently rewrite historical:

- orders
- pricing
- catalog snapshots
- customer snapshots
- addresses
- commercial records
- payments
- settlements

Historical transaction records remain authoritative for the transaction that occurred.

---

# 108. Seller Platform and Marketplace Boundary

Marketplace:

- customer discovery
- seller discovery
- customer order creation
- customer-facing lifecycle

Seller Platform:

- seller configuration
- seller operations
- seller users
- seller permissions
- seller services
- seller pricing
- seller order management

Neither frontend owns the underlying business rules.

---

# 109. Seller Platform and White-Label Boundary

Seller Platform configures:

- brand
- domain
- supported customer experience
- service presentation
- customer-facing configuration

White-label runtime consumes that configuration.

White-label does not create an independent seller business backend.

---

# 110. Seller Platform and Driver Boundary

Seller Platform manages:

- operational assignment
- supported pickup configuration
- operational exceptions

Driver Mobile executes:

- assigned duty
- pickup verification
- delivery workflow

Driver does not become a seller administrator.

---

# 111. Seller Platform and Payment Boundary

Seller Platform configures supported payment behavior.

Payment execution belongs to the payment domain.

Do not place gateway transaction logic directly inside Seller UI/business code.

---

# 112. Seller Platform and Billing Boundary

Seller Platform may display:

- subscription status
- commission information
- billing status
- restriction status

but Billing/Commercial domains own authoritative financial calculations.

---

# 113. Seller Platform and Fulfillment Boundary

Seller Platform initiates/manages supported operational workflows.

Fulfillment remains a distinct domain.

Do not turn Seller Platform into a monolithic fulfillment engine.

---

# 114. Configuration Resolution

Where configuration inheritance exists, use the established TTC precedence model.

Conceptually:

```text
Platform Defaults
      ↓
Tenant/Seller
      ↓
Tenant Application
```

More specific configuration overrides less specific configuration according to the existing resolver.

Do not create independent configuration-resolution logic inside each application.

---

# 115. Shared Types

Seller contracts should use shared TypeScript types from:

```text
packages/types
```

Do not duplicate:

- Seller
- Branch
- SellerUser
- Role
- Permission
- Order
- Pricing
- Service
- Catalog

types independently across applications.

---

# 116. Seller Backend Architecture

Seller business logic belongs in backend domain/application services.

Frontend responsibilities:

- presentation
- interaction
- state display
- API consumption

Backend responsibilities:

- authorization
- validation
- business rules
- pricing
- state transitions
- tenant isolation
- transactions
- audit

---

# 117. Seller Transaction Safety

Important mutations must use proper transactions.

Examples:

- order acceptance
- order rejection
- price adjustment
- user permission change
- branch state change
- seller restriction
- driver reassignment

Do not allow partially committed business operations.

---

# 118. Seller Concurrency

Concurrent seller actions must be safe.

Example:

- Seller User A accepts PENDING order
- Seller User B rejects same order

Only one valid state transition may succeed.

Database transaction/locking strategy must protect the state transition.

---

# 119. Seller API Style

Use explicit domain actions for state-changing operations.

Prefer:

```text
POST /orders/{id}/confirm
POST /orders/{id}/reject
POST /orders/{id}/cancel
POST /orders/{id}/start
POST /orders/{id}/complete
```

over:

```text
PATCH /orders/{id}
{
  "status": "..."
}
```

where arbitrary status mutation could bypass domain rules.

---

# 120. Seller Product Principle

The Seller Platform should answer:

> “What can this seller configure and operate?”

It must not answer:

> “What software can this seller invent?”

TTC remains a configuration-driven SaaS platform.

---

# 121. Seller Platform Success Criteria

Seller Platform is architecturally correct when:

- [ ] Seller tenancy is isolated
- [ ] Seller identity is not duplicated
- [ ] Seller branches are isolated
- [ ] Seller users use RBAC
- [ ] Seller permissions are controlled
- [ ] Marketplace Seller behavior is supported
- [ ] Full-Access Seller behavior is supported
- [ ] Master catalog remains TTC-owned
- [ ] Seller services use supported master entities
- [ ] Seller pricing uses Pricing Engine
- [ ] No duplicate pricing logic exists
- [ ] Seller orders are properly scoped
- [ ] Seller acceptance/rejection is explicit
- [ ] Seller cancellation is controlled
- [ ] Pickup configuration is supported
- [ ] Driver operations remain bounded
- [ ] Payment configuration is separated from payment execution
- [ ] Commercial configuration is separated from financial calculations
- [ ] Seller restrictions are auditable
- [ ] Historical transactions remain immutable
- [ ] White-label behavior is configuration-driven
- [ ] No seller-specific code forks exist
- [ ] Shared types are reused
- [ ] Backend remains authoritative
- [ ] Frontend remains presentation/orchestration

---

# 122. Implementation Boundary

This prompt does not authorize implementing every seller capability at once.

Implementation must follow the TTC vertical-slice strategy:

```text
Business Capability
        ↓
Backend Domain/API
        ↓
Shared Types
        ↓
Seller-Web
        ↓
Seller-Mobile where applicable
        ↓
Integration
        ↓
Tests
        ↓
Validation
        ↓
Focused Git Commit
```

Dependencies must be respected.

Do not build UI that depends on nonexistent backend contracts.

Do not build backend APIs without defining their consuming product behavior.

---

# 123. Initial Seller Implementation Dependency

The seller platform depends on established foundations:

```text
Identity/Auth
    ↓
TenantContext
    ↓
RBAC
    ↓
Seller/Tenant model
    ↓
Customization
    ↓
Catalog
    ↓
Pricing
    ↓
Marketplace
    ↓
Order
```

Later capabilities depend on:

```text
Order
    ↓
Pickup
    ↓
Fulfillment
    ↓
Payment
    ↓
Commercial/Billing
    ↓
Reservice
```

---

# 124. Explicitly Deferred

Do not treat the following as Seller Platform implementation requirements unless their dependency phase is being implemented:

- Payment gateway implementation
- Refund execution
- Invoice generation
- Accounting
- Vendor settlement
- Driver dispatch engine
- Live tracking
- Route optimization
- Inventory
- Warehouse
- Notifications infrastructure
- WhatsApp infrastructure
- SMS infrastructure
- Kafka
- RabbitMQ
- Kubernetes
- OpenSearch
- Microservices

---

# 125. Final Seller Platform Model

The final conceptual model is:

```text
                         TTC PLATFORM
                              │
                    ┌─────────┴─────────┐
                    │                   │
             MARKETPLACE SELLER   FULL-ACCESS SELLER
                    │                   │
                    │                   │
              TTC Marketplace      Seller Brand
                    │                   │
                    └─────────┬─────────┘
                              │
                         SELLER TENANT
                              │
              ┌───────────────┼───────────────┐
              │               │               │
           Branches         Users        Configuration
              │               │               │
              │             RBAC              │
              │               │               │
              └───────────────┼───────────────┘
                              │
                       Catalog / Services
                              │
                           Pricing
                              │
                            Orders
                              │
                         Operations
                              │
                    ┌─────────┴─────────┐
                    │                   │
                Marketplace         White-Label
                    │                   │
                 Customers           Customers
```

The core principle is:

> **One TTC platform, shared seller domain, tenant isolation, configuration-driven behavior, and two seller operating models — without seller-specific code forks.**
