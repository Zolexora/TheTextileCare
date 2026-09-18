# The Textile Care

The Textile Care is a multi-tenant, white-label platform for textile and service operations. The repository is intentionally structured as a single shared codebase with multiple tenant-aware applications and platform capabilities.

## Application map

- marketplace-web
- marketplace-mobile
- seller-web
- seller-mobile
- driver-mobile
- admin-web

## Architecture

- shared backend
- shared platform modules
- white-label and customisation capability
- app factory pipeline
- shared packages for config, types, API, auth, tenant, branding, and UI

## Local development

```bash
pnpm install
pnpm dev
```

## Environment setup

Copy `.env.example` to `.env` and adjust values for your local environment.

## Testing

```bash
pnpm test
```

## Building

```bash
pnpm build
```

## Deployment overview

The project is prepared for Docker-based local development and CI automation. Production deployment steps are intentionally deferred until infrastructure and environment requirements are validated.
