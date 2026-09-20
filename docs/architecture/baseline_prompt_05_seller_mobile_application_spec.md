# TTC Baseline Prompt 05 — Seller-Mobile Application Specification

## Purpose

Define the complete product, UX, authorization, mobile architecture, backend dependencies, operational behavior, and implementation boundaries of:

```text
apps/seller-mobile
```

Seller-Mobile is the mobile operational companion for TTC sellers.

It uses the same:

```text
Seller Domain
Backend
APIs
RBAC
TenantContext
Shared Types
Pricing Engine
Order Domain
Configuration
```

as Seller-Web.

It must not become a second seller business system.

---

# 1. Seller-Mobile Role

Seller-Mobile provides mobile-first access to seller capabilities that are useful while away from a desktop.

It should prioritize:

```text
Orders
Operations
Driver/assignment visibility
Pickup/delivery progress
Customer/order information
Operational exceptions
Approvals
Alerts
```

It may also provide selected configuration functionality where mobile interaction is appropriate.

Seller-Web remains the broader administration surface.

---

# 2. Application Identity

Application:

```text
apps/seller-mobile
```

It consumes:

```text
TTC Backend APIs
@ttc/types
@ttc/api-client
@ttc/auth
@ttc/tenant
@ttc/ui
```

where supported.

Do not duplicate domain logic inside the mobile application.

---

# 3. One Seller Platform

Seller-Mobile and Seller-Web are two interfaces to the same Seller Platform.

Conceptually:

```text
                    Seller Platform
                          │
             ┌────────────┴────────────┐
             │                         │
        Seller-Web              Seller-Mobile
             │                         │
             └────────────┬────────────┘
                          │
                     Same Backend
```

A user changing data in Seller-Web must see the same state in Seller-Mobile.

A user changing data in Seller-Mobile must see the same state in Seller-Web.

---

# 4. No Mobile-Specific Business Model

Do not create:

```text
MobileOrder
MobilePricing
MobileSeller
MobileBranch
MobileCustomer
```

as independent business models.

Use shared domain contracts.

---

# 5. Mobile Architecture

Preferred architecture:

```text
Seller-Mobile
      ↓
API Client
      ↓
Backend API
      ↓
Authentication
      ↓
TenantContext
      ↓
RBAC
      ↓
Application Service
      ↓
Domain Service
      ↓
Repository
      ↓
Database
```

The mobile client is not authoritative.

---

# 6. Authentication

Seller-Mobile uses the established TTC authentication system.

Conceptually:

```text
User
 ↓
Authenticated Session
 ↓
Seller Membership
 ↓
Seller/Tenant Context
 ↓
Roles
 ↓
Permissions
 ↓
Seller-Mobile
```

A user without an authorized seller membership must not receive seller data.

---

# 7. Session Security

Mobile authentication must follow the platform's established secure session/token architecture.

Do not store secrets insecurely.

Do not place:

```text
database credentials
gateway secrets
private keys
server credentials
```

inside the mobile application.

---

# 8. Tenant Isolation

Every API request must be evaluated against:

```text
authenticated user
+
tenant
+
seller
+
branch scope
+
permission
```

Never trust client-supplied:

```text
tenant_id
seller_id
branch_id
user_id
```

for authorization.

---

# 9. Effective Permissions

Seller-Mobile uses the same effective permission model as Seller-Web:

```text
Available Permissions
        ↓
Role
        ↓
Role Permissions
        ↓
User
        ↓
Individual Additions/Removals
        ↓
Effective Permissions
```

Permission changes apply immediately.

---

# 10. Seller Roles

The baseline seller roles remain:

```text
SELLER_OWNER
SELLER_ADMIN
SELLER_STAFF
SELLER_VIEWER
```

Mobile UI must prefer permission checks rather than hard-coded role assumptions.

Example:

```text
order.confirm
```

is preferable to:

```text
role == SELLER_ADMIN
```

for action visibility.

---

# 11. Mobile-First Principle

Seller-Mobile should prioritize tasks that benefit from immediate access.

Primary goals:

```text
See what requires attention
Take permitted operational action
Review current order state
Handle exceptions
Monitor active operations
```

