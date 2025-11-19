import asyncio
import logging
from typing import Any

from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import (
    ApiError,
    ConnectionTimeout,
    TransportError,
)
from elasticsearch.exceptions import (
    ConnectionError as ESConnectionError,
)

# Logger configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Settings & Analyzer Configuration (DD-029 Section 4 & 5) ---
INDEX_SETTINGS = {
    "number_of_shards": 3,
    "number_of_replicas": 2,
    "refresh_interval": "30s",
    "max_result_window": 10000,
    "index.merge.policy.max_merged_segment": "5gb",
    "index.merge.policy.segments_per_tier": 10,
    "index.translog.durability": "async",
    "index.translog.sync_interval": "5s",
    "analysis": {
        "analyzer": {
            "financial_analyzer": {
                "type": "custom",
                "tokenizer": "standard",
                "filter": [
                    "lowercase",
                    "asciifolding",
                    "financial_stop",
                    "financial_synonyms",
                    "english_stemmer",
                ],
            }
        },
        "filter": {
            "financial_stop": {
                "type": "stop",
                "stopwords": ["the", "a", "an", "and", "or", "but"],
            },
            "financial_synonyms": {
                "type": "synonym_graph",
                "synonyms": [
                    (
                        "EBITDA, Earnings Before Interest Taxes Depreciation Amortization, "
                        "earnings before interest taxes depreciation amortization"
                    ),
                    "P/E, PE, price to earnings, price earnings ratio, PE ratio",
                    "M&A, mergers and acquisitions, merger, acquisition, MA",
                    "ROE, return on equity, equity return",
                    "ROA, return on assets, asset return",
                    "ROIC, return on invested capital, invested capital return",
                    "FCF, free cash flow, cash flow",
                    "CAGR, compound annual growth rate, growth rate",
                    "AI, artificial intelligence",
                    "EPS, earnings per share",
                    "EV, enterprise value",
                    "P/B, price to book, book value ratio",
                    "D/E, debt to equity, debt equity ratio",
                    "CAPEX, capital expenditure, capital spending",
                    "OPEX, operating expenditure, operating expense",
                    "SG&A, selling general and administrative, SGA",
                    "R&D, research and development, RD",
                    "YoY, year over year, year-over-year",
                    "QoQ, quarter over quarter, quarter-over-quarter",
                    "TTM, trailing twelve months, last twelve months, LTM",
                ],
            },
            "english_stemmer": {"type": "stemmer", "language": "english"},
        },
    },
}


# --- Core Schema (DD-029 Section 1) ---
def get_core_properties() -> dict[str, Any]:
    return {
        # === Identity ===
        "doc_id": {"type": "keyword", "doc_values": True},
        "doc_type": {"type": "keyword", "doc_values": True},
        "source": {"type": "keyword", "doc_values": True},
        # === Company Linking ===
        "ticker": {"type": "keyword", "doc_values": True},
        "company_name": {
            "type": "text",
            "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
        },
        "cik": {"type": "keyword", "doc_values": True},
        # === Temporal ===
        "date": {"type": "date", "format": "strict_date_optional_time||epoch_millis"},
        "fiscal_year": {"type": "integer"},
        "fiscal_quarter": {"type": "keyword"},
        # === Classification ===
        "sector": {"type": "keyword", "doc_values": True},
        "industry": {"type": "keyword", "doc_values": True},
        # === Search Fields (REQUIRED for hybrid search) ===
        "text": {"type": "text", "analyzer": "financial_analyzer"},
        "embedding": {
            "type": "dense_vector",
            "dims": 1536,
            "index": True,
            "similarity": "cosine",
            "index_options": {"type": "hnsw", "m": 16, "ef_construction": 100},
        },
        # === Metadata ===
        "indexed_at": {"type": "date"},
        "updated_at": {"type": "date"},
    }


# --- Domain Extensions (DD-029 Section 2) ---


