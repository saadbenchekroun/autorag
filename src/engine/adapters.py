from __future__ import annotations

import shutil
from abc import ABC, abstractmethod
from typing import Any

from langchain_community.vectorstores import Chroma

from src.core.logging import get_logger

logger = get_logger(__name__)


class VectorStoreAdapter(ABC):
    """Abstract interface for all vector store backends."""

    @abstractmethod
    def upsert(
        self,
        project_id: str,
        chunks: list[Any],
        embedding_function: Any,
        persist_dir: str,
    ) -> None:
        """Embed *chunks* and persist them under *project_id*.

        Args:
            project_id: Unique project identifier.
            chunks: List of LangChain ``Document`` objects.
            embedding_function: An initialised LangChain embedding object.
            persist_dir: Local path for adapters that persist to disk.
        """

    @abstractmethod
    def as_retriever(
        self,
        project_id: str,
        embedding_function: Any,
        persist_dir: str,
        k: int = 3,
    ) -> Any:
        """Return a LangChain retriever for *project_id*."""

    @abstractmethod
    def delete(self, project_id: str, persist_dir: str) -> None:
        """Delete all vectors associated with *project_id*."""


# ---------------------------------------------------------------------------
# ChromaDB adapter (fully implemented)
# ---------------------------------------------------------------------------


class ChromaAdapter(VectorStoreAdapter):
    """Local ChromaDB vector store adapter."""

    def upsert(
        self,
        project_id: str,
        chunks: list[Any],
        embedding_function: Any,
        persist_dir: str,
    ) -> None:
        logger.info("chroma_upsert", project_id=project_id, chunks=len(chunks))
        Chroma.from_documents(
            documents=chunks,
            embedding=embedding_function,
            persist_directory=persist_dir,
        )

    def as_retriever(
        self,
        project_id: str,
        embedding_function: Any,
        persist_dir: str,
        k: int = 3,
    ) -> Any:
        store = Chroma(persist_directory=persist_dir, embedding_function=embedding_function)
        return store.as_retriever(search_kwargs={"k": k})

    def delete(self, project_id: str, persist_dir: str) -> None:
        logger.info("chroma_delete", project_id=project_id, path=persist_dir)
        shutil.rmtree(persist_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Qdrant adapter stub (Phase 3 implementation)
# ---------------------------------------------------------------------------


class QdrantAdapter(VectorStoreAdapter):
    """Qdrant vector store adapter.

    .. note::
        Full implementation planned for Phase 3.  This stub raises
        ``NotImplementedError`` so that the engine can still instantiate it
        and the CI test suite can verify registration.
    """

    def upsert(self, project_id, chunks, embedding_function, persist_dir):
        raise NotImplementedError("QdrantAdapter.upsert not yet implemented — Phase 3")

    def as_retriever(self, project_id, embedding_function, persist_dir, k=3):
        raise NotImplementedError("QdrantAdapter.as_retriever not yet implemented — Phase 3")

    def delete(self, project_id, persist_dir):
        raise NotImplementedError("QdrantAdapter.delete not yet implemented — Phase 3")


# ---------------------------------------------------------------------------
# Pinecone adapter stub (Phase 3 implementation)
# ---------------------------------------------------------------------------


class PineconeAdapter(VectorStoreAdapter):
    """Pinecone vector store adapter stub."""

    def upsert(self, project_id, chunks, embedding_function, persist_dir):
        raise NotImplementedError("PineconeAdapter.upsert not yet implemented — Phase 3")

    def as_retriever(self, project_id, embedding_function, persist_dir, k=3):
        raise NotImplementedError("PineconeAdapter.as_retriever not yet implemented — Phase 3")

    def delete(self, project_id, persist_dir):
        raise NotImplementedError("PineconeAdapter.delete not yet implemented — Phase 3")


# ---------------------------------------------------------------------------
# Adapter registry
# ---------------------------------------------------------------------------

ADAPTER_REGISTRY: dict[str, type[VectorStoreAdapter]] = {
    "chroma": ChromaAdapter,
    "qdrant": QdrantAdapter,
    "pinecone": PineconeAdapter,
    "weaviate": ChromaAdapter,  # TODO: replace with WeaviateAdapter in Phase 3
    "milvus": ChromaAdapter,  # TODO: replace with MilvusAdapter in Phase 3
    "pgvector": ChromaAdapter,  # TODO: replace with PgVectorAdapter in Phase 3
}


def get_adapter(vector_database: str) -> VectorStoreAdapter:
    """Return the adapter instance for *vector_database*.

    Falls back to :class:`ChromaAdapter` for unknown backends and emits a
    warning so engineers are notified during development.
    """
    adapter_cls = ADAPTER_REGISTRY.get(vector_database)
    if adapter_cls is None:
        logger.warning(
            "unknown_vector_store_using_chroma_fallback",
            requested=vector_database,
        )
        adapter_cls = ChromaAdapter
    return adapter_cls()