Do not attempt to reproduce every Seller-Web screen on mobile.

---

# 12. Primary Navigation

A baseline mobile navigation may include:

```text
Home
Orders
Operations
Customers
More
```

The exact navigation should be capability-driven.

Unavailable modules should not appear.

---

# 13. Home Screen

Home should provide a concise operational overview.

Potential cards:

```text
Pending Orders
Confirmed Orders
In Progress
Today's Operations
Exceptions
Alerts
```

Do not turn the mobile Home screen into a heavy analytics dashboard.

---

# 14. Attention-First Design

The mobile application should prioritize items requiring action.

Example:

```text
PENDING ORDERS
3 require seller decision
```

or:

```text
OPERATIONAL ALERT
Driver unavailable for Order TTC-2026-000123
```

This is an operational interface, not primarily a reporting interface.

---

# 15. Orders

Seller-Mobile must support seller-scoped order visibility.

Baseline:

```text
All
Pending
Confirmed
In Progress
Completed
Cancelled
```

Use backend pagination/filtering.

Never download the seller's entire order history.

---

# 16. Order List

Each order card should provide essential information:

```text
order number
customer
branch
status
amount
created time
```

Only display information authorized for the user.

---

# 17. Order Detail

Order detail should provide:

```text
Order Number
Status
Customer
Branch
Items
Add-ons
Quantity
Pricing
Tax
Discount
Surcharge
Grand Total
Currency
Timeline
Operational State
```

Do not recalculate totals on-device.

---

# 18. Historical Pricing

The mobile app displays the authoritative historical values returned by the backend.

It must not recalculate an old order using current:

```text
catalog
price book
price rule
tax
surcharge
discount
```

Historical order snapshots remain authoritative.

---

# 19. Pending Order

Seller-Mobile must clearly communicate:

```text
PENDING
```

means:

> Customer submitted the order and seller decision is pending.

It does not mean:

```text
payment pending
```

and does not mean:

```text
draft
```

---

# 20. Accept Order

Authorized seller users may accept:

```text
PENDING → CONFIRMED
```

The mobile action must call an explicit backend domain action.

Do not directly mutate:

```text
status
```

from the client.

---

# 21. Reject Order

Authorized users may reject:

```text
PENDING → CANCELLED
```

with:

```text
actor_type = SELLER
reason_code = SELLER_REJECTED
```

The UI must require the appropriate reason.

---

# 22. Reject Confirmation

Use a confirmation flow:

```text
Reject Order?

This will cancel the customer's order.

Reason:
[ Select ]

Explanation:
[ ... ]

[ Cancel ] [ Reject ]
```

Backend validates the order is still PENDING.

---

# 23. Concurrent Decisions

Example:

```text
Seller User A → Accept
Seller User B → Reject
```

Only one transition succeeds.

If the mobile user receives a conflict:

```text
refresh order
display current state
```

Do not show a false success state.

---

# 24. Confirmed Order

For:

```text
CONFIRMED
```

authorized users may see:

```text
Start
Cancel
```

according to permissions.

---

# 25. Start Order

Explicit action:

```text
CONFIRMED → IN_PROGRESS
```

The mobile client calls the backend transition.

No arbitrary status editing.

---

# 26. Seller Cancellation

Where permitted:

```text
CONFIRMED → CANCELLED
```

with:

```text
reason_code = SELLER_CANCELLED
```

The UI must request the required reason.

Do not allow cancellation of:

```text
IN_PROGRESS
COMPLETED
```

under the current baseline unless a later business decision changes this.

---

# 27. Completed Order

Completed orders are historical.

The mobile application should show:

```text
final status
final pricing
historical snapshots
timeline
operational history
```

No normal edit controls should be available.

---

# 28. Cancelled Order

Show:

```text
Cancelled
Reason
Actor
Timestamp
```

where authorized.

Examples:

```text
SELLER_REJECTED
CUSTOMER_CANCELLED
SELLER_CANCELLED
SELLER_RESTRICTED
```

---

# 29. Order Timeline

Mobile should provide a compact timeline:

```text
Created
  ↓
Pending
  ↓
Confirmed
  ↓
In Progress
  ↓
Completed
```

or:

