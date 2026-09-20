# THE TEXTILE CARE — MARKETPLACE BUSINESS & PRODUCT BASELINE

## Purpose

Define the complete business and product behavior of the **TTC Marketplace**.

The marketplace is the customer-facing multi-seller discovery, selection, ordering, pricing, payment, delivery, and reservice experience.

This prompt must be implemented using the Master Platform Architecture.

Do not create marketplace-specific backend business logic that duplicates domain services.

---

# 1. Marketplace Definition

The TTC Marketplace is a multi-seller customer platform.

Conceptually:

```text
Customer
   ↓
TTC Marketplace
   ↓
Discover Sellers
   ↓
Select Seller / Branch
   ↓
Browse Services
   ↓
Select Items / Add-ons
   ↓
Pricing
   ↓
Create Order
   ↓
Seller Decision
   ↓
Pickup
   ↓
Final Pricing
   ↓
Payment
   ↓
Delivery
   ↓
Reservice where eligible
```

The marketplace is not itself the source of truth for pricing, orders, payment, or fulfillment.

It consumes the authoritative backend domains.

---

# 2. Marketplace Applications

The marketplace initially has:

```text
marketplace-web
marketplace-mobile
```

Both must use the same backend APIs and shared domain contracts.

Do not create separate business rules for web and mobile.

---

# 3. Marketplace Customer

A customer can:

```text
discover sellers
view seller services
view branches
view catalog items
view pricing
select services
select items
select add-ons
create orders
view orders
cancel eligible orders
approve price changes
make payments
track operational progress
request reservice
```

All protected operations are authenticated and customer-scoped.

---

# 4. Seller Discovery

Marketplace discovery must expose only sellers that are:

```text
active
marketplace eligible
available to the customer/region where applicable
```

Inactive or marketplace-restricted sellers must not be presented as normally orderable.

Marketplace availability is determined by backend authority.

---

# 5. Marketplace Seller Eligibility

A seller may be technically active in TTC but not eligible for marketplace ordering.

The marketplace must distinguish:

```text
Seller exists
Seller active
Seller marketplace eligible
Seller operationally available
```

Do not infer marketplace eligibility from seller existence alone.

---

# 6. Branch Selection

A customer may select a seller branch where the seller exposes multiple branches.

The backend must verify:

```text
branch belongs to seller
branch belongs to tenant
branch is active
branch is marketplace eligible
```

A client must never be able to combine:

```text
Seller A
+
Branch B belonging to Seller B
```

---

# 7. Catalog Presentation

Marketplace customers see seller-configured catalog/service presentation.

The underlying master catalog remains controlled by TTC.

Conceptually:

```text
TTC Master Catalog
        ↓
Seller Configuration
        ↓
Marketplace Presentation
```

Seller presentation may customize supported fields such as:

```text
name
image
description
```

according to the platform configuration rules.

---

# 8. Master Catalog Rule

Sellers do not create arbitrary master catalog items.

If an item is missing:

```text
Seller
   ↓
Request master item
   ↓
TTC review
   ↓
TTC adds master item
   ↓
Seller can configure/use it
```

Marketplace must only expose valid catalog items.

---

# 9. Service Discovery

Customers select a seller service.

A service may define:

```text
supported catalog items
supported add-ons
billing measurement
pickup template
pricing configuration
availability
```

Marketplace must display only services currently eligible for ordering.

---

# 10. Billing Measurement

Marketplace presentation must distinguish estimated customer input from actual operational measurement.

Examples:

```text
PER_KG
PER_PIECE
COUNT
```

The exact supported measurement types come from the Pricing/Service domain.

Marketplace must not independently determine billing calculations.

---

# 11. Pickup Measurement Example

A KG service may allow:

```text
Shirt × 3
Pant × 3
Sock Set × 3

Weight:
4.6 KG
```

while billing:

```text
4.6 × ₹80/KG = ₹368
```

Pickup capture and billing measurement are separate concepts.

Marketplace may show the expected measurement, but the authoritative final measurement comes from operational pickup verification.

---

# 12. Initial Price

Marketplace may display an estimated price before order creation.

The displayed price is not automatically authoritative.

At order creation:

