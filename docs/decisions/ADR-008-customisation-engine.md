# ADR 008: Customisation Engine

## Context
Seller needs vary in configuration, feature flags, and workflows.

## Decision
Use a centralized customization model with configuration, flags, and workflow definitions.

## Reason
A single, shared capability layer supports many sellers without agency-specific code forks.

## Consequences
- config-driven behaviors
- predictable platform extension
- no seller-specific fork strategy