```text
Created
  ↓
Pending
  ↓
Seller Rejected
  ↓
Cancelled
```

The timeline is read-only.

---

# 30. Operations

Operations should provide mobile access to active seller operations.

Potential areas:

```text
Active Pickups
Active Deliveries
Driver Assignments
Exceptions
Operational Alerts
```

Only implement areas whose backend capability exists.

---

# 31. Active Operations

An active operation card may show:

```text
Order
Customer
Branch
Driver
Current Stage
Payment State
Pricing State
```

Do not expose operational data outside the user's authorized seller/branch scope.

---

# 32. Driver Assignment

Where implemented, seller users can inspect:

```text
assigned driver
vehicle
assignment time
assignment history
```

Authorized users may manually reassign drivers.

---

# 33. Manual Reassignment

Manual reassignment requires:

```text
previous driver
new driver
mandatory reason
actor
timestamp
```

The backend owns the assignment history.

Mobile must not overwrite previous assignment records.

---

# 34. Driver Availability

If a driver is unavailable:

```text
before duty starts
```

the platform may attempt automatic reassignment and alert seller operations.

After assignment:

```text
driver becomes unavailable
```

seller operations may manually intervene.

The mobile app displays the authoritative backend state.

---

# 35. Driver Assignment Notifications

The application may display assignment/notification state.

However:

> Notification delivery is separate from assignment persistence.

A failed notification must not cause the mobile app to assume the assignment failed.

---

# 36. Pickup Verification Visibility

Seller-Mobile may display pickup verification progress:

```text
PICKUP_ASSIGNED
PICKUP_STARTED
PICKUP_VERIFICATION
PICKUP_COMPLETED
```

This does not make Seller-Mobile the driver's execution interface.

Driver-Mobile performs the actual driver workflow.

---

# 37. Pickup Discrepancy

When a pickup discrepancy exists, Seller-Mobile may display:

```text
original item
actual item
quantity
weight
condition
evidence
customer approval state
```

The seller can access supported resolution actions.

---

# 38. Pickup Dispute

If the customer disputes pickup information:

```text
PICKUP DISPUTE / REVIEW
```

Seller-Mobile should clearly identify:

```text
dispute state
required seller action
current commercial state
```

Do not silently resolve disputes on the client.

---

# 39. Final Pricing

When pickup information produces final pricing, Seller-Mobile may show:

```text
Estimated Price
Actual Pickup Data
Recalculated Price
Customer Approval State
Price Lock State
```

The Pricing Engine remains authoritative.

---

# 40. Price Change

If a policy change or pickup discrepancy produces a new price:

```text
new calculated price
```

must come from the backend.

Seller-Mobile cannot directly decide the new commercial amount.

---

# 41. Price Adjustment

Authorized seller users may perform supported manual adjustments.

Permission:

```text
price.adjust
```

The UI should show:

```text
calculated price
allowed adjustment
configured limit
resulting price
reason
customer approval requirement
```

---

# 42. Price Adjustment Limits

The mobile app should display the effective allowed limit.

But the backend must enforce:

```text
TTC-supported limit
+
seller configuration
```

Do not rely on client-side validation.

---

# 43. Locked Price Adjustment

For:

```text
PRICE LOCKED
```

normal adjustment controls disappear.

If the user has:

```text
price.adjust_locked
```

the app may expose an exceptional correction workflow.

It must clearly warn:

> This changes a previously customer-approved price and requires a new customer approval.

---

# 44. Locked Price Workflow

Required sequence:

```text
Authorized User
      ↓
Exception Request
      ↓
Reason
      ↓
New Price Calculation/Adjustment
      ↓
New Price Version
      ↓
Customer Approval
      ↓
New Locked Price
```

Original locked price remains in history.

---

# 45. Reason Selection

Seller-Mobile must use TTC-controlled reason codes.

User selects:

```text
Primary Reason
Optional Secondary Reasons
```

The app does not select reason versions.

---

# 46. Customer-Safe Explanation

Where explanatory text is permitted, Seller-Mobile should make clear that the text may be shown to the customer.

Backend validation/sanitization remains authoritative.

---

# 47. Price Policy Visibility

Seller-Mobile may show applicable policy information.

