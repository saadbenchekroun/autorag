"""Tests for IndexingPipelineService with mocked vector store."""

from unittest.mock import MagicMock, patch

import pytest

from src.core.schemas import ArchitectureDecision, IndexingResult, IngestedDocument
from src.pipeline.indexer import IndexingPipelineService


@pytest.fixture
def service():
    return IndexingPipelineService()


@pytest.fixture
def architecture():
    return ArchitectureDecision(
        vector_database="chroma",
        chunking_strategy="recursive_hierarchical",
        chunk_size=500,
        overlap_size=50,
        embedding_model="sentence_transformers_minilm",
        reasoning=["test reasoning"],
    )


@pytest.fixture
def sample_doc():
    return IngestedDocument(
        source="/tmp/test.txt",
        filename="test.txt",
        type="text/plain",
        size_bytes=100,
        raw_text=(
            "AutoRAG Architect is a framework that automatically designs RAG pipelines. "
            "It supports multiple vector databases, chunking strategies, and embedding models. "
            "The decision engine analyses documents to find the optimal configuration."
        ),
        metadata={"extension": ".txt"},
    )


class TestBuildSplitter:
    def test_fixed_size_returns_character_splitter(self, service):
        from langchain_text_splitters import CharacterTextSplitter

        splitter = service._build_splitter("fixed_size", 500, 50)
        assert isinstance(splitter, CharacterTextSplitter)

    def test_semantic_returns_recursive_splitter(self, service):
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        splitter = service._build_splitter("semantic", 500, 50)
        assert isinstance(splitter, RecursiveCharacterTextSplitter)

    def test_code_aware_returns_recursive_splitter(self, service):
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        splitter = service._build_splitter("code_aware", 1000, 200)
        assert isinstance(splitter, RecursiveCharacterTextSplitter)

    def test_unknown_strategy_defaults_to_recursive(self, service):
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        splitter = service._build_splitter("unknown_strategy", 500, 50)
        assert isinstance(splitter, RecursiveCharacterTextSplitter)


class TestExecutePipeline:
    @patch("src.engine.adapters.Chroma")
    @patch("src.services.embedding_registry.HuggingFaceEmbeddings")
    def test_returns_indexing_result(
        self, mock_hf, mock_chroma, service, architecture, sample_doc, tmp_path
    ):
        mock_chroma.from_documents = MagicMock()
        with patch(
            "src.pipeline.indexer.IndexingPipelineService._get_persist_dir",
            return_value=str(tmp_path),
        ):
            result = service.execute_pipeline("test-project-id", architecture, [sample_doc])
        assert isinstance(result, IndexingResult)
        assert result.status == "completed"
        assert result.project_id == "test-project-id"

    @patch("src.engine.adapters.Chroma")
    @patch("src.services.embedding_registry.HuggingFaceEmbeddings")
    def test_chunks_created_positive(
        self, mock_hf, mock_chroma, service, architecture, sample_doc, tmp_path
    ):
        mock_chroma.from_documents = MagicMock()
        with patch(
            "src.pipeline.indexer.IndexingPipelineService._get_persist_dir",
            return_value=str(tmp_path),
        ):
            result = service.execute_pipeline("proj-123", architecture, [sample_doc])
        assert result.chunks_created > 0

    @patch("src.engine.adapters.Chroma")
    @patch("src.services.embedding_registry.HuggingFaceEmbeddings")
    def test_metadata_json_written(
        self, mock_hf, mock_chroma, service, architecture, sample_doc, tmp_path
    ):
        import json

        mock_chroma.from_documents = MagicMock()
        with patch(
            "src.pipeline.indexer.IndexingPipelineService._get_persist_dir",
            return_value=str(tmp_path),
        ):
            service.execute_pipeline("proj-456", architecture, [sample_doc])
        meta_file = tmp_path / "metadata.json"
        assert meta_file.exists()
        with open(meta_file) as f:
            meta = json.load(f)
        assert meta["project_id"] == "proj-456"

    def test_non_chroma_adapter_raises_not_implemented(self, service, sample_doc, tmp_path):
        """Non-Chroma adapters are honest stubs that raise NotImplementedError.
        This ensures the UI can surface a clear 'not yet supported' error instead of
        silently falling back to Chroma — which was the pre-refactor behaviour we fixed.
        """
        from src.core.exceptions import IndexingError

        arch = ArchitectureDecision(
            vector_database="qdrant",
            chunking_strategy="recursive_hierarchical",
            chunk_size=500,
            overlap_size=50,
            embedding_model="sentence_transformers_minilm",
        )
        with patch(
            "src.pipeline.indexer.IndexingPipelineService._get_persist_dir",
            return_value=str(tmp_path),
        ):
            with pytest.raises(IndexingError, match="not yet implemented"):
                service.execute_pipeline("proj-789", arch, [sample_doc])


class TestAdapterRegistry:
    def test_chroma_returns_chroma_adapter(self):
        from src.engine.adapters import ChromaAdapter, get_adapter

        assert isinstance(get_adapter("chroma"), ChromaAdapter)

    def test_unknown_backend_falls_back_to_chroma(self):
        from src.engine.adapters import ChromaAdapter, get_adapter

        assert isinstance(get_adapter("completely_unknown_db"), ChromaAdapter)

    def test_all_registered_backends_instantiable(self):
        from src.engine.adapters import ADAPTER_REGISTRY, VectorStoreAdapter

        for name, cls in ADAPTER_REGISTRY.items():
            instance = cls()
            assert isinstance(instance, VectorStoreAdapter), f"{name} is not a VectorStoreAdapter"
