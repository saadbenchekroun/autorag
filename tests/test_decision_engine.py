"""Tests for ArchitectureDecisionEngine — updated for Pydantic schemas."""

import pytest

from src.core.schemas import ArchitectureDecision
from src.engine.decision import ArchitectureDecisionEngine


@pytest.fixture
def engine():
    return ArchitectureDecisionEngine()


# ---------------------------------------------------------------------------
# Vector DB selection
# ---------------------------------------------------------------------------


class TestDetermineVectorDb:
    def test_local_small_returns_chroma(self, engine):
        db = engine._determine_vector_db(
            total_tokens=10_000, metadata_heavy=False, environment="local", latency_req="standard"
        )
        assert db == "chroma"

    def test_local_large_returns_qdrant(self, engine):
        db = engine._determine_vector_db(
            total_tokens=100_000_000,
            metadata_heavy=False,
            environment="local",
            latency_req="standard",
        )
        assert db == "qdrant"

    def test_local_metadata_heavy_returns_qdrant(self, engine):
        db = engine._determine_vector_db(
            total_tokens=1_000, metadata_heavy=True, environment="local", latency_req="standard"
        )
        assert db == "qdrant"

    def test_cloud_ultra_low_latency_returns_pinecone(self, engine):
        db = engine._determine_vector_db(
            total_tokens=50_000,
            metadata_heavy=False,
            environment="cloud",
            latency_req="ultra_low",
        )
        assert db == "pinecone"

    def test_cloud_metadata_heavy_returns_weaviate(self, engine):
        db = engine._determine_vector_db(
            total_tokens=50_000,
            metadata_heavy=True,
            environment="cloud",
            latency_req="standard",
        )
        assert db == "weaviate"

    def test_cloud_ultra_scale_returns_milvus(self, engine):
        db = engine._determine_vector_db(
            total_tokens=200_000_000,
            metadata_heavy=False,
            environment="cloud",
            latency_req="standard",
        )
        assert db == "milvus"


# ---------------------------------------------------------------------------
# Chunking strategy selection
# ---------------------------------------------------------------------------


class TestDetermineChunking:
    def test_code_content_selects_code_aware(self, engine):
        strategy, chunk, overlap = engine._determine_chunking(
            has_code=True, high_density=False, total_tokens=1_000
        )
        assert strategy == "code_aware"
        assert chunk == 1000
        assert overlap == 200

    def test_high_density_selects_semantic(self, engine):
        strategy, chunk, overlap = engine._determine_chunking(
            has_code=False, high_density=True, total_tokens=1_000
        )
        assert strategy == "semantic"
        assert chunk == 512
        assert overlap == 50

    def test_large_dataset_selects_sliding_window(self, engine):
        strategy, _, _ = engine._determine_chunking(
            has_code=False, high_density=False, total_tokens=6_000_000
        )
        assert strategy == "sliding_window"

    def test_default_returns_recursive_hierarchical(self, engine):
        strategy, _, _ = engine._determine_chunking(
            has_code=False, high_density=False, total_tokens=100
        )
        assert strategy == "recursive_hierarchical"

    def test_code_takes_priority_over_density(self, engine):
        """Code detection should take priority over high density."""
        strategy, _, _ = engine._determine_chunking(
            has_code=True, high_density=True, total_tokens=100
        )
        assert strategy == "code_aware"


# ---------------------------------------------------------------------------
# Embedding model selection
# ---------------------------------------------------------------------------


class TestDetermineEmbedding:
    def test_local_environment_uses_bge(self, engine):
        model = engine._determine_embedding(
            total_tokens=1_000, environment="local", latency_req="standard"
        )
        assert "bge" in model or "huggingface" in model

    def test_local_ultra_low_latency_uses_minilm(self, engine):
        model = engine._determine_embedding(
            total_tokens=1_000, environment="local", latency_req="ultra_low"
        )
        assert "minilm" in model or "sentence_transformers" in model

    def test_small_cloud_dataset_uses_small_embedding(self, engine):
        model = engine._determine_embedding(
            total_tokens=100_000, environment="cloud", latency_req="standard"
        )
        assert "large" in model

    def test_very_large_cloud_dataset_uses_small_embedding(self, engine):
        model = engine._determine_embedding(
            total_tokens=20_000_000, environment="cloud", latency_req="standard"
        )
        assert "small" in model


# ---------------------------------------------------------------------------
# Full architecture determination
# ---------------------------------------------------------------------------


class TestDetermineArchitecture:
    def test_returns_architecture_decision_instance(self, engine):
        metrics = [
            {
                "estimated_tokens": 5_000,
                "has_code_blocks": True,
                "semantic_density": "high",
                "metadata": {"author": "test"},
            }
        ]
        decision = engine.determine_architecture(metrics, api_keys={})
        assert isinstance(decision, ArchitectureDecision)

    def test_code_document_selects_code_aware(self, engine):
        metrics = [
            {
                "estimated_tokens": 5_000,
                "has_code_blocks": True,
                "semantic_density": "low",
                "metadata": {},
            }
        ]
        decision = engine.determine_architecture(metrics)
        assert decision.chunking_strategy == "code_aware"
        assert decision.vector_database == "chroma"

    def test_reasoning_not_empty(self, engine):
        metrics = [
            {
                "estimated_tokens": 1_000,
                "has_code_blocks": False,
                "semantic_density": "low",
                "metadata": {},
            }
        ]
        decision = engine.determine_architecture(metrics)
        assert len(decision.reasoning) > 0

    def test_empty_metrics_raises(self, engine):
        from src.core.exceptions import DecisionEngineError

        with pytest.raises(DecisionEngineError):
            engine.determine_architecture([])

    def test_none_api_keys_safe(self, engine):
        """Passing api_keys=None should not raise."""
        metrics = [
            {
                "estimated_tokens": 1_000,
                "has_code_blocks": False,
                "semantic_density": "low",
                "metadata": {},
            }
        ]
        decision = engine.determine_architecture(metrics, api_keys=None)
        assert isinstance(decision, ArchitectureDecision)