For example:

```text
Policy
Version
Why it applies
Recalculation behavior
Approval requirement
Rejection behavior
```

Do not allow mobile users to invent policy eligibility rules.

---

# 48. Branch Context

If the user has access to multiple branches, Seller-Mobile may allow branch filtering.

Example:

```text
All Branches
Branch A
Branch B
Branch C
```

The selected branch is a UI filter.

Backend authorization remains independent.

---

# 49. Branch-Restricted Users

If a user has access only to Branch A:

```text
Branch A → visible
Branch B → invisible
```

Changing API parameters manually must not expose Branch B.

---

# 50. Customers

Seller-Mobile may provide seller-scoped customer lookup.

Customer information must be limited to:

```text
authorized seller
authorized branch
authorized permission
```

where applicable.

---

# 51. Customer Detail

Where permitted:

```text
customer name
contact
seller order history
current operational orders
```

may be displayed.

Do not expose unrelated customer data.

---

# 52. Search

Mobile search should support high-value entities:

```text
order number
customer
phone where permitted
```

Backend search should be used.

Do not perform global search against locally cached full datasets.

---

# 53. Scan Support

If future implementation supports barcode/QR/order scanning, scanning is an interaction mechanism only.

It must resolve through backend-authorized resources.

Do not treat a scanned ID as authorization.

---

# 54. Alerts

Seller-Mobile should support an attention/alert surface for:

```text
pending order decisions
driver issues
pickup disputes
price disputes
payment issues
commercial restrictions
system errors
```

The exact notification infrastructure is a separate domain.

---

# 55. Notifications

Where notification infrastructure exists, Seller-Mobile may receive:

```text
push notifications
in-app notifications
```

Notification content must respect seller permissions and tenant scope.

Do not include sensitive data unnecessarily in push payloads.

---

# 56. Offline Principle

Seller-Mobile should not assume that the device is always online.

However:

> Offline operation must not bypass authoritative server-side business rules.

Critical mutations such as:

```text
accept order
reject order
cancel order
price adjustment
driver reassignment
```

must be confirmed by the backend.

---

# 57. Offline Read Cache

Read-only caching may be used for useful screens.

Examples:

```text
recent orders
recent customer information
recent operational summaries
```

Cached information must be treated as potentially stale.

---

# 58. Offline Mutations

Do not queue sensitive business mutations blindly for later execution.

For example:

```text
Accept PENDING order
```

must not be assumed successful while offline.

Show:

```text
Waiting for connection
```

rather than falsely confirming the transition.

---

# 59. Stale Data

Every critical detail screen must be able to refresh.

Example:

```text
User opens PENDING order
network reconnects
order is now CONFIRMED
```

The app must display current server state.

---

# 60. Error Handling

Handle:

```text
401
403
404
409
422
5xx
network timeout
offline
```

with useful user-facing states.

Do not expose internal backend errors.

---

# 61. Conflict Handling

Important conflict:

```text
409 INVALID_ORDER_STATUS_TRANSITION
```

or equivalent.

Expected behavior:

```text
refresh resource
show current state
explain action is no longer available
```

Do not retry a conflicting state mutation blindly.

---

# 62. Duplicate Actions

Mutation buttons must prevent accidental double submission.

Example:

```text
Reject
```

should become disabled while the request is pending.

Backend idempotency/safe transition handling remains required.

---

# 63. Forms

Mobile forms must support:

```text
validation
required fields
clear errors
submission state
keyboard-friendly inputs
confirmation
```

Do not rely only on mobile validation.

---

# 64. Confirmation for Destructive Actions

Require confirmation for:

```text
reject order
cancel order
locked-price correction
driver reassignment where applicable
```

The exact confirmation behavior depends on the domain action.

---

# 65. Mobile Permissions

Permission checks must exist at:

```text
navigation
screen
action
API
```

The first three improve UX.

The backend is the security boundary.

---

# 66. Seller Type

Seller-Mobile supports:

```text
Marketplace Seller
Full-Access Seller
```

through the same application.

Feature availability depends on:

```text
seller type
platform capability
seller configuration
effective permission
```

---

# 67. Marketplace Seller Mobile

