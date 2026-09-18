# Database Architecture

The backend uses PostgreSQL with SQLAlchemy 2 and Alembic. Phase 0 establishes infrastructure and connection configuration only.

Phase 1 will introduce tenant and identity tables such as:

- users
- organizations
- tenants
- memberships
- roles
- permissions

Phase 0 intentionally does not create those tables.
