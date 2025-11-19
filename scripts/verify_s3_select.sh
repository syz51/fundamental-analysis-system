#!/bin/bash
set -e

# S3 Select Capability Verification Script
# Verifies that the local MinIO instance supports S3 Select SQL queries
# as required by Design Decision DD-013.

# Load Configuration (matches setup_minio.sh)
export MC_CONFIG_DIR="$(pwd)/.mc_config"
MINIO_ALIAS="fundamental"
TEST_BUCKET="test-capability-check"
TEST_FILE="s3_select_test.json"

# Check for mc
if ! command -v mc &> /dev/null; then
    echo "Error: 'mc' not found. Run setup_minio.sh first."
    exit 1
fi

# Cleanup function
cleanup() {
    echo "Cleaning up..."
    mc rm --force "$MINIO_ALIAS/$TEST_BUCKET/$TEST_FILE" > /dev/null 2>&1 || true
    mc rb --force "$MINIO_ALIAS/$TEST_BUCKET" > /dev/null 2>&1 || true
    rm -f "$TEST_FILE"
}
trap cleanup EXIT

echo "1. Creating test bucket..."
mc mb --ignore-existing "$MINIO_ALIAS/$TEST_BUCKET"

echo "2. Uploading test JSON data..."
# Create simple JSON: ID 1 is cheap, ID 2 is expensive
echo '{"id": 1, "name": "cheap_item", "price": 10}' > "$TEST_FILE"
echo '{"id": 2, "name": "expensive_item", "price": 100}' >> "$TEST_FILE"
mc cp "$TEST_FILE" "$MINIO_ALIAS/$TEST_BUCKET/$TEST_FILE"

echo "3. Executing S3 Select Query (Filter price > 50)..."
# Query for items with price > 50. 
# Note: 's3object' is the default table name for S3 Select queries in MinIO
RESULT=$(mc sql --query "select s.name from s3object s where s.price > 50" "$MINIO_ALIAS/$TEST_BUCKET/$TEST_FILE")

echo "   Query Result: $RESULT"

if [[ "$RESULT" == *"expensive_item"* ]] && [[ "$RESULT" != *"cheap_item"* ]]; then
    echo "✅ SUCCESS: S3 Select is active and filtering correctly."
else
    echo "❌ FAILURE: S3 Select returned unexpected results."
    exit 1
fi
