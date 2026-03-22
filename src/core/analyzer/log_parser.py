"""Log parser — parse various log formats and extract insights."""

from __future__ import annotations

import json
import re
from typing import Optional

from src.core.models import LogEvent


class LogParser:
    """Parse logs in JSON or plain text format and extract key information."""

    # Pattern for common text log format: YYYY-MM-DD HH:MM:SS LEVEL [service] message
    _TEXT_LOG_PATTERN = re.compile(
        r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+"
        r"(DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL)\s+"
        r"(?:\[([^\]]*)\]\s+)?"
        r"(.*)"
    )

    _ERROR_CODE_PATTERN = re.compile(
        r"(SYNC-\d{3}|AUTH-\d{3}|PERF-\d{3}|API-\d{3}|ACCT-\d{3})"
    )

    def detect_format(self, raw_input: str) -> str:
        """Detect whether input is JSON or text logs."""
        stripped = raw_input.strip()
        if stripped.startswith("[") or stripped.startswith("{"):
            try:
                json.loads(stripped)
                return "json"
            except json.JSONDecodeError:
                pass
        return "text"

    def parse(self, raw_input: str) -> list[LogEvent]:
        """Parse raw log input into structured LogEvent objects."""
        if not raw_input or not raw_input.strip():
            return []

        fmt = self.detect_format(raw_input)
        if fmt == "json":
            return self._parse_json(raw_input)
        return self._parse_text(raw_input)

    def _parse_json(self, raw_input: str) -> list[LogEvent]:
        """Parse JSON log entries (array of objects or newline-delimited JSON)."""
        try:
            data = json.loads(raw_input.strip())
        except json.JSONDecodeError:
            # Try newline-delimited JSON
            events = []
            for line in raw_input.strip().split("\n"):
                line = line.strip().rstrip(",")
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            data = events

        if isinstance(data, dict):
            data = [data]

        result = []
        for entry in data:
            if not isinstance(entry, dict):
                continue
            # Extract standard fields, put the rest in metadata
            timestamp = str(entry.get("timestamp", ""))
            level = str(entry.get("level", "INFO")).upper()
            message = str(entry.get("message", ""))

            metadata = {
                k: v
                for k, v in entry.items()
                if k not in ("timestamp", "level", "message")
            }

            result.append(
                LogEvent(
                    timestamp=timestamp,
                    level=level,
                    message=message,
                    metadata=metadata,
                )
            )
        return result

    def _parse_text(self, raw_input: str) -> list[LogEvent]:
        """Parse text log lines."""
        result = []
        for line in raw_input.strip().split("\n"):
            line = line.strip()
            if not line:
                continue

            match = self._TEXT_LOG_PATTERN.match(line)
            if match:
                timestamp, level, service, message = match.groups()
                metadata = {}
                if service:
                    metadata["service"] = service
                result.append(
                    LogEvent(
                        timestamp=timestamp,
                        level=level.upper(),
                        message=message.strip(),
                        metadata=metadata,
                    )
                )
            else:
                # Unparseable line — store as INFO with raw content
                result.append(
                    LogEvent(timestamp="", level="INFO", message=line, metadata={})
                )
        return result

    def extract_errors(self, events: list[LogEvent]) -> list[LogEvent]:
        """Extract all ERROR and FATAL level events."""
        return [e for e in events if e.level in ("ERROR", "FATAL", "CRITICAL")]

    def extract_slow_operations(
        self, events: list[LogEvent], threshold_ms: int = 5000
    ) -> list[LogEvent]:
        """Extract events indicating slow operations."""
        slow = []
        for event in events:
            # Check metadata for duration
            duration = event.metadata.get("duration_ms")
            if duration is not None and int(duration) > threshold_ms:
                slow.append(event)
                continue

            # Check message for slow indicators
            if "slow" in event.message.lower():
                slow.append(event)

        return slow

    def extract_error_codes(self, events: list[LogEvent]) -> list[str]:
        """Extract unique error codes from log events."""
        codes: set[str] = set()
        for event in events:
            # Check metadata
            code = event.metadata.get("error_code")
            if code:
                codes.add(str(code).upper())

            # Check message
            found = self._ERROR_CODE_PATTERN.findall(event.message)
            codes.update(c.upper() for c in found)

        return sorted(codes)

    def generate_text_summary(self, events: list[LogEvent]) -> str:
        """Generate a human-readable summary of the log events."""
        if not events:
            return "No log events to summarize."

        total = len(events)
        errors = self.extract_errors(events)
        slow_ops = self.extract_slow_operations(events)
        error_codes = self.extract_error_codes(events)

        lines = [f"Log Summary: {total} events total"]

        if events[0].timestamp and events[-1].timestamp:
            lines.append(f"Time range: {events[0].timestamp} → {events[-1].timestamp}")

        # Level breakdown
        level_counts: dict[str, int] = {}
        for e in events:
            level_counts[e.level] = level_counts.get(e.level, 0) + 1
        breakdown = ", ".join(f"{k}: {v}" for k, v in sorted(level_counts.items()))
        lines.append(f"Levels: {breakdown}")

        if errors:
            lines.append(f"\n{len(errors)} ERROR(s) found:")
            for e in errors:
                lines.append(f"  [{e.timestamp}] {e.message}")

        if slow_ops:
            lines.append(f"\n{len(slow_ops)} slow operation(s):")
            for s in slow_ops:
                dur = s.metadata.get("duration_ms", "?")
                lines.append(f"  [{s.timestamp}] {s.message} (duration: {dur}ms)")

        if error_codes:
            lines.append(f"\nError codes: {', '.join(error_codes)}")

        return "\n".join(lines)
