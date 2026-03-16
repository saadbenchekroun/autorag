"""Domain exception hierarchy for AutoRAG Architect."""


class AutoRAGError(Exception):
    """Base exception for all AutoRAG domain errors."""


class IngestionError(AutoRAGError):
    """Raised when a file cannot be read or its text cannot be extracted."""


class AnalysisError(AutoRAGError):
    """Raised when document metric analysis fails."""


class IndexingError(AutoRAGError):
    """Raised when the indexing pipeline encounters an unrecoverable error."""


class RetrievalError(AutoRAGError):
    """Raised when vector store retrieval fails."""


class DecisionEngineError(AutoRAGError):
    """Raised when the architecture decision engine fails."""


class ConfigurationError(AutoRAGError):
    """Raised when required configuration or secrets are missing."""


class UnsupportedFileTypeError(IngestionError):
    """Raised when an uploaded file extension is not supported."""


class FileSizeLimitError(IngestionError):
    """Raised when an uploaded file exceeds the configured size limit."""
