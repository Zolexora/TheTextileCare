# ADR 001: Monorepo

## Context
The platform needs shared code, independent applications, and a production-ready foundation.

## Decision
Use a single pnpm/Turborepo monorepo.

## Reason
Shared packages and apps can evolve together without forking the repository.

## Consequences
- shared package reuse
- stable developer workflow
- consistent quality gates
