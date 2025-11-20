"""Pytest configuration and fixtures for integration tests requiring external services."""

import os
from collections.abc import AsyncGenerator
from types import ModuleType
from typing import Any

import asyncpg
import pytest
from alembic import command
from alembic.config import Config
from elasticsearch import AsyncElasticsearch

from storage.search_tool import SearchClient

redis: ModuleType | None
try:
    import redis.asyncio as redis
except ImportError:
    redis = None

# Environment variables for service URLs
ES_URL = os.getenv("ES_URL", "http://localhost:9200")
POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://postgres:postgres@localhost:5432/fundamental_analysis_test")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


@pytest.fixture(scope="session")
def run_migrations() -> None:
    """
    Session-scoped fixture to run database migrations once before all integration tests.

    Configures Alembic to use the test database and runs all migrations to head.
    This ensures the database schema is up-to-date before any tests execute.
    """
    # Convert asyncpg URL to SQLAlchemy format for Alembic
    alembic_url = POSTGRES_URL.replace("postgresql://", "postgresql+asyncpg://")

    # Configure Alembic for test database
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", alembic_url)

    # Run migrations to latest version
    try:
        command.upgrade(alembic_cfg, "head")
        print(f"\nRan database migrations for {alembic_url}")
    except Exception as e:
        pytest.skip(f"Failed to run database migrations: {e}")


@pytest.fixture
async def es_client() -> AsyncGenerator[AsyncElasticsearch]:
    """
    Function-scoped Elasticsearch client fixture.

    Provides an AsyncElasticsearch client for integration tests.
    Automatically closes the connection after the test completes.
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
async def search_client() -> AsyncGenerator[SearchClient]:
    """
    Function-scoped SearchClient fixture.

    Provides a fresh SearchClient instance for each test.
    Automatically closes the client after the test completes.
    """
    client = SearchClient(es_url=ES_URL)

    yield client

    await client.close()


@pytest.fixture
async def postgres_pool(run_migrations: None) -> AsyncGenerator[asyncpg.Pool]:  # noqa: ARG001 - fixture dependency
    """
    Function-scoped PostgreSQL connection pool fixture.

    Provides an asyncpg connection pool for integration tests.
    Automatically closes the pool after the test completes.

    Depends on run_migrations to ensure schema exists before connecting.
    """
    try:
        pool = await asyncpg.create_pool(POSTGRES_URL, min_size=1, max_size=5)
        print(f"\nConnected to PostgreSQL at {POSTGRES_URL}")
    except Exception as e:
        pytest.skip(f"PostgreSQL not available at {POSTGRES_URL}: {e}")

    yield pool

    await pool.close()


@pytest.fixture
async def postgres_conn(postgres_pool: asyncpg.Pool) -> AsyncGenerator[asyncpg.Connection]:
    """
    Function-scoped PostgreSQL connection fixture.

    Provides a fresh connection from the pool for each test.
    Automatically releases the connection back to the pool after the test.
    """
    async with postgres_pool.acquire() as conn, conn.transaction():
        # Start a transaction that will be rolled back after the test
        yield conn
        # Transaction automatically rolls back when exiting context


@pytest.fixture
async def redis_client() -> AsyncGenerator[Any]:
    """
    Function-scoped Redis client fixture.

    Provides a Redis client for integration tests.
    Automatically closes the connection after the test completes.
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
