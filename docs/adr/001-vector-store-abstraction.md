# ADR 001 — Vector Store Abstraction

**Date:** 2026-03-16
**Status:** Accepted

## Context

The original codebase hard-coded ChromaDB throughout `indexer.py` and `rag.py`,
while the `ArchitectureDecisionEngine` would select Pinecone, Weaviate, Milvus,
or Qdrant — but then silently fall back to Chroma with a `[Simulation]` print
statement. This created a gap between what the system advertised and what it
actually did.

## Decision

Introduce a `VectorStoreAdapter` abstract base class in `src/engine/adapters.py`
with three abstract methods: `upsert()`, `as_retriever()`, `delete()`.

All concrete backends implement this interface:
- `ChromaAdapter` — fully implemented (local dev and small-scale prod)
- `QdrantAdapter` — stub with `NotImplementedError` (Phase 3)
- `PineconeAdapter` — stub with `NotImplementedError` (Phase 3)

A `ADAPTER_REGISTRY` dict maps decision engine output strings to adapter classes.
`get_adapter(vector_database)` returns the correct instance, falling back to
`ChromaAdapter` with a warning for unregistered backends.

## Consequences

**Positive:**
- Adding a new vector store requires only one new file and one registry entry
- No other source files need to change when a new backend is added
- Stubs with `NotImplementedError` are honest about unimplemented backends
  (contrast with silent simulation prints)
- The adapter interface can be used to write isolated unit tests per backend

**Negative:**
- Adds one import level of indirection to `indexer.py` and `rag.py`
- Backends that require a running external service cannot be tested without mocks
