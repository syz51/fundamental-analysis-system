"""Unit tests for Elasticsearch index setup and mappings."""

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from elasticsearch.exceptions import (
    ApiError,
    TransportError,
)
from elasticsearch.exceptions import (
    ConnectionError as ESConnectionError,
)

from storage.elasticsearch_setup import (
    get_core_properties,
    get_index_settings,
    get_news_mapping,
    get_sec_filings_mapping,
    get_transcripts_mapping,
    initialize_indices,
)

# Test constants
EMBEDDING_DIMS = 1536
NUM_SHARDS = 3
NUM_REPLICAS_PROD = 2  # Production replica count
NUM_REPLICAS_TEST = 0  # Test/CI replica count
MAX_RESULT_WINDOW = 10000
NUM_INDICES = 3


class TestCoreProperties:
    """Tests for get_core_properties schema."""

    def test_get_core_properties_returns_dict(self) -> None:
        """Core properties should return dictionary."""
        props = get_core_properties()
        assert isinstance(props, dict)

    def test_get_core_properties_has_identity_fields(self) -> None:
        """Core schema includes doc_id, doc_type, source."""
        props = get_core_properties()
        assert "doc_id" in props
        assert props["doc_id"]["type"] == "keyword"
        assert "doc_type" in props
        assert props["doc_type"]["type"] == "keyword"
        assert "source" in props
        assert props["source"]["type"] == "keyword"

    def test_get_core_properties_has_company_linking(self) -> None:
        """Core schema includes ticker, company_name, cik."""
        props = get_core_properties()
        assert "ticker" in props
        assert props["ticker"]["type"] == "keyword"
        assert "company_name" in props
        assert props["company_name"]["type"] == "text"
        assert "cik" in props
        assert props["cik"]["type"] == "keyword"

    def test_get_core_properties_has_temporal_fields(self) -> None:
        """Core schema includes date, fiscal_year, fiscal_quarter."""
        props = get_core_properties()
        assert "date" in props
        assert props["date"]["type"] == "date"
        assert "fiscal_year" in props
        assert props["fiscal_year"]["type"] == "integer"
        assert "fiscal_quarter" in props
        assert props["fiscal_quarter"]["type"] == "keyword"

    def test_get_core_properties_has_classification(self) -> None:
        """Core schema includes sector, industry."""
        props = get_core_properties()
        assert "sector" in props
        assert props["sector"]["type"] == "keyword"
        assert "industry" in props
        assert props["industry"]["type"] == "keyword"

    def test_get_core_properties_has_search_fields(self) -> None:
        """Core schema includes text and embedding for hybrid search."""
        props = get_core_properties()
        assert "text" in props
        assert props["text"]["type"] == "text"
        assert props["text"]["analyzer"] == "financial_analyzer"
        assert "embedding" in props
        assert props["embedding"]["type"] == "dense_vector"
        assert props["embedding"]["dims"] == EMBEDDING_DIMS
        assert props["embedding"]["similarity"] == "cosine"

    def test_get_core_properties_has_metadata(self) -> None:
        """Core schema includes indexed_at, updated_at."""
        props = get_core_properties()
        assert "indexed_at" in props
        assert props["indexed_at"]["type"] == "date"
        assert "updated_at" in props
        assert props["updated_at"]["type"] == "date"