def get_sec_filings_mapping() -> dict[str, Any]:
    mapping: dict[str, Any] = {"properties": get_core_properties()}
    # Extensions
    mapping["properties"].update(
        {
            "filing_type": {"type": "keyword", "doc_values": True},
            "accession_number": {"type": "keyword", "doc_values": True},
            "section": {"type": "keyword", "doc_values": True},
            "url": {"type": "keyword", "index": False},
            "file_size": {"type": "long"},
            "revenue": {"type": "long"},
            "net_income": {"type": "long"},
            "market_cap": {"type": "long"},
        }
    )
    return mapping


def get_transcripts_mapping() -> dict[str, Any]:
    mapping: dict[str, Any] = {"properties": get_core_properties()}
    # Extensions
    mapping["properties"].update(
        {
            "call_type": {"type": "keyword", "doc_values": True},
            "speaker": {"type": "keyword", "doc_values": True},
            "speaker_role": {"type": "keyword", "doc_values": True},
            "segment": {"type": "keyword", "doc_values": True},
            "duration_seconds": {"type": "integer"},
            "sentiment_score": {"type": "float"},
        }
    )
    return mapping


def get_news_mapping() -> dict[str, Any]:
    mapping: dict[str, Any] = {"properties": get_core_properties()}
    # Extensions
    mapping["properties"].update(
        {
            "headline": {"type": "text", "analyzer": "financial_analyzer"},
            "author": {"type": "keyword", "doc_values": True},
            "publication": {"type": "keyword", "doc_values": True},
            "url": {"type": "keyword", "index": False},
            "word_count": {"type": "integer"},
            "event_type": {"type": "keyword", "doc_values": True},
            "mentioned_tickers": {"type": "keyword", "doc_values": True},
        }
    )
    return mapping


# --- Initialization Logic ---


async def initialize_indices(es_url: str = "http://localhost:9200", max_retries: int = 3) -> None:
    """
    Initializes Elasticsearch indices with standardized mappings.

    Args:
        es_url: Elasticsearch connection URL
        max_retries: Maximum retry attempts for connection failures
    """
    client = AsyncElasticsearch(hosts=[es_url])

    indices_config = {
        "sec_filings": get_sec_filings_mapping(),
        "transcripts": get_transcripts_mapping(),
        "news": get_news_mapping(),
    }

    # Retry logic for initial connection
    connected = False
    for attempt in range(max_retries):
        try:
            if await client.ping():
                connected = True
                logger.info(f"Connected to Elasticsearch at {es_url}")
                break
        except (ESConnectionError, ConnectionTimeout) as e:
            if attempt < max_retries - 1:
                delay = 2**attempt  # Exponential backoff: 1s, 2s, 4s
                logger.warning(f"Connection failed (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {delay}s...")
                await asyncio.sleep(delay)
            else:
                logger.error(f"Could not connect to Elasticsearch at {es_url} after {max_retries} attempts")

    if not connected:
        await client.close()
        return

    # Create indices with individual error handling
    for index_name, mapping in indices_config.items():
        try:
            exists = await client.indices.exists(index=index_name)

            if not exists:
                logger.info(f"Creating index: {index_name}")
                await client.indices.create(index=index_name, settings=INDEX_SETTINGS, mappings=mapping)
                logger.info(f"Successfully created index: {index_name}")
            else:
                logger.info(f"Index {index_name} already exists. Skipping.")
                # In production, consider validating mapping compatibility

        except ApiError as e:
            logger.error(f"API error creating index {index_name}: {e.status_code} - {e.message}")
            # Continue with other indices even if one fails
        except (ESConnectionError, ConnectionTimeout, TransportError) as e:
            logger.error(f"Connection error creating index {index_name}: {type(e).__name__}: {e}")
            # Continue with other indices
        except Exception as e:
            logger.error(f"Unexpected error creating index {index_name}: {type(e).__name__}: {e}")
            # Continue with other indices

    await client.close()
    logger.info("Index initialization completed")


if __name__ == "__main__":
    # Entry point for manual execution
    asyncio.run(initialize_indices())
