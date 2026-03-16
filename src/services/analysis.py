import re
from typing import Any

import tiktoken

from src.core.exceptions import AnalysisError
from src.core.logging import get_logger
from src.core.schemas import DocumentMetrics, IngestedDocument

logger = get_logger(__name__)


class DocumentAnalysisEngine:
    """Analyses raw documents to extract metrics used by the architecture decision engine."""

    def __init__(self) -> None:
        try:
            self.tokenizer: Any = tiktoken.get_encoding("cl100k_base")
        except Exception:
            logger.warning("tiktoken_unavailable_using_char_estimate")
            self.tokenizer = None

    def analyze_document(self, ingested_data: IngestedDocument) -> DocumentMetrics:
        """Compute structural and semantic metrics from an ingested document.

        Metrics produced:
        - ``estimated_tokens``: tiktoken-based token count (cl100k_base).
        - ``has_code_blocks``: heuristic detection of code content.
        - ``semantic_density``: **lexical diversity** (type-token ratio) used as a
          proxy for semantic richness. Values are bucketed into low / medium / high.
          See ``docs/adr/002-decision-engine-design.md`` for known limitations.
        - ``average_paragraph_length``: mean paragraph character length.

        Args:
            ingested_data: An :class:`IngestedDocument` from the ingestion layer.

        Returns:
            A :class:`DocumentMetrics` instance.

        Raises:
            :class:`AnalysisError`: On unexpected computation failure.
        """
        try:
            return self._compute_metrics(ingested_data)
        except Exception as exc:
            raise AnalysisError(
                f"Failed to analyse document '{ingested_data.filename}': {exc}"
            ) from exc

    def _compute_metrics(self, ingested_data: IngestedDocument) -> DocumentMetrics:
        raw_text = ingested_data.raw_text

        # Token estimation using tiktoken (OpenAI cl100k_base)
        if self.tokenizer:
            tokens = len(self.tokenizer.encode(raw_text, disallowed_special=()))
        else:
            tokens = len(raw_text) // 4  # ~4 chars per token fallback

        # Paragraph metrics
        paragraphs = [p for p in raw_text.split("\n\n") if p.strip()]
        avg_paragraph_length = (
            sum(len(p) for p in paragraphs) / len(paragraphs) if paragraphs else 0.0
        )

        # Code detection heuristics
        has_code_blocks = bool(
            re.search(r"```.*?```", raw_text, re.DOTALL)
            or ("def " in raw_text and "return " in raw_text)
            or "function(" in raw_text
            or ("class " in raw_text and (":" in raw_text or "{" in raw_text))
        )

        # Lexical diversity (type-token ratio) used as a semantic density proxy.
        # NOTE: This is a lexical metric, not a true semantic embedding measure.
        # Higher TTR → more diverse vocabulary → likely denser / technical content.
        words = re.findall(r"\b\w+\b", raw_text.lower())
        unique_words = set(words)
        ttr = len(unique_words) / len(words) if words else 0.0

        if ttr > 0.6:
            density_label = "high"
        elif ttr > 0.4:
            density_label = "medium"
        else:
            density_label = "low"

        logger.info(
            "document_analysed",
            filename=ingested_data.filename,
            tokens=tokens,
            has_code=has_code_blocks,
            density=density_label,
        )

        return DocumentMetrics(
            filename=ingested_data.filename,
            average_paragraph_length=round(avg_paragraph_length, 2),
            estimated_tokens=tokens,
            has_code_blocks=has_code_blocks,
            semantic_density=density_label,
            raw_length_chars=len(raw_text),
            metadata=dict(ingested_data.metadata),
        )


analysis_engine = DocumentAnalysisEngine()