```text
Marketplace Preview
       ↓
Order Request
       ↓
Backend validation
       ↓
Pricing Engine
       ↓
Authoritative pricing
```

The client must never submit a trusted final total.

---

# 13. Price Change at Order Creation

If the marketplace preview becomes stale:

```text
Customer saw:
₹500

Current authoritative price:
₹550
```

the backend must not silently create the order at ₹500.

Return the platform's structured price-change conflict.

Conceptually:

```text
409 PRICE_CHANGED
```

The marketplace then shows the current pricing and asks the customer to confirm according to the established UX.

---

# 14. Order Creation

Customer order creation follows:

```text
Customer
   ↓
Select seller
   ↓
Select branch
   ↓
Select service
   ↓
Select items
   ↓
Select add-ons
   ↓
Optional address
   ↓
Order request
   ↓
Backend validation
   ↓
Pricing Engine
   ↓
Order creation
   ↓
PENDING
```

The first persisted order state is:

```text
PENDING
```

---

# 15. Meaning of PENDING

Marketplace must clearly communicate that:

> `PENDING` means the customer successfully submitted the order and the seller has not yet accepted it.

It does not mean:

```text
payment pending
```

It does not mean:

```text
draft
```

---

# 16. Seller Decision

After creation:

```text
PENDING
   ├── Seller accepts → CONFIRMED
   │
   ├── Seller rejects → CANCELLED
   │
   └── Customer cancels → CANCELLED
```

Seller rejection is represented as cancellation with structured reason/history:

```text
actor_type = SELLER
reason_code = SELLER_REJECTED
```

Customer cancellation:

```text
actor_type = CUSTOMER
reason_code = CUSTOMER_CANCELLED
```

Marketplace must present these outcomes clearly to the customer.

---

# 17. Order Lifecycle Presented to Customer

Core lifecycle:

```text
PENDING
   ↓
CONFIRMED
   ↓
IN_PROGRESS
   ↓
COMPLETED
```

Terminal cancellation:

```text
CANCELLED
```

Do not expose internal backend implementation details unnecessarily.

Customer UX may provide human-readable labels.

---

# 18. Seller Rejection Experience

When a seller rejects an order:

```text
PENDING
   ↓
CANCELLED
```

The customer should understand that:

> The seller was unable to accept the order.

Where an approved customer-facing reason is available, show it.

Do not expose internal reason codes, permission names, or operational audit information.

---

# 19. Marketplace Cancellation

Customer may cancel only when the order is in an eligible state.

Initial supported cancellation:

```text
PENDING → CANCELLED
CONFIRMED → CANCELLED
```

Do not allow customer cancellation from:

```text
IN_PROGRESS
COMPLETED
```

unless a later approved business rule changes this.

---

# 20. Order History

Customers can view:

```text
order number
seller
branch
items
add-ons
quantities
prices
discounts
surcharges
tax
grand total
currency
status
timestamps
```

Historical commercial information must come from the Order's persisted snapshots and totals.

Do not recalculate historical orders using current catalog/pricing configuration.

---

# 21. Customer Snapshot

Order creation may snapshot appropriate customer display data.

The marketplace should continue to use the canonical customer domain for current customer information.

Historical order display must rely on order snapshots where required.

---

# 22. Address

If an order requires a customer address:

```text
Customer Address
      ↓
Verify ownership
      ↓
Snapshot into Order
```

Customer cannot submit another customer's address ID.

After order creation, changes to the customer's current address must not rewrite the order's historical address snapshot.

---

# 23. Price Policy

Price-change policies are platform-defined capabilities.

Sellers may configure supported policy options within TTC-defined boundaries.

Sellers do not create arbitrary policy logic.

The marketplace consumes the policy assigned to the order by the backend.

---

# 24. Policy Versioning

TTC price-policy versions are immutable after publication.

When a new applicable version is published:

```text
Existing unlocked order
        ↓
May move to new policy
        ↓
Pricing Engine recalculates
```

Historical orders already commercially locked remain protected.

---

# 25. Price Recalculation

If a policy change affects an unlocked order:

```text
New policy
   +
Latest pickup data
   ↓
Pricing Engine
   ↓
New calculation
```

Do not implement pricing calculations inside marketplace web/mobile.

---

# 26. Price Approval

