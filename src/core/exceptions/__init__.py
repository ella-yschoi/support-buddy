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


class PolicyError(SupportBuddyError):
    """Autonomy policy file is missing, malformed, or invalid."""


class ConfigError(SupportBuddyError):
    """Application configuration file is missing or invalid."""


class BriefingError(SupportBuddyError):
    """A briefing could not be stored, found, or updated."""


class BriefingStateError(BriefingError):
    """The briefing is not in a state that allows this operation (e.g. already approved)."""


class TicketSourceError(SupportBuddyError):
    """A ticket tool could not be reached or answered unexpectedly."""


class TicketNotFound(TicketSourceError):
    """The requested ticket does not exist in the source."""
