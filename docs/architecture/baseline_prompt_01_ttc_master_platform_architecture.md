# THE TEXTILE CARE — MASTER PLATFORM ARCHITECTURE BASELINE

## Purpose

Define the complete architectural foundation for **THE TEXTILE CARE (TTC)**.

This document is the master architectural baseline for all subsequent TTC implementation prompts.

It must be treated as the highest-level architectural contract unless a later approved business decision explicitly changes it.

Do not implement from this document alone. Detailed implementation must follow the domain-specific prompts that reference this baseline.

---

# 1. Product Definition

THE TEXTILE CARE is a multi-tenant laundry technology platform combining:

```text
TTC Platform
    │
    ├── Marketplace
    │
    ├── Seller Platform
    │
    ├── White-Label Seller Experiences
    │
    ├── Driver Operations
    │
    └── TTC Administration
```

The platform supports multiple sellers operating independently while sharing TTC's common platform infrastructure, capabilities, master data, security model, and configuration-driven runtime.

TTC is not merely a laundry website.

It is a configurable multi-tenant commerce and operations platform for laundry and textile-care businesses.

---

# 2. Core Architectural Principle

TTC must use:

```text
ONE PLATFORM
      +
CONFIGURATION
      +
TENANT CONTEXT
      +
ROLE/PERMISSION MODEL
      ↓
MANY SELLER EXPERIENCES
```

Do NOT create separate application codebases for every seller.

Do NOT create seller-specific forks.

Do NOT create arbitrary customer-specific business logic.

Do NOT create bespoke software implementations for individual sellers.

Seller-specific behavior must be expressed through supported configuration and platform capabilities.

---

# 3. Application Architecture

The initial platform application structure is:

```text
apps/
├── marketplace-web
├── marketplace-mobile
├── seller-web
├── seller-mobile
├── driver-mobile
└── admin-web
```

### marketplace-web

Customer-facing TTC marketplace.

### marketplace-mobile

Customer-facing TTC marketplace mobile application.

### seller-web

Common seller operational/admin application.

### seller-mobile

Common seller operational mobile application.

### driver-mobile

Common driver operational application.

### admin-web

TTC platform administration/control plane.

---

# 4. White-Label Architecture

White-label customer experiences are a core TTC capability.

They are NOT separate bespoke applications developed independently for every seller.

Conceptually:

```text
                    TTC PLATFORM
                         │
                         ▼
              WHITE-LABEL RUNTIME
                         │
          ┌──────────────┴──────────────┐
          │                             │
     Seller Config                 Seller Identity
          │                             │
          └──────────────┬──────────────┘
                         ▼
              Seller Customer Experience
                         │
                  ┌──────┴──────┐
                  ▼             ▼
               Website        Mobile
```

Multiple sellers must be able to run distinct branded experiences from the common platform.

The architecture must support:

* seller branding
* seller configuration
* seller-specific customer experience
* seller domain/subdomain configuration
* seller-specific catalog presentation
* seller-specific supported features
* seller-specific policies where the platform permits configuration

without duplicating application source code.

---

# 5. Seller Models

TTC supports two principal seller operating models.

## 5.1 Marketplace Seller

A Marketplace Seller:

* sells through the TTC marketplace
* operates within TTC marketplace governance
* configures supported catalog/services/pricing
* uses TTC marketplace infrastructure
* does not create arbitrary platform capabilities
* does not create arbitrary code/workflows
* does not independently control TTC platform governance

TTC controls marketplace-level capabilities and governance.

---

## 5.2 Full-Access Seller

A Full-Access Seller receives a broader operational platform.

It may have:

* white-label customer website
* white-label customer mobile application
* own branding
* own domain configuration
* seller-managed users
* seller-managed roles
* seller-managed permissions
* broader supported configuration
* seller-specific operational configuration

However:

> Full-Access Sellers still operate only within capabilities provided by TTC.

They cannot create arbitrary software, code, or unsupported workflows.

---

# 6. Separation of Responsibilities

The platform must maintain a clear boundary between:

```text
TTC Platform Governance
Seller Configuration
Customer Experience
Operational Execution
```

### TTC controls

Examples:

* platform architecture
* platform security
* tenant isolation
* master catalog
* platform-wide capabilities
* platform policies
* permission definitions
* supported configuration boundaries
* marketplace governance
* platform audit
* white-label runtime
* policy versioning
* platform-level restrictions

