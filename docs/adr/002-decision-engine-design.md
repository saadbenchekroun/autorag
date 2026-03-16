# ADR 002 — Decision Engine Design and Semantic Density Metric

**Date:** 2026-03-16
**Status:** Accepted (with known limitations documented)

## Context

The `ArchitectureDecisionEngine` uses a "semantic density" metric to decide
between semantic chunking and fixed/hierarchical chunking. The original
implementation computed `unique_words / total_words` (the **type-token ratio**,
TTR) and called it "semantic density."

TTR is a lexical diversity metric, not a semantic density metric:
- A legal contract has low TTR (repetitive terms) but high semantic density
- A children's book may have high TTR but low semantic content

## Decision

**Short-term (current):** Keep TTR as the metric but rename internal comments
to "lexical diversity proxy" and document the limitation in `analysis.py` and
this ADR. The decision engine's chunking selection is still directionally useful
(text with high lexical diversity is likely more technical and benefits from
semantic-boundary chunking).

**Phase 3 target:** Replace TTR with sentence-embedding variance:
1. Embed all sentences in a document using the default local embedding model
2. Compute pairwise cosine similarity variance
3. Low variance → semantically coherent → paragraph chunking
4. High variance → topic switching → semantic boundary chunking

## Consequences

- The current metric is a useful heuristic but not theoretically grounded
- All output reasoning strings now accurately describe it as a proxy metric
- Phase 3 implementation adds ~5-10 seconds to document analysis for large
  documents due to per-sentence embedding; this should be cached
