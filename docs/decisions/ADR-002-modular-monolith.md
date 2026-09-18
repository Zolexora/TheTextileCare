# ADR 002: Modular Monolith

## Context
The platform needs maintainable boundaries without premature microservice decomposition.

## Decision
Use a modular backend structure with clear API, schema, service, repository, and database boundaries.

## Reason
This preserves architectural clarity while keeping implementation practical for early phases.

## Consequences
- clear boundaries
- easier migration later
- no business logic in route handlers
