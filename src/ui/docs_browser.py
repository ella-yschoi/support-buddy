"""Documentation browser page - browse and read knowledge base articles."""

from dataclasses import dataclass
from pathlib import Path

import streamlit as st

from src.config import KNOWLEDGE_DIR
from src.ui.styles import (
    page_header,
    section_header,
    doc_card,
    doc_detail_header,
    PRIMARY,
    ERROR,
    TERTIARY,
    SECONDARY,
)


@dataclass
class DocInfo:
    title: str
    category: str
    filename: str
    file_path: Path


_CATEGORY_ACCENT = {
    "faq": PRIMARY,
    "troubleshooting": ERROR,
    "error_code": ERROR,
    "runbook": TERTIARY,
    "feature": SECONDARY,
}


def _parse_frontmatter(text: str) -> dict:
    """Parse YAML frontmatter from a Markdown string into a dict."""
    if not text.startswith("---"):
        return {}
    end = text.find("---", 3)
    if end == -1:
        return {}
    block = text[3:end].strip()
    result: dict[str, str] = {}
    for line in block.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()
    return result


def load_doc_index(knowledge_dir: Path) -> list[DocInfo]:
    """Scan a directory for *.md files and return a sorted list of DocInfo."""
    if not knowledge_dir.is_dir():
        return []

    docs: list[DocInfo] = []
    for md_file in sorted(knowledge_dir.glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        fm = _parse_frontmatter(text)
        title = fm.get("title") or md_file.stem
        category = fm.get("category") or "Uncategorized"
        docs.append(
            DocInfo(
                title=title,
                category=category,
                filename=md_file.name,
                file_path=md_file,
            )
        )

    docs.sort(key=lambda d: (d.category, d.title))
    return docs


def load_doc_content(file_path: Path) -> tuple[dict, str]:
    """Read a Markdown file and return (frontmatter_dict, body_str)."""
    text = file_path.read_text(encoding="utf-8")
    fm = _parse_frontmatter(text)

    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            body = text[end + 3:].lstrip("\n")
            return fm, body

    return fm, text


# ---------------------------------------------------------------------------
# Streamlit rendering
# ---------------------------------------------------------------------------


def render_documentation() -> None:
    """Entry point: dispatch between list view and detail view."""
    selected = st.session_state.get("docs_selected_file")
    if selected:
        _render_doc_detail(Path(selected))
    else:
        _render_doc_list()


def _render_doc_list() -> None:
    """Render the documentation index with category grouping and filter."""
    page_header("Documentation", "Browse internal knowledge base articles")

    docs = load_doc_index(KNOWLEDGE_DIR)
    if not docs:
        st.info("No documentation files found.")
        return

    # Category filter
    all_categories = sorted({d.category for d in docs})
    filter_options = ["All Categories"] + all_categories
    selected_filter = st.selectbox("Filter by category", filter_options, label_visibility="collapsed")

    if selected_filter != "All Categories":
        docs = [d for d in docs if d.category == selected_filter]

    # Group by category
    grouped: dict[str, list[DocInfo]] = {}
    for doc in docs:
        grouped.setdefault(doc.category, []).append(doc)

    for category, category_docs in grouped.items():
        accent = _CATEGORY_ACCENT.get(category.lower(), SECONDARY)
        section_header(category.replace("_", " ").title())

        # 3-column grid
        for row_start in range(0, len(category_docs), 3):
            cols = st.columns(3)
            for i, col in enumerate(cols):
                idx = row_start + i
                if idx >= len(category_docs):
                    break
                doc = category_docs[idx]
                with col:
                    st.markdown(
                        f'<div class="doc-card-click">'
                        f'{doc_card(doc.title, doc.category, doc.filename, accent)}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        doc.title,
                        key=f"doc_{doc.filename}",
                        use_container_width=True,
                    ):
                        st.session_state.docs_selected_file = str(doc.file_path)
                        st.rerun()


def _render_doc_detail(file_path: Path) -> None:
    """Render full document content with a back button."""
    if st.button("Back to Documentation", icon=":material/arrow_back:"):
        st.session_state.pop("docs_selected_file", None)
        st.rerun()

    fm, body = load_doc_content(file_path)
    title = fm.get("title", file_path.stem)
    category = fm.get("category", "Uncategorized")
    accent = _CATEGORY_ACCENT.get(category.lower(), SECONDARY)

    doc_detail_header(title, category, file_path.name, accent)
    st.markdown(body)
