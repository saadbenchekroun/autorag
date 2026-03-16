import json
from typing import Any

import litellm

from src.core.config import config
from src.core.exceptions import DecisionEngineError
from src.core.logging import get_logger
from src.core.schemas import ArchitectureDecision

logger = get_logger(__name__)


class ArchitectureDecisionEngine:
    """Intelligently analyses dataset metrics and selects the optimal RAG architecture."""

    def __init__(self) -> None:
        self.vector_dbs: list[str] = list(config.get("model", {}).get("vector_store", {}).values())
        self.chunking_strategies: list[str] = config.get_nested("pipeline.chunking.strategies", [])
        self.embedding_models: list[str] = list(
            config.get("model", {}).get("embedding", {}).values()
        )
        # Read model map from config; keep hard-coded map as fallback so
        # the engine is never broken by a missing config key.
        self._model_map: dict[str, str] = {
            "openai": config.get_nested("model.llm.models.openai", "gpt-4o"),
            "gemini": config.get_nested("model.llm.models.gemini", "gemini/gemini-1.5-pro"),
            "anthropic": config.get_nested(
                "model.llm.models.anthropic", "claude-3-5-sonnet-20240620"
            ),
            "deepseek": config.get_nested("model.llm.models.deepseek", "deepseek/deepseek-chat"),
            "groq": config.get_nested("model.llm.models.groq", "groq/llama-3.1-70b-versatile"),
            "openrouter": config.get_nested(
                "model.llm.models.openrouter", "openrouter/google/gemini-pro-1.5"
            ),
            "mistral": config.get_nested(
                "model.llm.models.mistral", "mistral/mistral-large-latest"
            ),
        }

    def _determine_vector_db(
        self, total_tokens: int, metadata_heavy: bool, environment: str, latency_req: str
    ) -> str:
        """Determines the vector database matching the scaling, semantic density, and cost factors."""
        cloud_ultra = config.get_nested(
            "pipeline.decision_engine.thresholds.cloud_ultra_scale", 100_000_000
        )
        local_max = config.get_nested(
            "pipeline.decision_engine.thresholds.local_max_tokens", 50_000_000
        )

        if environment == "local":
            if total_tokens > local_max or metadata_heavy:
                return "qdrant"
            return str(config.get_nested("model.vector_store.default_local", "chroma"))

        if latency_req == "ultra_low":
            return str(config.get_nested("model.vector_store.default_cloud", "pinecone"))
        if metadata_heavy:
            return "weaviate"
        if total_tokens > cloud_ultra:
            return "milvus"
        return str(config.get_nested("model.vector_store.default_cloud", "pinecone"))

    def _intelligent_decision(
        self, dataset_metrics: list[dict], api_keys: dict
    ) -> ArchitectureDecision | None:
        """Attempts LLM-powered architecture selection; returns ``None`` on any failure."""
        provider = api_keys.get("llm_provider", "openai")
        api_key = api_keys.get("llm_key")

        if not api_key:
            return None

        model = self._model_map.get(provider, "gpt-4o")
        vector_db_provider = api_keys.get("vector_db_provider", "none")
        embedding_provider = api_keys.get("embedding_provider", "none")

        system_prompt = f"""You are an AI RAG Architect. Analyse dataset metrics and output an optimal RAG configuration.
Metrics include tokens, code presence, semantic density, etc.

The user has explicitly provided API keys for the following infrastructure:
- Vector Database Provider: {vector_db_provider}
- Embedding Provider: {embedding_provider}

You MUST strongly consider selecting the infrastructure that matches the user's provided API keys if they are not 'none'.

Return EXACTLY a JSON object with:
- vector_database: (pinecone, weaviate, milvus, qdrant, chroma, pgvector, elasticsearch)
- chunking_strategy: (fixed_size, sliding_window, semantic, paragraph, recursive_hierarchical, structure_aware, code_aware)
- chunk_size: (int)
- overlap_size: (int)
- embedding_model: (openai_text_embedding_3_small, openai_text_embedding_3_large, huggingface_bge, huggingface_e5, huggingface_gte, instructor_xl, sentence_transformers_minilm)
- reasoning: [string array of expert explanations]

ONLY JSON. NO MARKDOWN."""

        try:
            logger.info(
                "requesting_llm_architecture",
                provider=provider,
                model=model,
            )
            response = litellm.completion(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Dataset Metrics: {json.dumps(dataset_metrics)}"},
                ],
                api_key=api_key,
            )

            content = response.choices[0].message.content.strip()
            # Strip possible markdown fences
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            raw: dict[str, Any] = json.loads(content)
            decision = ArchitectureDecision(**raw)
            logger.info("llm_architecture_chosen", vector_db=decision.vector_database)
            return decision
        except Exception:
            logger.exception("llm_reasoning_failed_using_deterministic_fallback")
            return None

    def _determine_chunking(
        self, has_code: bool, high_density: bool, total_tokens: int
    ) -> tuple[str, int, int]:
        """Calculates optimal chunking parameters based on document characteristics."""
        defaults = config.get_nested("pipeline.chunking.defaults", {})

        if has_code:
            return (
                "code_aware",
                int(defaults.get("code_aware", {}).get("size", 1000)),
                int(defaults.get("code_aware", {}).get("overlap", 200)),
            )
        if high_density:
            return (
                "semantic",
                int(defaults.get("semantic", {}).get("size", 512)),
                int(defaults.get("semantic", {}).get("overlap", 50)),
            )
        if total_tokens > 5_000_000:
            return (
                "sliding_window",
                int(defaults.get("sliding_window", {}).get("size", 1024)),
                int(defaults.get("sliding_window", {}).get("overlap", 256)),
            )

        return (
            "recursive_hierarchical",
            int(defaults.get("fixed_size", {}).get("size", 1500)),
            int(defaults.get("fixed_size", {}).get("overlap", 150)),
        )

    def _determine_embedding(self, total_tokens: int, environment: str, latency_req: str) -> str:
        """Selects the embedding model balancing cost, accuracy, and deployment constraints."""
        if environment == "local" or total_tokens < 50_000:
            if latency_req == "ultra_low":
                return str(
                    config.get_nested("model.embedding.local_fast", "sentence_transformers_minilm")
                )
            return str(config.get_nested("model.embedding.local_accurate", "huggingface_bge"))
        if total_tokens > 10_000_000:
            return str(
                config.get_nested("model.embedding.cloud_small", "openai_text_embedding_3_small")
            )
        return str(
            config.get_nested("model.embedding.cloud_large", "openai_text_embedding_3_large")
        )

    def determine_architecture(
        self,
        dataset_metrics: list[dict],
        api_keys: dict | None = None,
    ) -> ArchitectureDecision:
        """Evaluates structural and semantic metrics to select the optimal RAG architecture.

        Args:
            dataset_metrics: List of metric dicts produced by
                :class:`DocumentAnalysisEngine`.
            api_keys: Optional dict containing ``llm_provider``, ``llm_key``,
                ``vector_db_provider``, and ``embedding_provider`` keys.

        Returns:
            An :class:`ArchitectureDecision` instance.

        Raises:
            :class:`DecisionEngineError` if no metrics are provided.
        """
        if not dataset_metrics:
            raise DecisionEngineError("No metrics provided for decision engine.")

        if api_keys is None:
            api_keys = {}

        # --- 1. Try LLM-powered reasoning first ---
        intelligent_choice = self._intelligent_decision(dataset_metrics, api_keys)
        if intelligent_choice:
            return intelligent_choice

        # --- 2. Deterministic fallback ---
        total_tokens = sum(m.get("estimated_tokens", 0) for m in dataset_metrics)
        has_code = any(m.get("has_code_blocks", False) for m in dataset_metrics)
        metadata_heavy = any(len(m.get("metadata", {})) > 5 for m in dataset_metrics)

        densities = [m.get("semantic_density", "low") for m in dataset_metrics]
        majority_high_density = densities.count("high") > len(dataset_metrics) / 2

        environment = "local" if total_tokens < 1_000_000 else "cloud"
        latency_req = "ultra_low" if total_tokens < 100_000 else "standard"

        vector_db = self._determine_vector_db(
            total_tokens, metadata_heavy, environment, latency_req
        )
        chunking_strategy, chunk_size, overlap_size = self._determine_chunking(
            has_code, majority_high_density, total_tokens
        )
        embedding_model = self._determine_embedding(total_tokens, environment, latency_req)

        reasoning: list[str] = [
            f"Analysed {len(dataset_metrics)} document(s) totalling ~{total_tokens:,} tokens.",
        ]
        if environment == "local":
            reasoning.append(
                f"Selected local vector store ({vector_db}) for data privacy and zero cloud cost."
            )
        else:
            reasoning.append(
                f"Selected cloud vector store ({vector_db}) to support large-scale datasets."
            )
        if chunking_strategy == "code_aware":
            reasoning.append(
                "Code blocks detected — selected 'code_aware' chunking to preserve syntax structures."
            )
        elif chunking_strategy == "semantic":
            reasoning.append(
                "High semantic density — selected 'semantic' boundaries over fixed windows."
            )
        else:
            reason = (
                f"Selected '{chunking_strategy}' with chunk_size={chunk_size} "
                f"and overlap={overlap_size} for optimal structural retention."
            )
            reasoning.append(reason)
        if "openai" in embedding_model:
            reasoning.append(
                f"Selected {embedding_model} for maximum retrieval accuracy on large datasets."
            )
        else:
            reasoning.append(
                f"Selected open-source {embedding_model} to minimise latency and token cost."
            )

        logger.info(
            "deterministic_architecture_chosen",
            vector_db=vector_db,
            chunking=chunking_strategy,
            embedding=embedding_model,
            tokens=total_tokens,
        )

        return ArchitectureDecision(
            vector_database=vector_db,
            chunking_strategy=chunking_strategy,
            chunk_size=chunk_size,
            overlap_size=overlap_size,
            embedding_model=embedding_model,
            reasoning=reasoning,
        )


decision_engine = ArchitectureDecisionEngine()
