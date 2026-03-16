"""Shared embedding model registry used by both the indexing pipeline and RAG runtime.

This module centralises the logic that was previously duplicated across
``src/pipeline/indexer.py`` and ``src/runtime/rag.py``.
"""

import os
from typing import Any

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_openai import OpenAIEmbeddings

from src.core.logging import get_logger

logger = get_logger(__name__)

# Shared cache so the same model is not loaded twice per process
_embeddings_cache: dict[str, Any] = {}

#: Map of internal model-choice strings to HuggingFace model identifiers.
_HF_MODEL_MAP: dict[str, str] = {
    "huggingface_minilm": "sentence-transformers/all-MiniLM-L6-v2",
    "sentence_transformers_minilm": "sentence-transformers/all-MiniLM-L6-v2",
    "huggingface_bge": "BAAI/bge-small-en-v1.5",
    "instructor_xl": "BAAI/bge-small-en-v1.5",  # local demo fallback
    "huggingface_e5": "BAAI/bge-small-en-v1.5",
    "huggingface_gte": "BAAI/bge-small-en-v1.5",
}


def get_embedding_function(model_choice: str) -> Any:
    """Return (and cache) the embedding function for *model_choice*.

    Resolution order:
    1. If *model_choice* starts with ``openai`` and ``OPENAI_API_KEY`` is set,
       return an :class:`OpenAIEmbeddings` instance.
    2. Otherwise resolve through :data:`_HF_MODEL_MAP` and return a local
       :class:`HuggingFaceEmbeddings` instance.
    3. If *model_choice* is unknown, fall back to the BGE-small model.

    Args:
        model_choice: Internal model identifier string produced by the
            :class:`ArchitectureDecisionEngine`.

    Returns:
        An initialised LangChain embedding object.
    """
    if model_choice in _embeddings_cache:
        return _embeddings_cache[model_choice]

    effective_choice = model_choice

    if "openai" in model_choice:
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            model_name = (
                "text-embedding-3-small" if "small" in model_choice else "text-embedding-3-large"
            )
            logger.info(
                "loading_openai_embedding",
                model=model_name,
                choice=model_choice,
            )
            instance = OpenAIEmbeddings(model=model_name, api_key=api_key)
            _embeddings_cache[model_choice] = instance
            return instance
        else:
            logger.warning(
                "openai_key_missing_falling_back",
                choice=model_choice,
                fallback="huggingface_bge",
            )
            effective_choice = "huggingface_bge"

    hf_model = _HF_MODEL_MAP.get(effective_choice, "BAAI/bge-small-en-v1.5")
    if effective_choice not in _HF_MODEL_MAP:
        logger.warning(
            "unknown_embedding_choice_using_default",
            choice=effective_choice,
            default=hf_model,
        )

    logger.info("loading_hf_embedding", model=hf_model)
    instance = HuggingFaceEmbeddings(model_name=hf_model)
    _embeddings_cache[model_choice] = instance
    return instance


def warm_default_embedding() -> None:
    """Pre-load the default local embedding model at server startup.

    Call this inside the FastAPI ``lifespan`` handler to eliminate cold-start
    latency on the first request.
    """
    default = os.getenv("DEFAULT_EMBEDDING_MODEL", "huggingface_bge")
    logger.info("warming_default_embedding", model=default)
    get_embedding_function(default)
