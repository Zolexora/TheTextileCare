# TTC Baseline Prompt 04 — Seller-Web Application Specification

## Purpose

Define the complete product, UX, navigation, authorization, frontend architecture, backend dependencies, and operational behavior of:

```text
apps/seller-web
```

The Seller-Web application is the primary browser-based control surface for TTC sellers.

It must support both:

```text
Marketplace Seller
```

and:

```text
Full-Access Seller
```

using the same application architecture.

The application must be:

```text
configuration-driven
tenant-aware
permission-aware
responsive
shared-code based
```

Do not create seller-specific frontend forks.

Do not implement business rules exclusively in the frontend.

---

# 1. Seller-Web Role

Seller-Web answers:

> “What can this seller manage and operate within TTC?”

It is not:

```text
the marketplace customer application
the driver application
the TTC admin application
the payment gateway
the accounting system
the fulfillment engine
```

It is the seller's operational and configuration interface.

---

# 2. Application Identity

Application:

```text
apps/seller-web
```

It consumes:

```text
TTC Backend APIs
+
@ttc/types
+
@ttc/ui
+
@ttc/api-client
+
@ttc/auth
+
@ttc/tenant
```

where those packages exist in the repository.

Do not duplicate shared platform infrastructure inside Seller-Web.

---

# 3. Seller-Web Architecture

Use:

```text
Browser
   ↓
Seller-Web
   ↓
Shared API Client
   ↓
Backend API
   ↓
TenantContext
   ↓
Authorization
   ↓
Application Service
   ↓
Domain Service
   ↓
Repository
   ↓
Database
```

Frontend never becomes the authoritative business layer.

---

# 4. Tenant Context

After authentication, Seller-Web must establish the active seller/tenant context from the authenticated session and backend context.

Do not trust:

```text
localStorage.seller_id
query.seller_id
URL seller_id
request body seller_id
```

as authorization.

The backend remains authoritative.

---

# 5. Seller-Web Authentication

Seller-Web must support the established TTC authentication architecture.

After login:

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
Seller-Web
```

If the user has no valid seller membership:

```text
access denied
```

Do not display seller data before authorization is resolved.

---

# 6. Effective Permissions

Seller-Web receives or resolves effective permissions through the established authorization architecture.

Conceptually:

```text
Available Permissions
        ↓
Assigned Roles
        ↓
User
        ↓
Individual Additions/Removals
        ↓