If recalculation changes the customer price:

```text
New price
   ↓
Customer notified
   ↓
Customer approval REQUIRED
```

This applies even if the price decreases.

The marketplace must not automatically approve a lower price.

---

# 27. Price Dispute

If the customer rejects a new price:

```text
PRICE_DISPUTE / REVIEW
```

The exact dispute representation is controlled by the backend domain.

Marketplace provides the customer interface for:

```text
view proposed price
view customer-safe explanation
accept/reject
```

---

# 28. Manual Price Adjustment

An authorized resolver may:

```text
accept existing calculated price
```

or:

```text
make controlled manual adjustment
```

Manual adjustments:

* require authorization
* require reason
* are fully audited
* remain within TTC-supported limits
* require customer approval

Marketplace must never allow a customer to directly set a price.

---

# 29. Manual Adjustment Limits

TTC defines supported adjustment boundaries.

Seller configuration may select supported limits.

Limits may support:

```text
percentage
fixed amount
```

If both are configured:

```text
effective maximum =
smaller / safer limit
```

Direction may be configured:

```text
increase allowed
decrease allowed
both
```

The exact configured policy is enforced by backend authority.

---

# 30. Customer Approval After Manual Adjustment

Any manual adjustment produces a proposed commercial price.

Customer approval is mandatory.

```text
Manual Adjustment
       ↓
New Proposed Price
       ↓
Customer Approval
       ↓
PRICE LOCKED
```

No manual adjustment becomes final without approval.

---

# 31. Customer Non-Response

If the customer does not respond to an adjusted price:

```text
PRICE_DISPUTE / REVIEW
        ↓
Configured response timeout
        ↓
No response
        ↓
PRICE_EXPIRED
        ↓
Configured closure/cancellation behavior
```

Do not:

```text
auto-accept
auto-restore old price
```

The timeout is seller-configurable within TTC-supported options.

The selected timeout is snapshotted for the active dispute.

---

# 32. Price Lock

After customer approval:

```text
PRICE LOCKED
```

Normal pricing/policy changes cannot alter the locked price.

---

# 33. Locked-Price Exception

A locked price may only be corrected through a dedicated exception workflow.

```text
PRICE_LOCKED
     ↓
Exception request
     ↓
Authorization
     ↓
Mandatory reason
     ↓
Correction
     ↓
Customer approval again
     ↓
New PRICE LOCKED
```

The original locked price remains preserved.

---

# 34. Locked-Price Authorization

Normal:

```text
price.adjust
```

does not permit locked-price corrections.

A separate capability is used:

```text
price.adjust_locked
```

For Marketplace Sellers:

```text
TTC-authorized marketplace operations
```

perform the exception.

For Full-Access Sellers:

```text
Seller-authorized user
+
price.adjust_locked
```

may perform it, but TTC must explicitly enable this capability for the seller.

---

# 35. Locked-Price Capability Revocation

TTC can immediately revoke `price.adjust_locked`.

Existing users lose effective access immediately.

If an exception request is in progress when capability is revoked:

```text
Request
   ↓
FROZEN
   ↓
Fresh authorization required
```

Do not allow stale authorization to complete the correction.

---

# 36. Price Version History

Every price correction creates a new immutable price version/history entry.

Example:

```text
Price v1
₹500
APPROVED
LOCKED

Price v2
₹550
exception correction
customer approved
LOCKED
```

The system must never overwrite the original commercial state.

---

# 37. Customer Price History

Customer sees customer-relevant commercial history.

They may see:

```text
original price
price changed
customer-safe explanation
new proposed price
approval
final price
```

They must NOT see:

```text
internal permission names
internal security metadata
internal authorization details
private operational notes
```

---

# 38. Price Adjustment Reasons

TTC maintains structured reason codes.

Each adjustment has:

```text
one primary reason
zero or more secondary reasons
```

Example:

```text
Primary:
ITEM_CONDITION_CHANGE

Secondary:
ADDITIONAL_WORK_REQUIRED
```

Resolvers cannot create arbitrary machine-readable reason codes.

---

# 39. Reason Versioning

Reason definitions are versioned.

Example:

```text
ADDITIONAL_WORK_REQUIRED v1
ADDITIONAL_WORK_REQUIRED v2
ADDITIONAL_WORK_REQUIRED v3
```

