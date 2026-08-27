import json
from unittest.mock import Mock, patch

from aikb.domain import KnowledgeDocument
from aikb.enrichments.ollama import ENRICHMENT_SCHEMA, OllamaEnrichment


def document() -> KnowledgeDocument:
    return KnowledgeDocument(
        "doc-1",
        "exchange_notes",
        "SEARCHKEY",
        "Source title",
        "Original authoritative body.\nDo not rewrite this.",
        {"existing": "metadata"},
    )


def ollama_response(value: object) -> Mock:
    response = Mock()
    response.read.return_value = json.dumps({"response": json.dumps(value)}).encode()
    return response


@patch("aikb.enrichments.ollama.request.urlopen")
def test_complete_structured_enrichment_preserves_body(mock_urlopen: Mock) -> None:
    mock_urlopen.return_value = ollama_response(
        {
            "semantic_title": "  Quarterly Planning Decisions  ",
            "summary": "  Decisions from quarterly planning.  ",
            "tags": [" planning ", "decisions", "planning", ""],
            "domain": " operations ",
            "entities": [" Project Atlas ", "Team North", "Project Atlas"],
        }
    )
    original = document()

    enriched = OllamaEnrichment("http://127.0.0.1:11434", "local-model").enrich(
        original
    )

    assert enriched.title == "Quarterly Planning Decisions"
    assert enriched.content == original.content
    assert enriched.metadata == {
        "existing": "metadata",
        "enrichment.ollama.model": "local-model",
        "enrichment.summary": "Decisions from quarterly planning.",
        "enrichment.tags": ["decisions", "planning"],
        "enrichment.domain": "operations",
        "enrichment.entities": ["Project Atlas", "Team North"],
    }
    sent = json.loads(mock_urlopen.call_args.args[0].data.decode())
    assert sent["format"] == ENRICHMENT_SCHEMA
    assert set(sent["format"]["properties"]) == {
        "semantic_title",
        "summary",
        "tags",
        "domain",
        "entities",
    }


@patch("aikb.enrichments.ollama.request.urlopen")
def test_invalid_fields_are_conservatively_defaulted(mock_urlopen: Mock) -> None:
    mock_urlopen.return_value = ollama_response(
        {
            "semantic_title": "   ",
            "summary": {"not": "a string"},
            "tags": ["valid", 42, None, " valid "],
            "domain": 7,
            "entities": "not a list",
        }
    )
    original = document()

    enriched = OllamaEnrichment("http://127.0.0.1:11434", "local-model").enrich(
        original
    )

    assert enriched.title == original.title
    assert enriched.content == original.content
    assert enriched.metadata["enrichment.summary"] == ""
    assert enriched.metadata["enrichment.tags"] == ["valid"]
    assert enriched.metadata["enrichment.domain"] == ""
    assert enriched.metadata["enrichment.entities"] == []


@patch("aikb.enrichments.ollama.request.urlopen")
def test_optional_invalid_response_returns_original_document(
    mock_urlopen: Mock,
) -> None:
    mock_urlopen.return_value = ollama_response(["not", "an", "object"])
    original = document()

    enriched = OllamaEnrichment(
        "http://127.0.0.1:11434", "local-model", optional=True
    ).enrich(original)

    assert enriched is original
