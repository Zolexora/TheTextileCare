# ADR 006: White-Label Architecture

## Context
Seller brands need custom domains and branded experiences without separate repositories.

## Decision
Use shared applications with tenant configuration, brand assets, and custom domains layered in.

## Reason
The architecture requires a shared codebase and tenant-level configuration, not tenant-specific codebases.

## Consequences
- dynamic branding
- white-label domains
- reuse of shared mobile source
