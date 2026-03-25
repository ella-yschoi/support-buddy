"""UI styling module - The Intelligent Ledger design system.

All CSS injection and HTML helper functions for the Support Buddy reskin.
Uses Streamlit's st.markdown(unsafe_allow_html=True) pattern exclusively.
"""

import re

import streamlit as st

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------
PRIMARY = "#004bca"
PRIMARY_CONTAINER = "#0061ff"
ERROR = "#ba1a1a"
TERTIARY = "#005f75"
SECONDARY = "#525f73"
ON_SURFACE = "#191c1e"
ON_SURFACE_VARIANT = "#424656"
OUTLINE = "#737687"
SURFACE = "#f7f9fc"
SURFACE_CONTAINER = "#eceef1"
SURFACE_CONTAINER_LOW = "#f2f4f7"
SURFACE_CONTAINER_LOWEST = "#ffffff"
ERROR_CONTAINER = "#ffdad6"
ON_ERROR_CONTAINER = "#93000a"


def inject_global_css() -> None:
    """Inject the full global CSS into the Streamlit app."""
    st.markdown(
        """
        <style>
        /* ── Google Fonts ─────────────────────────────────── */
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

        /* ── Typography overrides ─────────────────────────── */
        h1, h2, h3 {
            font-family: 'Manrope', sans-serif !important;
            color: #191c1e !important;
        }
        /* NOTE: 'span' is intentionally excluded to avoid breaking
           Streamlit's internal Material Symbols icon ligatures
           (sidebar collapse, expander arrows, etc.). */
        html, body, p, li, div, input, textarea, label, button,
        [data-testid="stMarkdownContainer"],
        [data-testid="stMarkdownContainer"] p,
        [data-testid="stMarkdownContainer"] li,
        [data-testid="stMarkdownContainer"] span:not(.material-symbols-outlined) {
            font-family: 'Inter', sans-serif !important;
        }
        .material-symbols-outlined {
            font-family: 'Material Symbols Outlined' !important;
        }
        html, body, p, li, div {
            color: #191c1e;
        }

        /* ── Main area ────────────────────────────────────── */
        .stApp, [data-testid="stAppViewContainer"] {
            background-color: #f7f9fc !important;
        }
        .main .block-container {
            max-width: 1400px;
            padding-top: 0 !important;
        }

        /* ── Sidebar ──────────────────────────────────────── */
        [data-testid="stSidebar"] {
            background-color: #eceef1 !important;
            border-right: none !important;
        }
        /* ── Sidebar flex chain: push bottom section to the very bottom ──
           Uses > * wildcards so the chain works regardless of how many
           intermediate wrapper divs Streamlit injects between known
           data-testid nodes. */
        [data-testid="stSidebar"] > div {
            height: 100% !important;
        }
        [data-testid="stSidebarContent"] {
            display: flex !important;
            flex-direction: column !important;
            height: 100% !important;
        }
        /* Outer wrapper → grows to fill sidebar */
        [data-testid="stSidebarContent"] > [data-testid="stVerticalBlockBorderWrapper"] {
            flex: 1 !important;
            display: flex !important;
            flex-direction: column !important;
        }
        /* Propagate flex through any intermediate wrapper layers (1-3 deep)
           between the outer stVerticalBlockBorderWrapper and the
           top-level stVerticalBlock. */
        [data-testid="stSidebarContent"] > [data-testid="stVerticalBlockBorderWrapper"] > * {
            flex: 1 !important;
            display: flex !important;
            flex-direction: column !important;
        }
        [data-testid="stSidebarContent"] > [data-testid="stVerticalBlockBorderWrapper"] > * > * {
            flex: 1 !important;
            display: flex !important;
            flex-direction: column !important;
        }
        [data-testid="stSidebarContent"] > [data-testid="stVerticalBlockBorderWrapper"] > * > * > * {
            flex: 1 !important;
            display: flex !important;
            flex-direction: column !important;
        }
        /* Push st.container() (bottom section) to the sidebar bottom.
           This overrides the wildcard flex:1 rules above for the
           container wrapper, which is the only stVerticalBlockBorderWrapper
           that is a direct child of a stVerticalBlock. */
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] {
            margin-top: auto !important;
            flex: 0 0 auto !important;
        }
        [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] {
            border: none !important;
        }
        /* Sidebar nav buttons - shared base (both primary & secondary) */
        [data-testid="stSidebar"] [data-testid="stButton"] button {
            text-transform: uppercase !important;
            letter-spacing: 0.05em !important;
            font-family: 'Manrope', sans-serif !important;
            font-size: 11px !important;
            font-weight: 700 !important;
            border-radius: 0 !important;
            border: none !important;
            justify-content: flex-start !important;
            text-align: left !important;
            transition: background 0.2s, color 0.2s !important;
        }
        [data-testid="stSidebar"] [data-testid="stButton"] button > div {
            justify-content: flex-start !important;
        }
        /* Inactive nav (secondary) */
        [data-testid="stSidebar"] [data-testid="stButton"] button[kind="secondary"] {
            background: transparent !important;
            color: #525f73 !important;
        }
        [data-testid="stSidebar"] [data-testid="stButton"] button[kind="secondary"] p {
            text-align: left !important;
            color: #525f73 !important;
        }
        [data-testid="stSidebar"] [data-testid="stButton"] button[kind="secondary"]:hover {
            background: #f7f9fc !important;
        }
        /* Active nav (primary) - blue tint + right accent */
        [data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"] {
            background: rgba(0,75,202,0.1) !important;
            border-right: 4px solid #0061ff !important;
            color: #004bca !important;
        }
        [data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"] p {
            text-align: left !important;
            color: #004bca !important;
        }
        [data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"] span {
            color: #004bca !important;
        }

        /* ── Refresh Docs override ────────────────────────── */
        /* The bottom section is wrapped in st.container() which
           creates a nested stVerticalBlock. This lets us override
           the nav-active primary styling for the Refresh Docs button
           without any :has() selectors. */
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] [data-testid="stVerticalBlock"] [data-testid="stButton"] button[kind="primary"] {
            background: linear-gradient(135deg, #004bca, #0061ff) !important;
            border-radius: 0.5rem !important;
            border: none !important;
            border-right: none !important;
            color: #ffffff !important;
            font-size: 13px !important;
            letter-spacing: 0.02em !important;
        }
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] [data-testid="stVerticalBlock"] [data-testid="stButton"] button[kind="primary"] p,
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] [data-testid="stVerticalBlock"] [data-testid="stButton"] button[kind="primary"] span {
            color: #ffffff !important;
        }

        /* ── Primary buttons (main area + sidebar Refresh) ── */
        .stButton button[kind="primary"],
        [data-testid="stButton"] button[kind="primary"] {
            background: linear-gradient(135deg, #004bca, #0061ff) !important;
            border-radius: 0.5rem !important;
            border: none !important;
            color: #ffffff !important;
            font-weight: 700 !important;
            font-family: 'Manrope', sans-serif !important;
            letter-spacing: 0.02em !important;
        }
        .stButton button[kind="primary"] p,
        [data-testid="stButton"] button[kind="primary"] p,
        .stButton button[kind="primary"] span,
        [data-testid="stButton"] button[kind="primary"] span {
            color: #ffffff !important;
        }

        /* ── Text inputs / text areas ─────────────────────── */
        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea {
            background: #f2f4f7 !important;
            border: 1px solid rgba(194,198,217,0.2) !important;
            border-radius: 0.5rem !important;
            font-family: 'Inter', sans-serif !important;
            color: #191c1e !important;
            transition: background 0.2s, border 0.2s !important;
        }
        [data-testid="stTextInput"] input:focus,
        [data-testid="stTextArea"] textarea:focus {
            background: #ffffff !important;
            border: 1px solid rgba(0,75,202,0.3) !important;
        }

        /* ── Select box ───────────────────────────────────── */
        [data-testid="stSelectbox"] > div > div {
            background: #f2f4f7 !important;
            border: 1px solid rgba(194,198,217,0.2) !important;
            border-radius: 0.5rem !important;
        }

        /* ── Metric cards ─────────────────────────────────── */
        [data-testid="stMetric"] {
            background: #ffffff !important;
            border-left: 4px solid #004bca !important;
            border-radius: 0.5rem !important;
            padding: 1rem !important;
        }

        /* ── Expander ─────────────────────────────────────── */
        [data-testid="stExpander"] {
            background: #ffffff !important;
            border: none !important;
            box-shadow: 0 12px 40px rgba(25,28,30,0.06) !important;
            border-radius: 0.5rem !important;
        }

        /* ── Dataframe ────────────────────────────────────── */
        [data-testid="stDataFrame"] {
            border-radius: 0.5rem !important;
            overflow: hidden;
        }
        [data-testid="stDataFrame"] > div {
            border: none !important;
        }

        /* ── Tabs ─────────────────────────────────────────── */
        [data-testid="stTabs"] [data-baseweb="tab-list"] {
            gap: 1.5rem !important;
            border-bottom: 2px solid #eceef1 !important;
        }
        [data-testid="stTabs"] [data-baseweb="tab"] {
            font-family: 'Manrope', sans-serif !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.05em !important;
            font-size: 11px !important;
            color: #525f73 !important;
        }
        [data-testid="stTabs"] [aria-selected="true"] {
            color: #004bca !important;
            border-bottom-color: #004bca !important;
        }

        /* ── Toggle ───────────────────────────────────────── */
        [data-testid="stCheckbox"] label span {
            font-family: 'Inter', sans-serif !important;
        }

        /* ── Divider override: invisible spacer ───────────── */
        [data-testid="stHorizontalRule"],
        hr {
            border: none !important;
            margin: 2.25rem 0 !important;
            height: 0 !important;
        }

        /* ── Alert overrides ──────────────────────────────── */
        [data-testid="stAlert"] {
            border-radius: 0.5rem !important;
            border: none !important;
        }

        /* ── File uploader ────────────────────────────────── */
        [data-testid="stFileUploader"] {
            background: #f2f4f7 !important;
            border-radius: 0.5rem !important;
        }

        /* ── Slider ───────────────────────────────────────── */
        [data-testid="stSlider"] [data-baseweb="slider"] div {
            color: #004bca !important;
        }

        /* ── Spinner ──────────────────────────────────────── */
        .stSpinner > div {
            border-top-color: #004bca !important;
        }

        /* ── Doc card grid spacing ───────────────────────── */
        /* Match vertical gap between card rows to the horizontal column gap */
        [data-testid="stHorizontalBlock"]:has(.doc-card-click) {
            margin-bottom: 0.5rem !important;
        }

        /* ── Doc card click overlay ──────────────────────── */
        /* Card hover feedback */
        .doc-card-click {
            cursor: pointer;
        }
        .doc-card-click > div {
            transition: box-shadow 0.15s ease, transform 0.15s ease;
        }
        .doc-card-click:hover > div {
            box-shadow: 0 4px 20px rgba(25,28,30,0.12) !important;
            transform: translateY(-1px);
        }
        /* Column containing a doc card becomes a positioning context */
        [data-testid="stColumn"]:has(.doc-card-click) [data-testid="stVerticalBlock"] {
            position: relative !important;
        }
        /* Stretch the invisible button over the entire card area */
        [data-testid="stElementContainer"]:has(.doc-card-click) + [data-testid="stElementContainer"] {
            position: absolute !important;
            inset: 0 !important;
            z-index: 2 !important;
        }
        [data-testid="stElementContainer"]:has(.doc-card-click) + [data-testid="stElementContainer"] button {
            opacity: 0 !important;
            position: absolute !important;
            inset: 0 !important;
            width: 100% !important;
            height: 100% !important;
            min-height: unset !important;
            padding: 0 !important;
            margin: 0 !important;
            cursor: pointer !important;
        }

        /* ── Hide default Streamlit elements ──────────────── */
        #MainMenu {visibility: hidden;}
        header[data-testid="stHeader"] {
            background: rgba(247,249,252,0.8) !important;
            backdrop-filter: blur(12px) !important;
        }
        footer {visibility: hidden;}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# HTML helper functions
# ---------------------------------------------------------------------------

def page_header(title: str, subtitle: str = "") -> None:
    """Render a large editorial page header (4xl extrabold Manrope)."""
    subtitle_html = (
        f'<p style="color:{SECONDARY}; font-family:Inter,sans-serif; '
        f'font-size:0.95rem; font-weight:500; margin-top:0.25rem;">{subtitle}</p>'
        if subtitle
        else ""
    )
    st.markdown(
        f"""
        <div style="margin-bottom:2.25rem;">
            <h2 style="font-family:Manrope,sans-serif; font-size:2.25rem;
                        font-weight:800; letter-spacing:-0.02em; color:{ON_SURFACE};
                        margin:0; line-height:1.2;">
                {title}
            </h2>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(
    label: str,
    value: str,
    accent_color: str = PRIMARY,
    delta: str = "",
) -> str:
    """Return HTML for a metric card with left accent border.

    Call via st.markdown(metric_card(...), unsafe_allow_html=True).
    """
    delta_html = (
        f'<p style="font-size:0.625rem; color:{accent_color}; '
        f'font-weight:600; margin-top:0.5rem;">{delta}</p>'
        if delta
        else ""
    )
    return (
        f'<div style="background:#ffffff; border-left:4px solid {accent_color}; '
        f'border-radius:0.5rem; padding:1.25rem 1.5rem; height:100%;">'
        f'<p style="font-size:0.625rem; font-weight:700; color:{OUTLINE}; '
        f'text-transform:uppercase; letter-spacing:0.1em; margin:0 0 0.25rem 0; '
        f'font-family:Inter,sans-serif;">{label}</p>'
        f'<p style="font-family:Manrope,sans-serif; font-size:1.75rem; '
        f'font-weight:900; color:{ON_SURFACE}; margin:0; line-height:1.2;">{value}</p>'
        f'{delta_html}'
        f'</div>'
    )


def insight_card(title: str, body: str, icon: str = "auto_awesome") -> None:
    """Render a glassmorphism AI insight card with left accent border."""
    st.markdown(
        f"""
        <div style="background:rgba(255,255,255,0.8); backdrop-filter:blur(12px);
                    -webkit-backdrop-filter:blur(12px);
                    border-left:4px solid {PRIMARY}; border-radius:0.5rem;
                    padding:1.5rem; margin:1rem 0;
                    box-shadow:0 12px 40px rgba(25,28,30,0.06);">
            <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.75rem;">
                <span class="material-symbols-outlined"
                      style="color:{PRIMARY}; font-size:20px;
                             font-variation-settings:'FILL' 1;">{icon}</span>
                <span style="font-family:Manrope,sans-serif; font-weight:700;
                             font-size:0.95rem; color:{PRIMARY};">{title}</span>
            </div>
            <p style="font-family:Inter,sans-serif; font-size:0.875rem;
                      color:{ON_SURFACE}; line-height:1.7; margin:0;">{body}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_header(title: str, badge: str = "") -> None:
    """Render a section title with optional badge (e.g. 'AI Identified')."""
    badge_html = (
        f'<span style="background:{PRIMARY_CONTAINER}; color:#ffffff; '
        f'font-size:0.625rem; padding:0.15rem 0.5rem; border-radius:0.125rem; '
        f'text-transform:uppercase; letter-spacing:-0.02em; font-weight:700; '
        f'margin-left:0.5rem; vertical-align:middle;">{badge}</span>'
        if badge
        else ""
    )
    st.markdown(
        f"""
        <h3 style="font-family:Manrope,sans-serif; font-weight:800;
                    font-size:1.25rem; color:{ON_SURFACE}; margin:2.25rem 0 1rem 0;">
            {title}{badge_html}
        </h3>
        """,
        unsafe_allow_html=True,
    )


def search_result_card(
    title: str,
    category: str,
    relevance: str,
    content: str,
    accent_color: str = PRIMARY,
) -> None:
    """Render a knowledge-base search result as a card with <details> toggle."""
    # Choose category badge color based on common categories
    cat_colors = {
        "faq": PRIMARY,
        "troubleshooting": ERROR,
        "error_code": ERROR,
        "runbook": TERTIARY,
        "feature": SECONDARY,
    }
    cat_color = cat_colors.get(category.lower(), SECONDARY) if category else SECONDARY
    # Escape content for safe HTML embedding, then convert markdown bold
    safe_content = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    safe_content = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", safe_content)
    st.markdown(
        f"""
        <details style="background:#ffffff; border-left:4px solid {accent_color};
                        border-radius:0.5rem; padding:1.25rem 1.5rem; margin-bottom:0.75rem;
                        box-shadow:0 12px 40px rgba(25,28,30,0.06); cursor:pointer;">
            <summary style="display:flex; align-items:center; justify-content:space-between;
                            list-style:none;">
                <div style="flex:1;">
                    <span style="font-family:Manrope,sans-serif; font-weight:700;
                                 font-size:0.95rem; color:{ON_SURFACE};">{title}</span>
                    <span style="background:{cat_color}10; color:{cat_color};
                                 font-size:0.625rem; font-weight:700; padding:0.15rem 0.5rem;
                                 border-radius:0.125rem; text-transform:uppercase;
                                 letter-spacing:0.05em; margin-left:0.5rem;
                                 vertical-align:middle;">{category}</span>
                </div>
                <span style="font-size:0.625rem; font-weight:900; color:{PRIMARY};
                             text-transform:uppercase; letter-spacing:-0.02em;
                             white-space:nowrap;">{relevance} Match</span>
            </summary>
            <div style="margin-top:1rem; padding-top:1rem;
                        border-top:1px solid rgba(194,198,217,0.15);">
                <p style="font-family:Inter,sans-serif; font-size:0.875rem;
                          color:{ON_SURFACE_VARIANT}; line-height:1.7;
                          white-space:pre-wrap;">{safe_content}</p>
            </div>
        </details>
        """,
        unsafe_allow_html=True,
    )


def severity_chip(level: str) -> str:
    """Return HTML for a severity chip (inline badge).

    Returns the HTML string - caller wraps it in st.markdown().
    """
    level_lower = level.lower()
    chip_map = {
        "critical": (ERROR, ERROR_CONTAINER, ON_ERROR_CONTAINER),
        "high": ("#ff8c00", "#fff3e0", "#5d3a00"),
        "medium": ("#ffc107", "#fff8e1", "#5d4a00"),
        "low": ("#28a745", "#e8f5e9", "#1b5e20"),
    }
    bg, bg_container, fg = chip_map.get(level_lower, (OUTLINE, SURFACE_CONTAINER, ON_SURFACE))
    return (
        f'<span style="background:{bg_container}; color:{fg}; '
        f'padding:0.2rem 0.75rem; border-radius:0.125rem; font-size:0.625rem; '
        f'font-weight:700; text-transform:uppercase; letter-spacing:0.05em;">{level.upper()}</span>'
    )


def status_bar(docs_count: int, ai_status: str) -> None:
    """Render the sidebar bottom status bar."""
    ai_color = "#28a745" if ai_status == "ON" else OUTLINE
    st.markdown(
        f"""
        <div style="margin-top:1.5rem; padding-top:1rem;
                    border-top:1px solid rgba(194,198,217,0.2);">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <p style="font-size:0.625rem; font-weight:700; color:{OUTLINE};
                              text-transform:uppercase; letter-spacing:0.1em; margin:0;">
                        Knowledge Base</p>
                    <p style="font-family:Manrope,sans-serif; font-size:1.1rem;
                              font-weight:800; color:{ON_SURFACE}; margin:0.15rem 0 0 0;">
                        {docs_count} docs</p>
                </div>
                <div style="text-align:right;">
                    <p style="font-size:0.625rem; font-weight:700; color:{OUTLINE};
                              text-transform:uppercase; letter-spacing:0.1em; margin:0;">
                        AI Engine</p>
                    <p style="font-size:1.1rem; font-weight:800; margin:0.15rem 0 0 0;">
                        <span style="display:inline-block; width:8px; height:8px;
                                     border-radius:50%; background:{ai_color};
                                     margin-right:0.35rem; vertical-align:middle;"></span>
                        <span style="font-family:Manrope,sans-serif; color:{ON_SURFACE};
                                     vertical-align:middle;">{ai_status}</span>
                    </p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def action_card(title: str, items: list[str]) -> None:
    """Render a checklist / follow-up card as pure HTML.

    Everything - the green-bordered wrapper, title, and checkbox rows - is
    rendered in a single ``st.markdown`` call so the styling is guaranteed
    regardless of Streamlit's internal DOM structure.
    """
    rows = ""
    for item in items:
        safe = item.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        rows += (
            f'<label style="display:flex; align-items:flex-start; gap:0.5rem; '
            f'padding:0.35rem 0; cursor:pointer;">'
            f'<input type="checkbox" style="margin-top:0.2rem; '
            f'accent-color:#28a745; flex-shrink:0;"> '
            f'<span style="font-size:0.875rem; color:{ON_SURFACE}; '
            f'font-family:Inter,sans-serif; line-height:1.5;">{safe}</span>'
            f'</label>'
        )
    st.markdown(
        f'<div style="background:#ffffff; border-left:4px solid #28a745; '
        f'border-radius:0.5rem; padding:1rem 1.25rem; '
        f'box-shadow:0 12px 40px rgba(25,28,30,0.06);">'
        f'<p style="font-size:0.625rem; font-weight:700; color:{OUTLINE}; '
        f'text-transform:uppercase; letter-spacing:0.1em; '
        f'margin:0 0 0.5rem 0;">{title}</p>'
        f'{rows}'
        f'</div>',
        unsafe_allow_html=True,
    )


# Material Symbols font link (injected once alongside global CSS)
_MATERIAL_ICONS_CSS = (
    '<link href="https://fonts.googleapis.com/css2?family='
    'Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" '
    'rel="stylesheet"/>'
)


def inject_material_icons() -> None:
    """Inject Google Material Symbols Outlined font."""
    st.markdown(_MATERIAL_ICONS_CSS, unsafe_allow_html=True)


def doc_card(
    title: str,
    category: str,
    filename: str,
    accent_color: str = PRIMARY,
) -> str:
    """Return HTML for a documentation card (static, no <details>).

    The actual click behaviour is handled by a companion st.button.
    """
    cat_color = accent_color
    return (
        f'<div style="background:#ffffff; border-left:4px solid {accent_color}; '
        f'border-radius:0.5rem; padding:1rem 1.25rem; '
        f'box-shadow:0 12px 40px rgba(25,28,30,0.06);">'
        f'<span style="font-family:Manrope,sans-serif; font-weight:700; '
        f'font-size:0.95rem; color:{ON_SURFACE};">{title}</span>'
        f'<span style="background:{cat_color}10; color:{cat_color}; '
        f'font-size:0.625rem; font-weight:700; padding:0.15rem 0.5rem; '
        f'border-radius:0.125rem; text-transform:uppercase; '
        f'letter-spacing:0.05em; margin-left:0.5rem; '
        f'vertical-align:middle;">{category}</span>'
        f'<p style="font-size:0.75rem; color:{OUTLINE}; margin:0.35rem 0 0 0; '
        f'font-family:Inter,sans-serif;">{filename}</p>'
        f'</div>'
    )


def doc_detail_header(
    title: str,
    category: str,
    filename: str,
    accent_color: str = PRIMARY,
) -> None:
    """Render the detail-view header: category badge + filename + large title."""
    cat_color = accent_color
    st.markdown(
        f"""
        <div style="border-left:4px solid {accent_color}; padding-left:1.25rem;
                    margin-bottom:2rem;">
            <span style="background:{cat_color}10; color:{cat_color};
                         font-size:0.625rem; font-weight:700; padding:0.15rem 0.5rem;
                         border-radius:0.125rem; text-transform:uppercase;
                         letter-spacing:0.05em;">{category}</span>
            <span style="font-size:0.75rem; color:{OUTLINE}; margin-left:0.5rem;
                         font-family:Inter,sans-serif;">{filename}</span>
            <h2 style="font-family:Manrope,sans-serif; font-size:2rem;
                        font-weight:800; letter-spacing:-0.02em; color:{ON_SURFACE};
                        margin:0.5rem 0 0 0; line-height:1.2;">
                {title}
            </h2>
        </div>
        """,
        unsafe_allow_html=True,
    )


# Map page names to Material Symbols icon names for sidebar active indicator
_NAV_ICONS = {
    "Inquiry Analysis": "analytics",
    "Log Analysis": "terminal",
    "Email Analysis": "mail_lock",
    "Knowledge Search": "manage_search",
}


def nav_active_indicator(page_name: str) -> None:
    """Render a styled HTML active-page indicator for the sidebar.

    Dimensions are matched to Streamlit's st.button(type="secondary", icon=...)
    so that switching between active/inactive causes no layout shift.
    """
    icon = _NAV_ICONS.get(page_name, "circle")
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:0.5rem;
                    background:rgba(0,75,202,0.1); border-right:4px solid {PRIMARY_CONTAINER};
                    padding:0.25rem 1rem; min-height:38px;
                    font-family:Manrope,sans-serif; font-size:11px; font-weight:700;
                    text-transform:uppercase; letter-spacing:0.05em; color:{PRIMARY};
                    box-sizing:border-box;">
            <span class="material-symbols-outlined"
                  style="font-size:18px; color:{PRIMARY};
                         font-variation-settings:'FILL' 1;">{icon}</span>
            {page_name}
        </div>
        """,
        unsafe_allow_html=True,
    )
