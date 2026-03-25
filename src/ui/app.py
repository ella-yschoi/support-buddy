"""Streamlit Web UI for Support Buddy."""

# Streamlit Cloud ships an old SQLite; swap in pysqlite3 before chromadb loads.
try:
    __import__("pysqlite3")
    import sys
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except ImportError:
    pass

import tempfile
from pathlib import Path

import streamlit as st
import pandas as pd

from src.config import ANTHROPIC_API_KEY, KNOWLEDGE_DIR
from src.core.analyzer.inquiry import InquiryAnalyzer
from src.core.analyzer.log_parser import LogParser
from src.core.knowledge.engine import KnowledgeEngine
from src.integrations.email.parser import EmailParser

st.set_page_config(page_title="Support Buddy", page_icon="🎧", layout="wide")

# Use a fixed temp directory so ChromaDB persists across Streamlit reruns
_CHROMA_DIR = str(Path(tempfile.gettempdir()) / "support_buddy_chroma")

# Page config
_PAGES = {
    "Inquiry Analysis": {"icon": "🔍", "desc": "Analyze customer inquiries"},
    "Log Analysis": {"icon": "📊", "desc": "Parse and visualize logs"},
    "Email Analysis": {"icon": "📧", "desc": "Parse incoming emails"},
    "Knowledge Search": {"icon": "📚", "desc": "Search the knowledge base"},
}

_SEVERITY_STYLES = {
    "critical": ("🔴", "#ff4b4b"),
    "high": ("🟠", "#ff8c00"),
    "medium": ("🟡", "#ffc107"),
    "low": ("🟢", "#28a745"),
}


@st.cache_resource
def get_engine():
    engine = KnowledgeEngine(persist_dir=_CHROMA_DIR)
    if KNOWLEDGE_DIR.is_dir() and engine.doc_count() == 0:
        engine.ingest_directory(KNOWLEDGE_DIR)
    return engine


def render_sidebar():
    with st.sidebar:
        st.markdown(
            "<h1 style='text-align:center;'>🎧 Support Buddy</h1>"
            "<p style='text-align:center; color:gray; margin-top:-10px;'>"
            "AI-powered support tool</p>",
            unsafe_allow_html=True,
        )
        st.divider()

        # Navigation buttons
        if "page" not in st.session_state:
            st.session_state.page = "Inquiry Analysis"

        for page_name, info in _PAGES.items():
            is_active = st.session_state.page == page_name
            btn_type = "primary" if is_active else "secondary"
            if st.button(
                f"{info['icon']}  {page_name}",
                key=f"nav_{page_name}",
                use_container_width=True,
                type=btn_type,
            ):
                st.session_state.page = page_name
                st.rerun()

        st.divider()

        # Status
        engine = get_engine()
        col1, col2 = st.columns(2)
        col1.metric("KB Docs", engine.doc_count())
        has_ai = bool(ANTHROPIC_API_KEY)
        col2.metric("AI", "ON" if has_ai else "OFF")

    return st.session_state.page


def _severity_badge(severity: str) -> str:
    icon, color = _SEVERITY_STYLES.get(severity, ("⚪", "#888"))
    return f"<span style='background:{color}; color:white; padding:4px 12px; border-radius:12px; font-weight:bold;'>{icon} {severity.upper()}</span>"


