# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2024-03-21

### Added
- **Domain-Specific Exceptions**: Introduced a custom exception hierarchy in `src/core/exceptions.py`.
- **Structured Logging**: Implemented a centralized logging system in `src/core/logging.py`.
- **Pydantic v2 Schemas**: Migrated all data models to Pydantic v2 for improved performance and validation.
- **Unified Configuration**: Added `Settings` class in `src/core/config.py` for environment and YAML-based configuration.
- **Embedding Registry**: Centralized embedding model resolution in `src/services/embedding_registry.py`.
- **Vector Store Abstraction**: Created `VectorStoreAdapter` interface and `ChromaAdapter` implementation.
- **Database Persistence**: Added SQLAlchemy models for `Project` and `Job` tracking in SQLite/PostgreSQL.
- **New Frontend Components**:
    - `UploadDataset`: Added per-document analysis and better error reporting.
    - `DeploymentsList`: New project overview grid.
    - `Playground`: Added retrieval depth (k) control and metrics display.
- **CLI Tool**: Developed `autorag` CLI with `index`, `query`, and `serve` commands.
- **Production Infrastructure**: Added `docker-compose.prod.yml` with Nginx and Redis support.

### Changed
- **System Architecture**: Refactored core modules (`decision`, `ingestion`, `indexer`, `rag`) to be more modular and testable.
- **Security Updates**: Hardened file upload paths and implemented size limits.
- **API Response Format**: Standardized API responses using `ApiResponse` and `BuildPipelineResponse` models.

### Fixed
- Mutable default argument vulnerabilities in CLI and API.
- Path traversal risks in ingestion pipeline.
- Missing support for several file extensions (now supporting 12+ types).

## [0.1.0] - Initial Release

### Added
- Core RAG pipeline logic (Semantic Router, Chunking, Indexing).
- Initial Next.js dashboard.
- Support for OpenAI and HuggingFace embeddings.
