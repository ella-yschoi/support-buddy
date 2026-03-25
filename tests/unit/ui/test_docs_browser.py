"""Tests for the documentation browser module."""

from pathlib import Path

import pytest

from src.ui.docs_browser import _parse_frontmatter, load_doc_index, load_doc_content


class TestParseFrontmatter:
    def test_parses_valid_frontmatter(self):
        text = "---\ntitle: My Doc\ncategory: faq\n---\nBody here"
        result = _parse_frontmatter(text)
        assert result == {"title": "My Doc", "category": "faq"}

    def test_returns_empty_dict_when_no_frontmatter(self):
        text = "Just some markdown content\nNo frontmatter here."
        result = _parse_frontmatter(text)
        assert result == {}

    def test_returns_empty_dict_for_empty_string(self):
        result = _parse_frontmatter("")
        assert result == {}

    def test_handles_extra_fields(self):
        text = "---\ntitle: Guide\ncategory: runbook\nauthor: Alice\n---\nContent"
        result = _parse_frontmatter(text)
        assert result["title"] == "Guide"
        assert result["category"] == "runbook"
        assert result["author"] == "Alice"


class TestLoadDocIndex:
    def test_loads_docs_from_directory(self, tmp_path: Path):
        doc1 = tmp_path / "faq.md"
        doc1.write_text("---\ntitle: FAQ\ncategory: faq\n---\nContent")
        doc2 = tmp_path / "runbook.md"
        doc2.write_text("---\ntitle: Runbook\ncategory: runbook\n---\nContent")

        docs = load_doc_index(tmp_path)
        assert len(docs) == 2
        titles = {d.title for d in docs}
        assert titles == {"FAQ", "Runbook"}

    def test_empty_directory(self, tmp_path: Path):
        docs = load_doc_index(tmp_path)
        assert docs == []

    def test_nonexistent_directory(self, tmp_path: Path):
        missing = tmp_path / "nonexistent"
        docs = load_doc_index(missing)
        assert docs == []

    def test_fallback_title_when_no_frontmatter(self, tmp_path: Path):
        doc = tmp_path / "plain_doc.md"
        doc.write_text("# Just markdown, no frontmatter")

        docs = load_doc_index(tmp_path)
        assert len(docs) == 1
        assert docs[0].title == "plain_doc"
        assert docs[0].category == "Uncategorized"

    def test_sorted_by_category_then_title(self, tmp_path: Path):
        (tmp_path / "b.md").write_text("---\ntitle: Beta\ncategory: runbook\n---\n")
        (tmp_path / "a.md").write_text("---\ntitle: Alpha\ncategory: faq\n---\n")
        (tmp_path / "c.md").write_text("---\ntitle: Charlie\ncategory: faq\n---\n")

        docs = load_doc_index(tmp_path)
        categories = [d.category for d in docs]
        assert categories == ["faq", "faq", "runbook"]
        faq_titles = [d.title for d in docs if d.category == "faq"]
        assert faq_titles == ["Alpha", "Charlie"]


class TestLoadDocContent:
    def test_returns_frontmatter_and_body(self, tmp_path: Path):
        doc = tmp_path / "test.md"
        doc.write_text("---\ntitle: Test Doc\ncategory: faq\n---\n\nThis is the body.")

        fm, body = load_doc_content(doc)
        assert fm["title"] == "Test Doc"
        assert "This is the body." in body

    def test_returns_empty_frontmatter_when_missing(self, tmp_path: Path):
        doc = tmp_path / "plain.md"
        doc.write_text("# No frontmatter\n\nJust content.")

        fm, body = load_doc_content(doc)
        assert fm == {}
        assert "No frontmatter" in body

    def test_body_excludes_frontmatter(self, tmp_path: Path):
        doc = tmp_path / "test.md"
        doc.write_text("---\ntitle: Doc\ncategory: faq\n---\n\nBody only.")

        fm, body = load_doc_content(doc)
        assert "---" not in body
        assert "title:" not in body
