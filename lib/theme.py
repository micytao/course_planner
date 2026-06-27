"""Shared dark/light theme support for the UC Course Planner."""

from __future__ import annotations

import streamlit as st

_DARK_BG = "#0E1117"
_DARK_BG2 = "#1A1D26"
_DARK_BG3 = "#262A34"
_DARK_TEXT = "#E8EAED"
_DARK_TEXT2 = "#B0B8C1"
_DARK_BORDER = "#2D3748"
_DARK_PRIMARY = "#4DA6FF"

LIGHT_THEME = {
    "bg": "#FFFFFF",
    "secondary_bg": "#F0F4F8",
    "text": "#1A1A2E",
    "text_secondary": "#4A5568",
    "primary": "#005A9C",
    "primary_light": "#E8F0FE",
    "card_border": "#E2E8F0",
    "hero_title": "#005A9C",
}

DARK_THEME = {
    "bg": _DARK_BG,
    "secondary_bg": _DARK_BG2,
    "text": _DARK_TEXT,
    "text_secondary": _DARK_TEXT2,
    "primary": _DARK_PRIMARY,
    "primary_light": "#1A2A3A",
    "card_border": _DARK_BORDER,
    "hero_title": _DARK_PRIMARY,
}


def _is_dark() -> bool:
    return st.session_state.get("uc_dark_mode", False)


def get_theme() -> dict[str, str]:
    return DARK_THEME if _is_dark() else LIGHT_THEME


def render_theme_toggle() -> None:
    """Render a dark/light toggle at the bottom of the sidebar."""
    with st.sidebar:
        st.markdown("---")
        current = _is_dark()
        label = "Dark Mode" if not current else "Light Mode"
        if st.button(f"Switch to {label}", key="theme_toggle", use_container_width=True):
            st.session_state.uc_dark_mode = not current
            st.rerun()


