"""The trust layer must never depend on LLM code (FR-7.5)."""

from __future__ import annotations

import subprocess
import sys
import textwrap


def test_trust_layer_imports_without_anthropic_or_ai_modules():
    script = textwrap.dedent(
        """
        import sys
        sys.modules["anthropic"] = None  # any import of the SDK now raises ImportError
        import src.core.trust.verifier  # noqa: F401
        loaded = [m for m in sys.modules if m.startswith("src.core.ai")]
        assert not loaded, loaded
        """
    )
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