### Seller controls

Where permitted:

* services
* service configuration
* branch configuration
* seller pricing
* supported pricing policies
* operational configuration
* seller users
* seller roles
* seller permissions
* branding
* customer experience configuration
* seller commercial configuration

Seller configuration must remain inside TTC-defined boundaries.

---

# 7. Multi-Tenancy

TTC is fundamentally multi-tenant.

Every tenant-owned operation must execute within an authoritative tenant context.

Conceptually:

```text
Authenticated User
        ↓
Identity
        ↓
TenantContext
        ↓
Authorization
        ↓
Domain Operation
        ↓
Tenant-scoped Data
```

Never trust arbitrary tenant identifiers supplied by clients.

Tenant identity must be derived from authenticated/platform context and validated relationships.

---

# 8. Tenant Isolation

The system must prevent:

```text
Tenant A → Tenant B data
Tenant A → Tenant B orders
Tenant A → Tenant B customers
Tenant A → Tenant B services
Tenant A → Tenant B pricing
Tenant A → Tenant B configuration
```

Tenant isolation must be enforced at:

```text
API
Application Service
Repository
Database
Authorization
```

where appropriate.

Frontend filtering is not a security mechanism.

---

# 9. Seller Hierarchy

The conceptual hierarchy is:

```text
TTC Platform
     ↓
Tenant / Seller
     ↓
Branches
     ↓
Services / Catalog Configuration
     ↓
Orders
     ↓
Operational Execution
```

Relationships must be validated.

For example:

```text
Order
 ├── tenant
 ├── seller
 └── branch
```

must represent one consistent ownership hierarchy.

The system must reject cross-seller/cross-tenant combinations.

---

# 10. Customer Domain

Customers are platform users/entities distinct from sellers.

A customer may:

```text
discover seller
    ↓
select seller/branch
    ↓
select service
    ↓
receive pricing
    ↓
create order
    ↓
approve price where required
    ↓
track operational lifecycle
    ↓
pay according to payment policy
    ↓
receive delivery
    ↓
request reservice where eligible
```

Customers must only access their own protected customer data and orders.

---

# 11. Seller Operational Platform

Seller Web and Seller Mobile are common TTC applications.

They must not contain separate business implementations for individual sellers.

Instead:

```text
Common Seller Application
        +
Authenticated Seller
        +
TenantContext
        +
RBAC
        +
Seller Configuration
        ↓
Seller Experience
```

The same application can therefore serve many sellers.

---

# 12. Driver Platform

Driver Mobile is a common operational application.

Drivers operate against assignments created by the platform/seller operational workflow.

Driver-specific functionality includes:

* assignment
* reassignment
* pickup
* pickup verification
* item capture
* quantity
* weight
* condition
* damage evidence
* customer interaction
* OTP delivery verification
* payment collection where permitted
* reservice operations
* operational exceptions

Driver functionality must not create arbitrary commercial rules.

Commercial authority remains in the backend/domain services.

---

# 13. TTC Admin Platform

Admin Web is the TTC control plane.

It manages platform-level capabilities such as:

```text
platform configuration
seller governance
master catalog
platform policies
reason definitions
pricing policies
payment policies
permissions
RBAC
commercial configuration
white-label governance
restrictions
audit
```

Admin functionality must be clearly separated from seller administration.

---

# 14. Domain Architecture

TTC should be organized around business domains rather than screens.

Major domains include:

```text
Identity
Tenancy
RBAC
Seller
Branch
Master Catalog
Seller Catalog
Service
Pricing
Price Policy
Customer
Marketplace
Order
Pickup
Fulfillment
Driver
Payment
Settlement
Billing
Commercial
Reservice
White Label
Configuration
Audit
```

Detailed domain boundaries will be defined by subsequent baseline prompts.

---

# 15. Dependency Direction

The architecture must maintain controlled dependencies.

Conceptually:

```text
Frontend
   ↓
API
   ↓
Application Services
   ↓
Domain Services
   ↓
Repositories
   ↓
Database
```

Shared contracts:

```text
Backend
   ↓
Shared Types
   ↓
Frontend
```

Frontend must not directly implement authoritative commercial/business rules.

---

# 16. Backend + Frontend Development Strategy

