# Storage Layer

This directory contains the implementation of the persistence layer for the Fundamental Analysis System.

## Documentation

For detailed setup instructions, schema definitions, and migration guides, please refer to:

[📄 Database Infrastructure & Migration Guide](../../docs/implementation/technical-guides/01-database-infrastructure.md)

## Directory Structure

*   **`migrations/`**: Alembic migration scripts and configuration.
    *   `versions/`: Individual migration files (e.g., `a125ac7b2db7_initial_schema.py`).
    *   `env.py`: Alembic environment configuration with `asyncpg` support.
    *   `script.py.mako`: Template for new migration files.

## Quick Start (Migrations)

Run from project root:

```bash
# Apply all migrations
uv run alembic upgrade head

# Create new migration
uv run alembic revision -m "your_message"
```