Effective Permissions
```

The frontend uses permissions to determine:

```text
navigation visibility
button visibility
action availability
screen access
```

But:

> Frontend permission checks are UX controls, not security controls.

Every backend operation must independently authorize the action.

---

# 7. Seller Roles

Baseline seller roles:

```text
SELLER_OWNER
SELLER_ADMIN
SELLER_STAFF
SELLER_VIEWER
```

Seller-Web must not hard-code role names as the sole authorization mechanism.

Prefer permission checks.

Example:

```text
order.confirm
```

rather than:

```text
if role === "SELLER_ADMIN"
```

unless a specific platform-level rule requires role semantics.

---

# 8. Application Shell

Seller-Web should use a consistent application shell:

```text
┌──────────────────────────────────────────────┐
│ TTC / Seller Brand     Search   Notifications│
├──────────────┬───────────────────────────────┤
│              │                               │
│ Navigation   │        Main Content           │
│              │                               │
│              │                               │
├──────────────┴───────────────────────────────┤
│ Seller / Branch / User Context               │
└──────────────────────────────────────────────┘
```

The exact visual design follows the TTC design system.

Do not introduce a separate visual language for Seller-Web.

---

# 9. Primary Navigation

Seller-Web should be organized around capabilities.

Baseline navigation:

```text
Dashboard
Orders
Operations
Catalog
Services
Pricing
Branches
Customers
Users & Access
Commercial
Branding
Settings
```

Additional sections should appear only when the seller has the corresponding capability/permission.

Do not display irrelevant navigation permanently.

---

# 10. Dashboard

Dashboard provides a seller-level operational overview.

Possible information:

```text
pending orders
confirmed orders
in-progress orders
completed orders
cancelled orders
active branches
service availability
pricing/configuration warnings
operational alerts
commercial/restriction status
```

Do not turn Dashboard into an advanced BI/analytics system.

---

# 11. Dashboard Authorization

Dashboard data must respect:

```text
tenant
seller
branch
permission
```

A staff user with branch-limited access must not automatically receive seller-wide information.

Use backend-scoped aggregates where necessary.

Do not fetch all orders and filter them in the browser.

---

# 12. Orders Section

Primary seller order interface:

```text
Orders
```

Default views may include:

```text
All
Pending
Confirmed
In Progress
Completed
Cancelled
```

The exact filtering is driven by the backend order API.

---

# 13. Order List

Order list should support:

```text
pagination
status
order number
customer
branch
date range
```

where supported by the backend.

Default deterministic ordering:

```text
created_at DESC
id DESC
```

or repository-standard equivalent.

Never load an unbounded order dataset.

---

# 14. Order Detail

Seller order detail should display appropriate information:

```text
order number
status
customer information
branch
items
add-ons
quantities
pricing
discounts
surcharges
tax
grand total
currency
timestamps
status history
operational information
```

The display must distinguish:

```text
current operational state
historical pricing
historical snapshots
```

---

# 15. Order Commercial Integrity

Seller-Web must never recalculate:

```text
subtotal
discount
surcharge
tax
grand total
```

itself.

The backend/Pricing Engine provides authoritative values.

Frontend displays those values.

---

# 16. Pending Order

When an order is:

```text
PENDING
```

Seller-Web should clearly communicate:

> Customer has submitted the order and the seller has not yet accepted it.

It does not mean:

```text
payment pending
```

It does not mean:

```text
draft
```

---

# 17. Pending Order Actions

Authorized seller users may see:

```text
Accept
Reject
```

subject to permission.

Accept:

```text
PENDING → CONFIRMED
```

Reject:

```text
PENDING → CANCELLED
reason = SELLER_REJECTED
```

Do not expose arbitrary status editing.

---

# 18. Reject Order UI

Reject must be an explicit action.

Example:

```text
Reject Order
────────────

Reason
[ Select reason ]

Additional explanation
[ Optional/required according to policy ]

[ Cancel ] [ Reject Order ]
```

The exact reason mechanism must reuse the backend/domain model.

Do not create a frontend-only rejection reason catalog.

---

# 19. Reject Confirmation

Rejecting an order is a destructive/terminal business action.

Require explicit confirmation.

Example:

```text
Reject this order?

This will cancel the customer's order.

[Go Back] [Reject Order]
```

The backend remains responsible for validating that the order is still:

```text
PENDING
```

---

# 20. Accept Order UI

Accepting a pending order should use an explicit action:

```text
[ Accept Order ]
```

The frontend sends the domain action.

It does not send:

```text
PATCH status=CONFIRMED
```

---

# 21. Concurrent Order Decision

Two seller users may view the same PENDING order.

Example:

```text
User A → Accept
User B → Reject
```

Only one action can succeed.

If another user has already changed the state:

```text
show current order state
```

Do not display a false success.

---

# 22. Confirmed Order

For:

```text
CONFIRMED
```

Seller-Web may expose authorized actions such as:

```text
Start
Cancel
```

according to permissions and business rules.

Start:

```text
CONFIRMED → IN_PROGRESS
```

Cancel:

```text
CONFIRMED → CANCELLED
reason = SELLER_CANCELLED
```

---

# 23. Start Order

Starting an order is an explicit domain action.

Use:

```text
[ Start Order ]
```

Backend:

```text
POST /orders/{id}/start
```

or the established equivalent.

Do not allow arbitrary status mutation.

---

# 24. In-Progress Order

For:

```text
IN_PROGRESS
```

Seller-Web should display:

```text
operational progress
driver information
pickup status
delivery status
pricing state
payment state
```

only where the relevant backend capabilities exist.

Do not invent fake operational data.

---

# 25. Exceptional Reverse Transition

If the platform supports:

```text
IN_PROGRESS → CONFIRMED
```

it must be an exceptional action.

The UI must require:

```text
reason
confirmation
appropriate permission
```

The backend must audit the transition.

Do not place this action beside ordinary workflow actions as though it were routine.

---

# 26. Completed Order

Completed orders are primarily historical.

Seller-Web should show:

```text
final status
final commercial values
final snapshots
operational history
```

Do not expose generic editing controls.

Historical order data must not be silently changed.

---

# 27. Cancelled Order

Cancelled orders must display:

```text
cancelled status
cancellation actor
reason
timestamp
status history
```

where customer-safe/seller-authorized information permits.

Examples:

```text
SELLER_REJECTED
CUSTOMER_CANCELLED
SELLER_CANCELLED
SELLER_RESTRICTED
```

---

# 28. Order History

Order detail should provide a chronological status history.

Example:

```text
Order Created
PENDING
   ↓