def inject_theme_css() -> None:
    """Inject CSS variables that adapt to the current theme."""
    t = get_theme()
    dark = _is_dark()

    hero_css = f"""
        .hero-title {{
            font-size: 2.5rem;
            font-weight: 700;
            color: {t["hero_title"]};
            margin-bottom: 0.25rem;
        }}
        .hero-subtitle {{
            font-size: 1.25rem;
            color: {t["text_secondary"]};
            margin-bottom: 2rem;
        }}
    """

    if not dark:
        st.markdown(f"<style>{hero_css}</style>", unsafe_allow_html=True)
        return

    dark_css = f"""
    {hero_css}

    /* ── Global background and text ──────────────────────────── */
    .stApp, .main .block-container {{
        background-color: {_DARK_BG} !important;
        color: {_DARK_TEXT} !important;
    }}

    /* ── Sidebar ─────────────────────────────────────────────── */
    section[data-testid="stSidebar"],
    section[data-testid="stSidebar"] > div {{
        background-color: {_DARK_BG2} !important;
        color: {_DARK_TEXT} !important;
    }}

    /* ── ALL text elements (broad catch-all) ──────────────────── */
    .stApp p, .stApp span, .stApp li, .stApp td, .stApp th,
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
    .stApp label, .stApp .stMarkdown, .stApp div,
    [data-testid="stMarkdownContainer"],
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li,
    [data-testid="stMarkdownContainer"] h1,
    [data-testid="stMarkdownContainer"] h2,
    [data-testid="stMarkdownContainer"] h3,
    [data-testid="stMarkdownContainer"] h4,
    [data-testid="stMarkdownContainer"] span {{
        color: {_DARK_TEXT} !important;
    }}

    /* ── Captions and secondary text ──────────────────────────── */
    [data-testid="stCaptionContainer"],
    [data-testid="stCaptionContainer"] p,
    [data-testid="stCaptionContainer"] span,
    .stCaption, small {{
        color: {_DARK_TEXT2} !important;
    }}

    /* ── Metrics ──────────────────────────────────────────────── */
    [data-testid="stMetricValue"],
    [data-testid="stMetricLabel"],
    [data-testid="stMetricDelta"] {{
        color: {_DARK_TEXT} !important;
    }}

    /* ── Progress bar text ────────────────────────────────────── */
    [data-testid="stProgressBar"] + div,
    .stProgress > div > div > div + div {{
        color: {_DARK_TEXT} !important;
    }}

    /* ── Expanders ────────────────────────────────────────────── */
    [data-testid="stExpander"],
    [data-testid="stExpander"] summary,
    [data-testid="stExpander"] summary span,
    [data-testid="stExpander"] summary p,
    [data-testid="stExpander"] div {{
        color: {_DARK_TEXT} !important;
        background-color: transparent !important;
    }}
    details[data-testid="stExpander"] {{
        border-color: {_DARK_BORDER} !important;
    }}

    /* ── Containers with borders (cards) ──────────────────────── */
    [data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] > div {{
        background-color: {_DARK_BG2} !important;
        border-color: {_DARK_BORDER} !important;
    }}
    [data-testid="stVerticalBlockBorderWrapper"] {{
        border-color: {_DARK_BORDER} !important;
    }}
    div[data-testid="stVerticalBlockBorderWrapper"] > div[style] {{
        background-color: {_DARK_BG2} !important;
    }}

    /* ── Forms ────────────────────────────────────────────────── */
    [data-testid="stForm"],
    [data-testid="stForm"] > div {{
        background-color: {_DARK_BG2} !important;
        border-color: {_DARK_BORDER} !important;
    }}

    /* ── Inputs (text, select, checkbox) ──────────────────────── */
    .stTextInput input, .stTextArea textarea,
    .stSelectbox > div > div,
    [data-testid="stSelectbox"] > div > div {{
        background-color: {_DARK_BG3} !important;
        color: {_DARK_TEXT} !important;
        border-color: {_DARK_BORDER} !important;
    }}
    .stTextInput input::placeholder,
    .stTextArea textarea::placeholder {{
        color: {_DARK_TEXT2} !important;
    }}

    /* ── Checkboxes and radio labels ──────────────────────────── */
    .stCheckbox label span,
    .stRadio label span,
    [data-testid="stCheckbox"] label,
    [data-testid="stCheckbox"] label span {{
        color: {_DARK_TEXT} !important;
    }}

    /* ── Chat messages ────────────────────────────────────────── */
    [data-testid="stChatMessage"],
    .stChatMessage {{
        background-color: {_DARK_BG2} !important;
        border-color: {_DARK_BORDER} !important;
    }}
    [data-testid="stChatMessageContent"],
    [data-testid="stChatMessageContent"] p,
    [data-testid="stChatMessageContent"] span,
    [data-testid="stChatMessageContent"] li,
    [data-testid="stChatMessageContent"] code {{
        color: {_DARK_TEXT} !important;
    }}

    /* ── Chat input box — full coverage ───────────────────────── */
    [data-testid="stChatInput"],
    [data-testid="stChatInput"] > div,
    [data-testid="stChatInput"] > div > div,
    [data-testid="stChatInput"] [data-baseweb="textarea"],
    [data-testid="stChatInput"] [data-baseweb="base-input"],
    [data-testid="stChatInput"] [data-baseweb="input"],
    .stChatInput,
    .stChatInput > div,
    .stChatInput > div > div {{
        background-color: {_DARK_BG3} !important;
        border-color: {_DARK_BORDER} !important;
        color: {_DARK_TEXT} !important;
    }}
    [data-testid="stChatInput"] textarea,
    .stChatInput textarea {{
        background-color: {_DARK_BG3} !important;
        color: {_DARK_TEXT} !important;
        caret-color: {_DARK_TEXT} !important;
        -webkit-text-fill-color: {_DARK_TEXT} !important;
    }}
    [data-testid="stChatInput"] textarea::placeholder,
    .stChatInput textarea::placeholder {{
        color: {_DARK_TEXT2} !important;
        -webkit-text-fill-color: {_DARK_TEXT2} !important;
    }}

    /* Chat input container at bottom of page */
    [data-testid="stBottom"],
    [data-testid="stBottom"] > div {{
        background-color: {_DARK_BG} !important;
    }}
    [data-testid="stBottom"] [data-testid="stChatInput"] > div {{
        background-color: {_DARK_BG3} !important;
    }}

    /* Chat input send button */
    [data-testid="stChatInput"] button,
    [data-testid="stChatInputSubmitButton"],
    .stChatInput button {{
        color: {_DARK_TEXT} !important;
        background-color: transparent !important;
    }}
    [data-testid="stChatInput"] button:hover,
    .stChatInput button:hover {{
        color: {_DARK_PRIMARY} !important;
    }}

    /* ── DataFrames / tables ──────────────────────────────────── */
    .stDataFrame, .stDataFrame table,
    .stDataFrame th, .stDataFrame td,
    [data-testid="stDataFrame"],
    [data-testid="stTable"] th,
    [data-testid="stTable"] td {{
        color: {_DARK_TEXT} !important;
        background-color: {_DARK_BG2} !important;
    }}
    .glideDataEditor, .dvn-scroller {{
        background-color: {_DARK_BG2} !important;
    }}

    /* ── Alerts (info, warning, error, success) ──────────────── */
    [data-testid="stAlert"] {{
        border-color: {_DARK_BORDER} !important;
    }}
    [data-testid="stAlert"] p,
    [data-testid="stAlert"] span {{
        color: inherit !important;
    }}
    div[data-baseweb="notification"] {{
        color: inherit !important;
    }}

    /* ── Buttons ──────────────────────────────────────────────── */
    .stButton > button[kind="secondary"],
    .stButton > button:not([kind="primary"]) {{
        color: {_DARK_TEXT} !important;
        border-color: {_DARK_BORDER} !important;
        background-color: {_DARK_BG3} !important;
    }}
    .stButton > button[kind="secondary"]:hover,
    .stButton > button:not([kind="primary"]):hover {{
        background-color: {_DARK_BORDER} !important;
        border-color: {_DARK_PRIMARY} !important;
        color: {_DARK_TEXT} !important;
    }}

    /* ── Download button ──────────────────────────────────────── */
    .stDownloadButton > button {{
        color: white !important;
    }}

    /* ── Dividers / horizontal rules ──────────────────────────── */
    hr, [data-testid="stDivider"] {{
        border-color: {_DARK_BORDER} !important;
    }}

    /* ── Page links ───────────────────────────────────────────── */
    [data-testid="stPageLink"],
    [data-testid="stPageLink"] a,
    [data-testid="stPageLink"] span {{
        color: {_DARK_PRIMARY} !important;
    }}

    /* ── Toggle / switch ──────────────────────────────────────── */
    [data-testid="stToggle"] label span {{
        color: {_DARK_TEXT} !important;
    }}

    /* ── Sidebar navigation links ─────────────────────────────── */
    [data-testid="stSidebarNav"] a span,
    [data-testid="stSidebarNavItems"] a span {{
        color: {_DARK_TEXT} !important;
    }}
    """

    st.markdown(f"<style>{dark_css}</style>", unsafe_allow_html=True)
