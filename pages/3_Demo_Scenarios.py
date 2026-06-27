"""Pre-built demo scenarios page for customer presentations."""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.models import StudentBackground
from lib.theme import inject_theme_css, render_theme_toggle
from lib.data_layer import CoursePlannerMCP
from lib.course_engine import CourseEngine


inject_theme_css()

mcp = CoursePlannerMCP()
engine = CourseEngine(mcp)

st.title("Sample Scenarios")
st.caption("Pre-built student personas for live walkthrough. Select a persona to see the full course planning journey.")

students = mcp.get_sample_students()

# ── Sidebar: Persona Selector ─────────────────────────────────────────
with st.sidebar:
    st.header("Select a Persona")
    for s in students:
        if st.button(f"{s.name}", key=f"persona_{s.id}", use_container_width=True):
            st.session_state.demo_student = s.id
    st.divider()
    st.caption("These personas demonstrate different pathways through the course planning flow.")

if "demo_student" not in st.session_state:
    st.session_state.demo_student = students[0].id if students else None


# ── Main Content ──────────────────────────────────────────────────────
selected = mcp.get_sample_student(st.session_state.demo_student)

if not selected:
    st.warning("No persona selected.")
    st.stop()

st.header(f"Student Profile: {selected.name}")

col1, col2 = st.columns([2, 1])
with col1:
    st.markdown(f"**{selected.description}**")
    st.info(f"Demo narrative: {selected.demo_narrative}")
with col2:
    st.markdown("**Interests:** " + ", ".join(selected.interests))

st.divider()

# ── Background ────────────────────────────────────────────────────────
st.subheader("Background & Qualifications")
bg = selected.background
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f"**Qualification:** {bg.qualification_type}")
    st.markdown(f"**University Entrance:** {'Yes' if bg.has_ue else 'No'}")
with col2:
    st.markdown(f"**Year 13 Maths:** {'Yes' if bg.has_maths else 'No'}")
    st.markdown(f"**Year 13 Physics:** {'Yes' if bg.has_physics else 'No'}")
with col3:
    st.markdown(f"**Year 13 Chemistry:** {'Yes' if bg.has_chemistry else 'No'}")
    st.markdown(f"**Domestic Student:** {'Yes' if bg.domestic else 'No'}")

st.divider()

# ── Recommended Pathway ──────────────────────────────────────────────
st.subheader("Recommended Pathway")

faculty = mcp.get_faculty(selected.suggested_faculty)
degree = mcp.get_degree(selected.suggested_degree)

col1, col2, col3 = st.columns(3)
with col1:
    with st.container(border=True):
        st.markdown("**Faculty**")
        st.markdown(f"### {faculty.short_name if faculty else selected.suggested_faculty}")
with col2:
    with st.container(border=True):
        st.markdown("**Degree**")
        if degree:
            st.markdown(f"### {degree.code}")
            st.caption(f"{degree.name} ({degree.points} pts, {degree.duration_years} years)")
        else:
            st.markdown(f"### {selected.suggested_degree}")
with col3:
    with st.container(border=True):
        st.markdown("**Major / Focus**")
        st.markdown(f"### {selected.suggested_major or 'Fixed programme'}")
        if selected.double_degree:
            st.caption(f"Double degree with: {selected.double_degree}")
            if selected.double_degree_major:
                st.caption(f"Second degree major: {selected.double_degree_major}")

# ── Admission Check ──────────────────────────────────────────────────
st.divider()
st.subheader("Admission Check")

validation = engine.validate_admission(selected.suggested_degree, bg)
for msg in validation.messages:
    if msg.level == "error":
        st.error(msg.message)
    elif msg.level == "warning":
        st.warning(msg.message)
    else:
        st.info(msg.message)

if validation.valid:
    st.success("Admission requirements met.")

# ── Year 1 Course Plan ───────────────────────────────────────────────
st.divider()
st.subheader("Year 1 Course Plan")

if selected.year1_plan:
    rows = []
    for entry in selected.year1_plan:
        course = mcp.get_course_details(entry.course)
        rows.append({
            "Code": entry.course,
            "Title": course.title if course else "—",
            "Semester": entry.semester,
            "Points": entry.points,
            "Type": entry.note,
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, width="stretch", hide_index=True)

    total_pts = sum(e.points for e in selected.year1_plan)
    st.metric("Total Year 1 Points", f"{total_pts} pts")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Semester 1")
        s1 = [e for e in selected.year1_plan if e.semester in ("S1", "W")]
        for e in s1:
            course = mcp.get_course_details(e.course)
            st.markdown(f"- **{e.course}** — {course.title if course else '—'} ({e.points} pts)")

    with col2:
        st.markdown("#### Semester 2")
        s2 = [e for e in selected.year1_plan if e.semester == "S2"]
        for e in s2:
            course = mcp.get_course_details(e.course)
            st.markdown(f"- **{e.course}** — {course.title if course else '—'} ({e.points} pts)")

# ── Alternative Pathways ─────────────────────────────────────────────
st.divider()
st.subheader("Alternative Pathways")

if selected.alternative_paths:
    for alt in selected.alternative_paths:
        with st.container(border=True):
            alt_degree = alt.get("degree", "")
            alt_major = alt.get("major", "")
            alt_reason = alt.get("reason", "")
            label = f"**{alt_degree}**"
            if alt_major:
                label += f" — {alt_major}"
            st.markdown(label)
            st.caption(alt_reason)

# ── Notes ─────────────────────────────────────────────────────────────
if selected.notes:
    st.divider()
    st.subheader("Additional Notes")
    st.info(selected.notes)

render_theme_toggle()
