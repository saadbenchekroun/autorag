from typing import List, Dict, Optional, Tuple, Any
import litellm
import json
import os
from src.core.config import config

class ArchitectureDecisionEngine:
    """Intelligently analyzes dataset metrics and selects the optimal RAG architecture."""
    
    def __init__(self) -> None:
        self.vector_dbs: List[str] = list(config.get("model", {}).get("vector_store", {}).values())
        self.chunking_strategies: List[str] = config.get_nested("pipeline.chunking.strategies", [])
        self.embedding_models: List[str] = list(config.get("model", {}).get("embedding", {}).values())

    def _determine_vector_db(self, total_tokens: int, metadata_heavy: bool, environment: str, latency_req: str) -> str:
        """Determines the vector database matching the scaling, semantic density, and architecture cost factors."""
        cloud_ultra = config.get_nested("pipeline.decision_engine.thresholds.cloud_ultra_scale", 100000000)
        local_max = config.get_nested("pipeline.decision_engine.thresholds.local_max_tokens", 50000000)
        
        if environment == "local":
            if total_tokens > local_max or metadata_heavy:
                return "qdrant"
            return config.get_nested("model.vector_store.default_local", "chroma")
            
        if latency_req == "ultra_low":
            return config.get_nested("model.vector_store.default_cloud", "pinecone")
        if metadata_heavy:
            return "weaviate"
        if total_tokens > cloud_ultra:
            return "milvus"
        return config.get_nested("model.vector_store.default_cloud", "pinecone")

    def _intelligent_decision(self, dataset_metrics: List[Dict], api_keys: Dict) -> Optional[dict]:
        provider = api_keys.get("llm_provider", "openai")
        api_key = api_keys.get("llm_key")
        
        if not api_key:
            return None
            
        model_map = {
            "openai": "gpt-4o",
            "gemini": "gemini/gemini-1.5-pro",
            "anthropic": "claude-3-5-sonnet-20240620",
            "deepseek": "deepseek/deepseek-chat",
            "groq": "groq/llama-3.1-70b-versatile",
            "openrouter": "openrouter/google/gemini-pro-1.5",
            "mistral": "mistral/mistral-large-latest"
        }
        
        model = model_map.get(provider, "gpt-4o")
        model = model_map.get(provider, "gpt-4o")
        
        vector_db_provider = api_keys.get("vector_db_provider", "none")
        embedding_provider = api_keys.get("embedding_provider", "none")
        
        system_prompt = f"""You are an AI RAG Architect. Analyze dataset metrics and output an optimal RAG configuration.
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
            print(f"Requesting intelligent architecture design from {provider} ({model})...")
            response = litellm.completion(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Dataset Metrics: {json.dumps(dataset_metrics)}"}
                ],
                api_key=api_key
            )
            
            content = response.choices[0].message.content.strip()
            # Clean possible markdown
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            decision = json.loads(content)
            # Add a marker that it was AI generated
            decision["reasoning"].insert(0, f"Architecture autonomously designed by {provider.upper()} intelligence.")
            return decision
        except Exception as e:
            print(f"LLM Reasoning failed: {e}. Falling back to deterministic engine.")
            return None

    def _determine_chunking(self, has_code: bool, high_density: bool, total_tokens: int) -> Tuple[str, int, int]:
        """Calculates optimal overlapping token windows prioritizing semantic continuity or explicit markers."""
        defaults = config.get_nested("pipeline.chunking.defaults", {})
        
        if has_code:
            return "code_aware", defaults.get("code_aware", {}).get("size", 1000), defaults.get("code_aware", {}).get("overlap", 200)
        if high_density:
            return "semantic", defaults.get("semantic", {}).get("size", 512), defaults.get("semantic", {}).get("overlap", 50)
        if total_tokens > 5000000:
            return "sliding_window", defaults.get("sliding_window", {}).get("size", 1024), defaults.get("sliding_window", {}).get("overlap", 256)
        
        return "recursive_hierarchical", defaults.get("fixed_size", {}).get("size", 1500), defaults.get("fixed_size", {}).get("overlap", 150)

    def _determine_embedding(self, total_tokens: int, environment: str, latency_req: str) -> str:
        """Determines the mathematical translation layer optimizing embedding cost over cosine retrieval similarity."""
        if environment == "local" or total_tokens < 50000:
            if latency_req == "ultra_low":
                return config.get_nested("model.embedding.local_fast", "sentence_transformers_minilm")
            return config.get_nested("model.embedding.local_accurate", "huggingface_bge")
        if total_tokens > 10000000:
            return config.get_nested("model.embedding.cloud_small", "openai_text_embedding_3_small")
        return config.get_nested("model.embedding.cloud_large", "openai_text_embedding_3_large")

    def determine_architecture(self, dataset_metrics: List[Dict], api_keys: Dict = {}) -> dict:
        """
        Evaluates structural and semantic metrics to guide pipeline decisions.
        """
        if not dataset_metrics:
            raise ValueError("No metrics provided for decision engine.")
            
        # Try intelligent LLM reasoning first if keys are available
        intelligent_choice = self._intelligent_decision(dataset_metrics, api_keys)
        if intelligent_choice:
            return intelligent_choice

        total_tokens = sum([m.get("estimated_tokens", 0) for m in dataset_metrics])
        has_code = any([m.get("has_code_blocks", False) for m in dataset_metrics])
        avg_paragraph = sum([m.get("average_paragraph_length", 0) for m in dataset_metrics]) / len(dataset_metrics)
        
        metadata_heavy = any([len(m.get("metadata", {})) > 5 for m in dataset_metrics])
        
        # Calculate overall density mode
        densities = [m.get("semantic_density", "low") for m in dataset_metrics]
        high_density_count = densities.count("high")
        majority_high_density = high_density_count > len(dataset_metrics) / 2
        
        # Extract environment and requirements (mocked for now, in reality driven by user settings)
        environment = "local" if total_tokens < 1000000 else "cloud"
        latency_req = "ultra_low" if total_tokens < 100000 else "standard"
        
        # 1. Vector Database Selection
        vector_db = self._determine_vector_db(total_tokens, metadata_heavy, environment, latency_req)
        
        # 2. Chunking Strategy Selection
        chunking_strategy, chunk_size, overlap_size = self._determine_chunking(has_code, majority_high_density, total_tokens)
            
        # 3. Embedding Selection
        embedding_model = self._determine_embedding(total_tokens, environment, latency_req)
            
        reasoning = []
        reasoning.append(f"Analyzed {len(dataset_metrics)} documents totaling ~{total_tokens} tokens.")
        
        # Reasoning Vectors
        if environment == "local":
            reasoning.append(f"Selected Local Vector Store ({vector_db}) for data privacy and zero cloud cost on moderate scale.")
        else:
            reasoning.append(f"Selected Cloud Vector Store ({vector_db}) to support massive scaling >1M tokens.")
            
        # Reasoning Chunks
        if chunking_strategy == "code_aware":
            reasoning.append("Code blocks detected. Selected 'code_aware' chunking to preserve syntax structures intact.")
        elif chunking_strategy == "semantic":
            reasoning.append("High semantic density detected. Selected 'semantic' boundaries over fixed boundaries to trap meaning.")
        else:
            reasoning.append(f"Selected '{chunking_strategy}' with {chunk_size} chunk & {overlap_size} overlap for optimal structural retention.")
            
        # Reasoning Embeddings
        if "openai" in embedding_model:
            reasoning.append(f"Selected {embedding_model} to maximize retrieval accuracy via cloud API due to large dataset size.")
        else:
            reasoning.append(f"Selected open-source {embedding_model} mapping to local CPU/GPU hardware to minimize latency and token cost.")

        return {
            "vector_database": vector_db,
            "chunking_strategy": chunking_strategy,
            "chunk_size": chunk_size,
            "overlap_size": overlap_size,
            "embedding_model": embedding_model,
            "reasoning": reasoning
        }

decision_engine = ArchitectureDecisionEngine()
