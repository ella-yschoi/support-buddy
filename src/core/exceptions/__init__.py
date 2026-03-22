"""Custom exceptions for Support Buddy."""


class SupportBuddyError(Exception):
    """Base exception for all Support Buddy errors."""


class KnowledgeBaseError(SupportBuddyError):
    """Error related to knowledge base operations."""


class DocumentLoadError(KnowledgeBaseError):
    """Failed to load a document."""


class EmbeddingError(KnowledgeBaseError):
    """Failed to generate embeddings."""


class AnalysisError(SupportBuddyError):
    """Error during inquiry or log analysis."""


class AIClientError(SupportBuddyError):
    """Error communicating with the AI provider."""