Seller Accepted
CONFIRMED
   ↓
Started
IN_PROGRESS
   ↓
Completed
COMPLETED
```

For rejection:

```text
PENDING
   ↓
Seller Rejected
CANCELLED
```

History is read-only.

---

# 29. Operations Section

Operations groups seller operational capabilities.

Potential sections:

```text
Pickup
Driver Assignment
Active Duties
Delivery
Exceptions
```

Only expose capabilities whose backend domains exist.

Do not build future fulfillment functionality prematurely.

---

# 30. Driver Assignment

When driver assignment becomes available, Seller-Web may provide:

```text
assigned driver
vehicle
assignment history
manual reassignment
```

Manual reassignment requires:

```text
previous driver
new driver
reason
```

The backend creates the authoritative assignment history.

---

# 31. Driver Assignment Notifications

Seller-Web may display assignment state and notification status.

Notification delivery failure must not make the assignment itself appear invalid.

Do not couple operational assignment persistence to frontend notification rendering.

---

# 32. Pickup Configuration

Seller-Web provides supported pickup configuration.

Example:

```text
Pickup Template
[ Weight + Item Count ]

Required:
☑ Weight
☑ Item Count

Optional:
☑ Condition
☑ Damage Photos
☐ Notes
```

The available choices come from TTC-supported configuration.

---

# 33. Pickup Measurement Boundary

Seller-Web must clearly distinguish:

```text
Billing Measurement
```

from:

```text
Pickup Capture
```

Example:

```text
Billing:
PER_KG

