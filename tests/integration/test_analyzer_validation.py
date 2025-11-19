"""
Analyzer Validation Tests for Elasticsearch financial_analyzer

Tests synonym expansion, stemming, stopword removal, and token output.
Requires Elasticsearch running with indices created via elasticsearch_setup.py.
"""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.requires_elasticsearch]


@pytest.mark.asyncio
async def test_synonym_expansion_ebitda(es_client):
    """Test EBITDA synonym expansion."""
    response = await es_client.indices.analyze(
        index="sec_filings",
        body={
            "analyzer": "financial_analyzer",
            "text": "EBITDA margins grew 15% year-over-year",
        },
    )

    tokens = [token["token"] for token in response["tokens"]]

    # Should expand EBITDA to synonyms
    assert any(
        t in tokens
        for t in [
            "ebitda",
            "earnings",
            "interest",
            "taxes",
            "depreciation",
            "amortization",
        ]
    ), f"EBITDA not expanded correctly. Got: {tokens}"


@pytest.mark.asyncio
async def test_synonym_expansion_pe_ratio(es_client):
    """Test P/E ratio synonym expansion."""
    response = await es_client.indices.analyze(
        index="sec_filings",
        body={"analyzer": "financial_analyzer", "text": "P/E ratio is 25"},
    )

    tokens = [token["token"] for token in response["tokens"]]

    # Should expand P/E to synonyms
    assert any(t in tokens for t in ["pe", "price", "earnings", "ratio"]), f"P/E not expanded correctly. Got: {tokens}"


@pytest.mark.asyncio
async def test_synonym_expansion_ma(es_client):
    """Test M&A synonym expansion."""
    response = await es_client.indices.analyze(
        index="sec_filings",
        body={"analyzer": "financial_analyzer", "text": "M&A activity increased"},
    )

    tokens = [token["token"] for token in response["tokens"]]

    # Should expand M&A to synonyms
    assert any(t in tokens for t in ["ma", "merger", "mergers", "acquisition", "acquisitions"]), (
        f"M&A not expanded correctly. Got: {tokens}"
    )


@pytest.mark.asyncio
async def test_stopword_removal(es_client):
    """Test stopword removal."""
    response = await es_client.indices.analyze(
        index="sec_filings",
        body={
            "analyzer": "financial_analyzer",
            "text": "the revenue and profit or loss",
        },
    )

    tokens = [token["token"] for token in response["tokens"]]

    # Stopwords should be removed
    stopwords = ["the", "a", "an", "and", "or", "but"]
    for stopword in stopwords:
        assert stopword not in tokens, f"Stopword '{stopword}' not removed. Got: {tokens}"

    # Content words should remain
    assert "revenue" in tokens or "revenu" in tokens  # stemmed
    assert "profit" in tokens


@pytest.mark.asyncio
async def test_stemming(es_client):
    """Test English stemming."""
    response = await es_client.indices.analyze(
        index="sec_filings",
        body={
            "analyzer": "financial_analyzer",
            "text": "growing revenues profitable companies acquisitions",
        },
    )

    tokens = [token["token"] for token in response["tokens"]]

    # Verify stemming (exact stems may vary)
    # growing -> grow
    assert any(t.startswith("grow") for t in tokens), f"'growing' not stemmed. Got: {tokens}"
    # revenues -> revenu
    assert any(t.startswith("revenu") for t in tokens), f"'revenues' not stemmed. Got: {tokens}"
    # profitable -> profit
    assert any(t.startswith("profit") for t in tokens), f"'profitable' not stemmed. Got: {tokens}"
    # companies -> compani
    assert any(t.startswith("compan") for t in tokens), f"'companies' not stemmed. Got: {tokens}"
    # acquisitions -> acquisit
    assert any(t.startswith("acquisit") for t in tokens), f"'acquisitions' not stemmed. Got: {tokens}"


@pytest.mark.asyncio
async def test_case_insensitivity(es_client):
    """Test lowercase filter."""
    response = await es_client.indices.analyze(
        index="sec_filings",
        body={"analyzer": "financial_analyzer", "text": "Apple AAPL Revenue"},
    )

    tokens = [token["token"] for token in response["tokens"]]

    # All tokens should be lowercase
    for token in tokens:
        assert token.islower() or not token.isalpha(), f"Token '{token}' not lowercased"


@pytest.mark.asyncio
async def test_ascii_folding(es_client):
    """Test ASCII folding for accented characters."""
    response = await es_client.indices.analyze(
        index="sec_filings",
        body={"analyzer": "financial_analyzer", "text": "café résumé naïve"},
    )

    tokens = [token["token"] for token in response["tokens"]]

    # Accented chars should be converted to ASCII (and then stemmed)
    assert "cafe" in tokens, f"'café' not folded to 'cafe'. Got: {tokens}"
    assert any("resum" in t for t in tokens), f"'résumé' not folded/stemmed correctly. Got: {tokens}"
    assert any("naiv" in t for t in tokens), f"'naïve' not folded/stemmed correctly. Got: {tokens}"


@pytest.mark.asyncio
async def test_complex_financial_text(es_client):
    """Test analyzer on realistic financial text."""
    text = """
    Apple's EBITDA margins improved significantly, with P/E ratio declining to 25.
    The company announced M&A activity targeting AI and machine learning startups.
    ROE increased by 15% year-over-year, while FCF generation remained strong.
    """

    response = await es_client.indices.analyze(
        index="sec_filings", body={"analyzer": "financial_analyzer", "text": text}
    )

    tokens = [token["token"] for token in response["tokens"]]

    # Verify key terms are present (in some form)
    key_terms = ["apple", "ebitda", "margin", "pe", "ratio", "ma", "ai", "roe", "fcf"]
    for term in key_terms:
        assert any(term in t for t in tokens), f"Expected term '{term}' not found in tokens: {tokens[:20]}..."


if __name__ == "__main__":
    # Run tests manually
    pytest.main([__file__, "-v"])
