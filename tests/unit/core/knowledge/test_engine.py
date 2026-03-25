"""Tests for knowledge engine update operations."""

from pathlib import Path

import pytest

from src.core.knowledge.engine import KnowledgeEngine


@pytest.fixture
def engine(tmp_path: Path) -> KnowledgeEngine:
    return KnowledgeEngine(persist_dir=str(tmp_path / "chroma"))


class TestKnowledgeEngineUpdate:
    def test_update_file_refreshes_content(self, engine: KnowledgeEngine, tmp_path: Path):
        kb_dir = tmp_path / "knowledge"
        kb_dir.mkdir()
        faq = kb_dir / "faq.md"
        faq.write_text(
            "---\ntitle: FAQ\ncategory: faq\n---\n\n"
            "## How to reset?\n\nGo to Settings > Reset.\n"
        )
        engine.ingest_file(faq)
        assert engine.doc_count() == 1

        # Modify the file content
        faq.write_text(
            "---\ntitle: FAQ\ncategory: faq\n---\n\n"
            "## How to reset?\n\nUse the new Reset Wizard in Settings > Advanced > Reset.\n"
        )
        engine.update_file(faq)

        results = engine.search("Reset Wizard")
        assert any("Reset Wizard" in r.content for r in results)
        assert engine.doc_count() == 1

    def test_update_file_handles_structural_change(self, engine: KnowledgeEngine, tmp_path: Path):
        kb_dir = tmp_path / "knowledge"
        kb_dir.mkdir()
        guide = kb_dir / "guide.md"
        guide.write_text(
            "---\ntitle: Guide\ncategory: troubleshooting\n---\n\n"
            "## Step One\n\nDo step one.\n\n"
            "## Step Two\n\nDo step two.\n"
        )
        engine.ingest_file(guide)
        assert engine.doc_count() == 2

        # Change structure: remove one section, add two new ones
        guide.write_text(
            "---\ntitle: Guide\ncategory: troubleshooting\n---\n\n"
            "## Step One\n\nDo step one revised.\n\n"
            "## Step Three\n\nBrand new step three.\n\n"
            "## Step Four\n\nBrand new step four.\n"
        )
        engine.update_file(guide)
        assert engine.doc_count() == 3

        # Old orphan "Step Two" should be gone
        results = engine.search("Do step two", top_k=5)
        for r in results:
            assert "Do step two." not in r.content

    def test_update_directory(self, engine: KnowledgeEngine, tmp_path: Path):
        kb_dir = tmp_path / "knowledge"
        kb_dir.mkdir()
        (kb_dir / "a.md").write_text(
            "---\ntitle: A\ncategory: faq\n---\n\n## Section A\n\nContent A.\n"
        )
        (kb_dir / "b.md").write_text(
            "---\ntitle: B\ncategory: faq\n---\n\n## Section B\n\nContent B.\n"
        )
        engine.ingest_directory(kb_dir)
        assert engine.doc_count() == 2

        # Modify one file
        (kb_dir / "a.md").write_text(
            "---\ntitle: A\ncategory: faq\n---\n\n## Section A\n\nUpdated Content A.\n"
        )
        engine.update_directory(kb_dir)

        results = engine.search("Updated Content A")
        assert any("Updated" in r.content for r in results)
        assert engine.doc_count() == 2
