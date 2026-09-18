# Architecture Overview

The Textile Care is a multi-tenant platform built around a shared platform and shared codebase.

## Application map

- Marketplace Web
- Marketplace Mobile
- Seller Web
- Seller Mobile
- Driver Mobile
- Admin Web
- White-label and app-factory modules

## Architectural layers

```text
Marketplace | Seller SaaS | Driver App | Admin
     \            |             |         /
      \-----------|-------------|--------/
                 Shared Platform
                        |
                Shared Backend
                        |
               Customers / Drivers / Finance
```