class TestDomainMappings:
    """Tests for domain-specific mapping functions."""

    def test_sec_filings_includes_core_properties(self) -> None:
        """SEC filings mapping includes all core properties."""
        mapping = get_sec_filings_mapping()
        core_props = get_core_properties()
        for key in core_props:
            assert key in mapping["properties"]

    def test_sec_filings_extensions(self) -> None:
        """SEC filings has filing_type, accession_number, section, etc."""
        mapping = get_sec_filings_mapping()
        props = mapping["properties"]
        assert "filing_type" in props
        assert props["filing_type"]["type"] == "keyword"
        assert "accession_number" in props
        assert "section" in props
        assert "url" in props
        assert props["url"]["index"] is False
        assert "file_size" in props
        assert props["file_size"]["type"] == "long"
        assert "revenue" in props
        assert "net_income" in props
        assert "market_cap" in props

    def test_transcripts_includes_core_properties(self) -> None:
        """Transcripts mapping includes all core properties."""
        mapping = get_transcripts_mapping()
        core_props = get_core_properties()
        for key in core_props:
            assert key in mapping["properties"]

    def test_transcripts_extensions(self) -> None:
        """Transcripts has call_type, speaker, segment, etc."""
        mapping = get_transcripts_mapping()
        props = mapping["properties"]
        assert "call_type" in props
        assert props["call_type"]["type"] == "keyword"
        assert "speaker" in props
        assert "speaker_role" in props
        assert "segment" in props
        assert "duration_seconds" in props
        assert props["duration_seconds"]["type"] == "integer"
        assert "sentiment_score" in props
        assert props["sentiment_score"]["type"] == "float"

    def test_news_includes_core_properties(self) -> None:
        """News mapping includes all core properties."""
        mapping = get_news_mapping()
        core_props = get_core_properties()
        for key in core_props:
            assert key in mapping["properties"]

    def test_news_extensions(self) -> None:
        """News has headline, author, publication, event_type, etc."""
        mapping = get_news_mapping()
        props = mapping["properties"]
        assert "headline" in props
        assert props["headline"]["type"] == "text"
        assert props["headline"]["analyzer"] == "financial_analyzer"
        assert "author" in props
        assert "publication" in props
        assert "url" in props
        assert props["url"]["index"] is False
        assert "word_count" in props
        assert props["word_count"]["type"] == "integer"
        assert "event_type" in props
        assert "mentioned_tickers" in props


class TestIndexSettings:
    """Tests for get_index_settings() configuration function."""

    def test_index_settings_structure_production(self) -> None:
        """Production settings have 2 replicas."""
        settings = get_index_settings(replica_count=NUM_REPLICAS_PROD)
        assert "number_of_shards" in settings
        assert settings["number_of_shards"] == NUM_SHARDS
        assert "number_of_replicas" in settings
        assert settings["number_of_replicas"] == NUM_REPLICAS_PROD
        assert "refresh_interval" in settings
        assert "max_result_window" in settings
        assert settings["max_result_window"] == MAX_RESULT_WINDOW

    def test_index_settings_structure_test(self) -> None:
        """Test settings have 0 replicas."""
        settings = get_index_settings(replica_count=NUM_REPLICAS_TEST)
        assert settings["number_of_replicas"] == NUM_REPLICAS_TEST

    def test_index_settings_auto_detect_test_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Auto-detects test environment and uses 0 replicas."""
        monkeypatch.setenv("PYTEST_CURRENT_TEST", "test_something")
        settings = get_index_settings()
        assert settings["number_of_replicas"] == NUM_REPLICAS_TEST

    def test_index_settings_auto_detect_ci_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Auto-detects CI environment and uses 0 replicas."""
        monkeypatch.setenv("CI", "true")
        settings = get_index_settings()
        assert settings["number_of_replicas"] == NUM_REPLICAS_TEST

    def test_index_settings_has_analysis(self) -> None:
        """Settings include analysis configuration."""
        settings = get_index_settings()
        assert "analysis" in settings
        analysis = cast(dict[str, Any], settings["analysis"])
        assert "analyzer" in analysis
        assert "filter" in analysis

    def test_financial_analyzer_configuration(self) -> None:
        """Financial analyzer uses correct tokenizer and filters."""
        settings = get_index_settings()
        analysis = cast(dict[str, Any], settings["analysis"])
        analyzers = cast(dict[str, Any], analysis["analyzer"])
        analyzer = cast(dict[str, Any], analyzers["financial_analyzer"])
        assert analyzer["type"] == "custom"
        assert analyzer["tokenizer"] == "standard"
        assert "lowercase" in analyzer["filter"]
        assert "asciifolding" in analyzer["filter"]
        assert "financial_stop" in analyzer["filter"]
        assert "financial_synonyms" in analyzer["filter"]
        assert "english_stemmer" in analyzer["filter"]

    def test_financial_synonyms_configuration(self) -> None:
        """Financial synonyms filter includes key financial terms."""
        settings = get_index_settings()
        analysis = cast(dict[str, Any], settings["analysis"])
        filters = cast(dict[str, Any], analysis["filter"])
        synonyms_filter = cast(dict[str, Any], filters["financial_synonyms"])
        assert synonyms_filter["type"] == "synonym"
        synonyms = synonyms_filter["synonyms"]
        # Check a few key synonyms
        ebitda_synonym = [s for s in synonyms if "EBITDA" in s]
        assert len(ebitda_synonym) > 0
        pe_synonym = [s for s in synonyms if "P/E" in s[0:10]]
        assert len(pe_synonym) > 0

    def test_stopwords_configuration(self) -> None:
        """Financial stop filter has appropriate stopwords."""
        settings = get_index_settings()
        analysis = cast(dict[str, Any], settings["analysis"])
        filters = cast(dict[str, Any], analysis["filter"])
        stop_filter = cast(dict[str, Any], filters["financial_stop"])
        assert stop_filter["type"] == "stop"
        assert "the" in stop_filter["stopwords"]
        assert "a" in stop_filter["stopwords"]


