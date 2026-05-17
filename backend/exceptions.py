"""
SPECTRA Custom Exceptions
=========================
Hierarchical exception classes for structured error handling.

Exception hierarchy::

    SpectraError (base)
    ├── DataError
    │   └── DatasetNotFoundError
    ├── KnowledgeBaseError
    │   └── KnowledgeBaseNotLoadedError
    ├── ChromaDBError
    │   └── ChromaDBNotAvailableError
    ├── LLMError
    │   ├── LLMNotAvailableError
    │   └── LLMResponseError
    ├── AnalysisError
    └── ValidationError
"""


class SpectraError(Exception):
    """Base exception for all SPECTRA errors."""


class DataError(SpectraError):
    """Raised when there is an issue with data loading or processing."""


class DatasetNotFoundError(DataError):
    """Raised when the source dataset file cannot be found."""


class KnowledgeBaseError(SpectraError):
    """Raised when there is an issue with the ICD-10 knowledge base."""


class KnowledgeBaseNotLoadedError(KnowledgeBaseError):
    """Raised when the knowledge base is required but not loaded."""


class ChromaDBError(SpectraError):
    """Raised when there is an issue with ChromaDB."""


class ChromaDBNotAvailableError(ChromaDBError):
    """Raised when ChromaDB operations are attempted but the DB is unavailable."""


class LLMError(SpectraError):
    """Raised when there is an issue with the LLM/Ollama service."""


class LLMNotAvailableError(LLMError):
    """Raised when the LLM service is not available."""


class LLMResponseError(LLMError):
    """Raised when the LLM response cannot be parsed."""


class AnalysisError(SpectraError):
    """Raised when patient analysis fails."""


class ValidationError(SpectraError):
    """Raised when input validation fails."""
