"""Claude when allowed and answering, the local builder otherwise, and say which it was."""

from __future__ import annotations

from src.core.briefing.budget import DailyAiBudget
from src.core.briefing.routed import RoutedBuilder
from src.core.trust.models import Customer

from .test_store import make_briefing


class FakeBuilder:
    def __init__(self, name: str, on_build=None):
        self.name = name
        self.calls = 0
        self._on_build = on_build

    def build(self, *args, **kwargs):
        self.calls += 1
        if self._on_build:
            self._on_build()
        return make_briefing(id_=f"from-{self.name}")


def budget(tmp_path, limit: int) -> DailyAiBudget:
    return DailyAiBudget(tmp_path / "b.db", limit=limit, today=lambda: "2026-11-06")


def test_uses_claude_and_labels_the_briefing(tmp_path):
    answered = [0]
    ai = FakeBuilder("ai", on_build=lambda: answered.__setitem__(0, answered[0] + 1))
    local = FakeBuilder("local")
    routed = RoutedBuilder(ai, local, budget(tmp_path, 5), probes=[lambda: answered[0]])

    result = routed.build("text", Customer(plan="pro"))

    assert (ai.calls, local.calls) == (1, 0)
    assert result.produced_by == "claude"


def test_label_says_so_when_claude_did_not_answer(tmp_path):
    """The AI analyzer swallows API errors and falls back to keywords. The label must not lie."""
    ai = FakeBuilder("ai")  # never moves the probe
    routed = RoutedBuilder(ai, FakeBuilder("local"), budget(tmp_path, 5), probes=[lambda: 0])

    result = routed.build("text", Customer(plan="pro"))

    assert result.produced_by == "local (Claude did not answer)"


def test_every_ai_stage_must_answer_to_count_as_claude(tmp_path):
    state = {"classify": 0, "draft": 0}
    ai = FakeBuilder("ai", on_build=lambda: state.__setitem__("classify", 1))
    routed = RoutedBuilder(
        ai, FakeBuilder("local"), budget(tmp_path, 5),
        probes=[lambda: state["classify"], lambda: state["draft"]],
    )

    assert routed.build("t", Customer(plan="pro")).produced_by == "local (Claude did not answer)"


def test_falls_back_to_local_when_the_daily_limit_is_reached(tmp_path):
    ai = FakeBuilder("ai")
    local = FakeBuilder("local")
    routed = RoutedBuilder(ai, local, budget(tmp_path, 0), probes=[lambda: 0])

    result = routed.build("text", Customer(plan="pro"))

    assert (ai.calls, local.calls) == (0, 1)
    assert result.produced_by == "local (daily AI limit reached)"


def test_passes_arguments_through(tmp_path):
    seen = {}

    class Recording(FakeBuilder):
        def build(self, *args, **kwargs):
            seen.update(args=args, kwargs=kwargs)
            return super().build()

    routed = RoutedBuilder(Recording("ai"), FakeBuilder("local"), budget(tmp_path, 1), probes=[])
    routed.build("text", Customer(plan="pro"), "logs", briefing_id="x", origin=None)

    assert seen["args"][0] == "text"
    assert seen["kwargs"]["briefing_id"] == "x"
