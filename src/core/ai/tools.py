"""Tool definitions for Claude API tool use."""

from __future__ import annotations

KNOWLEDGE_SEARCH_TOOL = {
    "name": "search_knowledge_base",
    "description": (
        "Search the CloudSync knowledge base for relevant articles, FAQs, "
        "troubleshooting guides, runbooks, and error code references. "
        "Returns the most relevant documents matching the query."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query describing the topic or issue to look up",
            },
            "category": {
                "type": "string",
                "enum": ["faq", "troubleshooting", "error_code", "runbook", "feature"],
                "description": "Optional category filter to narrow results",
            },
        },
        "required": ["query"],
    },
}

ERROR_CODE_TOOL = {
    "name": "get_error_code_info",
    "description": (
        "Look up detailed information about a specific CloudSync error code. "
        "Returns causes, resolution steps, and related documentation."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "error_code": {
                "type": "string",
                "description": "The error code to look up (e.g., SYNC-001, AUTH-002, API-001)",
            },
        },
        "required": ["error_code"],
    },
}

ALL_TOOLS = [KNOWLEDGE_SEARCH_TOOL, ERROR_CODE_TOOL]
