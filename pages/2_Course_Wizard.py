"""Step-by-step guided wizard for course planning."""

import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.models import StudentBackground
from lib.theme import inject_theme_css, render_theme_toggle, get_theme
from lib.mcp_factory import render_mcp_toggle, get_mcp_client, get_engine


render_mcp_toggle()
inject_theme_css()

mcp = get_mcp_client()
engine = get_engine(mcp)

if "wizard_step" not in st.session_state:
    st.session_state.wizard_step = 1
if "wizard_data" not in st.session_state:
    st.session_state.wizard_data = {}


def go_to(step: int) -> None:
    st.session_state.wizard_step = step


def reset_wizard() -> None:
    st.session_state.wizard_step = 1
    st.session_state.wizard_data = {}


st.title("Course Planning Wizard")
st.caption("Follow the steps below to build your personalised Year 1 course plan.")

_STEP_LABELS = [
    "Study Level",
    "Interests",
    "Degree",
    "Major",
    "Background",
    "Year 1 Plan",
    "Summary",
]

def _render_stepper(current: int) -> None:
    """Render a visual step indicator showing all 7 steps."""
    t = get_theme()
    done_color = "#28a745"
    active_color = t["primary"]
    pending_bg = t["card_border"]
    pending_text = t["text_secondary"]
    label_text = t["text"]

    cols = st.columns(len(_STEP_LABELS))
    for i, (col, label) in enumerate(zip(cols, _STEP_LABELS), start=1):
        with col:
            if i < current:
                st.markdown(
                    f"<div style='text-align:center'>"
                    f"<div style='width:32px;height:32px;border-radius:50%;background:{done_color};"
                    f"color:white;margin:0 auto;line-height:32px;font-weight:bold'>✓</div>"
                    f"<div style='font-size:0.75rem;margin-top:4px;color:{done_color}'>{label}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            elif i == current:
                st.markdown(
                    f"<div style='text-align:center'>"
                    f"<div style='width:32px;height:32px;border-radius:50%;background:{active_color};"
                    f"color:white;margin:0 auto;line-height:32px;font-weight:bold'>{i}</div>"
                    f"<div style='font-size:0.75rem;margin-top:4px;font-weight:bold;color:{active_color}'>{label}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<div style='text-align:center'>"
                    f"<div style='width:32px;height:32px;border-radius:50%;background:{pending_bg};"
                    f"color:{pending_text};margin:0 auto;line-height:32px;font-weight:bold'>{i}</div>"
                    f"<div style='font-size:0.75rem;margin-top:4px;color:{pending_text}'>{label}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

_render_stepper(st.session_state.wizard_step)

with st.expander("View Triage Decision Tree"):
    st.graphviz_chart("""
    digraph triage {
        rankdir=TB
        node [shape=box style="rounded,filled" fontname="Helvetica" fontsize=11 margin="0.2,0.1"]
        edge [fontname="Helvetica" fontsize=9]

        start [label="Start" shape=circle fillcolor="#007bff" fontcolor=white width=0.6]

        step1 [label="Step 1\\nStudy Level" fillcolor="#e3f2fd"]
        step2 [label="Step 2\\nInterests / Faculty" fillcolor="#e3f2fd"]
        step3 [label="Step 3\\nDegree Selection\\n(dynamic)" fillcolor="#e3f2fd"]
        step4 [label="Step 4\\nMajor / Endorsement\\n(dynamic)" fillcolor="#e3f2fd"]
        step5 [label="Step 5\\nBackground Check" fillcolor="#e3f2fd"]
        step6 [label="Step 6\\nYear 1 Plan\\n(generated)" fillcolor="#e3f2fd"]
        step7 [label="Step 7\\nSummary & Export" fillcolor="#c8e6c9"]

        postgrad [label="Postgraduate\\nRedirect to Faculty\\n& UC website" fillcolor="#fff3e0" shape=note]
        unsure [label="Free Text\\nExplore Interests" fillcolor="#f3e5f5"]

        start -> step1
        step1 -> step2 [label="Undergraduate"]
        step1 -> postgrad [label="Postgraduate"]
        postgrad -> step2 [label="Switch to\\nundergrad" style=dashed]
        step2 -> step3 [label="Select faculty"]
        step2 -> unsure [label="Not sure"]
        unsure -> step2 [label="Re-select" style=dashed]
        step3 -> step4 [label="Select degree"]
        step4 -> step5 [label="Select major"]
        step5 -> step6 [label="Submit"]
        step6 -> step7 [label="Continue"]
        step7 -> step1 [label="Start over" style=dashed color="#999"]
    }
    """)

st.divider()

# ── Load triage data once ────────────────────────────────────────────
_triage = mcp.get_triage_data()
_triage_steps = {s["id"]: s for s in _triage["steps"]}

# ── Step 1: Study Level ──────────────────────────────────────────────
if st.session_state.wizard_step == 1:
    _sl = _triage_steps["study_level"]
    st.header("Step 1: Study Level")
    st.write(_sl["question"])

    _sl_opts = _sl["options"]
    cols = st.columns(len(_sl_opts))
    for col, opt in zip(cols, _sl_opts):
        with col:
            is_primary = opt["value"] == "undergraduate"
            if st.button(opt["label"], use_container_width=True,
                         type="primary" if is_primary else "secondary"):
                if opt["next"] == "postgrad_note":
                    _pg = _triage_steps["postgrad_note"]
                    st.info(_pg["question"])
                    if _pg.get("hint"):
                        st.info(_pg["hint"])
                else:
                    st.session_state.wizard_data["study_level"] = opt["value"]
                    go_to(2)
                    st.rerun()

# ── Step 2: Interest Area / Faculty ──────────────────────────────────
elif st.session_state.wizard_step == 2:
    _ia = _triage_steps["interest_area"]
    st.header("Step 2: What interests you?")
    st.write(_ia["question"])

    faculties = mcp.get_faculties()
    faculty_options = [opt for opt in _ia["options"] if opt["value"] != "unsure"]

    cols = st.columns(2)
    for i, opt in enumerate(faculty_options):
        code = opt.get("faculty", opt["value"])
        fac = next((f for f in faculties if f.code == code), None)
        with cols[i % 2]:
            with st.container(border=True):
                st.subheader(fac.short_name if fac else code.title())
                st.write(opt["label"])
                if fac:
                    st.caption(fac.description)
                if st.button("Select", key=f"fac_{code}", use_container_width=True):
                    st.session_state.wizard_data["faculty"] = code
                    go_to(3)
                    st.rerun()

    st.divider()
    if st.button("← Back"):
        go_to(1)
        st.rerun()

# ── Step 3: Degree Selection ─────────────────────────────────────────
elif st.session_state.wizard_step == 3:
    faculty_code = st.session_state.wizard_data.get("faculty", "")
    faculty = mcp.get_faculty(faculty_code)
    degrees = mcp.get_available_degrees(faculty_code)

    bachelor_degrees = [d for d in degrees if getattr(d, "degree_type", "bachelor") == "bachelor"]
    cert_diplomas = [d for d in degrees if getattr(d, "degree_type", "bachelor") in ("certificate", "diploma")]

    st.header(f"Step 3: Choose a Qualification — {faculty.short_name if faculty else ''}")
    st.write(f"These are the qualifications available in {faculty.short_name if faculty else 'your selected faculty'}.")

    if bachelor_degrees:
        st.subheader("Bachelor Degrees")
        for deg in bachelor_degrees:
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.subheader(f"{deg.code} — {deg.name}")
                    st.write(f"**{deg.points} points** | {deg.duration_years} years")
                    if deg.pathway_options:
                        st.caption("Pathways: " + " | ".join(deg.pathway_options))
                with col2:
                    if deg.admission and ("limited" in deg.admission.lower() or "special" in deg.admission.lower()):
                        st.warning("Special entry", icon="⚠️")
                with col3:
                    if st.button("Select", key=f"deg_{deg.code}", use_container_width=True):
                        st.session_state.wizard_data["degree"] = deg.code
                        st.session_state.wizard_data["degree_name"] = deg.name
                        go_to(4)
                        st.rerun()

    if cert_diplomas:
        st.divider()
        st.subheader("Certificates & Diplomas")
        st.caption("Shorter qualifications — great as a pathway, taster, or alongside another degree.")
        for deg in cert_diplomas:
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    badge = "Certificate" if deg.degree_type == "certificate" else "Diploma"
                    st.subheader(f"{deg.code} — {deg.name}")
                    st.write(f"**{deg.points} points** | {badge} | {deg.duration_years} year{'s' if deg.duration_years > 1 else ''}")
                    if deg.notes:
                        st.caption(deg.notes)
                with col2:
                    st.info(badge, icon="📜")
                with col3:
                    if st.button("Select", key=f"deg_{deg.code}", use_container_width=True):
                        st.session_state.wizard_data["degree"] = deg.code
                        st.session_state.wizard_data["degree_name"] = deg.name
                        go_to(4)
                        st.rerun()

    st.divider()
    if st.button("← Back"):
        go_to(2)
        st.rerun()

# ── Step 4: Major / Endorsement / Discipline ─────────────────────────
elif st.session_state.wizard_step == 4:
    degree_code = st.session_state.wizard_data.get("degree", "")
    degree = mcp.get_degree(degree_code)
    majors = mcp.get_majors_for_degree(degree_code)

    st.header(f"Step 4: Choose Your Focus — {degree_code}")

    if not majors:
        st.info(
            f"{degree.name if degree else degree_code} is a fixed programme — "
            "no major selection required."
        )
        st.session_state.wizard_data["major"] = None
        if st.button("Continue →", type="primary"):
            go_to(5)
            st.rerun()
    else:
        if degree_code == "BE(Hons)":
            label = "discipline"
        elif degree_code == "BTchLn":
            label = "endorsement"
        elif degree_code == "BPsycSc":
            label = "Group 1 minor"
        else:
            label = "major"

        st.write(f"Select your {label}:")

        cols = st.columns(3)
        for i, m in enumerate(majors):
            with cols[i % 3]:
                with st.container(border=True):
                    st.markdown(f"**{m.name}**")
                    if m.notes:
                        st.caption(m.notes)
                    if st.button("Select", key=f"maj_{m.name}", use_container_width=True):
                        st.session_state.wizard_data["major"] = m.name
                        go_to(5)
                        st.rerun()

        if degree_code == "BA":
            specs = mcp.get_specialisations("BA")
            if specs:
                st.divider()
                st.subheader("Or choose a Specialisation (instead of major + minor)")
                cols = st.columns(3)
                for i, s in enumerate(specs):
                    with cols[i % 3]:
                        with st.container(border=True):
                            st.markdown(f"**{s['name']}**")
                            if st.button("Select", key=f"spec_{s['name']}", use_container_width=True):
                                st.session_state.wizard_data["major"] = s["name"]
                                st.session_state.wizard_data["is_specialisation"] = True
                                go_to(5)
                                st.rerun()

    st.divider()
    if st.button("← Back"):
        go_to(3)
        st.rerun()

# ── Step 5: Background Check ─────────────────────────────────────────
elif st.session_state.wizard_step == 5:
    st.header("Step 5: Your Background")
    st.write("Tell us about your qualifications so we can check entry requirements and prerequisites.")

    with st.form("background_form"):
        qual_type = st.selectbox(
            "Qualification type",
            ["NCEA", "Cambridge International", "International Baccalaureate",
             "Other NZ qualification", "Overseas qualification", "Mature student (20+)"],
        )
        has_ue = st.checkbox("I have (or expect to have) University Entrance", value=True)
        has_maths = st.checkbox("I have studied Mathematics at Year 13 / Level 3")
        has_physics = st.checkbox("I have studied Physics at Year 13 / Level 3")
        has_chemistry = st.checkbox("I have studied Chemistry at Year 13 / Level 3")
        domestic = st.checkbox("I am a domestic (NZ/Australian) student", value=True)

        submitted = st.form_submit_button("Check & Continue →", type="primary")

        if submitted:
            bg = StudentBackground(
                qualification_type=qual_type,
                has_ue=has_ue,
                has_maths=has_maths,
                has_physics=has_physics,
                has_chemistry=has_chemistry,
                domestic=domestic,
            )
            st.session_state.wizard_data["background"] = bg.model_dump()

            degree_code = st.session_state.wizard_data.get("degree", "")
            validation = engine.validate_admission(degree_code, bg)

            for msg in validation.messages:
                if msg.level == "error":
                    st.error(msg.message)
                elif msg.level == "warning":
                    st.warning(msg.message)
                else:
                    st.info(msg.message)

            major_name = st.session_state.wizard_data.get("major")
            if major_name:
                major_val = engine.validate_degree_major_combination(degree_code, major_name)
                for msg in major_val.messages:
                    if msg.level == "error":
                        st.error(msg.message)
                    elif msg.level == "warning":
                        st.warning(msg.message)
                    else:
                        st.info(msg.message)

            go_to(6)
            st.rerun()

    st.divider()
    if st.button("← Back"):
        go_to(4)
        st.rerun()

# ── Step 6: Year 1 Course Plan ───────────────────────────────────────
elif st.session_state.wizard_step == 6:
    st.header("Step 6: Your Year 1 Course Plan")

    degree_code = st.session_state.wizard_data.get("degree", "")
    major = st.session_state.wizard_data.get("major")
    bg_data = st.session_state.wizard_data.get("background", {})
    bg = StudentBackground(**bg_data) if bg_data else StudentBackground()

    plan = mcp.generate_year1_plan(degree_code, major, bg)

    st.subheader(plan.notes)

    if plan.entries:
        s1 = [e for e in plan.entries if e.semester in ("S1", "W")]
        s2 = [e for e in plan.entries if e.semester == "S2"]
        other = [e for e in plan.entries if e.semester not in ("S1", "S2", "W")]

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Semester 1")
            for e in s1:
                course = mcp.get_course_details(e.course)
                with st.container(border=True):
                    st.markdown(f"**{e.course}** — {course.title if course else 'Unknown'}")
                    st.caption(f"{e.points} pts | {e.note}")

        with col2:
            st.markdown("### Semester 2")
            for e in s2:
                course = mcp.get_course_details(e.course)
                with st.container(border=True):
                    st.markdown(f"**{e.course}** — {course.title if course else 'Unknown'}")
                    st.caption(f"{e.points} pts | {e.note}")

        if other:
            st.markdown("### Other")
            for e in other:
                course = mcp.get_course_details(e.course)
                with st.container(border=True):
                    st.markdown(f"**{e.course}** — {course.title if course else 'Unknown'}")
                    st.caption(f"{e.points} pts | {e.semester} | {e.note}")

        st.metric("Total Points", f"{plan.total_points} pts")
    else:
        st.warning("Could not generate a course plan. Please go back and adjust your selections.")

    st.divider()
    col_back, col_next = st.columns(2)
    with col_back:
        if st.button("← Back"):
            go_to(5)
            st.rerun()
    with col_next:
        if st.button("Continue to Summary →", type="primary"):
            go_to(7)
            st.rerun()

# ── Step 7: Summary & Export ─────────────────────────────────────────
elif st.session_state.wizard_step == 7:
    st.header("Step 7: Your Course Plan Summary")

    data = st.session_state.wizard_data
    degree_code = data.get("degree", "")
    degree = mcp.get_degree(degree_code)
    major = data.get("major")
    bg_data = data.get("background", {})
    bg = StudentBackground(**bg_data) if bg_data else StudentBackground()
    faculty = mcp.get_faculty(data.get("faculty", ""))

    st.subheader("Your Selections")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"**Faculty:** {faculty.short_name if faculty else 'N/A'}")
    with col2:
        st.markdown(f"**Degree:** {degree.name if degree else degree_code} ({degree.points if degree else '?'} pts)")
    with col3:
        st.markdown(f"**Major:** {major or 'Fixed programme'}")

    st.divider()

    plan = mcp.generate_year1_plan(degree_code, major, bg)

    st.subheader("Year 1 Course Plan")
    if plan.entries:
        import pandas as pd
        rows = []
        for e in plan.entries:
            course = mcp.get_course_details(e.course)
            rows.append({
                "Code": e.course,
                "Title": course.title if course else "—",
                "Semester": e.semester,
                "Points": e.points,
                "Type": e.note,
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, width="stretch", hide_index=True)
        st.metric("Total Year 1 Points", f"{plan.total_points} pts")

    st.divider()

    validation = engine.validate_admission(degree_code, bg)
    if validation.messages:
        st.subheader("Admission Notes")
        for msg in validation.messages:
            if msg.level == "error":
                st.error(msg.message)
            elif msg.level == "warning":
                st.warning(msg.message)
            else:
                st.info(msg.message)

    st.divider()

    summary_text = f"""UC Course Plan Summary
=======================
Faculty: {faculty.short_name if faculty else 'N/A'}
Degree: {degree.name if degree else degree_code} ({degree.points if degree else '?'} pts, {degree.duration_years if degree else '?'} years)
Major: {major or 'Fixed programme'}

Year 1 Courses:
"""
    if plan.entries:
        for e in plan.entries:
            course = mcp.get_course_details(e.course)
            summary_text += f"  {e.course} — {course.title if course else '—'} ({e.points} pts, {e.semester}) [{e.note}]\n"
        summary_text += f"\nTotal Year 1 Points: {plan.total_points}\n"

    if degree and degree.notes:
        summary_text += f"\nNotes: {degree.notes}\n"

    st.download_button(
        "Download Plan as Text",
        data=summary_text,
        file_name="uc_course_plan.txt",
        mime="text/plain",
        type="primary",
    )

    st.divider()
    if st.button("Start Over", type="secondary"):
        reset_wizard()
        st.rerun()

render_theme_toggle()
