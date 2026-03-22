"""Load and chunk knowledge documents from Markdown files."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path

from src.core.models import KnowledgeCategory, KnowledgeDoc


class KnowledgeLoader:
    """Loads Markdown files and splits them into searchable chunks by H2 heading."""

    def load_file(self, file_path: Path) -> list[KnowledgeDoc]:
        if not file_path.exists():
            raise FileNotFoundError(f"Knowledge file not found: {file_path}")

        text = file_path.read_text(encoding="utf-8")
        frontmatter, body = self._parse_frontmatter(text)
        title = frontmatter.get("title", file_path.stem)
        category = self._parse_category(frontmatter.get("category", "faq"))

        chunks = self._split_by_h2(body)
        docs = []
        for i, (section_title, section_content) in enumerate(chunks):
            doc_id = self._make_id(str(file_path), i)
            docs.append(
                KnowledgeDoc(
                    id=doc_id,
                    title=section_title or title,
                    content=section_content.strip(),
                    category=category,
                    source_file=str(file_path),
                    metadata={"parent_title": title, "chunk_index": i},
                    last_updated=datetime.fromtimestamp(file_path.stat().st_mtime),
                )
            )
        return docs

    def load_directory(self, dir_path: Path) -> list[KnowledgeDoc]:
        if not dir_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {dir_path}")

        docs = []
        for md_file in sorted(dir_path.glob("*.md")):
            docs.extend(self.load_file(md_file))
        return docs

    def _parse_frontmatter(self, text: str) -> tuple[dict, str]:
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", text, re.DOTALL)
        if not match:
            return {}, text

        frontmatter_str = match.group(1)
        body = match.group(2)

        frontmatter = {}
        for line in frontmatter_str.strip().split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                frontmatter[key.strip()] = value.strip()

        return frontmatter, body

    def _split_by_h2(self, text: str) -> list[tuple[str, str]]:
        pattern = r"^## (.+)$"
        sections: list[tuple[str, str]] = []
        parts = re.split(pattern, text, flags=re.MULTILINE)

        # parts[0] is text before first H2 (usually empty)
        # then alternating: title, content, title, content, ...
        if len(parts) < 3:
            # No H2 sections found, return whole text
            if text.strip():
                return [("", text)]
            return []

        for i in range(1, len(parts), 2):
            title = parts[i].strip()
            content = parts[i + 1] if i + 1 < len(parts) else ""
            sections.append((title, content))

        return sections

    def _parse_category(self, value: str) -> KnowledgeCategory:
        try:
            return KnowledgeCategory(value)
        except ValueError:
            return KnowledgeCategory.FAQ

    def _make_id(self, file_path: str, chunk_index: int) -> str:
        raw = f"{file_path}::{chunk_index}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
