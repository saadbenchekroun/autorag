"""Pydantic v2 models for all internal data schemas.

These replace the ``Dict[str, Any]`` types that previously flowed through
the entire pipeline without schema enforcement.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Ingestion layer
# ---------------------------------------------------------------------------


class IngestedDocument(BaseModel):
    """Output of :class:`DocumentIngestionService.ingest_file`."""

    source: str
    filename: str
    type: str
    size_bytes: int
    raw_text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Analysis layer
# ---------------------------------------------------------------------------


class DocumentMetrics(BaseModel):
    """Output of :class:`DocumentAnalysisEngine.analyze_document`."""

    filename: str | None = None
    average_paragraph_length: float = 0.0
    estimated_tokens: int = 0
    has_code_blocks: bool = False
    semantic_density: str = "low"  # "low" | "medium" | "high"
    raw_length_chars: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Decision engine
# ---------------------------------------------------------------------------


class ArchitectureDecision(BaseModel):
    """Output of :class:`ArchitectureDecisionEngine.determine_architecture`."""

    vector_database: str
    chunking_strategy: str
    chunk_size: int
    overlap_size: int
    embedding_model: str
    reasoning: list[str] = Field(default_factory=list)

    @field_validator("chunk_size", "overlap_size")
    @classmethod
    def positive_int(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Must be a positive integer")
        return v


# ---------------------------------------------------------------------------
# Pipeline / indexing
# ---------------------------------------------------------------------------


class IndexingResult(BaseModel):
    """Output of :class:`IndexingPipelineService.execute_pipeline`."""

    status: str
    project_id: str
    chunks_created: int
    vector_database_path: str
    message: str
    errors: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# RAG runtime
# ---------------------------------------------------------------------------


class ContextChunk(BaseModel):
    """A single retrieved context fragment returned in a query response."""

    text: str
    source: str


class QueryMetrics(BaseModel):
    chunks_retrieved: int
    generation_mode: str


class QueryResponse(BaseModel):
    """Full response from :class:`RAGRuntimeSystem.generate_response`."""

    answer: str
    context_used: list[ContextChunk] = Field(default_factory=list)
    metrics: QueryMetrics


# ---------------------------------------------------------------------------
# API request/response schemas
# ---------------------------------------------------------------------------


class QueryRequest(BaseModel):
    """HTTP request body for the query endpoint."""

    query: str = Field(..., min_length=1, max_length=2000)
    architecture: ArchitectureDecision


class BuildPipelineResponse(BaseModel):
    """HTTP response from the build-pipeline endpoint."""

    project_id: str
    message: str
    architecture_decision: ArchitectureDecision
    dataset_analysis: list[DocumentMetrics]
    errors: list[str] = Field(default_factory=list)