Pickup:
Item count + Weight + Condition
```

Do not make the UI imply that pickup fields automatically determine billing.

---

# 34. Catalog Section

Seller-Web provides seller configuration of the TTC master catalog.

Typical views:

```text
Catalog
Categories
Items
Add-ons
```

Seller users select supported TTC entities.

They do not create arbitrary master catalog entities.

---

# 35. Catalog Item Selection

A seller may:

```text
enable supported item
disable supported item
customize supported presentation
```

where permitted.

Historical orders remain unaffected.

---

# 36. Missing Catalog Item

Seller-Web may provide:

```text
Request New Catalog Item
```

The request goes to TTC.

It does not create the item immediately in the seller's database as an arbitrary master item.

---

# 37. Catalog Presentation

Seller-Web may allow field-specific customization:

```text
Name
Image
Description
```

Each field independently supports:

```text
TTC default
Seller custom value
```

A reset operation affects only that field.

---

# 38. Services Section

Seller-Web manages seller service configuration.

Example:

```text
Services
├── Wash & Fold
├── Dry Cleaning
├── Ironing
└── Premium Care
```

The actual services are based on TTC master service definitions.

---

# 39. Service Configuration

Seller may configure supported fields such as:

```text
enabled
availability
branches
presentation
supported items
supported add-ons
billing measurement
pickup template
pricing
```

Only supported configuration options are exposed.

---

# 40. Branch Service Availability

A service may be:

```text
seller-enabled
```

but unavailable at a particular branch.

Seller-Web must support branch-level availability where the domain supports it.

---

# 41. Pricing Section

Pricing configuration is one of the most sensitive Seller-Web areas.

It may include:

```text
Price Books
Service Pricing
Item Pricing
Add-on Pricing
Price Rules
Price Policies
Manual Adjustment Limits
```

depending on the Pricing Engine implementation.

---

# 42. Pricing Authority

Seller-Web does not calculate customer prices.

It configures pricing inputs.

The Pricing Engine calculates:

```text
subtotal
discount
surcharge
tax
grand total
```

---

# 43. Price Preview

Seller-Web may provide a pricing preview.

The preview must call the authoritative Pricing Engine.

Do not implement:

```text
frontend subtotal = quantity × price
```

as an authoritative calculation.

Client-side arithmetic may be used only for presentation where appropriate, never as the commercial source of truth.

---

# 44. Price Policy Configuration

Seller-Web may allow supported configuration of:

```text
price-change policy
manual adjustment limit
adjustment direction
timeout option
```

within TTC-defined boundaries.

The seller cannot create arbitrary policy eligibility conditions.

---

# 45. Price Policy Version Display

Seller users should be able to inspect:

```text
policy name
version
description
eligibility
existing-order behavior
recalculation behavior
customer approval behavior
rejection behavior
```

Published versions are immutable.

---

# 46. Price Adjustment

Authorized users may access:

```text
price.adjust
```

for supported disputes/adjustments.

UI should show:

```text
calculated price
proposed adjustment
resulting price
limit
reason
customer approval requirement
```

---

# 47. Price Adjustment Limits

Seller-Web must prevent users from entering values outside the configured limit.

However, frontend validation is not sufficient.

Backend must enforce:

```text
TTC maximum
+
seller configured maximum
```

---

# 48. Locked Price Adjustment

The locked-price adjustment UI is separate from normal adjustment.

Permission:

```text
price.adjust_locked
```

is required.

The UI must clearly indicate:

> This changes a previously customer-approved locked price and requires a new customer approval.

---

# 49. Adjustment Reason UI

The user selects:

```text
Primary Reason
Secondary Reasons
```

from TTC-controlled reason codes.

The user does not select a reason version.

The system resolves the current applicable published version.

---

# 50. Resolver Explanation

Where explanation text is allowed:

```text
Additional explanation
```

must be constrained by backend validation.

The frontend should communicate the customer-facing nature of the text.

Do not expose internal reason codes.

---

# 51. Branches Section

Seller-Web branch management should support:

```text
branch list
branch detail
create branch
edit branch
activate/deactivate
service availability
operational settings
```

where permitted.

---

# 52. Branch Creation

Branch creation must validate:

```text
seller ownership
required address fields
supported configuration
```

The backend creates the authoritative branch.

---

# 53. Branch Activation

A branch should only become operational when required configuration is complete.

The UI may show:

```text
Configuration readiness
```

but the backend remains authoritative.

---

# 54. Customers Section

Seller-Web may provide seller-scoped customer visibility.

Customer information must be limited to customers associated with the seller and permitted by role/permission.

Do not expose unrelated marketplace-wide customer information.

---

# 55. Customer Detail

Where permitted, seller users may see:

```text
customer name
contact information
seller order history
operational information
```

Do not expose unrelated customer accounts or private platform data.

---

# 56. Users & Access

Full-Access Sellers may manage supported seller users.

Sections:

```text
Users
Roles
Permissions
```

Marketplace Seller capabilities remain restricted according to TTC policy.

---

# 57. User Creation

User creation must follow:

```text
authenticated seller admin
↓
permission check
↓
seller context
↓
invite/create user
↓
assign supported role
↓
optional individual permission overrides
```

Do not allow a seller to create arbitrary permissions.

---

# 58. User Access Editing

Seller administrators may modify supported:

```text
role
individual additions
individual removals
active/inactive state
```

where authorized.

Changes take effect immediately.

---

# 59. Permission Safety

A seller administrator cannot grant a permission that the platform has not made available to that seller.

Sensitive permissions such as:

```text
price.adjust_locked
```

require explicit platform enablement.

---

# 60. Commercial Section

Seller-Web may expose seller commercial information:

```text
commercial model
commission/subscription status
billing
settlement
restriction status
```

The actual authoritative financial calculations belong to the appropriate backend domains.

---

# 61. Commercial Model

Display the seller's current model:

```text
Percentage Commission
```

or:

```text
Monthly Subscription
```

The two models remain mutually exclusive.

---

# 62. Model Switching

Where enabled, Seller-Web can request a commercial model switch.

The backend determines:

```text
effective date
applicable transactions
historical preservation
```

Frontend must not calculate retroactive effects.

---

# 63. Billing Status

Seller-Web may display:

```text
current invoice
amount due
due date
overdue amount
penalty
restriction level
```

Do not implement accounting calculations in Seller-Web.

---

# 64. Restriction Banner

If a seller is restricted, Seller-Web should prominently communicate:

```text
current restriction
reason
financial status where appropriate
affected capabilities
restoration requirements
```

Do not hide operationally important restrictions.

---

# 65. Restriction Progression

Seller-Web may show:

```text
WARNING
MARKETPLACE_RESTRICTED
WHITE_LABEL_RESTRICTED
FULL_SUSPENSION
```

as the seller's current platform state.

The frontend cannot override restriction state.

---

# 66. Branding

Seller-Web provides supported seller branding configuration.

Potential settings:

```text
logo
favicon
brand name
colors
customer-facing imagery
support information
```

These settings feed the white-label customer experience where applicable.

---

# 67. White-Label Configuration

Full-Access Sellers may see:

```text
White-Label
```

configuration.

Marketplace Sellers should not see unsupported white-label controls.

Configuration can include:

```text
domain
branding
customer experience settings
supported features
```

---

# 68. Domain Configuration

Seller-Web may provide a guided domain configuration workflow.

The seller may configure:

```text
custom domain
```

or use:

```text
TTC-provided subdomain
```

The backend/platform controls domain verification and activation.

Do not make the browser itself authoritative for DNS verification.

---

# 69. Settings

General settings may include:

```text
seller profile
business information
support contact
operational defaults
application configuration
```

Only supported settings should be displayed.

---

# 70. Audit / History

Where permitted, Seller-Web should expose relevant history.

Examples:

```text
configuration changes
price adjustments
order state transitions
permission changes
driver reassignment
restriction history
```

Sensitive internal audit information should remain protected.

---

# 71. Notifications

Seller-Web may eventually display:

```text
order alerts
operational alerts
commercial alerts
system notices
```

Notification infrastructure itself is a separate capability.

Do not implement a complete notification platform inside Seller-Web.

---

# 72. Search

Seller-Web should provide contextual search where useful.

Examples:

```text
order number
customer
branch
service
```

Search must call backend APIs.

Do not download entire datasets to perform browser-side global search.

---

# 73. Filtering

Lists should support server-side filtering.

Examples:

```text
status
branch
date range
customer
service
```

Pagination must remain server-controlled.

---

# 74. Empty States

Every major Seller-Web list must have a meaningful empty state.

Example:

```text
No pending orders

