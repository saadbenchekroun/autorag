"""Tests for DocumentAnalysisEngine."""

from pathlib import Path

import pytest

from src.core.schemas import DocumentMetrics, IngestedDocument
from src.services.analysis import DocumentAnalysisEngine
from src.services.ingestion import DocumentIngestionService

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def engine():
    return DocumentAnalysisEngine()


def _make_doc(text: str, filename: str = "test.txt") -> IngestedDocument:
    """Helper to create an IngestedDocument with given text."""
    return IngestedDocument(
        source=f"/tmp/{filename}",
        filename=filename,
        type="text/plain",
        size_bytes=len(text.encode()),
        raw_text=text,
        metadata={"extension": ".txt"},
    )


class TestAnalyzeDocument:
    def test_returns_document_metrics(self, engine):
        doc = _make_doc("Hello world. This is a test document with some words.")
        result = engine.analyze_document(doc)
        assert isinstance(result, DocumentMetrics)

    def test_token_estimation_positive(self, engine):
        doc = _make_doc("The quick brown fox jumps over the lazy dog." * 10)
        result = engine.analyze_document(doc)
        assert result.estimated_tokens > 0

    def test_filename_preserved(self, engine):
        doc = _make_doc("some text", filename="myfile.txt")
        result = engine.analyze_document(doc)
        assert result.filename == "myfile.txt"

    def test_code_detection_positive(self, engine):
        code_text = "def my_function(x):\n    return x * 2\n\nresult = my_function(3)"
        doc = _make_doc(code_text)
        result = engine.analyze_document(doc)
        assert result.has_code_blocks is True

    def test_code_detection_negative_for_prose(self, engine):
        prose = (
            "The history of computing spans many decades. "
            "Pioneers like Turing laid the theoretical groundwork. "
            "Modern systems are vastly more powerful than early machines."
        )
        doc = _make_doc(prose)
        result = engine.analyze_document(doc)
        assert result.has_code_blocks is False

    def test_semantic_density_label_range(self, engine):
        doc = _make_doc("word " * 100)  # very repetitive → low density
        result = engine.analyze_document(doc)
        assert result.semantic_density in ("low", "medium", "high")

    def test_repetitive_text_low_density(self, engine):
        doc = _make_doc("the the the the the the the the the the the the")
        result = engine.analyze_document(doc)
        assert result.semantic_density == "low"

    def test_unique_words_high_density(self, engine):
        words = " ".join(f"uniqueword{i}" for i in range(200))
        doc = _make_doc(words)
        result = engine.analyze_document(doc)
        assert result.semantic_density == "high"

    def test_raw_length_matches_text(self, engine):
        text = "Hello world"
        doc = _make_doc(text)
        result = engine.analyze_document(doc)
        assert result.raw_length_chars == len(text)

    def test_analyse_from_fixture_txt(self, engine):
        """Integration check using a real fixture file."""
        ingestion = DocumentIngestionService()
        doc = ingestion.ingest_file(str(FIXTURES / "sample.txt"))
        result = engine.analyze_document(doc)
        assert result.estimated_tokens > 10
        assert result.has_code_blocks is True  # fixture contains def/return
