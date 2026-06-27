"""UC Course Planner — Home Page."""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.theme import inject_theme_css, render_theme_toggle, get_theme
import base64

inject_theme_css()

t = get_theme()

_APP_DIR = Path(__file__).resolve().parent.parent
_LOGO_PATHS = [
    _APP_DIR / "assets" / "uc-logo.png",
    _APP_DIR / "assets" / "uc-logo.svg",
    _APP_DIR / "assets" / "uc-logo.jpg",
]
_logo_file = next((p for p in _LOGO_PATHS if p.exists()), None)

if _logo_file:
    _logo_data = base64.b64encode(_logo_file.read_bytes()).decode()
    _ext = _logo_file.suffix.lstrip(".")
    _mime = {"png": "image/png", "jpg": "image/jpeg", "svg": "image/svg+xml"}.get(_ext, "image/png")
    logo_html = f'<img src="data:{_mime};base64,{_logo_data}" style="max-height: 120px; max-width: 180px; object-fit: contain;" alt="University of Canterbury">'
else:
    logo_html = '<div style="width:120px;height:120px;border-radius:16px;background:linear-gradient(135deg,{},{});display:flex;align-items:center;justify-content:center;box-shadow:0 4px 24px rgba(0,0,0,0.15);"><span style="font-size:2.8rem;font-weight:900;color:white;letter-spacing:-0.04em;">UC</span></div>'.format(
        t['primary'], '#003D6B' if t['primary'] == '#005A9C' else '#2A7FCC'
    )

st.markdown(
    f"""
    <div style="display: flex; align-items: center; justify-content: space-between; padding: 1.5rem 0 1rem 0;">
        <div style="flex: 1;">
            <h1 style="
                font-size: 3.5rem;
                font-weight: 900;
                color: {t['hero_title']};
                margin: 0;
                line-height: 1.08;
                letter-spacing: -0.03em;
                text-shadow: 0 2px 8px rgba(0, 90, 156, 0.12);
            ">UC Course Planner</h1>
            <p style="
                font-size: 1.35rem;
                color: {t['text_secondary']};
                margin: 1rem 0 0 0;
                font-weight: 400;
                line-height: 1.5;
            ">Your personalised guide to choosing the right degree, major,
               and courses at the University of Canterbury.</p>
        </div>
        <div style="flex-shrink: 0; margin-left: 2.5rem;">
            {logo_html}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if not _logo_file:
    st.caption("_To show the official UC logo, place the file at `assets/uc-logo.png`._")

st.divider()

col1, col2, col3 = st.columns(3)

_cards = [
    ("💬", "Chat Advisor", "Have a natural conversation with our AI-powered course advisor. Ask questions about degrees, majors, prerequisites, and more.", "pages/1_Chat_Advisor.py"),
    ("📋", "Course Wizard", "Follow a step-by-step guided flow to select your faculty, degree, major, and build a personalised Year 1 course plan.", "pages/2_Course_Wizard.py"),
    ("🎭", "Sample Scenarios", "Explore pre-built student personas that demonstrate different pathways through the course planning process.", "pages/3_Demo_Scenarios.py"),
]

st.markdown("""<style>.card-box { min-height: 160px; display: flex; flex-direction: column; justify-content: space-between; }</style>""", unsafe_allow_html=True)

for col, (icon, title, desc, page) in zip(st.columns(3), _cards):
    with col:
        with st.container(border=True):
            st.markdown(f'<div class="card-box"><div><h3>{icon} {title}</h3><p>{desc}</p></div></div>', unsafe_allow_html=True)
            st.page_link(page, label=f"Open {title}", icon=icon)

st.divider()

st.subheader("About This Tool")

st.markdown(
    """
This prototype demonstrates an AI-powered course planning assistant for the
University of Canterbury. It covers all **7 faculties** and **18 active
undergraduate degrees** from the UC 2026 Calendar.

**Key Features:**
- **Triage flow** that maps student interests to the right faculty and degree
- **Cross-faculty disambiguation** for subjects like Psychology, Economics, and
  Computer Science that span multiple faculties
- **Prerequisite checking** and admission requirement validation
- **Year 1 course plan generation** tailored to each degree and major
- **Dual-mode interface** — conversational chatbot or guided wizard

**Architecture:**
The tool is powered by a standalone **MCP (Model Context Protocol) server** that
exposes UC course data as standardised tools and resources. The Streamlit frontend
communicates with the MCP server over Streamable HTTP — the same protocol used by
AI coding tools like Cursor. Both components are containerised and deployable
independently on OpenShift.
"""
)

st.divider()

from lib.mcp_factory import get_mcp_client

mcp = get_mcp_client()

with st.expander("UC Faculties at a Glance"):
    faculties = mcp.get_faculties()

    for f in faculties:
        degrees = mcp.get_available_degrees(f.code)
        bachelor_degrees = [d for d in degrees if d.points and d.points >= 360]
        sub_degrees = [d for d in degrees if d.points and d.points < 360]

        st.markdown(f"**{f.name}**")
        st.caption(f.description)

        if bachelor_degrees:
            deg_list = ", ".join(f"{d.code} ({d.points}pts)" for d in bachelor_degrees)
            st.markdown(f"Degrees: {deg_list}")
        if sub_degrees:
            sub_list = ", ".join(f"{d.code} ({d.points}pts)" for d in sub_degrees)
            st.markdown(f"Certificates/Diplomas: {sub_list}")

        if f != faculties[-1]:
            st.markdown("---")

render_theme_toggle()