Orders submitted by customers will appear here
when they are awaiting seller acceptance.
```

Do not show blank screens.

---

# 75. Loading States

Use consistent loading states.

Do not block the entire application when only one panel is loading.

Use appropriate:

```text
skeletons
spinners
progress indicators
```

according to the shared UI system.

---

# 76. Error Handling

API errors should be translated into useful user-facing messages.

Examples:

```text
ORDER_ALREADY_PROCESSED
PRICE_CHANGED
ORDER_ACCESS_DENIED
INVALID_ORDER_STATUS_TRANSITION
IDEMPOTENCY_CONFLICT
```

Do not expose:

```text
stack traces
database errors
internal exception details
```

---

# 77. Stale Data

Seller-Web must handle stale data gracefully.

Example:

```text
User opens PENDING order
Another seller user accepts it
First user clicks Reject
```

Expected behavior:

```text
backend rejects transition
frontend refreshes order state
user sees current status
```

Do not overwrite the new state.

---

# 78. Optimistic Updates

Use optimistic UI only where safe.

Do not optimistically mark an order:

```text
CONFIRMED
```

before the backend confirms the transition.

For important commercial/operational mutations:

```text
server confirmation first
```

is preferred.

---

# 79. Forms

All important forms require:

```text
client validation
server validation
clear errors
submission state
duplicate-submit protection
```

Frontend validation improves UX.

Backend validation remains authoritative.

---

# 80. Duplicate Submission

Buttons for mutations should prevent accidental repeated clicks.

Example:

```text
[Reject Order]
```

becomes disabled while the request is processing.

The backend must still support idempotent/safe behavior.

---

# 81. Responsive Design

Seller-Web must support:

```text
desktop
tablet
mobile browser
```

However:

> Seller-Mobile is the dedicated mobile application.

Responsive Seller-Web should remain functional, but mobile-specific operational experiences belong in Seller-Mobile where appropriate.

---

# 82. Accessibility

Seller-Web should follow accessible UI practices:

```text
keyboard navigation
semantic controls
labels
focus states
error association
sufficient contrast
screen-reader compatibility
```

Use the shared UI system.

---

# 83. Performance

Avoid:

```text
unbounded API requests
large client-side datasets
duplicate API fetching
unnecessary re-renders
```

Use:

```text
pagination
caching where safe
query invalidation
lazy loading
code splitting
```

according to the frontend architecture.

---

# 84. API Contract Ownership

Every Seller-Web API dependency must correspond to an actual backend contract.

For a new capability:

```text
Business Rule
↓
Backend API
↓
Shared Type
↓
Seller-Web UI
```

Do not invent API responses in frontend code.

---

# 85. Shared Types

Seller-Web must use:

```text
@ttc/types
```

for shared contracts.

Examples:

```text
Seller
Branch
SellerUser
Role
Permission
Service
CatalogItem
Order
OrderStatus
Pricing
PricePolicy
```

Do not duplicate interfaces inside components.

---

# 86. API Client

Use:

```text
@ttc/api-client
```

or the repository's established API abstraction.

Do not scatter raw HTTP calls throughout components.

Prefer:

```text
page/component
↓
query/action hook
↓
API client
↓
backend
```

---

# 87. State Management

Use the established TTC frontend state architecture.

Separate:

```text
server state
UI state
form state
authentication state
tenant context
```

Do not put the entire application into one global store.

---

# 88. Routing

Routes should reflect business capabilities.

Conceptually:

```text
/dashboard

