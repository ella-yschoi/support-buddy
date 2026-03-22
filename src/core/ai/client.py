"""Claude API client wrapper with tool use support."""

from __future__ import annotations

import json
from typing import Any

import anthropic

from src.config import ANTHROPIC_API_KEY, MODEL_FAST, MODEL_STANDARD
from src.core.ai.prompts import INQUIRY_ANALYSIS_PROMPT, LOG_ANALYSIS_PROMPT
from src.core.ai.tools import ALL_TOOLS
from src.core.exceptions import AIClientError
from src.core.knowledge.engine import KnowledgeEngine
from src.core.models import SearchResult


class AIClient:
    """Wrapper around Claude API with tool use for knowledge base search.

    Uses two model tiers:
    - FAST (Haiku): classification, simple tasks — cheap & quick
    - STANDARD (Sonnet): complex analysis, log insights, response drafting
    """

    def __init__(
        self,
        knowledge_engine: KnowledgeEngine,
        api_key: str | None = None,
        model: str | None = None,
    ):
        self._knowledge = knowledge_engine
        self._api_key = api_key or ANTHROPIC_API_KEY
        if not self._api_key:
            raise AIClientError("ANTHROPIC_API_KEY is not set")
        self._client = anthropic.Anthropic(api_key=self._api_key)
        self._model_override = model  # If set, always use this model

    def analyze_inquiry(self, inquiry_text: str) -> dict[str, Any]:
        """Analyze a customer inquiry using Claude with tool use. (Haiku)"""
        return self._run_with_tools(
            system_prompt=INQUIRY_ANALYSIS_PROMPT,
            user_message=(
                f"Analyze this customer inquiry and respond with a JSON object containing: "
                f"category, severity, summary, checklist (array of strings), "
                f"follow_up_questions (array of strings), confidence (float 0-1).\n\n"
                f"Customer inquiry:\n{inquiry_text}"
            ),
            model=self._model_override or MODEL_FAST,
        )

    def analyze_logs(self, log_summary: str) -> dict[str, Any]:
        """Analyze parsed log data using Claude. (Sonnet)"""
        return self._run_with_tools(
            system_prompt=LOG_ANALYSIS_PROMPT,
            user_message=(
                f"Analyze these parsed logs and respond with a JSON object containing: "
                f"summary (string), root_cause_hypothesis (string), "
                f"anomalies (array of strings), next_steps (array of strings).\n\n"
                f"Parsed log data:\n{log_summary}"
            ),
            model=self._model_override or MODEL_STANDARD,
        )

    def _run_with_tools(
        self,
        system_prompt: str,
        user_message: str,
        max_rounds: int = 5,
        model: str | None = None,
    ) -> dict[str, Any]:
        """Run a Claude conversation with tool use, handling tool calls automatically."""
        use_model = model or self._model_override or MODEL_STANDARD
        messages: list[dict[str, Any]] = [{"role": "user", "content": user_message}]

        for _ in range(max_rounds):
            response = self._client.messages.create(
                model=use_model,
                max_tokens=4096,
                system=system_prompt,
                tools=ALL_TOOLS,
                messages=messages,
            )

            # Collect text and tool use blocks
            tool_uses = []
            text_content = ""

            for block in response.content:
                if block.type == "text":
                    text_content = block.text
                elif block.type == "tool_use":
                    tool_uses.append(block)

            if response.stop_reason == "end_turn" or not tool_uses:
                return self._parse_json_response(text_content)

            # Handle tool calls
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for tool_use in tool_uses:
                result = self._execute_tool(tool_use.name, tool_use.input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )
            messages.append({"role": "user", "content": tool_results})

        return self._parse_json_response(text_content)

    def _execute_tool(self, tool_name: str, tool_input: dict[str, Any]) -> Any:
        """Execute a tool call and return the result."""
        if tool_name == "search_knowledge_base":
            results = self._knowledge.search(
                query=tool_input["query"],
                top_k=5,
                category=tool_input.get("category"),
            )
            return [self._search_result_to_dict(r) for r in results]

        elif tool_name == "get_error_code_info":
            code = tool_input["error_code"]
            results = self._knowledge.search(
                query=code, top_k=3, category="error_code"
            )
            if results:
                return [self._search_result_to_dict(r) for r in results]
            return {"error": f"No information found for error code: {code}"}

        return {"error": f"Unknown tool: {tool_name}"}

    def _search_result_to_dict(self, result: SearchResult) -> dict[str, Any]:
        return {
            "title": result.title,
            "content": result.content,
            "category": result.category,
            "score": result.score,
            "source": result.source_file,
        }

    def _parse_json_response(self, text: str) -> dict[str, Any]:
        """Extract JSON from Claude's text response."""
        # Try to find JSON in the response
        text = text.strip()

        # Remove markdown code blocks if present
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first and last lines (```json and ```)
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON object within the text
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
            return {"raw_response": text, "parse_error": True}
