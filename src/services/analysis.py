import tiktoken
import re
from typing import Dict, Any

class DocumentAnalysisEngine:
    """Analyzes raw documents to extract metrics needed by the RAG architecture decision engine."""
    
    def __init__(self) -> None:
        try:
            self.tokenizer: Any = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.tokenizer = None
        
    def analyze_document(self, ingested_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzes the ingested document and computes actual structural and semantic metrics.
        Returns metrics used by the Decision Engine.
        """
        raw_text = ingested_data.get("raw_text", "")
        
        # Token estimation using tiktoken (OpenAI standard)
        if self.tokenizer:
            tokens = len(self.tokenizer.encode(raw_text, disallowed_special=()))
        else:
            tokens = len(raw_text) // 4 # Fallback
            
        # Paragraph metrics
        paragraphs = [p for p in raw_text.split("\n\n") if p.strip()]
        avg_paragraph_length = sum(len(p) for p in paragraphs) / len(paragraphs) if paragraphs else 0
        
        # Detect structures using simple heuristics
        has_code_blocks = bool(re.search(r'```.*?```', raw_text, re.DOTALL)) or \
                          ("def " in raw_text and "return " in raw_text) or \
                          ("function(" in raw_text) or ("class " in raw_text)
                          
        # Calculate semantic density (unique words / total words approximation)
        words = re.findall(r'\b\w+\b', raw_text.lower())
        unique_words = set(words)
        semantic_density = len(unique_words) / len(words) if words else 0
        
        if semantic_density > 0.6:
            density_label = "high"
        elif semantic_density > 0.4:
            density_label = "medium"
        else:
            density_label = "low"

        return {
            "filename": ingested_data.get("filename"),
            "average_paragraph_length": round(avg_paragraph_length, 2),
            "estimated_tokens": tokens,
            "has_code_blocks": has_code_blocks,
            "semantic_density": density_label,
            "raw_length_chars": len(raw_text)
        }

analysis_engine = DocumentAnalysisEngine()
