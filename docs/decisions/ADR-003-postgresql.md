# ADR 003: PostgreSQL

## Context
The platform requires a strong transactional relational store and future tenant-aware data storage.

## Decision
Use PostgreSQL as the canonical primary database.

## Reason
It supports structured multi-tenant data and aligns with SQLAlchemy, Alembic, and operational best practices.

## Consequences
- relational consistency
- mature ecosystem
- straightforward migration tooling