TTC will NOT be developed as:

```text
Complete backend
        ↓
Complete frontend later
```

Instead use vertical slices.

For each capability:

```text
Business Capability
        ↓
Backend Domain/API
        ↓
Shared Type Contract
        ↓
Web UI
        ↓
Mobile UI where applicable
        ↓
Integration
        ↓
Tests
        ↓
Validation
        ↓
Git Commit
```

This is the required implementation strategy for the project.

---

# 17. Platform-Specific Applications First

Initial implementation focus is:

```text
admin-web
marketplace-web
marketplace-mobile
seller-web
seller-mobile
```

The common driver application remains part of the architecture, but detailed driver implementation should occur according to the implementation dependency plan.

White-label seller-specific customer experiences should also be implemented only after the shared platform capabilities they depend on are stable.

Do not prematurely create:

```text
Seller A codebase
Seller B codebase
Seller C codebase
```

---

# 18. Shared Packages

The monorepo should use shared packages where appropriate:

```text
packages/
├── types
├── ui
├── config
├── auth
├── tenant
└── api-client
```

Shared packages should provide reusable infrastructure and contracts.

Do not move domain authority into frontend shared packages.

---

# 19. Shared Types

Shared TypeScript types represent API/domain contracts.

Examples:

```text
Order
OrderItem
OrderStatus
Seller
Branch
Service
CatalogItem
PricingResult
Payment
DriverAssignment
```

The exact interfaces belong to their respective domain prompts.

Frontend applications should not independently redefine backend contracts.

---

# 20. Master Catalog Principle

TTC maintains a master catalog.

Sellers do not freely create arbitrary master catalog objects.

Conceptually:

```text
TTC Master Catalog
        ↓
Seller selects/configures
        ↓
Seller Service
        ↓
Customer Experience
```

If a seller needs an unavailable master item:

```text
Seller Request
      ↓
TTC Review
      ↓
Master Catalog Addition
      ↓
Seller can select it
```

Master catalog changes must not silently corrupt existing seller configuration or historical orders.

---

# 21. Historical Immutability

Historical commercial records must not depend on current configuration.

Especially:

```text
Order
Pricing
Catalog
Customer snapshot
Address snapshot
Payment policy snapshot
Price policy snapshot
```

must preserve the historical state required to understand what actually occurred.

General principle:

```text
Current Configuration
       ↓
Transaction Creation
       ↓
Historical Snapshot
       ↓
Immutable Commercial Record
```

Future configuration changes must not silently rewrite historical transactions.

---

# 22. Pricing Authority

The Pricing Engine is the authoritative source for pricing calculations.

No application may duplicate pricing calculations.

Correct:

```text
Marketplace
     ↓
Backend
     ↓
Pricing Engine
     ↓
Authoritative Result
```

Incorrect:

```text
Marketplace calculates price
Seller Mobile calculates price
Backend calculates different price
```

There must be one authoritative pricing domain.

---

# 23. Order Authority

The Order becomes the historical commercial source of truth once created.

Conceptually:

```text
Catalog
"What is offered?"

Pricing
"How much does it cost?"

Order
"What did this customer actually purchase?"
```

Order creation must snapshot the necessary commercial state.

---

# 24. Price Lock

Final commercial price becomes immutable after customer approval.

```text
Order
 ↓
Estimated pricing
 ↓
Pickup actuals
 ↓
Final pricing
 ↓
Customer approval
 ↓
PRICE LOCKED
```

After price lock:

* normal pricing-policy changes cannot alter the price
* catalog changes cannot alter the price
* seller configuration changes cannot alter the price

Exceptional corrections require a dedicated controlled workflow.

---

# 25. Price Policy Versioning

Published price-policy versions are immutable.

New corrections require new versions.

Historical orders preserve the policy version relevant to them.

If an applicable policy changes before an order reaches final price approval, the order may move to the newer policy according to the established business rules.

Pricing Engine remains responsible for recalculation.

---

# 26. Customer Approval

Customer approval is a commercial authorization boundary.

Any price change requiring approval must explicitly obtain customer approval.

This includes:

* price increases
* price decreases
* manual adjustments
* exceptional locked-price corrections

No unapproved price may silently become final.

---

# 27. Order Lifecycle

The core order lifecycle remains intentionally small:

```text
PENDING
   ↓
CONFIRMED
   ↓
IN_PROGRESS
   ↓
COMPLETED
```

Cancellation is a controlled terminal path:

```text
PENDING → CANCELLED
CONFIRMED → CANCELLED
```

The exact actor/reason is recorded separately.

Do not create unnecessary top-level states for every operational event.

Operational stages such as pickup and delivery should not automatically become dozens of core Order statuses.

---

# 28. Seller Acceptance / Rejection

Seller acceptance:

```text
PENDING → CONFIRMED
```

Seller rejection:

```text
PENDING → CANCELLED
```

with structured history such as:

```text
actor_type = SELLER
reason_code = SELLER_REJECTED
```

Customer cancellation:

```text
PENDING → CANCELLED
```

with:

```text
actor_type = CUSTOMER
reason_code = CUSTOMER_CANCELLED
```

This preserves a simple core state machine while retaining business meaning.

---

# 29. Operational State vs Commercial State

TTC must distinguish:

```text
Order State
```

from:

```text
Operational Events / Stages
```

For example:

```text
Order:
CONFIRMED

Operational:
PICKUP_ASSIGNED
PICKUP_STARTED
PICKUP_VERIFICATION
PICKUP_COMPLETED
```

Do not turn every operational event into a top-level Order status unless there is a strong domain requirement.

---

# 30. Pickup Architecture

Pickup verification is an operational capability.

It can capture:

```text
item
quantity
weight
condition
damage
photos
notes
actual pickup details
```

Billing measurement and pickup capture are separate concepts.

Example:

```text
Service billing:
KG

Pickup capture:
item count + weight
```

The driver must use predefined master catalog entries permitted by the service.

---

# 31. Fulfillment Boundary

Maintain:

```text
ORDER
=
commercial customer transaction
```

and:

```text
FULFILLMENT
=
operational execution
```

Do not merge them into one giant domain.

---

# 32. Payment Boundary

Maintain:

```text
ORDER
=
what was purchased/agreed

PAYMENT
=
money movement
```

An Order can exist before payment.

Payment state must not redefine the meaning of `PENDING`.

`PENDING` means:

> Customer successfully submitted the order and the seller has not yet accepted it.

It does NOT mean:

> Payment pending.

---

# 33. Billing Boundary

Maintain:

```text
ORDER
≠
INVOICE
```

Order represents the commercial transaction.

Invoice represents formal billing/accounting.

They must remain separate domains.

---

# 34. Settlement Boundary

Maintain:

```text
PAYMENT
   ↓
Settlement
```

Seller settlement is distinct from customer payment.

Settlement calculations must not be embedded inside Order.

---

# 35. Reservice Boundary

Reservice is an operational case associated with a completed order.

It does not replace the original order.

The original order remains historically complete.

Reservice has its own lifecycle, pricing/payment rules, and operational workflow.

Detailed reservice behavior belongs to the Reservice domain prompt.

---

# 36. Commercial Model

TTC supports seller commercial models including:

```text
Percentage Commission
        OR
Monthly Subscription / Platform Fee
```

The exact commercial rules are defined by the Commercial domain.

Commercial model changes must not silently rewrite historical transactions.

---

# 37. Configuration-Driven Architecture

Seller behavior should be configurable where the platform supports configuration.

However:

```text
Configuration
≠
arbitrary programming
```

TTC defines:

```text
available capability
allowed configuration
valid ranges
supported combinations
```

Seller chooses from those supported options.

---

# 38. Configuration Precedence

Where multiple configuration layers exist, use the established TTC precedence model.

Conceptually:

```text
Platform Defaults
       ↓
Tenant/Seller Configuration
       ↓
Application-Specific Configuration
```

More specific configuration may override less specific configuration where explicitly supported.

Sensitive configuration must be redacted according to security rules.

---

# 39. Versioning Principle

Any configuration that affects historical commercial interpretation must be versioned or snapshotted.

Examples:

```text
pricing policy
payment policy
reason definition
seller commercial configuration
```

Published/used versions must not be silently rewritten.

---

# 40. Auditability

Important business actions must produce auditable history.

Examples:

```text
order created
order accepted
order rejected
order cancelled
price adjusted
price locked
locked price exception
policy change
permission change
seller restriction
payment action
driver reassignment
```

Audit should preserve:

```text
actor
tenant
timestamp
action
relevant entity
before/after where appropriate
reason where required
```

Do not store unnecessary sensitive information.

---

# 41. Security Principle

Security must be enforced server-side.

Never rely on:

```text
frontend hiding a button
frontend filtering a list
URL obscurity
client-supplied tenant ID
client-supplied seller ID
client-supplied customer ID
```

The backend must independently authorize every protected operation.

---

# 42. RBAC Principle

TTC uses:

```text
Roles
+
Permissions
+
Optional User-Level Overrides
```

Conceptually:

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

Users cannot invent arbitrary permissions.

Permission administration itself is permission-controlled.

---

# 43. Permission Dependencies

Permissions may have dependencies/inheritance.

The platform must validate permission relationships rather than allowing an invalid permission combination.

Role changes apply according to the current permission model.

User-level overrides remain where applicable.

---

# 44. Concurrency Principle

Critical operations must be concurrency-safe.

Examples:

```text
order creation
idempotency
order number generation
status transitions
seller acceptance/rejection
price adjustment
payment operations
driver reassignment
```

Do not rely only on application-level checks.

Use PostgreSQL transactions and constraints where appropriate.

---

# 45. Idempotency

Customer order creation must support idempotency.

Repeated requests with the same valid idempotency key must not create duplicate orders.

Reusing a key with materially different input must produce a conflict.

Other business operations should use idempotency where repeated requests could create duplicate commercial/operational effects.

---

# 46. API Principle

APIs must expose explicit domain operations.

Prefer:

```text
POST /orders/{id}/confirm
POST /orders/{id}/reject
POST /orders/{id}/cancel
```

over arbitrary status mutation:

```text
PATCH /orders/{id}
{
  "status": "CONFIRMED"
}
```

Domain transitions must remain controlled.

---

# 47. Frontend Principle

Frontend applications are clients of the platform.

They should:

* consume API contracts
* use shared types
* enforce presentation-level permissions
* provide appropriate UX
* handle loading/error states
* display configuration-driven behavior

They must not become an alternative backend.

---

# 48. Mobile Principle

Mobile applications use the same authoritative backend.

Do not create separate mobile business logic for:

```text
pricing
orders
payments
permissions
seller rules
```

where those rules already belong to backend domains.

Mobile-specific behavior should be limited to mobile UX and platform capabilities.

---

# 49. White-Label Principle

White-label is a runtime/configuration capability.

Correct:

```text
Common Application
+
Tenant Resolution
+
Seller Configuration
+
Branding
```

Incorrect:

```text
Seller A source code
Seller B source code
Seller C source code
```

The system must be able to serve many seller experiences without code duplication.

---

# 50. Domain Ownership

Each major business rule must have one authoritative owner.

Examples:

```text
Authentication → Identity/Auth
Authorization → RBAC
Catalog → Catalog Domain
Pricing → Pricing Engine
Order lifecycle → Order Domain
Pickup → Pickup/Fulfillment
Payment → Payment Domain
Settlement → Settlement Domain
Billing → Billing Domain
White-label behavior → White-Label/Configuration Domain
```

Do not duplicate the same rule in multiple services.

---

# 51. Testing Principle

Every implementation unit must validate:

```text
business behavior
authorization
tenant isolation
database integrity
API contract
frontend integration
```

Where applicable also test:

```text
concurrency
idempotency
versioning
historical immutability
price calculations
state transitions
```

Never declare the system green based only on isolated test files.

---

# 52. Implementation Unit Completion

A capability is not considered complete merely because code exists.

Required completion sequence:

```text
Implementation
    ↓
Backend validation
    ↓
Frontend validation
    ↓
Integration tests
    ↓
Regression tests
    ↓
Lint/typecheck/build
    ↓
Git diff review
    ↓
Focused commit
```

Do not claim success without actual validation.

---

# 53. Git Policy

Before work:

```bash
git status --short
```

Never use destructive commands such as:

```bash
git reset --hard
git clean -fd
```

Do not blindly use:

```bash
git add .
```

Stage only relevant files.

Every completed implementation unit requires a focused Git commit.

Never claim a commit or push unless it was actually verified.

---

# 54. Implementation Dependency Principle

Implementation follows domain dependency rather than arbitrary screen order.

Example:

