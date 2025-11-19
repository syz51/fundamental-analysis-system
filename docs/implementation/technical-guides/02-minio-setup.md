# MinIO Object Storage Setup

## Overview

This document describes the local S3-compatible object storage setup using MinIO for the Fundamental Analysis System. This setup mirrors the tiered storage architecture defined in [Data Management](../../operations/03-data-management.md) and [Backup & Disaster Recovery](../../design-decisions/DD-019_DATA_TIER_OPERATIONS.md).

## Infrastructure

The MinIO service is defined in `docker-compose.yml`:

- **Service Name**: `minio`
- **Image**: `minio/minio:latest`
- **API Port**: `9000` (S3 API)
- **Console Port**: `9001` (Web UI)
- **Data Volume**: `minio_data` (Docker volume)

### Credentials (Local Development)

- **Username**: `minioadmin`
- **Password**: `minioadmin`

## Bucket Structure

The following buckets are created to organize data according to the system's lifecycle policies:

| Bucket Name                | Logical Path (Docs)      | Versioning | Purpose                                                                |
| -------------------------- | ------------------------ | ---------- | ---------------------------------------------------------------------- |
| `raw`                      | `/data/raw`              | ✅ Enabled | Unprocessed source data (SEC filings, transcripts, news, market data). |
| `processed`                | `/data/processed`        | -          | Cleaned and structured data (financial statements, ratios, sentiment). |
| `models`                   | `/data/models`           | -          | Valuation models and scenario analysis files (Excel, JSON, Parquet).   |
| `pattern-archives`         | `/data/pattern_archives` | ✅ Enabled | Tier 1 and Tier 2 archives for critical pattern evidence (DD-009).     |
| `outputs`                  | `/data/outputs`          | -          | Final analysis products (reports, watchlists, decision logs).          |
| `neo4j-backups-primary`    | -                        | -          | Neo4j database backups (DD-021 HA requirements).                       |
| `postgres-backups-primary` | -                        | -          | PostgreSQL database backups (DD-021 HA requirements).                  |

**_Versioning Rationale (Development vs. Production)_**

In the current development setup, versioning is selectively enabled only for the `raw` and `pattern-archives` buckets. This design choice is intentional for the following reasons:

- **`raw` bucket**: Versioning is enabled to maintain an immutable audit trail of unprocessed source data, which is critical for compliance and re-validation of patterns.
- **`pattern-archives` bucket**: Versioning is enabled as mandated by [DD-009: Data Retention & Pattern Evidence](../../design-decisions/DD-009_DATA_RETENTION_PATTERN_EVIDENCE.md) to ensure the preservation of critical pattern evidence used in investment decisions.
- **Other buckets (`processed`, `models`, `outputs`, `*-backups-primary`)**: These buckets primarily store derived or transient data that can be regenerated from source data or are managed by other backup strategies. Versioning is not enabled in the development environment to optimize local storage and performance.

This selective approach aligns with a **phased implementation strategy**. While versioning is limited in development, a more comprehensive versioning policy is planned for the production environment (e.g., AWS S3) to meet broader data governance and disaster recovery requirements, as outlined in the "Production vs. Development" table below and the project's [Roadmap](../../implementation/01-roadmap.md).

> **Note**: The `/data/memory` paths for Knowledge Graph and Agent Memories are stored in Neo4j and Redis, respectively, not MinIO. Only the `pattern_archives` component of memory uses object storage.

## Setup Instructions

### Prerequisites

1. **Docker**: Ensure Docker and Docker Compose are running.
2. **MinIO Client (`mc`)**: Required for the setup script.
   - macOS: `brew install minio/stable/mc`
   - Linux: Follow [official guide](https://min.io/docs/minio/linux/reference/minio-mc.html).

### Initialization

1. Start the MinIO service:

   ```bash
   docker-compose up -d minio
   ```

2. Run the setup script to configure the client and create buckets:

   ```bash
   ./scripts/setup_minio.sh
   ```

   This script will:

   - Configure a local `mc` alias named `fundamental` pointing to localhost:9000.
   - Create all required buckets if they don't exist.
   - Use a local `.mc_config` directory to avoid modifying your global system configuration.

## Verification

### S3 Select Capability

To verify S3 Select functionality (required by DD-013), run the verification script:

```bash
./scripts/verify_s3_select.sh
```

This script:

- Creates a test bucket with sample JSON data
- Executes an S3 Select SQL query to filter records
- Validates that MinIO correctly processes the query
- Cleans up test resources automatically

Expected output: `✅ SUCCESS: S3 Select is active and filtering correctly.`

## Accessing Data

### Web Console

Access the MinIO Console at **[http://localhost:9001](http://localhost:9001)**.

### CLI Access

You can interact with the buckets using the configured alias (after running the setup script):

```bash
# List buckets
MC_CONFIG_DIR=$(pwd)/.mc_config mc ls fundamental/

# Upload a file
MC_CONFIG_DIR=$(pwd)/.mc_config mc cp my-document.pdf fundamental/raw/sec_filings/

# List files in a bucket
MC_CONFIG_DIR=$(pwd)/.mc_config mc ls fundamental/raw/
```

## Production vs. Development

| Feature           | Development (MinIO)         | Production (AWS S3)                    |
| :---------------- | :-------------------------- | :------------------------------------- |
| **Endpoint**      | `http://localhost:9000`     | `https://s3.us-east-1.amazonaws.com`   |
| **Buckets**       | Manually created / Scripted | Managed via Terraform/IaC              |
| **Storage Class** | Standard (Simulated)        | Standard, Intelligent-Tiering, Glacier |
| **Encryption**    | Disabled (Default)          | SSE-S3 or SSE-KMS                      |
| **Versioning**    | Enabled (if configured)     | Enabled                                |

## Related Documentation

- [DD-009: Data Retention & Pattern Evidence](../../design-decisions/DD-009_DATA_RETENTION_PATTERN_EVIDENCE.md)
- [DD-019: Data Tier Operations](../../design-decisions/DD-019_DATA_TIER_OPERATIONS.md)
- [Operations: Data Management](../../operations/03-data-management.md)
