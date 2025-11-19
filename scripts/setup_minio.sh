#!/bin/bash

# MinIO Setup Script
# This script configures the MinIO client (mc) and creates the necessary buckets
# for the Fundamental Analysis System.

# Exit on error
set -e

# Configuration
MINIO_HOST="http://localhost:9000"
MINIO_USER="minioadmin"
MINIO_PASS="minioadmin"
MINIO_ALIAS="fundamental"

# Use a local directory for mc configuration to avoid system-level permission issues
export MC_CONFIG_DIR="$(pwd)/.mc_config"

echo "Checking for mc (MinIO Client)..."
if ! command -v mc &> /dev/null; then
    echo "Error: 'mc' is not installed. Please install it first."
    echo "  macOS: brew install minio/stable/mc"
    echo "  Linux: wget https://dl.min.io/client/mc/release/linux-amd64/mc && chmod +x mc && sudo mv mc /usr/local/bin/"
    exit 1
fi

echo "Configuring MinIO alias '$MINIO_ALIAS'..."
# The --api "s3v4" flag is often helpful for compatibility
mc alias set "$MINIO_ALIAS" "$MINIO_HOST" "$MINIO_USER" "$MINIO_PASS"

echo "Creating buckets..."

create_bucket() {
    local bucket_name=$1
    echo "Creating bucket: $bucket_name"
    # "mb -p" ignores the error if the bucket already exists
    mc mb -p "$MINIO_ALIAS/$bucket_name"
}

enable_versioning() {
    local bucket_name=$1
    echo "Enabling versioning for bucket: $bucket_name"
    mc version enable "$MINIO_ALIAS/$bucket_name"
}

# Core Data Buckets
create_bucket "raw"
enable_versioning "raw"  # Immutability requirement

create_bucket "processed"
create_bucket "models"

create_bucket "pattern-archives"
enable_versioning "pattern-archives" # Immutability requirement

create_bucket "outputs"

# Backup Buckets (DD-021 High Availability & Data Management Policy)
create_bucket "neo4j-backups-primary"
create_bucket "postgres-backups-primary"

echo "MinIO setup complete!"
echo "Access the console at: http://localhost:9001"
echo "Credentials: $MINIO_USER / $MINIO_PASS"