# ADR 004: Multi-Tenancy

## Context
The system serves many sellers and brands from a single codebase.

## Decision
Implement a shared platform with tenant resolution layered on top of a single application runtime.

## Reason
This avoids source duplication and supports white-label configuration patterns.

## Consequences
- one codebase per platform
- tenant-level configuration
- domain-based and app-based resolution preparation
