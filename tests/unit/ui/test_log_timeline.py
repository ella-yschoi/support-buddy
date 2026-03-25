"""Tests for log timeline helper (build_timeline_df)."""

import pandas as pd
import pytest

from src.core.models import LogEvent
from src.ui.app import build_timeline_df


class TestBuildTimelineDf:
    def test_build_timeline_df_from_events(self):
        events = [
            LogEvent(timestamp="2024-01-15T10:00:00Z", level="INFO", message="Started"),
            LogEvent(timestamp="2024-01-15T10:01:00Z", level="ERROR", message="Failed"),
        ]
        df = build_timeline_df(events)
        assert df is not None
        assert len(df) == 2
        assert list(df.columns) == ["timestamp", "level", "message"]
        assert pd.api.types.is_datetime64_any_dtype(df["timestamp"])

    def test_build_timeline_df_skips_empty_timestamps(self):
        events = [
            LogEvent(timestamp="2024-01-15T10:00:00Z", level="INFO", message="Valid"),
            LogEvent(timestamp="", level="ERROR", message="No timestamp"),
            LogEvent(timestamp="not-a-date", level="WARN", message="Bad timestamp"),
        ]
        df = build_timeline_df(events)
        assert df is not None
        assert len(df) == 1
        assert df.iloc[0]["message"] == "Valid"

    def test_build_timeline_df_empty_events(self):
        assert build_timeline_df([]) is None

    def test_build_timeline_df_all_invalid_timestamps(self):
        events = [
            LogEvent(timestamp="", level="INFO", message="No ts"),
            LogEvent(timestamp="garbage", level="ERROR", message="Bad ts"),
        ]
        assert build_timeline_df(events) is None
