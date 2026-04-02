"""Streamlit Web UI for Support Buddy."""

# Ensure project root is on sys.path so "from src.…" imports work on Streamlit Cloud.
import sys
from pathlib import Path as _Path

_project_root = str(_Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Streamlit Cloud ships an old SQLite; swap in pysqlite3 before chromadb loads.
try:
    __import__("pysqlite3")
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except ImportError:
    pass

import tempfile
from pathlib import Path

import streamlit as st
import pandas as pd

import altair as alt

from src.config import ANTHROPIC_API_KEY, KNOWLEDGE_DIR
from src.core.analyzer.inquiry import InquiryAnalyzer
from src.core.analyzer.log_parser import LogParser
from src.core.knowledge.engine import KnowledgeEngine
from src.integrations.email.parser import EmailParser
import base64 as _b64

from src.ui.docs_browser import render_documentation
from src.ui.styles import (
    inject_global_css,
    inject_material_icons,
    page_header,
    metric_card,
    insight_card,
    section_header,
    search_result_card,
    severity_chip,
    status_bar,
    action_card,
    PRIMARY,
    PRIMARY_CONTAINER,
    ERROR,
    TERTIARY,
    SECONDARY,
    ON_SURFACE,
    SURFACE_CONTAINER_LOW,
)

_LOGO_PATH = Path(__file__).parent / "static" / "logo.png"
st.set_page_config(
    page_title="Support Buddy",
    page_icon=str(_LOGO_PATH),
    layout="wide",
)

# OG meta tags for social media link previews (LinkedIn, Twitter, etc.)
_OG_IMAGE = "https://raw.githubusercontent.com/ella-yschoi/support-buddy/main/docs/images/log-analysis-charts.png"
st.markdown(
    f"""
    <meta property="og:title" content="Support Buddy" />
    <meta property="og:description" content="AI-powered support tool that helps Technical Support Engineers handle customer inquiries faster and more accurately." />
    <meta property="og:image" content="{_OG_IMAGE}" />
    <meta property="og:url" content="https://support-buddy.streamlit.app/" />
    <meta property="og:type" content="website" />
    <meta name="twitter:card" content="summary_large_image" />
    """,
    unsafe_allow_html=True,
)

# Use a fixed temp directory so ChromaDB persists across Streamlit reruns
_CHROMA_DIR = str(Path(tempfile.gettempdir()) / "support_buddy_chroma")

# Page config - icon uses Streamlit's :material/ syntax
_PAGES = {
    "Inquiry Analysis": {"desc": "Analyze customer inquiries", "icon": ":material/analytics:"},
    "Log Analysis": {"desc": "Parse and visualize logs", "icon": ":material/terminal:"},
    "Email Analysis": {"desc": "Parse incoming emails", "icon": ":material/mail_lock:"},
    "Knowledge Search": {"desc": "Search the knowledge base", "icon": ":material/manage_search:"},
}

_SEVERITY_ACCENT = {
    "critical": ERROR,
    "high": "#ff8c00",
    "medium": "#ffc107",
    "low": "#28a745",
}


def build_timeline_df(events: list) -> pd.DataFrame | None:
    """Convert LogEvent list to a DataFrame for timeline charting.

    Returns None if no events have valid timestamps.
    """
    if not events:
        return None

    rows = []
    for e in events:
        if not e.timestamp:
            continue
        ts = pd.to_datetime(e.timestamp, errors="coerce")
        if pd.isna(ts):
            continue
        rows.append({"timestamp": ts, "level": e.level, "message": e.message})

    if not rows:
        return None

    return pd.DataFrame(rows)


@st.cache_resource
def get_engine():
    engine = KnowledgeEngine(persist_dir=_CHROMA_DIR)
    if KNOWLEDGE_DIR.is_dir() and engine.doc_count() == 0:
        engine.ingest_directory(KNOWLEDGE_DIR)
    return engine


def render_sidebar():
    with st.sidebar:
        # Branding - logo with icon
        _logo_b64 = _b64.b64encode(_LOGO_PATH.read_bytes()).decode()
        st.markdown(
            f"""
            <div style="display:flex; align-items:center; gap:0.6rem;
                        margin-bottom:1.5rem; padding:0 0.25rem;">
                <img src="data:image/png;base64,{_logo_b64}"
                     style="width:40px; height:40px; border-radius:6px;"
                     alt="Support Buddy logo" />
                <h1 style="font-family:Manrope,sans-serif; font-size:1.7rem;
                           font-weight:900; color:#191c1e;
                           letter-spacing:-0.03em; margin:0;">
                    Support Buddy
                </h1>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Navigation
        if "page" not in st.session_state:
            st.session_state.page = "Inquiry Analysis"

        for page_name, info in _PAGES.items():
            btn_type = "primary" if st.session_state.page == page_name else "secondary"
            if st.button(
                page_name,
                key=f"nav_{page_name}",
                use_container_width=True,
                type=btn_type,
                icon=info["icon"],
            ):
                st.session_state.page = page_name
                st.rerun()

        # Bottom section - wrapped in st.container() so its primary button
        # gets a nested stVerticalBlock, allowing CSS to distinguish it
        # from the nav-active primary buttons above.
        with st.container():
            if st.button(
                "Documentation",
                key="nav_docs",
                use_container_width=True,
                type="secondary",
                icon=":material/library_books:",
            ):
                st.session_state.page = "Documentation"
                st.session_state.pop("docs_selected_file", None)
                st.rerun()

            engine = get_engine()
            has_ai = bool(ANTHROPIC_API_KEY)
            status_bar(engine.doc_count(), "ON" if has_ai else "OFF")

            if KNOWLEDGE_DIR.is_dir():
                st.markdown(
                    '<div style="margin-top:0.75rem;"></div>',
                    unsafe_allow_html=True,
                )
                if st.button("Refresh Docs", use_container_width=True, type="primary"):
                    get_engine.clear()
                    fresh_engine = get_engine()
                    with st.spinner("Updating knowledge base..."):
                        count = fresh_engine.update_directory(KNOWLEDGE_DIR)
                    st.session_state["kb_refreshed"] = count
                    st.rerun()

                if st.session_state.get("kb_refreshed") is not None:
                    st.success(f"Docs refreshed - {st.session_state.pop('kb_refreshed')} chunks")

    return st.session_state.page


def _render_analysis_results(result, show_draft_button=False, inquiry=""):
    """Shared result display for inquiry and email analysis."""
    severity = result.severity.value
    sev_accent = _SEVERITY_ACCENT.get(severity, SECONDARY)

    # Metric cards
    col1, col2, col3 = st.columns(3)
    col1.markdown(
        metric_card("Category", result.category.value.upper(), PRIMARY),
        unsafe_allow_html=True,
    )
    col2.markdown(
        metric_card(
            "Severity",
            f'{severity_chip(severity)} {severity.upper()}',
            sev_accent,
        ),
        unsafe_allow_html=True,
    )
    col3.markdown(
        metric_card("Confidence", f"{result.confidence:.0%}", TERTIARY),
        unsafe_allow_html=True,
    )

    # AI Summary
    insight_card("AI Summary", result.summary)

    # Checklist + Follow-up side by side
    col_left, col_right = st.columns(2)

    with col_left:
        action_card("Checklist", result.checklist)

    with col_right:
        action_card("Follow-up Questions", result.follow_up_questions)

    # Relevant articles
    if result.relevant_articles:
        section_header("Relevant Articles")
        for a in result.relevant_articles:
            score_pct = f"{a.score:.0%}"
            # Choose accent color based on category
            cat_accent_map = {
                "faq": PRIMARY,
                "troubleshooting": ERROR,
                "error_code": ERROR,
                "runbook": TERTIARY,
                "feature": SECONDARY,
            }
            accent = cat_accent_map.get(a.category.lower(), PRIMARY) if a.category else PRIMARY
            search_result_card(
                title=a.title,
                category=a.category,
                relevance=score_pct,
                content=a.content[:500],
                accent_color=accent,
            )

    if result.confidence < 0.6:
        st.warning("Low confidence - consider escalating to a senior TSE.")

    # Draft response button
    if show_draft_button and ANTHROPIC_API_KEY and inquiry:
        st.markdown('<div style="margin:2.25rem 0;"></div>', unsafe_allow_html=True)
        if st.button("Generate Response Draft", type="primary"):
            from src.core.responder.drafter import ResponseDrafter
            engine = get_engine()
            with st.spinner("Generating draft..."):
                drafter = ResponseDrafter(engine)
                response = drafter.draft(inquiry, result)

            section_header("Draft Response")
            st.text_area("Response body", value=response.body, height=200, label_visibility="collapsed")

            col1, col2 = st.columns(2)
            col1.markdown(
                metric_card("Draft Confidence", f"{response.confidence:.0%}", PRIMARY),
                unsafe_allow_html=True,
            )
            if response.needs_escalation:
                col2.markdown(
                    metric_card("Escalation", "Recommended", ERROR),
                    unsafe_allow_html=True,
                )
            else:
                col2.markdown(
                    metric_card("Escalation", "Not Needed", "#28a745"),
                    unsafe_allow_html=True,
                )

            if response.suggested_internal_note:
                with st.expander("Internal Note (not sent to customer)"):
                    st.write(response.suggested_internal_note)


def render_inquiry_analysis():
    page_header("Inquiry Analysis", "Autonomous NLP processing and sentiment clustering")

    use_ai = False
    if ANTHROPIC_API_KEY:
        use_ai = st.toggle("Use AI (Claude)", value=False, help="Uses Haiku for classification. Costs ~$0.003/request.")

    inquiry = st.text_area(
        "Customer Inquiry",
        height=150,
        placeholder="e.g., My files are not syncing between my Mac and Windows laptop. I see SYNC-002 error...",
        label_visibility="collapsed",
    )

    if st.button("Analyze", type="primary", disabled=not inquiry):
        engine = get_engine()

        with st.spinner("Analyzing inquiry..."):
            if use_ai:
                from src.core.analyzer.ai_inquiry import AIInquiryAnalyzer
                analyzer = AIInquiryAnalyzer(engine)
                result = analyzer.analyze(inquiry)
            else:
                analyzer = InquiryAnalyzer(engine)
                result = analyzer.classify(inquiry)

        st.markdown('<div style="margin:2.25rem 0;"></div>', unsafe_allow_html=True)
        _render_analysis_results(result, show_draft_button=use_ai, inquiry=inquiry)


def render_log_analysis():
    page_header("Log Diagnostics", "Session trace analysis")

    use_ai = False
    if ANTHROPIC_API_KEY:
        use_ai = st.toggle("Use AI (Claude)", value=False, key="log_ai", help="Uses Sonnet for deep analysis. Costs ~$0.017/request.")

    tab_paste, tab_upload = st.tabs(["Paste Logs", "Upload File"])

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

    if st.button("Analyze Logs", type="primary", disabled=not raw_logs):
        parser = LogParser()
        events = parser.parse(raw_logs)

        if not events:
            st.error("No log events could be parsed from the input.")
            return

        st.markdown('<div style="margin:2.25rem 0;"></div>', unsafe_allow_html=True)

        # AI insights first
        if use_ai:
            engine = get_engine()
            from src.core.analyzer.log_analyzer import AILogAnalyzer
            with st.spinner("AI analyzing logs..."):
                ai_analyzer = AILogAnalyzer(engine)
                insight = ai_analyzer.analyze(raw_logs)

            section_header("AI Insights", badge="AI Generated")
            insight_card("Summary", insight.summary)
            insight_card("Root Cause Hypothesis", insight.root_cause_hypothesis, icon="psychology")

            if insight.anomalies:
                with st.expander("Anomalies Detected", expanded=True):
                    for a in insight.anomalies:
                        st.markdown(f"- {a}")
            st.markdown('<div style="margin:2.25rem 0;"></div>', unsafe_allow_html=True)

        # Metrics
        errors = parser.extract_errors(events)
        slow_ops = parser.extract_slow_operations(events)

        col1, col2, col3 = st.columns(3)
        col1.markdown(
            metric_card("Total Events", str(len(events)), PRIMARY),
            unsafe_allow_html=True,
        )
        col2.markdown(
            metric_card("Errors", str(len(errors)), ERROR, delta=f"{len(errors)} found"),
            unsafe_allow_html=True,
        )
        col3.markdown(
            metric_card("Slow Ops", str(len(slow_ops)), TERTIARY),
            unsafe_allow_html=True,
        )

        # Level distribution chart
        section_header("Event Level Distribution")
        level_counts = {}
        for e in events:
            level_counts[e.level] = level_counts.get(e.level, 0) + 1

        level_df = pd.DataFrame({
            "Level": list(level_counts.keys()),
            "Count": list(level_counts.values()),
        })

        level_color_map = {
            "ERROR": ERROR,
            "FATAL": ERROR,
            "CRITICAL": ERROR,
            "WARN": "#ff8c00",
            "WARNING": "#ff8c00",
            "INFO": PRIMARY,
            "DEBUG": "#737687",
        }

        bar_chart = (
            alt.Chart(level_df)
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(
                x=alt.X("Level:N", title=None, axis=alt.Axis(labelAngle=0)),
                y=alt.Y("Count:Q", title="Count"),
                color=alt.Color(
                    "Level:N",
                    scale=alt.Scale(
                        domain=list(level_color_map.keys()),
                        range=list(level_color_map.values()),
                    ),
                    legend=None,
                ),
            )
            .properties(height=200, width="container")
        )
        st.altair_chart(bar_chart, use_container_width=True)

        # Event timeline chart
        timeline_df = build_timeline_df(events)
        if timeline_df is not None:
            section_header("Event Timeline")

            color_domain = list(level_color_map.keys())
            color_range = list(level_color_map.values())

            chart = (
                alt.Chart(timeline_df)
                .mark_circle(size=80)
                .encode(
                    x=alt.X("timestamp:T", title="Time"),
                    y=alt.Y("level:N", title="Level"),
                    color=alt.Color(
                        "level:N",
                        scale=alt.Scale(domain=color_domain, range=color_range),
                        title="Level",
                    ),
                    tooltip=["timestamp:T", "level:N", "message:N"],
                )
                .interactive()
                .properties(height=250, width="container")
            )
            st.altair_chart(chart, use_container_width=True)

        # Error details
        if errors:
            section_header("Errors")
            error_data = [{"Timestamp": e.timestamp, "Message": e.message} for e in errors]
            st.dataframe(pd.DataFrame(error_data), use_container_width=True, hide_index=True)

        # Slow operations
        if slow_ops:
            section_header("Slow Operations")
            slow_data = [
                {"Timestamp": s.timestamp, "Message": s.message, "Duration (ms)": s.metadata.get("duration_ms", "?")}
                for s in slow_ops
            ]
            st.dataframe(pd.DataFrame(slow_data), use_container_width=True, hide_index=True)

        # Error code reference
        error_codes = parser.extract_error_codes(events)
        if error_codes:
            engine = get_engine()
            section_header("Error Code Reference")
            for code in error_codes:
                results = engine.search(code, top_k=1, category="error_code")
                if results:
                    with st.expander(f"`{code}` - {results[0].title}"):
                        st.markdown(results[0].content)

        # Raw summary
        with st.expander("Raw Text Summary"):
            st.code(parser.generate_text_summary(events))


def render_email_analysis():
    page_header("Email Analysis", "Automated email parsing and AI-powered response drafting")

    raw_email = st.text_area(
        "Raw Email",
        height=250,
        placeholder="From: customer@example.com\nTo: support@cloudsync.io\nSubject: Files not syncing\n\nHi, my files are...",
        label_visibility="collapsed",
    )

    if st.button("Parse & Analyze", type="primary", disabled=not raw_email):
        email_parser = EmailParser()
        parsed = email_parser.parse(raw_email)

        st.markdown('<div style="margin:2.25rem 0;"></div>', unsafe_allow_html=True)

        # Email metadata
        section_header("Parsed Email")
        col1, col2, col3 = st.columns(3)
        col1.markdown(
            metric_card("Sender", parsed.sender or "Unknown", PRIMARY),
            unsafe_allow_html=True,
        )
        subject_display = (
            parsed.subject[:30] + "..."
            if len(parsed.subject) > 30
            else parsed.subject or "None"
        )
        col2.markdown(
            metric_card("Subject", subject_display, TERTIARY),
            unsafe_allow_html=True,
        )
        col3.markdown(
            metric_card("Error Codes", ", ".join(parsed.error_codes) or "None", ERROR),
            unsafe_allow_html=True,
        )

        with st.expander("View email body", expanded=False):
            st.text(parsed.body)

        if parsed.body:
            engine = get_engine()
            analyzer = InquiryAnalyzer(engine)
            result = analyzer.classify(parsed.to_inquiry_text())

            st.markdown('<div style="margin:2.25rem 0;"></div>', unsafe_allow_html=True)
            section_header("Analysis Results")
            _render_analysis_results(result)


def render_knowledge_search():
    page_header("Knowledge Engine", "Query internal documentation with semantic AI")

    query = st.text_input(
        "Search",
        placeholder="e.g., SYNC-002, webhook not firing, how to enable delta sync, SSO login failure...",
        label_visibility="collapsed",
    )

    col1, col2 = st.columns(2)
    category_options = ["All Categories", "faq", "troubleshooting", "error_code", "runbook", "feature"]
    category_display = ["All Categories", "FAQ", "Troubleshooting", "Error Codes", "Runbooks", "Features"]
    selected_idx = col1.selectbox("Category", range(len(category_options)), format_func=lambda i: category_display[i])
    category = None if selected_idx == 0 else category_options[selected_idx]
    top_k = col2.slider("Max results", 1, 20, 5)

    if query:
        engine = get_engine()
        results = engine.search(query, top_k=top_k, category=category)

        if not results:
            st.warning("No results found. Try different keywords.")
        else:
            st.markdown(
                f'<p style="font-family:Inter,sans-serif; font-weight:600; '
                f'color:{ON_SURFACE}; margin:1rem 0;">'
                f'{len(results)} result(s) found</p>',
                unsafe_allow_html=True,
            )
            for r in results:
                relevance = f"{r.score:.0%}"
                cat_accent_map = {
                    "faq": PRIMARY,
                    "troubleshooting": ERROR,
                    "error_code": ERROR,
                    "runbook": TERTIARY,
                    "feature": SECONDARY,
                }
                accent = cat_accent_map.get(r.category.lower(), PRIMARY) if r.category else PRIMARY
                search_result_card(
                    title=r.title,
                    category=r.category,
                    relevance=relevance,
                    content=r.content,
                    accent_color=accent,
                )


def main():
    inject_global_css()
    inject_material_icons()
    page = render_sidebar()

    if page == "Inquiry Analysis":
        render_inquiry_analysis()
    elif page == "Log Analysis":
        render_log_analysis()
    elif page == "Email Analysis":
        render_email_analysis()
    elif page == "Knowledge Search":
        render_knowledge_search()
    elif page == "Documentation":
        render_documentation()


if __name__ == "__main__":
    main()
