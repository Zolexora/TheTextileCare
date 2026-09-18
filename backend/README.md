# The Textile Care Backend

This directory contains the shared backend foundation for the platform. Phase 0 establishes the API boundary, request lifecycle, configuration, logging, exception handling, and health checks without implementing business-domain tables or workflows.

## Responsibilities

- FastAPI application bootstrap
- configuration and environment handling
- request IDs and security middleware
- health endpoint and standard API error handling
- SQLAlchemy and Alembic foundation
- Redis and PostgreSQL connection preparation

## Planned boundaries

- API → Schema → Service → Repository → Database
- platform, white-label, and app-factory modules are reserved for future work
