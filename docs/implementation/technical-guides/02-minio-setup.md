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

| Bucket Name        | Logical Path (Docs)      | Purpose                                                                |
| ------------------ | ------------------------ | ---------------------------------------------------------------------- |
| `raw`              | `/data/raw`              | Unprocessed source data (SEC filings, transcripts, news, market data). |
| `processed`        | `/data/processed`        | Cleaned and structured data (financial statements, ratios, sentiment). |
| `models`           | `/data/models`           | Valuation models and scenario analysis files (Excel, JSON, Parquet).   |
| `pattern-archives` | `/data/pattern_archives` | Tier 1 and Tier 2 archives for critical pattern evidence (DD-009).     |
| `outputs`          | `/data/outputs`          | Final analysis products (reports, watchlists, decision logs).          |

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