Marketplace Seller may receive:

```text
orders
operations
branches
services
pricing
customers
commercial visibility
```

according to permissions.

Unsupported white-label administration should not be exposed.

---

# 68. Full-Access Seller Mobile

Full-Access Seller may receive additional capabilities:

```text
white-label status
branding
customer experience settings
seller user management
```

only where mobile UX is appropriate.

Complex administration may remain Seller-Web-only.

---

# 69. Seller-Web vs Seller-Mobile

Seller-Web:

```text
deep configuration
complex forms
advanced pricing
RBAC administration
commercial configuration
white-label setup
```

Seller-Mobile:

```text
quick operations
order decisions
active order monitoring
alerts
exceptions
approvals
mobile-friendly configuration
```

Do not force feature parity when it harms mobile usability.

---

# 70. Shared Domain Contracts

Seller-Mobile uses the same types as Seller-Web.

Examples:

```text
Seller
Branch
SellerUser
Permission
Service
CatalogItem
Order
OrderStatus
OrderItem
Pricing
PricePolicy
DriverAssignment
Pickup
```

Do not create mobile-specific copies.

---

# 71. API Client

Use the shared API client.

Preferred architecture:

```text
Screen
 ↓
Query/Mutation Hook
 ↓
@ttc/api-client
 ↓
Backend
```

Do not scatter raw HTTP implementation throughout screens.

---

# 72. State Management

Separate:

```text
server state
authentication state
tenant/seller context
UI state
form state
offline/cache state
```

Do not put every value into one global store.

---

# 73. Data Synchronization

Where appropriate, Seller-Mobile may refresh:

```text
orders
active operations
alerts
driver assignments
```

Use the repository's established data-fetching strategy.

Do not create an independent synchronization system unless required.

---

# 74. Real-Time Updates

If TTC's backend later provides WebSocket/realtime capabilities, Seller-Mobile may subscribe to relevant seller-scoped events.

Examples:

```text
order status changed
driver assignment changed
price dispute updated
operational alert
```

Subscriptions must remain:

```text
tenant-scoped
seller-scoped
permission-aware
```

Do not expose cross-tenant events.

---

# 75. Mobile Security

Protect:

```text
authentication state
cached customer information
cached order information
commercial data
```

Use platform-secure storage mechanisms where available.

Do not store sensitive data in plain text local storage.

---

# 76. Sensitive Push Notifications

Push notifications should avoid unnecessary sensitive information.

Prefer:

```text
New order requires action
```

over exposing full customer details in a lock-screen notification.

The user opens the application to retrieve authorized details.

---

# 77. Deep Links

Seller-Mobile may support deep links such as:

```text
seller://orders/{id}
```

or the repository's chosen scheme.

A deep link is not authorization.

On opening:

```text
authenticate
resolve seller context
authorize order
load order
```

---

# 78. Customer Contact

Where seller permissions and operational requirements allow customer contact, the mobile app may initiate:

```text
phone call
```

using the platform's contact capability.

The backend still controls whether the user is authorized to access the phone number.

---

# 79. Location

Seller-Mobile may consume operational location data when the domain supports it.

It must not independently decide:

```text
driver assignment
delivery completion
pickup completion
```

based only on device location.

Authoritative operational state remains backend-controlled.

---

# 80. Driver Boundary

Seller-Mobile is not Driver-Mobile.

Seller users manage/monitor supported operations.

Drivers execute their assigned workflow in:

```text
apps/driver-mobile
```

Do not duplicate the complete driver experience inside Seller-Mobile.

---

# 81. Payment Boundary

Seller-Mobile may display payment state:

```text
UNPAID
PARTIALLY_PAID
PAID
```

and other authorized payment information.

It does not become the payment processor.

Do not embed gateway secrets.

---

# 82. Commercial Boundary

Seller-Mobile may display:

```text
commission
subscription
billing status
restriction
settlement status
```

where authorized.

Financial calculations remain in backend commercial/payment domains.

---

# 83. Historical Integrity

Mobile configuration changes must never mutate historical order snapshots.

For example:

```text
Seller changes service name
```

must not change an existing order's historical service name.

---

# 84. Accessibility

Mobile UI should support:

```text
accessible labels
dynamic text sizing
touch target sizes
screen readers
contrast
clear error states
```

Use the shared design system where applicable.

---

# 85. Performance

Seller-Mobile should prioritize:

```text
fast startup
small initial payload
efficient API usage
cached read data
paginated lists
lazy-loaded modules
```

Do not preload the entire seller dataset.

---

# 86. Network Efficiency

Mobile networks may be slower/unreliable.

Prefer:

```text
paginated APIs
compact responses
incremental loading
request deduplication
cached read state
```

Do not repeatedly fetch identical data unnecessarily.

---

# 87. Testing

Seller-Mobile testing should include:

```text
authentication
tenant isolation
permission behavior
navigation
order list
order detail
accept
reject
cancel
start
pricing display
price adjustment
stale state
network failure
offline behavior
deep links
push notification handling
```

---

# 88. Security Tests

Verify:

```text
Seller A cannot read Seller B order
Seller A cannot mutate Seller B order
Customer cannot access Seller-Mobile APIs
Viewer cannot perform mutations
Revoked permission immediately blocks actions
Branch-restricted user cannot access another branch
```

Backend authorization tests remain mandatory.

---

# 89. Order Action Tests

At minimum:

```text
PENDING → CONFIRMED
PENDING → CANCELLED / SELLER_REJECTED
CONFIRMED → IN_PROGRESS
CONFIRMED → CANCELLED / SELLER_CANCELLED
```

Invalid transitions must fail.

---

# 90. Conflict Tests

Test:

```text
two users accept/reject same order
```

Expected:

```text
only one valid transition
```

The losing mobile client refreshes state.

---

# 91. Price Tests

Test:

```text
price values come from backend
manual adjustment limit enforced
reason required
locked price protected
customer approval required
```

Do not rely on mobile arithmetic.

---

# 92. Offline Tests

Test:

```text
open cached order offline
attempt critical mutation offline
network reconnect
refresh current state
```

Critical mutations must not be falsely reported as successful.

---

# 93. Build Validation

Run the actual repository commands for:

```text
lint
typecheck
build
tests
```

Do not claim success without executing them.

Do not suppress errors using:

```text
any
ignore
skip
```

without an explicit architectural reason.

---

# 94. Vertical-Slice Implementation

Seller-Mobile must be developed together with its backend capability.

Preferred flow:

```text
Business Capability
       ↓
Backend Domain/API
       ↓
Shared Types
       ↓
Seller-Web if applicable
       ↓
Seller-Mobile
       ↓
Integration
       ↓
Tests
       ↓
Validation
       ↓
Focused Git Commit
```

Do not build mobile screens against invented APIs.

---

# 95. Recommended Initial Mobile Slices

Suggested order:

```text
1. Authentication + seller context
2. Mobile application shell
3. Dashboard/Home
4. Order list
5. Order detail
6. Pending accept/reject
7. Confirmed/start/cancel
8. Operational monitoring
9. Pickup/price-dispute visibility
10. Driver assignment visibility
11. Customer lookup
12. Alerts/notifications
13. Selected administration
```

The actual order follows backend dependency readiness.

---

# 96. Seller-Web Relationship

Complex configuration should generally remain Seller-Web-first.

For example:

```text
Advanced RBAC
Complex pricing policy configuration
Complex white-label setup
Deep commercial administration
```

may be implemented primarily in Seller-Web.

Seller-Mobile should expose operationally useful subsets where justified.

---

# 97. Shared UI

Seller-Mobile should reuse TTC shared design principles.

Do not create an unrelated visual identity.

Seller-specific branding affects the seller/customer-facing experience where applicable; it does not change the internal Seller-Mobile application architecture arbitrarily.

---

# 98. Error Messages

Use domain-level error identifiers where available.

Examples:

```text
ORDER_NOT_FOUND
ORDER_ACCESS_DENIED
INVALID_ORDER_STATUS_TRANSITION
ORDER_ALREADY_CANCELLED
PRICE_CHANGED
IDEMPOTENCY_CONFLICT
INVALID_CATALOG_ITEM
```

Translate them into understandable mobile messages.

---

# 99. Documentation

Document Seller-Mobile under:

