import pytest

from src.engine.decision import ArchitectureDecisionEngine


@pytest.fixture
def engine():
    return ArchitectureDecisionEngine()


def test_determine_vector_db_local_small(engine):
    db = engine._determine_vector_db(
        total_tokens=10000, metadata_heavy=False, environment="local", latency_req="standard"
    )
    assert db == "chroma"


def test_determine_vector_db_local_large(engine):
    db = engine._determine_vector_db(
        total_tokens=100000000, metadata_heavy=False, environment="local", latency_req="standard"
    )
    assert db == "qdrant"


def test_determine_chunking_code_aware(engine):
    strategy, chunk, overlap = engine._determine_chunking(
        has_code=True, high_density=False, total_tokens=1000
    )
    assert strategy == "code_aware"
    assert chunk == 1000
    assert overlap == 200


def test_determine_chunking_semantic(engine):
    strategy, chunk, overlap = engine._determine_chunking(
        has_code=False, high_density=True, total_tokens=1000
    )
    assert strategy == "semantic"
    assert chunk == 512
    assert overlap == 50


def test_architecture_determination(engine):
    mock_metrics = [
        {
            "estimated_tokens": 5000,
            "has_code_blocks": True,
            "semantic_density": "high",
            "metadata": {"author": "test"},
        }
    ]
    decision = engine.determine_architecture(mock_metrics, api_keys={})

    assert decision["chunking_strategy"] == "code_aware"
    assert decision["vector_database"] == "chroma"
    assert "huggingface" in decision["embedding_model"] or "minilm" in decision["embedding_model"]
    assert len(decision["reasoning"]) > 0