/orders
/orders/:id

/operations
/operations/drivers
/operations/pickups

/catalog
/catalog/items
/catalog/addons

/services
/services/:id

/pricing

/branches

/customers

/users
/roles
/permissions

/commercial

/branding

/settings
```

Exact routes should follow repository conventions.

---

# 89. Route Authorization

Routes must be protected by:

```text
authentication
+
seller membership
+
permission/capability
```

Do not rely only on route hiding.

A user manually entering:

```text
/admin-only-route
```

must receive proper authorization handling.

---

# 90. Branch Scope

If a user is limited to specific branches, Seller-Web must respect that scope.

Example:

```text
Seller
 ├── Branch A ← user access
 ├── Branch B ← no access
 └── Branch C ← no access
```

The user must not access Branch B by changing a URL or request parameter.

Backend authorization remains authoritative.

---

# 91. Marketplace Seller UI Differences

Marketplace Seller may see:

```text
Marketplace participation
orders
branches
services
pricing
operations
commercial
```

but should not receive unsupported:

```text
white-label administration
seller-managed customer application configuration
arbitrary user-management capabilities
```

---

# 92. Full-Access Seller UI Differences

Full-Access Seller may additionally see:

```text
Users & Access
Branding
White-Label
Domain
Customer Experience
```

subject to platform enablement and permissions.

The same Seller-Web codebase renders these features conditionally.

---

# 93. Feature Availability

Feature visibility should be determined through:

```text
seller type
+
platform capability
+
seller configuration
+
effective permissions
```

Do not create separate applications for seller types.

---

# 94. No Frontend Business Forks

Avoid:

```text
if marketplaceSeller
   completely different application

if fullAccessSeller
   completely different application
