"""Integration tests for the FastAPI router layer.

These tests use ``httpx.AsyncClient`` with the FastAPI ``app`` directly
so no network port is needed and the full request/response cycle is exercised.
"""

import io
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app

FIXTURES = Path(__file__).parent / "fixtures"

API_PREFIX = "/api/v1"


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"{API_PREFIX}/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_root_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")
    assert response.status_code == 200
    assert "AutoRAG" in response.json()["message"]


# ---------------------------------------------------------------------------
# Build pipeline — file upload security
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_path_traversal_filename_sanitised():
    """A filename like '../../etc/passwd' must be sanitised to 'passwd' (basename only)."""
    from src.api.routers import _safe_filename

    sanitised = _safe_filename("../../etc/passwd")
    assert sanitised == "passwd"
    assert ".." not in sanitised
    assert "/" not in sanitised


@pytest.mark.asyncio
async def test_safe_filename_normal_name():
    from src.api.routers import _safe_filename

    assert _safe_filename("myfile.pdf") == "myfile.pdf"


@pytest.mark.asyncio
async def test_safe_filename_none_returns_default():
    from src.api.routers import _safe_filename

    assert _safe_filename(None) == "upload"


@pytest.mark.asyncio
async def test_safe_filename_strips_leading_dot():
    from src.api.routers import _safe_filename

    result = _safe_filename(".hidden")
    assert not result.startswith(".")


# ---------------------------------------------------------------------------
# Build pipeline — no valid documents
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_pipeline_no_valid_documents_returns_422():
    """Uploading an unsupported file type should return HTTP 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = [("files", ("test.xyz", io.BytesIO(b"some content"), "application/octet-stream"))]
        response = await client.post(f"{API_PREFIX}/projects/build", files=files)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# List projects — empty state
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_projects_empty(tmp_path, monkeypatch):
    """When no chroma_db directory exists, list should return empty list."""

    monkeypatch.chdir(tmp_path)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"{API_PREFIX}/projects")
    assert response.status_code == 200
    assert response.json()["projects"] == []


# ---------------------------------------------------------------------------
# Query — missing project returns 404
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_query_missing_project_returns_404(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    payload = {
        "query": "What is RAG?",
        "architecture": {
            "vector_database": "chroma",
            "chunking_strategy": "recursive_hierarchical",
            "chunk_size": 500,
            "overlap_size": 50,
            "embedding_model": "sentence_transformers_minilm",
            "reasoning": [],
        },
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"{API_PREFIX}/projects/nonexistent-project-id/query",
            json=payload,
        )
    assert response.status_code == 404