```text
Identity
   ↓
Tenancy
   ↓
RBAC
   ↓
Seller
   ↓
Master Catalog
   ↓
Seller Catalog
   ↓
Service
   ↓
Pricing
   ↓
Marketplace
   ↓
Order
   ↓
Pickup
   ↓
Payment
   ↓
Fulfillment
   ↓
Delivery
   ↓
Reservice / Advanced Operations
```

Actual implementation sequencing will be defined in the dedicated roadmap prompt.

---

# 55. Current Development Strategy

The project should initially concentrate on the platform-specific applications:

```text
admin-web
marketplace-web
marketplace-mobile
seller-web
seller-mobile
```

Development should proceed through vertical slices.

For example:

```text
Seller Management
      ↓
Backend
      ↓
Shared Types
      ↓
Seller Web
      ↓
Seller Mobile where required
      ↓
Admin Web where required
      ↓
Tests
      ↓
Commit
```

Then move to the next capability.

---

# 56. No Premature Infrastructure Complexity

Do not introduce infrastructure merely because it may be useful later.

Do not prematurely introduce:

```text
microservices
Kafka
RabbitMQ
Kubernetes
OpenSearch
distributed event buses
```

unless an actual TTC requirement and architecture decision later justify them.

Prefer a modular, maintainable platform architecture.

---

# 57. Historical Source-of-Truth Rule

The most important commercial rule is:

```text
Current Configuration
        ↓
Transaction
        ↓
Snapshot
        ↓
Historical Truth
```

Never:

```text
Historical Order
        ↓
Recalculate using today's configuration
```

This principle applies across:

```text
pricing
catalog
customer information
address
payment policy
price policy
commercial configuration
```

where historical interpretation matters.

---

# 58. Architectural Boundaries

At the highest level:

```text
                    TTC PLATFORM
                         │
        ┌────────────────┼────────────────┐
        │                │                │
    CUSTOMER          SELLER            DRIVER
        │                │                │
        └────────────────┼────────────────┘
                         │
                     MARKETPLACE
                         │
                      CATALOG
                         │
                      PRICING
                         │
                       ORDER
                         │
                     PICKUP
                         │
                    FULFILLMENT
                         │
                     PAYMENT
                         │
                    SETTLEMENT
                         │
                      BILLING
```

White-label operates as a configurable customer-experience layer over the shared platform.

Admin operates as the TTC control plane.

---

# 59. What This Baseline Does Not Do

This master prompt does NOT finalize every field, endpoint, screen, database table, workflow, or business rule.

Those belong to the subsequent specialized prompts:

```text
Marketplace
Seller
Driver
Backend
Frontend
Mobile
White-label
Catalog
Pricing
Order
Pickup
Payment
Commercial
Reservice
RBAC
Database
Testing
DevOps
Documentation
Implementation Roadmap
```

If a detailed prompt conflicts with this master architecture, identify the conflict explicitly rather than silently choosing one.

---

# 60. Baseline Governance

This document represents **TTC Baseline v1.0**.

Future business decisions may modify this baseline.

When a decision changes the architecture:

```text
New Business Decision
        ↓
Impact Analysis
        ↓
Affected Baseline Prompt(s)
        ↓
Baseline Version Update
        ↓
Implementation Plan Update
```

Do not silently modify architecture because of an implementation convenience.

Business requirements take precedence over implementation convenience, while maintaining clear domain boundaries.

---

# Final Principle

THE TEXTILE CARE should be built as:

```text
ONE
MULTI-TENANT
CONFIGURATION-DRIVEN
MODULAR
PLATFORM

with

COMMON WEB
COMMON MOBILE
COMMON BACKEND
COMMON DOMAIN LOGIC
COMMON WHITE-LABEL RUNTIME

serving

TTC MARKETPLACE
+
MULTIPLE MARKETPLACE SELLERS
+
MULTIPLE FULL-ACCESS SELLERS
+
DRIVERS
+
TTC ADMINISTRATION
```

The platform must scale through **configuration and tenant isolation**, not through source-code duplication.

The implementation strategy must be:

```text
BUSINESS CAPABILITY
       ↓
BACKEND
       ↓
SHARED TYPES
       ↓
WEB
       ↓
MOBILE
       ↓
INTEGRATION
       ↓
TEST
       ↓
COMMIT
```

This is the architectural foundation for all subsequent TTC baseline prompts.