```

Prefer shared components and capability-driven rendering.

---

# 95. Example Capability Model

Conceptually:

```text
seller.capabilities = {
  marketplace: true,
  whiteLabel: false,
  userManagement: false,
  advancedPricing: true
}
```

The actual implementation should use the established backend configuration/capability model rather than inventing a second one.

---

# 96. Security

Seller-Web must protect:

```text
authentication tokens
seller context
customer information
pricing information
commercial information
operational information
```

Never expose secrets in frontend code.

Never put:

```text
database credentials
gateway secrets
server secrets
private signing keys
```

in the browser.

---

# 97. Audit UI

Audit display must respect authorization.

Not every seller user should see every internal audit event.

Use permission-controlled audit visibility.

---

# 98. Testing Strategy

Seller-Web tests must cover:

```text
authentication
tenant isolation
permission visibility
route protection
order actions
pricing displays
form validation
stale state
API errors
responsive behavior
```

Critical business authorization must also be tested at backend level.

Frontend tests must never be considered sufficient for security.

---

# 99. Order UI Tests

At minimum:

```text
PENDING displays Accept/Reject for authorized user
PENDING does not expose unauthorized actions
Accept calls explicit domain action
Reject requires reason
Rejected order displays CANCELLED + seller rejection
CONFIRMED displays Start where permitted
Completed order has no normal mutation controls
```

---

# 100. Permission UI Tests

Test:

```text
SELLER_OWNER
SELLER_ADMIN
SELLER_STAFF
SELLER_VIEWER
```

through effective permissions rather than assuming role names alone.

Verify:

```text
no permission → no action
permission → action available
permission revoked → action unavailable
```

---

# 101. Price UI Tests

Test:

```text
pricing values come from backend
manual adjustment limits displayed correctly
invalid adjustment blocked
reason required
customer approval indicated
locked-price adjustment protected
```

Do not test frontend arithmetic as the authoritative pricing behavior.

---

# 102. Seller Isolation Tests

Test:

```text
Seller A cannot display Seller B order
Seller A cannot open Seller B branch
Seller A cannot edit Seller B service
Seller A cannot access Seller B customers
```

Direct URL manipulation must not bypass backend authorization.

---

# 103. API Failure Tests

Test important failures:

```text
401
403
404
409
422
5xx
```

The UI should provide useful recovery behavior.

For `409 PRICE_CHANGED`:

```text
display current authoritative pricing
request customer/seller confirmation according to workflow
```

Do not silently submit the old price.

---

# 104. Build Validation

Seller-Web implementation must pass the repository's actual:

```text
lint
typecheck
build
tests
```

Do not claim success without running them.

Do not suppress TypeScript errors using broad:

```text
any
```

---

# 105. Vertical-Slice Implementation

Seller-Web must be built together with its backend capability.

Preferred sequence:

```text
Seller Capability
      ↓
Backend Model/Domain
      ↓
API
      ↓
Shared Types
      ↓
Seller-Web
      ↓
Integration
      ↓
Tests
      ↓
Validation
      ↓
