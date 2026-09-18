# ADR 005: Shared Application Codebase

## Context
Multiple sellers require the same platform capabilities with branding and configuration differences.

## Decision
Keep a single shared source base and generate or configure tenant experiences through configuration and branding.

## Reason
This prevents seller-specific forks and keeps operations maintainable.

## Consequences
- lower maintenance cost
- easier platform improvements
- tenant-specific configuration via domain and app metadata