```text
/home/chickenman/Documents/01_projects/Zolexora/TheTextileCare/docs/architecture
```

Recommended:

```text
seller-mobile-application.md
```

Document:

```text
navigation
mobile responsibilities
Seller-Web boundary
permissions
offline behavior
API dependencies
security
notifications
deep links
vertical-slice dependencies
```

---

# 100. Git Discipline

Before implementation:

```bash
git status --short
```

Never use:

```bash
git reset --hard
git clean -fd
```

Do not blindly run:

```bash
git add .
```

Stage only the files belonging to the completed Seller-Mobile capability.

---

# 101. Focused Commits

Every completed Seller-Mobile vertical slice gets a focused commit.

Examples:

```text
feat(seller-mobile): add seller application shell
```

```text
feat(seller-mobile): add order decision workflow
```

Use the actual completed capability in the commit message.

---

# 102. Final Seller-Mobile Architecture

```text
                         SELLER PLATFORM
                               │
                    ┌──────────┴──────────┐
                    │                     │
               Seller-Web           Seller-Mobile
                    │                     │
                    └──────────┬──────────┘
                               │
                         Shared API
                               │
                 ┌─────────────┼─────────────┐
                 │             │             │
               RBAC         Orders        Pricing
                 │             │             │
                 └─────────────┼─────────────┘
                               │
                         Backend Domains
                               │
                         TenantContext
                               │
                            Database
```

---

# 103. Final Product Principle

Seller-Mobile is:

> **A secure, mobile-first operational interface to the shared TTC Seller Platform.**

It is:

```text
shared
tenant-aware
permission-aware
backend-authoritative
mobile-first
configuration-aware
```

It is not:

```text
a second backend
a second pricing engine
a second order system
a driver application
a payment processor
a separate seller codebase
```

---

# 104. Acceptance Criteria

Seller-Mobile architecture is considered complete when:

```text
[ ] Shared seller-mobile application defined
[ ] Marketplace Seller supported
[ ] Full-Access Seller supported
[ ] Shared backend used
[ ] Shared types used
[ ] Authentication defined
[ ] Tenant isolation defined
[ ] Seller isolation defined
[ ] Branch scope defined
[ ] RBAC defined
[ ] Permission-aware navigation defined
[ ] Permission-aware actions defined
[ ] Home/dashboard defined
[ ] Order list defined
[ ] Order detail defined
[ ] Pending acceptance defined
[ ] Pending rejection defined
[ ] Confirmed workflow defined
[ ] Cancellation defined
[ ] Order timeline defined
[ ] Operations defined
[ ] Driver assignment visibility defined
[ ] Pickup visibility defined
[ ] Price dispute visibility defined
[ ] Manual price adjustment defined
[ ] Locked price exception defined
[ ] Customer lookup defined
[ ] Alerts defined
[ ] Notification boundary defined
[ ] Offline read behavior defined
[ ] Critical offline mutation behavior defined
[ ] Deep-link security defined
[ ] API client defined
[ ] Shared state architecture defined
[ ] Error handling defined
[ ] Conflict handling defined
[ ] Security tests defined
[ ] Business workflow tests defined
[ ] Mobile performance defined
[ ] Accessibility defined
[ ] Seller-Web boundary defined
[ ] Vertical-slice implementation defined
[ ] Git discipline defined
[ ] Documentation location defined
```

---

# 105. Architectural Boundary

The final relationship is:

```text
                       TTC PLATFORM
                            │
                     SELLER PLATFORM
                            │
              ┌─────────────┴─────────────┐
              │                           │
         SELLER-WEB                SELLER-MOBILE
              │                           │
       Deep configuration          Mobile operations
       Administration              Quick decisions
       Advanced pricing             Order monitoring
       RBAC                         Alerts
       White-label                  Exceptions
              │                           │
              └─────────────┬─────────────┘
                            │
                       Shared APIs
                            │
                       Shared Types
                            │
                     Backend Domains
                            │
                  Tenant + RBAC + Audit
                            │
                         Database
```

The critical principle is:

> **Seller-Web and Seller-Mobile are two interfaces to one Seller Platform. They must never diverge into separate business systems.**
