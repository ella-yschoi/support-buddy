"""Tests for knowledge document loader."""

from pathlib import Path

import pytest

from src.core.knowledge.loader import KnowledgeLoader


class TestKnowledgeLoader:
    def test_load_markdown_file_extracts_frontmatter(self, sample_knowledge_dir: Path):
        loader = KnowledgeLoader()
        docs = loader.load_file(sample_knowledge_dir / "faq.md")

        assert len(docs) > 0
        # Each chunk title is the H2 heading; parent_title in metadata holds frontmatter title
        assert docs[0].metadata["parent_title"] == "CloudSync FAQ"
        assert docs[0].category.value == "faq"
        assert docs[0].source_file == str(sample_knowledge_dir / "faq.md")

    def test_load_markdown_chunks_by_h2(self, sample_knowledge_dir: Path):
        loader = KnowledgeLoader()
        docs = loader.load_file(sample_knowledge_dir / "faq.md")

        # faq.md has 2 H2 sections
        assert len(docs) == 2
        assert docs[0].title == "How do I reset my sync?"
        assert docs[1].title == "What file types are supported?"

    def test_load_directory(self, sample_knowledge_dir: Path):
        loader = KnowledgeLoader()
        docs = loader.load_directory(sample_knowledge_dir)

        # faq (2) + error_codes (2) + troubleshooting (2) = 6
        assert len(docs) == 6

    def test_load_nonexistent_file_raises(self):
        loader = KnowledgeLoader()
        with pytest.raises(FileNotFoundError):
            loader.load_file(Path("/nonexistent/file.md"))

    def test_chunk_preserves_section_title(self, sample_knowledge_dir: Path):
        loader = KnowledgeLoader()
        docs = loader.load_file(sample_knowledge_dir / "error_codes.md")

        assert docs[0].title == "SYNC-001: File Conflict"
        assert docs[1].title == "SYNC-002: Upload Failed"

    def test_each_chunk_has_unique_id(self, sample_knowledge_dir: Path):
        loader = KnowledgeLoader()
        docs = loader.load_directory(sample_knowledge_dir)
        ids = [d.id for d in docs]
        assert len(ids) == len(set(ids))
