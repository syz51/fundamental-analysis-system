# Database Infrastructure & Migration Guide

## Overview

This document details the implementation of the persistent storage layer for the Fundamental Analysis System. It covers the PostgreSQL and Redis infrastructure managed via Docker, the database schema organization, and the workflow for managing schema changes using Alembic.

## 1. Infrastructure Setup

### Docker Configuration

We use **Docker Compose** to manage our database services, ensuring consistent environments across development and production.

- **File**: `docker-compose.yml` (Project Root)
- **Services**:
  - **PostgreSQL**: Image `postgres:18.1`
    - **Port**: `5432`
    - **Volume**: `postgres_data:/var/lib/postgresql` (Compatible with PG 18+ standards)
    - **Default DB**: `fundamental_analysis`
    - **Credentials**: `postgres` / `postgres`
  - **Redis (L1 Working Memory)**: Image `redis:7`
    - **Port**: `6379`
    - **Volume**: `redis_l1_data:/data`
    - **Persistence**: AOF + RDB (Hybrid)
  - **Redis (L2 Cache)**: Image `redis:7`
    - **Port**: `6380`
    - **Volume**: `redis_l2_data:/data`
    - **Persistence**: RDB Only
  - **Redis (Checkpoint)**: Image `redis:7`
    - **Port**: `6381`
    - **Volume**: `redis_checkpoint_data:/data`
    - **Persistence**: AOF + RDB (Hybrid)

### Running the Infrastructure

```bash
# Start services in background
docker compose up -d

# Check status
docker compose ps

# Stop services
docker compose down

# Stop and remove volumes (RESET DATA)
docker compose down -v
```

## 2. Database Schemas

The system uses a single PostgreSQL database (`fundamental_analysis`) organized into logical **schemas** to separate concerns. This approach was chosen over multiple databases to facilitate cross-domain queries and simplify management.

### Active Schemas

| Schema              | Purpose                          | Key Tables                                                         |
| :------------------ | :------------------------------- | :----------------------------------------------------------------- |
| `workflow`          | Agent execution state & recovery | `agent_checkpoints`, `paused_analyses`, `batch_pause_operations`   |
| `access_tracking`   | Data access patterns & auditing  | `file_access_log`, `file_access_weekly` (Materialized View)        |
| `outcomes`          | Prediction tracking & learning   | `predictions`, `actuals`, `prediction_outcomes`, `lessons_learned` |
| `public`            | System-wide security audit       | `memory_access_audit`                                              |
| `financial_data`    | Financial statements (Future)    | _Provisioned_                                                      |
| `market_data`       | Price/Volume data (Future)       | _Provisioned_                                                      |
| `metadata`          | Ticker/Company info (Future)     | _Provisioned_                                                      |
| `document_registry` | S3 file tracking (Future)        | _Provisioned_                                                      |

## 3. Database Migrations (Alembic)

We use **Alembic** for database migrations. It is configured to use **asyncpg** to align with the project's async Python stack.

- **Config File**: `alembic.ini` (Project Root)
- **Script Location**: `src/storage/migrations/`
- **Versions**: `src/storage/migrations/versions/`

### Migration Workflow

#### 1. Create a New Migration

When you need to modify the database schema (e.g., add a table, change a column):

1. **Edit your models** (if using an ORM) or plan your SQL changes.
2. **Generate a revision script**:

   ```bash
   uv run alembic revision -m "description_of_change"
   ```

3. **Edit the generated file**:

   - Navigate to `src/storage/migrations/versions/`.
   - Open the new `.py` file.
   - Implement the `upgrade()` and `downgrade()` functions.

   **CRITICAL NOTE FOR ASYNCPG**:
   The `asyncpg` driver **does not support** multiple SQL statements in a single `op.execute()` call. You must split them:

   - ❌ **Bad**:

     ```python
     op.execute("CREATE TABLE a (...); CREATE TABLE b (...);")
     ```

   - ✅ **Good**:

     ```python
     op.execute("CREATE TABLE a (...)")
     op.execute("CREATE TABLE b (...)")
     ```

#### 2. Apply Migrations

To apply pending migrations and update your local database schema:

```bash
uv run alembic upgrade head
```

#### 3. Rollback Migrations

To undo the last applied migration:

```bash
uv run alembic downgrade -1
```

To revert to a specific version (e.g., `base` for empty DB):

```bash
uv run alembic downgrade base
```

#### 4. View History

To see the migration history and current state:

```bash
uv run alembic history --verbose
uv run alembic current
```

## 4. Implementation Details

### Asyncpg Integration

Alembic usually runs synchronously. To support `asyncpg`, we customized `src/storage/migrations/env.py`:

1. It uses `run_migrations_online()` which spins up an `asyncio` loop.
2. It utilizes `run_async_migrations()` to connect via `create_async_engine`.
3. It uses `connection.run_sync()` to execute the actual Alembic context, bridging the async connection to Alembic's synchronous internals.

### Schema Qualification

All tables in migration scripts are explicitly schema-qualified (e.g., `CREATE TABLE workflow.agent_checkpoints`). This ensures tables are created in the correct logical namespace, regardless of the user's default `search_path`.

### Initial Schema Revision

- **ID**: `a125ac7b2db7`

- **Description**: "Initial schema"
- **Content**: Contains the DDL for all base tables defined in Design Decisions DD-011, DD-012, DD-017, DD-019, and DD-020.

## Related Guides

- [Elasticsearch Setup & Search Component Guide](./03-elasticsearch-setup.md)
