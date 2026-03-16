import json
import os
import time
from typing import Any, Dict, List

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import CharacterTextSplitter, RecursiveCharacterTextSplitter


class IndexingPipelineService:
    """Manages document chunking, embeddings, and vector database indexing workloads."""

    def __init__(self) -> None:
        self.embeddings_cache: Dict[str, Any] = {}

    def _get_embedding_function(self, model_choice: str) -> Any:
        """Retrieves and initializes the required embedding function, falling back logically."""
        if model_choice not in self.embeddings_cache:
            if "openai" in model_choice:
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key:
                    print(f"Loading Cloud OpenAI Embedding model: {model_choice}")
                    model_name = (
                        "text-embedding-3-small"
                        if "small" in model_choice
                        else "text-embedding-3-large"
                    )
                    self.embeddings_cache[model_choice] = OpenAIEmbeddings(model=model_name)
                    return self.embeddings_cache[model_choice]
                else:
                    print(
                        f"Warning: OPENAI_API_KEY not found. Falling back to local open-source BGE model instead of {model_choice}."
                    )
                    model_choice = "huggingface_bge"  # fallback

            if "minilm" in model_choice or model_choice == "huggingface_minilm":
                model_name = "sentence-transformers/all-MiniLM-L6-v2"
            elif "e5" in model_choice or "gte" in model_choice or "instructor" in model_choice:
                # Mocking massive models to BGE for local fast execution demonstration
                print(
                    f"Note: Mapping {model_choice} to optimized BGE local model for rapid testing."
                )
                model_name = "BAAI/bge-small-en-v1.5"
            else:
                model_name = "BAAI/bge-small-en-v1.5"

            print(f"Loading local embedding model: {model_name}")
            self.embeddings_cache[model_choice] = HuggingFaceEmbeddings(model_name=model_name)
        return self.embeddings_cache[model_choice]

    def execute_pipeline(
        self,
        project_id: str,
        architecture_decision: Dict[str, Any],
        documents: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Executes the indexing pipeline using LangChain core functionalities based on the decision engine's output.

        Args:
            project_id: Unique UUID for the deployment.
            architecture_decision: JSON schema defining exact RAG components.
            documents: List of raw document objects to chunk and index.

        Returns:
            Dict containing pipeline status.
        """
        print(f"Starting indexing for project {project_id} with config: {architecture_decision}")

        chunking_strategy = architecture_decision.get("chunking_strategy", "recursive_character")
        chunk_size = architecture_decision.get("chunk_size", 1000)
        overlap_size = architecture_decision.get("overlap_size", 200)

        # 1. Chunking
        if chunking_strategy == "fixed_size":
            splitter = CharacterTextSplitter(
                separator="", chunk_size=chunk_size, chunk_overlap=overlap_size
            )
        elif chunking_strategy in ["semantic", "paragraph", "sliding_window"]:
            # Semantic/Sliding chunking usually requires a dedicated embedder during the split.
            # For local reliability, we implement it via targeted Recursive Splitting with tailored params.
            splitter = RecursiveCharacterTextSplitter(
                separators=["\n\n", "\n", ".", "!", "?", " ", ""],
                chunk_size=chunk_size,
                chunk_overlap=overlap_size,
            )
        elif chunking_strategy in ["code_aware", "structure_aware"]:
            # Code aware prioritizes code blocks and syntax delimiters
            splitter = RecursiveCharacterTextSplitter(
                separators=["\nclass ", "\ndef ", "\n\n", "\n", " ", ""],
                chunk_size=chunk_size,
                chunk_overlap=overlap_size,
            )
        else:
            # default recursive_hierarchical
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size, chunk_overlap=overlap_size
            )

        langchain_docs = []
        for doc in documents:
            text = doc.get("raw_text", "")
            if not text:
                continue
            metadata = doc.get("metadata", {})
            metadata["source"] = doc.get("filename", "unknown")
            langchain_docs.append(Document(page_content=text, metadata=metadata))

        chunks = splitter.split_documents(langchain_docs)

        # 2. Embedding Configuration
        embedding_model_choice = architecture_decision.get("embedding_model", "huggingface_minilm")
        embedding_function = self._get_embedding_function(embedding_model_choice)

        # 3. Vector Storage
        # Simulate connection to Enterprise DBs if selected, then gracefully write to local Chroma for retrieval testing
        db_choice = architecture_decision.get("vector_database", "chroma")
        if db_choice != "chroma":
            print(f"[Simulation] Connecting to {db_choice.upper()} cloud/enterprise cluster...")
            print(f"[Simulation] Initializing {db_choice} collection for project {project_id}...")
            print("[Simulation] Note: Falling back to local ChromaDB payload for demo persistence.")

        persist_dir = os.path.join(os.getcwd(), "chroma_db", project_id)
        os.makedirs(persist_dir, exist_ok=True)

        print(f"Embedding {len(chunks)} chunks into vector database at {persist_dir}...")
        _ = Chroma.from_documents(
            documents=chunks, embedding=embedding_function, persist_directory=persist_dir
        )

        # 4. Save metadata for deployment tracking
        metadata = {
            "project_id": project_id,
            "architecture": architecture_decision,
            "documents_indexed": len(documents),
            "chunks_created": len(chunks),
            "created_at": time.time(),
        }
        with open(os.path.join(persist_dir, "metadata.json"), "w") as f:
            json.dump(metadata, f)

        return {
            "status": "completed",
            "project_id": project_id,
            "chunks_created": len(chunks),
            "vector_database_path": persist_dir,
            "message": "Indexing jobs generated and vector database populated successfully.",
        }


indexer_service = IndexingPipelineService()
