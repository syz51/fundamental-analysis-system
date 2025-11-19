"""Pytest configuration and fixtures for integration tests requiring external services."""

import os

import asyncpg
import pytest
from elasticsearch import AsyncElasticsearch
from src.storage.search_tool import SearchClient

try:
    import redis.asyncio as redis
except ImportError:
    redis = None

# Environment variables for service URLs
ES_URL = os.getenv("ES_URL", "http://localhost:9200")
POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://postgres:postgres@localhost:5432/fundamental_analysis_test")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


@pytest.fixture(scope="session")
async def es_client():
    """
    Session-scoped Elasticsearch client fixture.

    Provides an AsyncElasticsearch client for integration tests.
    Automatically closes the connection after all tests complete.
    """
    client = AsyncElasticsearch(hosts=[ES_URL])

    # Verify connection
    try:
        info = await client.info()
        print(f"\nConnected to Elasticsearch {info['version']['number']}")
    except Exception as e:
        pytest.skip(f"Elasticsearch not available at {ES_URL}: {e}")

    yield client

    await client.close()


@pytest.fixture
async def search_client():
    """
    Function-scoped SearchClient fixture.

    Provides a fresh SearchClient instance for each test.
    Automatically closes the client after the test completes.
    """
    client = SearchClient(es_url=ES_URL)

    yield client

    await client.close()


@pytest.fixture(scope="session")
async def postgres_pool():
    """
    Session-scoped PostgreSQL connection pool fixture.

    Provides an asyncpg connection pool for integration tests.
    Automatically closes the pool after all tests complete.
    """
    pool = None
    try:
        pool = await asyncpg.create_pool(POSTGRES_URL, min_size=1, max_size=5)
        print(f"\nConnected to PostgreSQL at {POSTGRES_URL}")
    except Exception as e:
        pytest.skip(f"PostgreSQL not available at {POSTGRES_URL}: {e}")

    yield pool

    if pool is not None:
        await pool.close()


@pytest.fixture
async def postgres_conn(postgres_pool):
    """
    Function-scoped PostgreSQL connection fixture.

    Provides a fresh connection from the pool for each test.
    Automatically releases the connection back to the pool after the test.
    """
    async with postgres_pool.acquire() as conn, conn.transaction():
        # Start a transaction that will be rolled back after the test
        yield conn
        # Transaction automatically rolls back when exiting context


@pytest.fixture(scope="session")
async def redis_client():
    """
    Session-scoped Redis client fixture.

    Provides a Redis client for integration tests.
    Automatically closes the connection after all tests complete.
    """
    if redis is None:
        pytest.skip("redis.asyncio not available")

    client = None
    try:
        client = await redis.from_url(REDIS_URL)
        await client.ping()
        print(f"\nConnected to Redis at {REDIS_URL}")
    except Exception as e:
        pytest.skip(f"Redis not available at {REDIS_URL}: {e}")

    yield client

    if client is not None:
        await client.close()
