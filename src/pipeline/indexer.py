import json
import os
import time
from typing import Any

from langchain_core.documents import Document
from langchain_text_splitters import CharacterTextSplitter, RecursiveCharacterTextSplitter

from src.core.exceptions import IndexingError
from src.core.logging import get_logger
from src.core.schemas import ArchitectureDecision, IndexingResult, IngestedDocument
from src.services.embedding_registry import get_embedding_function

logger = get_logger(__name__)


class IndexingPipelineService:
    """Manages document chunking, embedding, and vector database indexing."""

    def execute_pipeline(
        self,
        project_id: str,
        architecture_decision: ArchitectureDecision,
        documents: list[IngestedDocument],
    ) -> IndexingResult:
        """Execute the full indexing pipeline for a set of documents.

        Args:
            project_id: Unique UUID for this deployment.
            architecture_decision: Validated architecture config from the decision engine.
            documents: List of ingested document objects to chunk and index.

        Returns:
            An :class:`IndexingResult` with pipeline status and statistics.

        Raises:
            :class:`IndexingError`: If the pipeline cannot complete.
        """
        logger.info(
            "indexing_started",
            project_id=project_id,
            vector_db=architecture_decision.vector_database,
            chunking=architecture_decision.chunking_strategy,
            embedding=architecture_decision.embedding_model,
            documents=len(documents),
        )

        chunking_strategy = architecture_decision.chunking_strategy
        chunk_size = architecture_decision.chunk_size
        overlap_size = architecture_decision.overlap_size

        # --- 1. Build text splitter ---
        splitter = self._build_splitter(chunking_strategy, chunk_size, overlap_size)

        # --- 2. Convert to LangChain Documents ---
        langchain_docs: list[Document] = []
        for doc in documents:
            if not doc.raw_text:
                continue
            meta = dict(doc.metadata)
            meta["source"] = doc.filename
            langchain_docs.append(Document(page_content=doc.raw_text, metadata=meta))

        chunks = splitter.split_documents(langchain_docs)
        logger.info("chunking_complete", project_id=project_id, chunks=len(chunks))

        # --- 3. Embedding ---
        embedding_function = get_embedding_function(architecture_decision.embedding_model)

        # --- 4. Vector Storage ---
        db_choice = architecture_decision.vector_database
        if db_choice != "chroma":
            logger.info(
                "non_chroma_adapter_not_yet_implemented",
                requested=db_choice,
                fallback="chroma",
            )

        persist_dir = self._get_persist_dir(project_id)
        os.makedirs(persist_dir, exist_ok=True)

        from src.engine.adapters import get_adapter

        adapter = get_adapter(db_choice)
        try:
            adapter.upsert(
                project_id=project_id,
                chunks=chunks,
                embedding_function=embedding_function,
                persist_dir=persist_dir,
            )
        except Exception as exc:
            raise IndexingError(
                f"Failed to persist vector store for project '{project_id}': {exc}"
            ) from exc

        # --- 5. Save metadata ---
        metadata_payload = {
            "project_id": project_id,
            "architecture": architecture_decision.model_dump(),
            "documents_indexed": len(documents),
            "chunks_created": len(chunks),
            "created_at": time.time(),
        }
        with open(os.path.join(persist_dir, "metadata.json"), "w") as f:
            json.dump(metadata_payload, f, indent=2)

        logger.info(
            "indexing_complete",
            project_id=project_id,
            chunks=len(chunks),
            path=persist_dir,
        )

        return IndexingResult(
            status="completed",
            project_id=project_id,
            chunks_created=len(chunks),
            vector_database_path=persist_dir,
            message="Indexing complete — vector database populated successfully.",
        )

    @staticmethod
    def _build_splitter(strategy: str, chunk_size: int, overlap_size: int) -> Any:
        """Instantiate the appropriate LangChain text splitter."""
        if strategy == "fixed_size":
            return CharacterTextSplitter(
                separator="", chunk_size=chunk_size, chunk_overlap=overlap_size
            )
        if strategy in ("semantic", "paragraph", "sliding_window"):
            # SemanticChunker requires an embedding model during splits which
            # adds latency to the indexing path. We use RecursiveCharacterTextSplitter
            # with natural language separators as a pragmatic approximation.
            # See Phase 3 roadmap item for the full SemanticChunker implementation.
            return RecursiveCharacterTextSplitter(
                separators=["\n\n", "\n", ".", "!", "?", " ", ""],
                chunk_size=chunk_size,
                chunk_overlap=overlap_size,
            )
        if strategy in ("code_aware", "structure_aware"):
            return RecursiveCharacterTextSplitter(
                separators=["\nclass ", "\ndef ", "\n\n", "\n", " ", ""],
                chunk_size=chunk_size,
                chunk_overlap=overlap_size,
            )
        # Default: recursive hierarchical
        return RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap_size,
        )

    @staticmethod
    def _get_persist_dir(project_id: str) -> str:
        from src.core.config import config

        chroma_dir = config.get_nested("pipeline.ingestion.directories.chroma_db_dir", "chroma_db")
        return os.path.join(os.getcwd(), chroma_dir, project_id)


indexer_service = IndexingPipelineService()