def _render_analysis_results(result, show_draft_button=False, inquiry=""):
    """Shared result display for inquiry and email analysis."""
    severity = result.severity.value
    sev_icon, sev_color = _SEVERITY_STYLES.get(severity, ("⚪", "#888"))

    # Header metrics
    col1, col2, col3 = st.columns(3)
    col1.markdown(
        f"<div style='text-align:center;'>"
        f"<div style='font-size:0.85em; color:gray;'>Category</div>"
        f"<div style='font-size:1.5em; font-weight:bold;'>{result.category.value.upper()}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    col2.markdown(
        f"<div style='text-align:center;'>"
        f"<div style='font-size:0.85em; color:gray;'>Severity</div>"
        f"<div style='font-size:1.5em;'>{_severity_badge(severity)}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    col3.markdown(
        f"<div style='text-align:center;'>"
        f"<div style='font-size:0.85em; color:gray;'>Confidence</div>"
        f"<div style='font-size:1.5em; font-weight:bold;'>{result.confidence:.0%}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.markdown("")
    st.info(f"**Summary:** {result.summary}")

    # Checklist + Follow-up side by side
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("#### ✅ Checklist")
        for i, item in enumerate(result.checklist):
            st.checkbox(item, key=f"chk_{id(result)}_{i}")

    with col_right:
        st.markdown("#### 💬 Follow-up Questions")
        for q in result.follow_up_questions:
            st.markdown(f"- {q}")

    # Relevant articles
    if result.relevant_articles:
        st.markdown("#### 📄 Relevant Knowledge Base Articles")
        articles_data = []
        for a in result.relevant_articles:
            score_pct = f"{a.score:.0%}"
            articles_data.append({
                "Title": a.title,
                "Category": a.category,
                "Relevance": score_pct,
            })
        st.dataframe(
            pd.DataFrame(articles_data),
            use_container_width=True,
            hide_index=True,
        )

        with st.expander("View article details"):
            for a in result.relevant_articles:
                st.markdown(f"**{a.title}** `{a.category}`")
                st.markdown(a.content[:500])
                st.divider()

    if result.confidence < 0.6:
        st.warning("⚠️ Low confidence — consider escalating to a senior TSE.")

    # Draft response button
    if show_draft_button and ANTHROPIC_API_KEY and inquiry:
        st.divider()
        if st.button("✉️ Generate Response Draft", type="primary"):
            from src.core.responder.drafter import ResponseDrafter
            engine = get_engine()
            with st.spinner("Generating draft..."):
                drafter = ResponseDrafter(engine)
                response = drafter.draft(inquiry, result)

            st.markdown("#### ✉️ Draft Response")
            st.text_area("Response body", value=response.body, height=200, label_visibility="collapsed")

            col1, col2 = st.columns(2)
            col1.metric("Draft Confidence", f"{response.confidence:.0%}")
            if response.needs_escalation:
                col2.error("🚨 Escalation Recommended")
            else:
                col2.success("✅ No Escalation Needed")

            if response.suggested_internal_note:
                with st.expander("🔒 Internal Note (not sent to customer)"):
                    st.write(response.suggested_internal_note)


def render_inquiry_analysis():
    st.markdown("## 🔍 Inquiry Analysis")
    st.caption("Paste a customer inquiry to get instant classification, checklist, and relevant articles.")

    use_ai = False
    if ANTHROPIC_API_KEY:
        use_ai = st.toggle("⚡ Use AI (Claude)", value=False, help="Uses Haiku for classification. Costs ~$0.003/request.")

    inquiry = st.text_area(
        "Customer Inquiry",
        height=150,
        placeholder="e.g., My files are not syncing between my Mac and Windows laptop. I see SYNC-002 error...",
        label_visibility="collapsed",
    )

    if st.button("Analyze", type="primary", disabled=not inquiry, use_container_width=True):
        engine = get_engine()

        with st.spinner("Analyzing inquiry..."):
            if use_ai:
                from src.core.analyzer.ai_inquiry import AIInquiryAnalyzer
                analyzer = AIInquiryAnalyzer(engine)
                result = analyzer.analyze(inquiry)
            else:
                analyzer = InquiryAnalyzer(engine)
                result = analyzer.classify(inquiry)

        st.divider()
        _render_analysis_results(result, show_draft_button=use_ai, inquiry=inquiry)


def render_log_analysis():
    st.markdown("## 📊 Log Analysis")
    st.caption("Paste logs or upload a log file to get parsed insights and visualizations.")

    use_ai = False
    if ANTHROPIC_API_KEY:
        use_ai = st.toggle("⚡ Use AI (Claude)", value=False, key="log_ai", help="Uses Sonnet for deep analysis. Costs ~$0.017/request.")

    tab_paste, tab_upload = st.tabs(["📋 Paste Logs", "📁 Upload File"])

    raw_logs = ""
    with tab_paste:
        raw_logs = st.text_area(
            "Log content",
            height=200,
            placeholder='[{"timestamp": "2024-01-15T10:00:00Z", "level": "ERROR", "message": "..."}]',
            label_visibility="collapsed",
        )

    with tab_upload:
        uploaded = st.file_uploader("Upload log file", type=["json", "log", "txt"])
        if uploaded:
            raw_logs = uploaded.read().decode("utf-8")
            st.code(raw_logs[:500] + ("..." if len(raw_logs) > 500 else ""), language="json")

    if st.button("Analyze Logs", type="primary", disabled=not raw_logs, use_container_width=True):
        parser = LogParser()
        events = parser.parse(raw_logs)

        if not events:
            st.error("No log events could be parsed from the input.")
            return

        st.divider()

        # AI insights first
        if use_ai:
            engine = get_engine()
            from src.core.analyzer.log_analyzer import AILogAnalyzer
            with st.spinner("AI analyzing logs..."):
                ai_analyzer = AILogAnalyzer(engine)
                insight = ai_analyzer.analyze(raw_logs)

            st.markdown("#### 🤖 AI Insights")
            st.info(f"**Summary:** {insight.summary}")
            st.warning(f"**Root Cause Hypothesis:** {insight.root_cause_hypothesis}")

            if insight.anomalies:
                with st.expander("⚠️ Anomalies Detected", expanded=True):
                    for a in insight.anomalies:
                        st.markdown(f"- {a}")
            st.divider()

        # Metrics
        errors = parser.extract_errors(events)
        slow_ops = parser.extract_slow_operations(events)

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Events", len(events))
        col2.metric("Errors", len(errors), delta=f"{len(errors)} found", delta_color="inverse")
        col3.metric("Slow Ops", len(slow_ops))

        # Level distribution chart
        st.markdown("#### Event Level Distribution")
        level_counts = {}
        for e in events:
            level_counts[e.level] = level_counts.get(e.level, 0) + 1

        chart_df = pd.DataFrame({
            "Level": list(level_counts.keys()),
            "Count": list(level_counts.values()),
        }).set_index("Level")
        st.bar_chart(chart_df)

        # Error details
        if errors:
            st.markdown("#### 🔴 Errors")
            error_data = [{"Timestamp": e.timestamp, "Message": e.message} for e in errors]
            st.dataframe(pd.DataFrame(error_data), use_container_width=True, hide_index=True)

        # Slow operations
        if slow_ops:
            st.markdown("#### 🐢 Slow Operations")
            slow_data = [
                {"Timestamp": s.timestamp, "Message": s.message, "Duration (ms)": s.metadata.get("duration_ms", "?")}
                for s in slow_ops
            ]
            st.dataframe(pd.DataFrame(slow_data), use_container_width=True, hide_index=True)

        # Error code reference
        error_codes = parser.extract_error_codes(events)
        if error_codes:
            engine = get_engine()
            st.markdown("#### 📖 Error Code Reference")
            for code in error_codes:
                results = engine.search(code, top_k=1, category="error_code")
                if results:
                    with st.expander(f"`{code}` — {results[0].title}"):
                        st.markdown(results[0].content)

        # Raw summary
        with st.expander("📝 Raw Text Summary"):
            st.code(parser.generate_text_summary(events))


def render_email_analysis():
    st.markdown("## 📧 Email Analysis")
    st.caption("Paste a raw customer email to automatically parse and analyze the inquiry.")

    raw_email = st.text_area(
        "Raw Email",
        height=250,
        placeholder="From: customer@example.com\nTo: support@cloudsync.io\nSubject: Files not syncing\n\nHi, my files are...",
        label_visibility="collapsed",
    )

    if st.button("Parse & Analyze", type="primary", disabled=not raw_email, use_container_width=True):
        email_parser = EmailParser()
        parsed = email_parser.parse(raw_email)

        st.divider()

        # Email metadata
        st.markdown("#### 📬 Parsed Email")
        col1, col2, col3 = st.columns(3)
        col1.metric("Sender", parsed.sender or "Unknown")
        col2.metric("Subject", parsed.subject[:30] + "..." if len(parsed.subject) > 30 else parsed.subject or "None")
        col3.metric("Error Codes", ", ".join(parsed.error_codes) or "None")

        with st.expander("View email body", expanded=False):
            st.text(parsed.body)

        if parsed.body:
            engine = get_engine()
            analyzer = InquiryAnalyzer(engine)
            result = analyzer.classify(parsed.to_inquiry_text())

            st.divider()
            st.markdown("#### 📋 Analysis Results")
            _render_analysis_results(result)


def render_knowledge_search():
    st.markdown("## 📚 Knowledge Search")
    st.caption("Search the knowledge base using natural language. No exact keywords needed.")

    query = st.text_input(
        "Search",
        placeholder="e.g., SYNC-002, webhook not firing, how to enable delta sync, SSO login failure...",
        label_visibility="collapsed",
    )

    col1, col2 = st.columns(2)
    category_options = ["All Categories", "faq", "troubleshooting", "error_code", "runbook", "feature"]
    category_display = ["🗂️ All Categories", "❓ FAQ", "🔧 Troubleshooting", "⚠️ Error Codes", "📋 Runbooks", "⭐ Features"]
    selected_idx = col1.selectbox("Category", range(len(category_options)), format_func=lambda i: category_display[i])
    category = None if selected_idx == 0 else category_options[selected_idx]
    top_k = col2.slider("Max results", 1, 20, 5)

    if query:
        engine = get_engine()
        results = engine.search(query, top_k=top_k, category=category)

        if not results:
            st.warning("No results found. Try different keywords.")
        else:
            st.markdown(f"**{len(results)} result(s) found**")
            for r in results:
                relevance = f"{r.score:.0%}"
                with st.expander(f"**{r.title}**  `{r.category}` — relevance: {relevance}"):
                    st.markdown(r.content)


def main():
    page = render_sidebar()

    if page == "Inquiry Analysis":
        render_inquiry_analysis()
    elif page == "Log Analysis":
        render_log_analysis()
    elif page == "Email Analysis":
        render_email_analysis()
    elif page == "Knowledge Search":
        render_knowledge_search()


if __name__ == "__main__":
    main()
