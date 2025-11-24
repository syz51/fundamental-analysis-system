"""Pytest configuration and fixtures for integration tests using testcontainers."""

import asyncio
import os
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from types import ModuleType

import asyncpg
import pytest
from alembic import command
from alembic.config import Config
from elasticsearch import AsyncElasticsearch
from filelock import FileLock
from testcontainers.elasticsearch import ElasticSearchContainer
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from storage.elasticsearch_setup import initialize_indices
from storage.search_tool import SearchClient

# Configure Docker socket for macOS Docker Desktop if needed
if not os.environ.get("DOCKER_HOST"):
    macos_socket = Path.home() / ".docker" / "run" / "docker.sock"
    if macos_socket.exists():
        os.environ["DOCKER_HOST"] = f"unix://{macos_socket}"

redis: ModuleType | None
try:
    import redis.asyncio as redis
except ImportError:
    redis = None


# Global session-scoped containers shared across ALL workers
# Uses file locks to ensure only one worker starts containers
# All workers share the same container set and run tests in parallel
@pytest.fixture(scope="session")
def postgres_url(tmp_path_factory: pytest.TempPathFactory) -> Generator[str]:
    """
    Provide PostgreSQL connection URL from shared container.

    First worker starts container, writes URL to file.
    Other workers read URL from file and reuse container.
    """
    # Use truly global temp directory shared across ALL workers
    root_tmp_dir = Path(tmp_path_factory.getbasetemp()).parent.parent
    lock_file = root_tmp_dir / "postgres.lock"
    url_file = root_tmp_dir / "postgres_url.txt"

    container = None
    with FileLock(str(lock_file)):
        if url_file.exists():
            # Reuse existing container
            connection_url = url_file.read_text().strip()
            print(f"\n[POSTGRES] Worker reusing existing container: {connection_url}")
        else:
            # First worker - start container
            print("\n[POSTGRES] First worker starting new container...")
            container = PostgresContainer(
                image="postgres:18.1",
                username="postgres",
                password="postgres",  # noqa: S106
                dbname="fundamental_analysis_test",
            )
            container.start()
            connection_url = container.get_connection_url()
            url_file.write_text(connection_url)
            print(f"\n[POSTGRES] Container started: {connection_url}")

    yield connection_url

    # Only worker that started container stops it
    if container:
        container.stop()
        with FileLock(str(lock_file)):
            if url_file.exists():
                url_file.unlink()


@pytest.fixture(scope="session")
def elasticsearch_url(tmp_path_factory: pytest.TempPathFactory) -> Generator[str]:
    """
    Provide Elasticsearch URL from shared container.

    First worker starts container, writes URL to file.
    Other workers read URL from file and reuse container.
    """
    # Use truly global temp directory shared across ALL workers
    root_tmp_dir = Path(tmp_path_factory.getbasetemp()).parent.parent
    lock_file = root_tmp_dir / "elasticsearch.lock"
    url_file = root_tmp_dir / "elasticsearch_url.txt"

    container = None
    with FileLock(str(lock_file)):
        if url_file.exists():
            # Reuse existing container
            es_url = url_file.read_text().strip()
            print(f"\n[ELASTICSEARCH] Worker reusing existing container: {es_url}")
        else:
            # First worker - start container
            print("\n[ELASTICSEARCH] First worker starting new container...")
            container = (
                ElasticSearchContainer(
                    image="docker.elastic.co/elasticsearch/elasticsearch:8.14.0",
                )
                .with_env("xpack.security.enabled", "false")
                .with_env("ES_JAVA_OPTS", "-Xms512m -Xmx512m")
            )
            container.start()
            es_url = container.get_url()
            url_file.write_text(es_url)
            print(f"\n[ELASTICSEARCH] Container started: {es_url}")

    yield es_url

    # Only worker that started container stops it
    if container:
        container.stop()
        with FileLock(str(lock_file)):
            if url_file.exists():
                url_file.unlink()


@pytest.fixture(scope="session")
def redis_url(tmp_path_factory: pytest.TempPathFactory) -> Generator[str]:
    """
    Provide Redis URL from shared container.

    First worker starts container, writes URL to file.
    Other workers read URL from file and reuse container.
    """
    # Use truly global temp directory shared across ALL workers
    root_tmp_dir = Path(tmp_path_factory.getbasetemp()).parent.parent
    lock_file = root_tmp_dir / "redis.lock"
    url_file = root_tmp_dir / "redis_url.txt"

    container = None
    with FileLock(str(lock_file)):
        if url_file.exists():
            # Reuse existing container
            redis_connection_url = url_file.read_text().strip()
        else:
            # First worker - start container
            container = RedisContainer(image="redis:7")
            container.start()
            # Build Redis URL from container
            host = container.get_container_host_ip()
            port = container.get_exposed_port(6379)
            redis_connection_url = f"redis://{host}:{port}/0"
            url_file.write_text(redis_connection_url)

    yield redis_connection_url

    # Only worker that started container stops it
    if container:
        container.stop()
        with FileLock(str(lock_file)):
            if url_file.exists():
                url_file.unlink()


