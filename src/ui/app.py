"""Streamlit Web UI for Support Buddy."""

import json
from pathlib import Path

import streamlit as st
import pandas as pd

from src.config import ANTHROPIC_API_KEY, KNOWLEDGE_DIR
from src.core.analyzer.inquiry import InquiryAnalyzer
from src.core.analyzer.log_parser import LogParser
from src.core.knowledge.engine import KnowledgeEngine
from src.integrations.email.parser import EmailParser

st.set_page_config(page_title="Support Buddy", page_icon="🎧", layout="wide")


@st.cache_resource
def get_engine():
    engine = KnowledgeEngine()
    if KNOWLEDGE_DIR.is_dir():
        engine.ingest_directory(KNOWLEDGE_DIR)
    return engine


def render_sidebar():
    with st.sidebar:
        st.title("Support Buddy")
        st.caption("AI-powered support tool for TSEs")
        st.divider()

        page = st.radio(
            "Navigate",
            ["Inquiry Analysis", "Log Analysis", "Email Analysis", "Knowledge Search"],
            label_visibility="collapsed",
        )

        st.divider()
        engine = get_engine()
        st.metric("Knowledge Docs", engine.doc_count())

        has_ai = bool(ANTHROPIC_API_KEY)
        st.caption(f"AI Mode: {'Available' if has_ai else 'Not configured'}")

    return page


def render_inquiry_analysis():
    st.header("Inquiry Analysis")
    st.caption("Paste a customer inquiry to get classification, checklist, and relevant articles.")

    use_ai = False
    if ANTHROPIC_API_KEY:
        use_ai = st.toggle("Use AI (Claude)", value=False)

    inquiry = st.text_area("Customer Inquiry", height=150, placeholder="e.g., My files are not syncing between my Mac and Windows laptop...")

    if st.button("Analyze", type="primary", disabled=not inquiry):
        engine = get_engine()

        with st.spinner("Analyzing..."):
            if use_ai:
                from src.core.analyzer.ai_inquiry import AIInquiryAnalyzer
                analyzer = AIInquiryAnalyzer(engine)
                result = analyzer.analyze(inquiry)
            else:
                analyzer = InquiryAnalyzer(engine)
                result = analyzer.classify(inquiry)

        # Results
        col1, col2, col3 = st.columns(3)
        col1.metric("Category", result.category.value.upper())
        col2.metric("Severity", result.severity.value.upper())
        col3.metric("Confidence", f"{result.confidence:.0%}")

        st.subheader("Summary")
        st.info(result.summary)

        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("Checklist")
            for item in result.checklist:
                st.checkbox(item, key=f"check_{item[:20]}")

        with col_right:
            st.subheader("Follow-up Questions")
            for q in result.follow_up_questions:
                st.write(f"- {q}")

        if result.relevant_articles:
            st.subheader("Relevant Knowledge Base Articles")
            articles_data = [
                {"Title": a.title, "Category": a.category, "Score": f"{a.score:.2f}"}
                for a in result.relevant_articles
            ]
            st.dataframe(pd.DataFrame(articles_data), use_container_width=True)

            with st.expander("View article details"):
                for a in result.relevant_articles:
                    st.markdown(f"**{a.title}** ({a.category})")
                    st.markdown(a.content[:500])
                    st.divider()

        if result.confidence < 0.6:
            st.warning("Low confidence — consider escalating to a senior TSE.")

        # Draft response (AI only)
        if use_ai and ANTHROPIC_API_KEY:
            if st.button("Generate Response Draft"):
                from src.core.responder.drafter import ResponseDrafter
                with st.spinner("Generating draft..."):
                    drafter = ResponseDrafter(engine)
                    response = drafter.draft(inquiry, result)

                st.subheader("Draft Response")
                st.text_area("Response", value=response.body, height=200)
                st.metric("Draft Confidence", f"{response.confidence:.0%}")
                if response.needs_escalation:
                    st.error("Escalation recommended")
                if response.suggested_internal_note:
                    st.info(f"Internal note: {response.suggested_internal_note}")