Published reason versions are immutable.

The system automatically uses the current published version.

Resolvers select the reason code, not the version.

---

# 40. Reason Lifecycle

Reason definitions use:

```text
DRAFT
   ↓
PUBLISHED
   ↓
ACTIVE
```

Only published/active definitions may be used for live adjustments.

A published reason version can be retired only when a replacement exists.

Historical records retain the original version.

Multiple reason codes may be active simultaneously.

---

# 41. Customer-Facing Reason

Internal reason codes are not shown directly to customers.

TTC maintains customer-facing descriptions/templates.

Example:

```text
Internal:
ADDITIONAL_WORK_REQUIRED

Customer:
"Additional work was required for your items."
```

Historical orders preserve the exact reason-definition version/template used.

---

# 42. Reason Template

TTC controls the customer-facing explanation template.

Resolver input can populate only approved placeholders.

Conceptually:

```text
TTC Template
+
Validated Resolver Explanation
↓
Customer-safe Explanation
```

Resolver text must pass customer-safety/privacy validation.

The original internal resolver explanation remains available to authorized audit users.

---

# 43. Pickup

After seller acceptance:

```text
CONFIRMED
   ↓
Pickup workflow
```

Pickup operational stages may include:

```text
PICKUP_ASSIGNED
PICKUP_STARTED
PICKUP_VERIFICATION
PICKUP_COMPLETED
```

These are operational events/stages, not necessarily top-level Order statuses.

---

# 44. Pickup Verification

Pickup can capture:

```text
item type
actual quantity
actual weight
condition
damage
photos
evidence
notes
```

Required fields depend on seller/service configuration within TTC-supported capabilities.

---

# 45. Additional Items

Driver may add a new item during pickup verification if permitted by the service.

The driver selects from predefined master catalog entries.

The driver cannot invent arbitrary catalog items.

---

# 46. Quantity Changes

Pickup verification may allow:

```text
quantity increase
quantity decrease
item removal
```

according to service configuration.

Customer approval requirements are configurable within TTC-supported behavior.

Default behavior for material pickup changes is customer approval where established.

---

# 47. Pickup Dispute

If customer does not approve a material pickup change:

```text
PICKUP DISPUTE / REVIEW
```

The order may be held until the discrepancy is resolved.

Marketplace must show the customer the relevant safe information and approval action.

---

# 48. Condition and Damage

Condition/damage evidence may be configured.

Where damage reporting is enabled:

```text
damage reported
      ↓
photos/evidence
```

may be mandatory according to the configured workflow.

Marketplace customer experience should expose appropriate evidence where business rules require it.

---

# 49. Pickup Notes

General pickup notes are optional by default.

The platform may require them for specific workflows/configurations.

---

# 50. Final Pricing After Pickup

Pickup actuals may change commercial pricing.

Example:

```text
Estimated:
₹400

Actual pickup:
4.6 KG

Final:
₹368
```

The Pricing Engine calculates the authoritative final price.

Marketplace must never independently recalculate the final commercial amount.

---

# 51. Payment Timing

Payment occurs after the relevant pickup/final-pricing stage according to the applicable payment policy.

Conceptually:

```text
Order
 ↓
Seller acceptance
 ↓
Pickup
 ↓
Actual data
 ↓
Customer approval where required
 ↓
Final price
 ↓
Payment due
```

Payment policy details belong to the Payment domain.

---

# 52. Payment Methods

Marketplace may support platform-approved payment methods such as:

```text
online gateway
cash
partial cash
mixed payment
```

The exact availability is controlled by Payment Policy.

Marketplace must not independently decide payment applicability.

---

# 53. Driver Assignment and Payment

Payment state may influence driver assignment eligibility according to the configured payment policy.

Conceptually:

```text
UNPAID
PARTIALLY_PAID
PAID
        ↓
Driver Assignment Eligibility
```

Marketplace should communicate relevant customer-facing payment requirements but must not implement assignment logic.

---

# 54. Delivery

After operational fulfillment, delivery is completed using the approved driver workflow.

Delivery OTP may be used:

```text
Driver reaches customer
        ↓
OTP requested
        ↓
Customer provides OTP
        ↓
Driver verifies
        ↓
Delivery completed
        ↓
Order COMPLETED
```

Marketplace customer sees the appropriate delivery state.

---

# 55. Delivery OTP

Current rules include:

```text
OTP generated when requested at delivery
OTP valid for 2 minutes
maximum 5 generations
new OTP invalidates old OTP
```

After the generation limit is reached:

```text
platform/back-office exception
```

Customer cannot bypass OTP through normal UI.

---

# 56. Customer Unable to Provide OTP

If customer cannot provide OTP:

```text
Driver
 ↓
Back-office exception workflow
```

Only authorized platform/admin personnel can exception-complete the delivery.

Mandatory reason is required.

No OTP should be fabricated or bypassed in the customer application.

---

# 57. Reservice

A customer may request reservice within the seller-configured window measured from actual final delivery/drop-off.

A request submitted before the deadline remains valid even if reviewed later.

Only one reservice request is allowed per original order.

---

# 58. Reservice Lifecycle

Conceptually:

```text
REQUESTED
   ↓
UNDER_REVIEW
   ↓
APPROVED
   ↓
DRIVER_ASSIGNED
   ↓
ARRIVED_AT_PICKUP
   ↓
PICKUP_STARTED
   ↓
PICKUP_COMPLETED
   ↓
IN_PROGRESS
   ↓
COMPLETED
```

Seller may reject from appropriate review states.

Customer cancellation is allowed through the defined pickup stage.

---

# 59. Reservice Commercial Model

Reservice pricing is:

```text
PER_PIECE
```

The seller decides whether reservice is:

```text
free
```

or:

```text
chargeable
```

For chargeable reservice:

```text
item-specific per-piece rate
```

may apply.

Rates are snapshotted when the seller approves the reservice.

---

# 60. Reservice Payment

Chargeable reservice payment occurs:

```text
after seller approval
+
before driver assignment
```

Free reservice creates the appropriate zero-value payment record.

If chargeable payment is not completed before the configured deadline:

```text
PAYMENT_EXPIRED
```

may terminate the reservice.

---

# 61. Reservice and Original Order

A reservice does NOT create a new customer order number.

It is a separate case/job under the original order.

The original completed order remains unchanged.

A completed reservice cannot create another reservice cycle.

---

# 62. Marketplace Seller Restrictions

Marketplace sellers may be subject to TTC commercial restrictions.

Example:

```text
WARNING
   ↓
MARKETPLACE_RESTRICTED
   ↓
WHITE_LABEL_RESTRICTED
   ↓
FULL_SUSPENSION
```

When a marketplace seller becomes restricted, new marketplace PENDING orders may be cancelled with:

```text
SELLER_RESTRICTED
```

Customers can then choose another seller where supported.

---

# 63. Reselection

If marketplace seller restriction requires reselection:

```text
Old Order
   ↓
CANCELLED
   ↓
Customer selects another seller
   ↓
New Order ID
+
New Order Number
```

The original order remains historically preserved.

An optional relationship such as:

```text
reselected_from_order_id
```

may preserve the chain.

No refund is required merely for this pre-payment reselection case where no payment has occurred.

---

# 64. Marketplace UX

The marketplace must clearly support:

```text
discovery
selection
pricing
confirmation
order status
price approval
pickup information
payment
delivery
reservice
```

Do not expose unnecessary internal implementation terminology.

---

# 65. Marketplace Error Handling

Customer-facing errors must be understandable.

Examples:

```text
PRICE_CHANGED
ORDER_NOT_FOUND
ORDER_ACCESS_DENIED
INVALID_CATALOG_ITEM
INVALID_BRANCH
SELLER_UNAVAILABLE
SELLER_RESTRICTED
INVALID_ORDER_STATUS_TRANSITION
```

Internal stack traces and database details must never be exposed.

---

# 66. Customer Order Isolation

A customer must only access their own orders.

Test:

```text
Customer A → Customer A order = allowed
Customer A → Customer B order = denied
```

The backend must enforce this independently of frontend behavior.

---

# 67. Seller Isolation

Marketplace customer requests must not allow manipulation of:

```text
seller_id
tenant_id
branch_id
```

to access another seller's internal data.