@pytest.fixture(scope="session")
def run_migrations(postgres_url: str) -> None:
    """
    Run database migrations once before all integration tests.

    Uses the shared Postgres URL from testcontainer.
    """
    # Convert to async URL for Alembic
    alembic_url = postgres_url.replace("postgresql://", "postgresql+asyncpg://").replace(
        "postgresql+psycopg2://", "postgresql+asyncpg://"
    )

    # Configure Alembic for test database
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", alembic_url)

    # Run migrations to latest version
    try:
        command.upgrade(alembic_cfg, "head")
        print(f"\nRan database migrations for {alembic_url}")
    except Exception as e:
        pytest.fail(f"Failed to run database migrations: {e}")


@pytest.fixture(scope="session")
def initialize_es_indices(tmp_path_factory: pytest.TempPathFactory, elasticsearch_url: str) -> None:
    """
    Initialize Elasticsearch indices once before all integration tests.

    Creates sec_filings, transcripts, and news indices with proper mappings.
    Uses file lock to prevent parallel workers from racing to create indices.
    """
    # Use file lock to ensure only one worker initializes indices
    root_tmp_dir = Path(tmp_path_factory.getbasetemp()).parent.parent
    lock_file = root_tmp_dir / "es_indices.lock"

    with FileLock(str(lock_file)):
        try:
            asyncio.run(initialize_indices(elasticsearch_url))
            print(f"\nInitialized Elasticsearch indices at {elasticsearch_url}")
        except Exception as e:
            pytest.fail(f"Failed to initialize Elasticsearch indices: {e}")


@pytest.fixture
async def es_client(initialize_es_indices: None, elasticsearch_url: str) -> AsyncGenerator[AsyncElasticsearch]:  # noqa: ARG001 - fixture dependency
    """
    Provide Elasticsearch client for individual tests.

    Automatically closes connection after test completes.
    """
    client = AsyncElasticsearch(hosts=[elasticsearch_url])

    # Verify connection
    try:
        info = await client.info()
        print(f"\nConnected to Elasticsearch {info['version']['number']}")
    except Exception as e:
        pytest.fail(f"Elasticsearch not available at {elasticsearch_url}: {e}")

    yield client

    await client.close()


@pytest.fixture
async def search_client(initialize_es_indices: None, elasticsearch_url: str) -> AsyncGenerator[SearchClient]:  # noqa: ARG001 - fixture dependency
    """
    Provide SearchClient for individual tests.

    Automatically closes client after test completes.
    """
    client = SearchClient(es_url=elasticsearch_url)

    yield client

    await client.close()


@pytest.fixture
async def postgres_pool(run_migrations: None, postgres_url: str) -> AsyncGenerator[asyncpg.Pool]:  # noqa: ARG001 - fixture dependency
    """
    Provide PostgreSQL connection pool for individual tests.

    Automatically closes pool after test completes.
    """
    # Parse URL to get connection params
    # Format: postgresql://postgres:postgres@hostname:port/dbname
    asyncpg_url = postgres_url.replace("postgresql://", "").replace("postgresql+psycopg2://", "")
    user_pass, host_port_db = asyncpg_url.split("@")
    user, password = user_pass.split(":")
    host_port, database = host_port_db.split("/")
    host, port = host_port.split(":")

    try:
        pool = await asyncpg.create_pool(
            user=user, password=password, host=host, port=int(port), database=database, min_size=1, max_size=5
        )
        print(f"\nConnected to PostgreSQL at {postgres_url}")
    except Exception as e:
        pytest.fail(f"PostgreSQL not available: {e}")

    yield pool

    await pool.close()


@pytest.fixture
async def postgres_conn(postgres_pool: asyncpg.Pool) -> AsyncGenerator[asyncpg.Connection]:
    """
    Provide PostgreSQL connection for individual tests.

    Wraps connection in transaction that rolls back after test,
    ensuring test isolation without affecting other tests.
    """
    async with postgres_pool.acquire() as conn, conn.transaction():
        yield conn
        # Transaction automatically rolls back when exiting context


@pytest.fixture
async def redis_client(redis_url: str) -> AsyncGenerator[object]:
    """
    Provide Redis client for individual tests.

    Automatically closes connection after test completes.
    """
    if redis is None:
        pytest.skip("redis.asyncio not available")

    client = None
    try:
        client = await redis.from_url(redis_url)
        await client.ping()
        print(f"\nConnected to Redis at {redis_url}")
    except Exception as e:
        pytest.fail(f"Redis not available at {redis_url}: {e}")

    yield client

    if client is not None:
        await client.close()
