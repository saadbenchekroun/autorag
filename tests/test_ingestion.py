"""Tests for DocumentIngestionService."""

import os
from pathlib import Path

import pytest

from src.core.exceptions import IngestionError, UnsupportedFileTypeError
from src.core.schemas import IngestedDocument
from src.services.ingestion import DocumentIngestionService

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def service():
    return DocumentIngestionService()


class TestIngestTxtFile:
    def test_returns_ingested_document(self, service):
        result = service.ingest_file(str(FIXTURES / "sample.txt"))
        assert isinstance(result, IngestedDocument)

    def test_raw_text_not_empty(self, service):
        result = service.ingest_file(str(FIXTURES / "sample.txt"))
        assert len(result.raw_text) > 0

    def test_filename_is_basename(self, service):
        result = service.ingest_file(str(FIXTURES / "sample.txt"))
        assert result.filename == "sample.txt"

    def test_size_bytes_correct(self, service):
        path = str(FIXTURES / "sample.txt")
        result = service.ingest_file(path)
        assert result.size_bytes == os.path.getsize(path)


class TestIngestMarkdownFile:
    def test_html_stripped_from_markdown(self, service):
        result = service.ingest_file(str(FIXTURES / "sample.md"))
        # BeautifulSoup should strip markdown-generated HTML tags
        assert "<h1>" not in result.raw_text
        assert "<p>" not in result.raw_text

    def test_content_preserved(self, service):
        result = service.ingest_file(str(FIXTURES / "sample.md"))
        assert "AutoRAG" in result.raw_text


class TestIngestJsonFile:
    def test_json_text_extracted(self, service):
        result = service.ingest_file(str(FIXTURES / "sample.json"))
        assert "RAG" in result.raw_text or "Vector" in result.raw_text


class TestIngestionErrors:
    def test_file_not_found_raises(self, service):
        with pytest.raises(FileNotFoundError):
            service.ingest_file("/nonexistent/path/file.txt")

    def test_unsupported_extension_raises(self, service, tmp_path):
        bad_file = tmp_path / "test.xyz"
        bad_file.write_text("content")
        with pytest.raises(UnsupportedFileTypeError):
            service.ingest_file(str(bad_file))

    def test_empty_file_raises_ingestion_error(self, service, tmp_path):
        empty = tmp_path / "empty.txt"
        empty.write_text("")
        with pytest.raises(IngestionError):
            service.ingest_file(str(empty))

    def test_oversized_file_raises(self, service, tmp_path, monkeypatch):
        """Files exceeding MAX_FILE_SIZE_BYTES should raise IngestionError."""
        import src.services.ingestion as ing_module

        monkeypatch.setattr(ing_module, "MAX_FILE_SIZE_BYTES", 5)
        big_file = tmp_path / "big.txt"
        big_file.write_text("A" * 100)
        with pytest.raises(IngestionError):
            service.ingest_file(str(big_file))
