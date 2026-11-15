"""Pick the Claude builder or the local one per ticket, and record which one did the work."""

from __future__ import annotations

import dataclasses
from collections.abc import Callable, Sequence
from typing import Any, Protocol

from src.core.briefing.budget import DailyAiBudget
from src.core.briefing.models import Briefing


class Builds(Protocol):
    def build(self, *args: Any, **kwargs: Any) -> Briefing: ...


class RoutedBuilder:
    """Same `build` as BriefingBuilder.

    Claude is used while today's budget lasts. The AI analyzer and drafter swallow API errors
    and fall back to keyword rules, so `probes` (one per AI stage, each returning a counter
    that rises on every answered call) tell us whether Claude actually answered.
    """

    def __init__(
        self,
        ai: Builds,
        local: Builds,
        budget: DailyAiBudget,
        probes: Sequence[Callable[[], int]],
    ):
        self._ai = ai
        self._local = local
        self._budget = budget
        self._probes = tuple(probes)

    def build(self, *args: Any, **kwargs: Any) -> Briefing:
        if not self._budget.try_take():
            briefing = self._local.build(*args, **kwargs)
            return dataclasses.replace(briefing, produced_by="local (daily AI limit reached)")

        before = [probe() for probe in self._probes]
        briefing = self._ai.build(*args, **kwargs)
        answered = all(probe() > start for probe, start in zip(self._probes, before))
        label = "claude" if answered else "local (Claude did not answer)"
        return dataclasses.replace(briefing, produced_by=label)