class TestInitializeIndices:
    """Tests for initialize_indices function with mocked Elasticsearch."""

    @pytest.mark.asyncio
    async def test_initialize_indices_success(self) -> None:
        """Initialize indices successfully creates all indices."""
        mock_es = AsyncMock()
        mock_es.ping.return_value = True
        mock_es.indices.exists.return_value = False
        mock_es.indices.create.return_value = {"acknowledged": True}

        with patch("storage.elasticsearch_setup.AsyncElasticsearch", return_value=mock_es):
            await initialize_indices("http://localhost:9200")

        # Verify connection attempt
        mock_es.ping.assert_called_once()

        # Verify all indices checked and created
        assert mock_es.indices.exists.call_count == NUM_INDICES
        assert mock_es.indices.create.call_count == NUM_INDICES

        # Verify indices created with correct names
        call_args = [call[1]["index"] for call in mock_es.indices.create.call_args_list]
        assert "sec_filings" in call_args
        assert "transcripts" in call_args
        assert "news" in call_args

        # Verify close called
        mock_es.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_indices_connection_retry(self) -> None:
        """Connection failure triggers exponential backoff retry."""
        mock_es = AsyncMock()
        mock_es.ping.side_effect = [
            ESConnectionError("Connection refused"),
            ESConnectionError("Connection refused"),
            True,  # Success on 3rd attempt
        ]
        mock_es.indices.exists.return_value = False
        mock_es.indices.create.return_value = {"acknowledged": True}

        with (
            patch("storage.elasticsearch_setup.AsyncElasticsearch", return_value=mock_es),
            patch("asyncio.sleep") as mock_sleep,
        ):
            await initialize_indices("http://localhost:9200", max_retries=3)

        # Verify connection attempts
        assert mock_es.ping.call_count == NUM_INDICES

        # Verify exponential backoff (2^0=1s, 2^1=2s)
        assert mock_sleep.call_count == NUM_REPLICAS_PROD
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(NUM_REPLICAS_PROD)

        # Verify indices created after successful connection
        assert mock_es.indices.create.call_count == NUM_INDICES

    @pytest.mark.asyncio
    async def test_initialize_indices_connection_failure(self) -> None:
        """Complete connection failure stops initialization."""
        mock_es = AsyncMock()
        mock_es.ping.side_effect = ESConnectionError("Connection refused")

        with (
            patch("storage.elasticsearch_setup.AsyncElasticsearch", return_value=mock_es),
            patch("asyncio.sleep"),
        ):
            await initialize_indices("http://localhost:9200", max_retries=3)

        # Verify max retries attempted
        assert mock_es.ping.call_count == NUM_INDICES

        # Verify no indices created
        mock_es.indices.exists.assert_not_called()
        mock_es.indices.create.assert_not_called()

        # Verify close called even on failure
        mock_es.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_indices_already_exists(self) -> None:
        """Existing indices are skipped."""
        mock_es = AsyncMock()
        mock_es.ping.return_value = True
        mock_es.indices.exists.return_value = True

        with patch("storage.elasticsearch_setup.AsyncElasticsearch", return_value=mock_es):
            await initialize_indices("http://localhost:9200")

        # Verify existence checked
        assert mock_es.indices.exists.call_count == NUM_INDICES

        # Verify no creation attempted
        mock_es.indices.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_initialize_indices_partial_failure(self) -> None:
        """Failure on one index continues with others."""
        mock_es = AsyncMock()
        mock_es.ping.return_value = True
        mock_es.indices.exists.return_value = False

        # Create mock meta for ApiError
        mock_meta = MagicMock()
        mock_meta.status = 400

        # First index succeeds, second fails, third succeeds
        mock_es.indices.create.side_effect = [
            {"acknowledged": True},
            ApiError("Invalid mapping", meta=mock_meta, body={}),
            {"acknowledged": True},
        ]

        with patch("storage.elasticsearch_setup.AsyncElasticsearch", return_value=mock_es):
            await initialize_indices("http://localhost:9200")

        # Verify all attempts made despite middle failure
        assert mock_es.indices.create.call_count == NUM_INDICES

    @pytest.mark.asyncio
    async def test_initialize_indices_api_error(self) -> None:
        """ApiError during creation is handled gracefully."""
        mock_es = AsyncMock()
        mock_es.ping.return_value = True
        mock_es.indices.exists.return_value = False

        # Create mock meta for ApiError
        mock_meta = MagicMock()
        mock_meta.status = 500

        mock_es.indices.create.side_effect = ApiError("Internal error", meta=mock_meta, body={})

        with patch("storage.elasticsearch_setup.AsyncElasticsearch", return_value=mock_es):
            await initialize_indices("http://localhost:9200")

        # Verify attempts made for all indices
        assert mock_es.indices.create.call_count == NUM_INDICES

        # Verify close called despite errors
        mock_es.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_indices_transport_error(self) -> None:
        """TransportError during creation is handled gracefully."""
        mock_es = AsyncMock()
        mock_es.ping.return_value = True
        mock_es.indices.exists.return_value = False
        mock_es.indices.create.side_effect = TransportError("Network error")

        with patch("storage.elasticsearch_setup.AsyncElasticsearch", return_value=mock_es):
            await initialize_indices("http://localhost:9200")

        # Verify attempts made for all indices
        assert mock_es.indices.create.call_count == NUM_INDICES

        # Verify close called despite errors
        mock_es.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_indices_unexpected_error(self) -> None:
        """Unexpected exceptions are caught and logged."""
        mock_es = AsyncMock()
        mock_es.ping.return_value = True
        mock_es.indices.exists.return_value = False
        mock_es.indices.create.side_effect = ValueError("Unexpected error")

        with patch("storage.elasticsearch_setup.AsyncElasticsearch", return_value=mock_es):
            await initialize_indices("http://localhost:9200")

        # Verify attempts made for all indices
        assert mock_es.indices.create.call_count == NUM_INDICES

        # Verify close called despite errors
        mock_es.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_indices_creates_with_correct_mappings(self) -> None:
        """Indices are created with correct settings and mappings."""
        mock_es = AsyncMock()
        mock_es.ping.return_value = True
        mock_es.indices.exists.return_value = False
        mock_es.indices.create.return_value = {"acknowledged": True}

        with patch("storage.elasticsearch_setup.AsyncElasticsearch", return_value=mock_es):
            await initialize_indices("http://localhost:9200", replica_count=NUM_REPLICAS_TEST)

        # Check first index call (sec_filings)
        first_call = mock_es.indices.create.call_args_list[0]
        assert first_call[1]["index"] == "sec_filings"
        # Verify settings structure (get_index_settings with 0 replicas)
        settings = first_call[1]["settings"]
        assert settings["number_of_replicas"] == NUM_REPLICAS_TEST
        assert settings["number_of_shards"] == NUM_SHARDS
        assert "properties" in first_call[1]["mappings"]
        assert "filing_type" in first_call[1]["mappings"]["properties"]