Git Commit
```

Do not build dozens of disconnected frontend screens against mocked APIs and call the application complete.

---

# 106. Recommended Initial Seller-Web Vertical Slices

The initial implementation order should follow dependencies:

```text
1. Seller context / application shell
2. Seller dashboard foundation
3. Branch management
4. Service/catalog configuration
5. Pricing configuration
6. Order list/detail
7. Pending order acceptance/rejection
8. Order operational actions
9. Users/RBAC
10. Commercial/restriction visibility
11. Branding/white-label configuration
```

Exact sequencing may change if the actual repository dependency graph requires it.

---

# 107. Backend Dependency Principle

A Seller-Web screen is not considered complete merely because its UI exists.

For every capability verify:

```text
backend implementation
API contract
shared types
frontend implementation
authorization
tests
```

---

# 108. Documentation

Seller-Web documentation should live under the TTC architecture documentation structure:

```text
/home/chickenman/Documents/01_projects/Zolexora/TheTextileCare/docs/architecture
```

Recommended document:

```text
seller-web-application.md
```

Document:

```text
navigation
screens
permissions
seller-type differences
API dependencies
configuration behavior
security
vertical-slice dependencies
```

---

# 109. Git Discipline

Before Seller-Web work:

```bash
git status --short
```

Never use:

```bash
git reset --hard
git clean -fd
```

Do not blindly:

```bash
git add .
```

Stage only files belonging to the completed work unit.

---

# 110. Focused Commits

Every completed Seller-Web vertical slice requires a focused Git commit.

Example:

```text
feat(seller-web): add seller application shell
```

or:

```text
feat(seller-web): add order acceptance workflow
```

The actual commit message must describe the actual completed capability.

Do not create one giant commit containing unrelated work.

---

# 111. Final Seller-Web Architecture

```text
                         SELLER-WEB
                              │
              ┌───────────────┼───────────────┐
              │               │               │
          Configuration     Operations      Administration
              │               │               │
        ┌─────┼─────┐    ┌────┼────┐     ┌────┼────┐
        │     │     │    │    │    │     │    │    │
     Catalog Services Pricing Orders Pickup Users Roles
        │     │     │    │    │
        └─────┴─────┴────┴────┴───────┐
                                      │
                                Backend APIs
                                      │
                                Domain Services
                                      │
                              Tenant + RBAC + Audit
```

---

# 112. Final Product Principle

Seller-Web is:

> **A shared, permission-aware, tenant-isolated operational and configuration application for TTC sellers.**

It is:

```text
shared
configuration-driven
backend-authoritative
permission-controlled
historically safe
```

It is not:

```text
seller-specific code
seller-specific backend
customer marketplace
driver application
payment gateway
accounting system
```

---

# 113. Acceptance Criteria

Seller-Web architecture is considered complete when:

```text
[ ] Shared seller-web application exists
[ ] Marketplace Seller supported
[ ] Full-Access Seller supported
[ ] No seller-specific code forks
[ ] Authentication integrated
[ ] Tenant context integrated
[ ] Seller context integrated
[ ] Permission-aware navigation
[ ] Permission-aware actions
[ ] Backend authorization remains authoritative
[ ] Dashboard foundation defined
[ ] Orders defined
[ ] Pending acceptance defined
[ ] Pending rejection defined
[ ] Confirmed workflow defined
[ ] Cancellation defined
[ ] Order history defined
[ ] Catalog configuration defined
[ ] Service configuration defined
[ ] Pricing configuration defined
[ ] Price policy configuration defined
[ ] Manual price adjustment defined
[ ] Locked price adjustment defined
[ ] Branch management defined
[ ] Customer visibility defined
[ ] Seller user management defined
[ ] RBAC management defined
[ ] Commercial visibility defined
[ ] Restriction visibility defined
[ ] Branding defined
[ ] White-label configuration defined
[ ] API contracts use shared types
[ ] Server-side authorization defined
[ ] Seller isolation defined
[ ] Branch isolation defined
[ ] Stale-state handling defined
[ ] Error handling defined
[ ] Responsive behavior defined
[ ] Accessibility defined
[ ] Testing strategy defined
[ ] Vertical-slice implementation defined
[ ] Git discipline defined
[ ] Architecture documentation location defined
```

---

# 114. Architectural Boundary

The final Seller-Web relationship is:

```text
                    TTC BACKEND
                         │
              ┌──────────┴──────────┐
              │                     │
        Seller Domain          Shared Domains
              │                     │
       ┌──────┼──────┐       ┌──────┼───────┐
       │      │      │       │      │       │
      RBAC  Catalog Pricing  Order  Payment Commercial
       │      │      │       │      │       │
       └──────┴──────┴───────┴──────┴───────┘
                         │
                    Shared API
                         │
                    Seller-Web
                         │
          ┌──────────────┴──────────────┐
          │                             │
   Marketplace Seller             Full-Access Seller
          │                             │
   TTC Marketplace               Seller White-Label
```

The critical principle is:

> **Seller-Web is one shared application whose behavior is determined by authenticated seller context, seller type, supported capabilities, configuration, and effective permissions. Backend domains remain authoritative for all business decisions.**