def render_log_analysis():
    st.header("Log Analysis")
    st.caption("Paste logs or upload a log file to get insights.")

    use_ai = False
    if ANTHROPIC_API_KEY:
        use_ai = st.toggle("Use AI (Claude)", value=False, key="log_ai")

    tab_paste, tab_upload = st.tabs(["Paste Logs", "Upload File"])

    raw_logs = ""
    with tab_paste:
        raw_logs = st.text_area("Paste log content", height=200, placeholder='[{"timestamp": "...", "level": "ERROR", ...}]')

    with tab_upload:
        uploaded = st.file_uploader("Upload log file", type=["json", "log", "txt"])
        if uploaded:
            raw_logs = uploaded.read().decode("utf-8")
            st.code(raw_logs[:500] + ("..." if len(raw_logs) > 500 else ""), language="json")

    if st.button("Analyze Logs", type="primary", disabled=not raw_logs):
        parser = LogParser()
        events = parser.parse(raw_logs)

        if not events:
            st.error("No log events could be parsed.")
            return

        if use_ai:
            engine = get_engine()
            from src.core.analyzer.log_analyzer import AILogAnalyzer
            with st.spinner("AI analyzing logs..."):
                ai_analyzer = AILogAnalyzer(engine)
                insight = ai_analyzer.analyze(raw_logs)

            st.subheader("AI Summary")
            st.info(insight.summary)
            st.subheader("Root Cause Hypothesis")
            st.warning(insight.root_cause_hypothesis)

            if insight.anomalies:
                st.subheader("Anomalies")
                for a in insight.anomalies:
                    st.write(f"- {a}")

        # Always show parsed data
        st.subheader("Parsed Events")

        # Timeline chart
        errors = parser.extract_errors(events)
        slow_ops = parser.extract_slow_operations(events)

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Events", len(events))
        col2.metric("Errors", len(errors))
        col3.metric("Slow Ops", len(slow_ops))

        # Level distribution
        level_counts = {}
        for e in events:
            level_counts[e.level] = level_counts.get(e.level, 0) + 1

        st.subheader("Event Level Distribution")
        st.bar_chart(pd.DataFrame({"Level": list(level_counts.keys()), "Count": list(level_counts.values())}).set_index("Level"))

        # Error details
        if errors:
            st.subheader("Errors")
            error_data = [{"Timestamp": e.timestamp, "Message": e.message} for e in errors]
            st.dataframe(pd.DataFrame(error_data), use_container_width=True)

        # Slow operations
        if slow_ops:
            st.subheader("Slow Operations")
            slow_data = [
                {"Timestamp": s.timestamp, "Message": s.message, "Duration (ms)": s.metadata.get("duration_ms", "?")}
                for s in slow_ops
            ]
            st.dataframe(pd.DataFrame(slow_data), use_container_width=True)

        # Error codes
        error_codes = parser.extract_error_codes(events)
        if error_codes:
            engine = get_engine()
            st.subheader("Error Code Reference")
            for code in error_codes:
                results = engine.search(code, top_k=1, category="error_code")
                if results:
                    with st.expander(f"{code}: {results[0].title}"):
                        st.markdown(results[0].content)

        # Raw text summary
        with st.expander("Text Summary"):
            st.code(parser.generate_text_summary(events))


def render_email_analysis():
    st.header("Email Analysis")
    st.caption("Paste a raw email to parse and analyze the customer inquiry.")

    raw_email = st.text_area("Raw Email", height=250, placeholder="From: customer@example.com\nSubject: ...\n\n...")

    if st.button("Parse & Analyze", type="primary", disabled=not raw_email):
        email_parser = EmailParser()
        parsed = email_parser.parse(raw_email)

        col1, col2 = st.columns(2)
        col1.metric("Sender", parsed.sender or "Unknown")
        col2.metric("Error Codes", ", ".join(parsed.error_codes) or "None")

        st.subheader("Subject")
        st.write(parsed.subject)

        st.subheader("Body")
        st.text(parsed.body)

        if parsed.body:
            engine = get_engine()
            analyzer = InquiryAnalyzer(engine)
            result = analyzer.classify(parsed.to_inquiry_text())

            st.divider()
            st.subheader("Analysis")
            col1, col2, col3 = st.columns(3)
            col1.metric("Category", result.category.value.upper())
            col2.metric("Severity", result.severity.value.upper())
            col3.metric("Confidence", f"{result.confidence:.0%}")

            st.subheader("Checklist")
            for item in result.checklist:
                st.checkbox(item, key=f"email_check_{item[:20]}")


def render_knowledge_search():
    st.header("Knowledge Search")

    query = st.text_input("Search query", placeholder="e.g., SYNC-002, webhook not firing, how to enable delta sync")
    col1, col2 = st.columns(2)
    category = col1.selectbox("Category filter", [None, "faq", "troubleshooting", "error_code", "runbook", "feature"])
    top_k = col2.slider("Results", 1, 20, 5)

    if query:
        engine = get_engine()
        results = engine.search(query, top_k=top_k, category=category)

        if not results:
            st.warning("No results found.")
        else:
            for r in results:
                with st.expander(f"{r.title} ({r.category}) — score: {r.score:.2f}"):
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
