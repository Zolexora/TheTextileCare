# ADR 007: App Factory

## Context
The platform needs to support branded mobile and web experiences for sellers.

## Decision
Use an app factory that consumes the shared mobile source, applies brand assets, and manages build and signing workflows.

## Reason
This enables consistent production builds while allowing tenant customization.

## Consequences
- asset validation
- release tracking
- standard build pipeline