Backend resolves and validates the seller/branch hierarchy.

---

# 68. Marketplace Security

Never trust client-provided:

```text
customer_id
tenant_id
seller_id
branch_id
price
grand_total
permission
status
```

where these values are authoritative server-side concepts.

---

# 69. Marketplace Web

`marketplace-web` should provide the browser customer experience.

Initial capability groups:

```text
home/discovery
seller browsing
branch
catalog
service
pricing
order creation
my orders
order detail
price approval
payment
delivery
reservice
account
```

Detailed UI architecture belongs to the Frontend baseline.

---

# 70. Marketplace Mobile

`marketplace-mobile` provides the equivalent customer journey optimized for mobile.

It must use:

```text
same backend
same API contracts
same shared types
same business rules
```

Do not duplicate domain logic.

---

# 71. Marketplace vs White-Label

Marketplace:

```text
TTC-branded
multi-seller
customer chooses seller
```

White-label:

```text
seller-branded
seller-specific customer experience
customer operates within that seller context
```

Both use the same platform domains where applicable.

---

# 72. Marketplace vs Full-Access Seller

Marketplace Seller:

```text
TTC marketplace
TTC marketplace governance
seller configuration
```

Full-Access Seller:

```text
seller-branded experience
broader seller configuration
seller-managed operations
```

Do not confuse seller operational applications with customer-facing marketplace/white-label applications.

---

# 73. Marketplace Business Rule Authority

The marketplace UI may:

```text
display
collect input
request action
show status
```

but authoritative rules remain in:

```text
Catalog Domain
Pricing Engine
Order Domain
Payment Domain
Fulfillment Domain
RBAC
Tenant Context
```

---

# 74. Marketplace Testing

At minimum test:

```text
seller discovery
seller eligibility
branch validation
catalog visibility
service visibility
price calculation integration
stale price handling
order creation
customer isolation
seller rejection
customer cancellation
price approval
price dispute
manual adjustment
price lock
pickup changes
payment flow
delivery state
reservice
seller restriction
```

---

# 75. Marketplace Regression

Marketplace changes must not break:

```text
Seller Platform
Pricing
Order
RBAC
Tenant isolation
White-label runtime
Driver operations
Payment
```

Use shared backend/domain tests wherever possible.

---

# 76. Marketplace Architectural Boundary

The final conceptual flow is:

```text
                     MARKETPLACE
                          │
                    Customer chooses
                          │
                    Seller / Branch
                          │
                      Catalog
                          │
                       Service
                          │
                       Pricing
                          │
                    Order Request
                          │
                          ▼
                        ORDER
                          │
                 ┌────────┼────────┐
                 │        │        │
              Pickup   Payment  Fulfillment
                 │        │        │
                 └────────┼────────┘
                          │
                       Delivery
                          │
                       Reservice
```

The marketplace is the customer-facing orchestration surface, not the owner of these domain rules.

---

# 77. Implementation Strategy

Marketplace implementation must follow vertical slices:

```text
Business Capability
      ↓
Backend domain/API
      ↓
Shared Type
      ↓
marketplace-web
      ↓
marketplace-mobile
      ↓
Integration tests
      ↓
Regression
      ↓
Git commit
```

Do not implement marketplace frontend independently from its backend contract.

---

# 78. Out of Scope for This Prompt

Do not use this prompt to implement:

```text
seller administration
driver administration
TTC admin internals
white-label provisioning
app-store provisioning
billing administration
settlement administration
microservices
Kafka
RabbitMQ
Kubernetes
```

Those are defined in separate baseline prompts.

---

# Final Marketplace Principle

The TTC Marketplace must provide a simple customer experience over a strong domain architecture:

```text
DISCOVER
   ↓
SELECT
   ↓
PRICE
   ↓
ORDER
   ↓
SELLER DECISION
   ↓
PICKUP
   ↓
FINAL PRICE
   ↓
PAY
   ↓
DELIVERY
   ↓
RESERVICE
```

while maintaining:

```text
ONE BACKEND
ONE PRICING AUTHORITY
ONE ORDER AUTHORITY
ONE SECURITY MODEL
ONE TENANT MODEL
ONE SHARED PLATFORM
```

and supporting many sellers without duplicating code.
