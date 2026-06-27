"""Datasets — knowledge base explorer with table and visual views."""

import asyncio
import json
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.theme import inject_theme_css, render_theme_toggle
from lib.mcp_factory import render_mcp_toggle

render_mcp_toggle()
inject_theme_css()

_KB = Path(__file__).resolve().parent.parent / "knowledge"

_RESOURCE_MAP = {
    "faculties.json": "data://faculties",
    "degrees.json": "data://degrees",
    "majors.json": "data://majors",
    "courses.json": "data://courses",
    "triage.json": "data://triage",
    "sample_students.json": "data://sample-students",
}


@st.cache_data
def _load(filename: str, _mtime: float = 0.0):
    with open(_KB / filename, encoding="utf-8") as f:
        return json.load(f)


def _load_local(filename: str):
    """Load JSON from local files with cache-busting."""
    mtime = (_KB / filename).stat().st_mtime
    return _load(filename, _mtime=mtime)


def _load_remote(filename: str) -> dict | list:
    """Load JSON from MCP server resources."""
    uri = _RESOURCE_MAP.get(filename)
    if not uri:
        return {}
    url = st.session_state.get("mcp_server_url", "http://localhost:8100").rstrip("/") + "/mcp"
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    async def _read():
        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client
        async with streamable_http_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.read_resource(uri)
                return json.loads(result.contents[0].text)

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, _read()).result(timeout=30)
    return asyncio.run(_read())


def _load_fresh(filename: str):
    """Load data from local files or remote MCP server based on toggle."""
    if st.session_state.get("mcp_remote_mode"):
        return _load_remote(filename)
    return _load_local(filename)


def _list_to_str(val) -> str:
    if isinstance(val, list):
        return ", ".join(str(v) for v in val)
    if isinstance(val, dict):
        return json.dumps(val, default=str)
    if val is None:
        return "—"
    return str(val)


st.title("Datasets")
st.caption("Browse the knowledge base that powers the Course Planner.")

DATASETS = {
    "Faculties": "faculties.json",
    "Degrees": "degrees.json",
    "Majors": "majors.json",
    "Courses": "courses.json",
    "Triage Steps": "triage.json",
    "Sample Students": "sample_students.json",
}

with st.sidebar:
    st.header("Datasets")
    selected = st.radio("Select a dataset:", list(DATASETS.keys()), key="ds_selector")
    st.divider()
    view_mode = st.radio("View mode:", ["Table", "Visual"], key="view_mode", horizontal=True)
    st.divider()
    if st.session_state.get("mcp_remote_mode"):
        uri = _RESOURCE_MAP.get(DATASETS[selected], "")
        st.caption(f"Source: `{uri}`")
        st.caption("Mode: Remote MCP")
    else:
        filepath = _KB / DATASETS[selected]
        size_kb = filepath.stat().st_size / 1024
        st.caption(f"Source: `{DATASETS[selected]}`")
        st.caption(f"Size: {size_kb:.1f} KB")

data = _load_fresh(DATASETS[selected])
TABLE_MODE = view_mode == "Table"


# ── Faculties ────────────────────────────────────────────────────────

if selected == "Faculties":
    st.header(f"Faculties ({len(data)})")

    if TABLE_MODE:
        rows = []
        for f in data:
            rows.append({
                "code": f["code"],
                "name": f["name"],
                "short_name": f["short_name"],
                "description": f["description"],
                "interest_keywords": ", ".join(f.get("interest_keywords", [])),
                "schools": ", ".join(f.get("schools", [])),
            })
        st.dataframe(rows, width="stretch", hide_index=True, height=350)
    else:
        cols = st.columns(2)
        for i, fac in enumerate(data):
            with cols[i % 2]:
                with st.container(border=True):
                    st.subheader(fac["short_name"])
                    st.caption(fac["code"].upper())
                    st.write(fac["description"])
                    with st.expander("Schools"):
                        for s in fac.get("schools", []):
                            st.markdown(f"- {s}")
                    with st.expander("Interest Keywords"):
                        st.markdown(", ".join(f"`{k}`" for k in fac.get("interest_keywords", [])))


# ── Degrees ──────────────────────────────────────────────────────────

elif selected == "Degrees":
    st.header(f"Degrees ({len(data)})")

    faculty_filter = st.selectbox(
        "Filter by faculty:",
        ["All"] + sorted(set(d["faculty"] for d in data)),
        key="deg_filter",
    )
    filtered = data if faculty_filter == "All" else [d for d in data if d["faculty"] == faculty_filter]

    if TABLE_MODE:
        rows = []
        for d in filtered:
            struct = d.get("structure", {})
            rows.append({
                "code": d["code"],
                "name": d["name"],
                "faculty": d["faculty"],
                "degree_type": d.get("degree_type", "bachelor"),
                "points": d["points"],
                "duration_years": d["duration_years"],
                "schedule_c_courses": ", ".join(d.get("schedule_c_courses", [])),
                "schedule_e_courses": ", ".join(d.get("schedule_e_courses", [])),
                "schedule_s_courses": ", ".join(d.get("schedule_s_courses", [])),
                "pathway_options": ", ".join(d.get("pathway_options", [])),
                "above_100_min": str(struct.get("above_100_min", "—")),
                "at_300_min": str(struct.get("at_300_min", "—")),
                "schedule_v_min": str(struct.get("schedule_v_min", "—")),
                "schedule_c_min": str(struct.get("schedule_c_min", "—")),
                "admission": d.get("admission", ""),
                "notes": d.get("notes", ""),
            })
        st.dataframe(rows, width="stretch", hide_index=True, height=500)
    else:
        overview = []
        for d in filtered:
            dtype = d.get("degree_type", "bachelor")
            badge = {"bachelor": "🎓", "certificate": "📜", "diploma": "📋"}.get(dtype, "")
            overview.append({
                "Code": d["code"],
                "Name": d["name"],
                "Type": f"{badge} {dtype.title()}",
                "Faculty": d["faculty"].title(),
                "Points": d["points"],
                "Years": d["duration_years"],
            })
        st.dataframe(overview, width="stretch", hide_index=True)

        st.divider()
        degree_codes = [d["code"] for d in filtered]
        if degree_codes:
            detail_code = st.selectbox("View degree details:", degree_codes, key="deg_detail")
            deg = next(d for d in filtered if d["code"] == detail_code)

            col1, col2, col3 = st.columns(3)
            col1.metric("Total Points", deg["points"])
            col2.metric("Duration", f"{deg['duration_years']} year(s)")
            col3.metric("Faculty", deg["faculty"].title())

            if deg.get("schedule_c_courses"):
                label = "**Schedule C (Compulsory):** "
                if deg.get("schedule_c_note"):
                    label = f"**Schedule C — {deg['schedule_c_note']}:** "
                st.markdown(label + ", ".join(f"`{c}`" for c in deg["schedule_c_courses"]))
            if deg.get("schedule_e_courses"):
                label = "**Schedule E (Elective):** "
                if deg.get("schedule_e_note"):
                    label = f"**Schedule E — {deg['schedule_e_note']}:** "
                st.markdown(label + ", ".join(f"`{c}`" for c in deg["schedule_e_courses"]))
            if deg.get("schedule_s_courses"):
                label = "**Schedule S (Subject/Major):** "
                if deg.get("schedule_s_note"):
                    label = f"**Schedule S — {deg['schedule_s_note']}:** "
                st.markdown(label + ", ".join(f"`{c}`" for c in deg["schedule_s_courses"]))
            if deg.get("pathway_options"):
                st.markdown("**Pathways:** " + " | ".join(deg["pathway_options"]))
            if deg.get("admission"):
                st.info(deg["admission"])
            if deg.get("notes"):
                st.caption(deg["notes"])

            struct = deg.get("structure", {})
            if any(v is not None for v in struct.values()):
                with st.expander("Degree Structure Rules"):
                    for k, v in struct.items():
                        if v is not None:
                            label = k.replace("_", " ").title()
                            st.markdown(f"- **{label}:** {v}")


# ── Majors ───────────────────────────────────────────────────────────

elif selected == "Majors":
    degree_keys = list(data.keys())
    selected_deg = st.selectbox("Select a degree:", degree_keys, key="maj_deg")
    entry = data[selected_deg]

    if "majors" in entry:
        majors = entry["majors"]
        st.header(f"Majors for {selected_deg} ({len(majors)})")

        if TABLE_MODE:
            rows = []
            for m in majors:
                rows.append({
                    "degree": selected_deg,
                    "name": m["name"],
                    "required_100": ", ".join(m.get("required_100", [])),
                    "required_200": ", ".join(m.get("required_200", [])),
                    "required_300": ", ".join(m.get("required_300", [])),
                    "honours_req": m.get("honours_req", "—"),
                    "has_minor": m.get("has_minor", True),
                    "notes": m.get("notes", ""),
                })
            st.dataframe(rows, width="stretch", hide_index=True, height=500)
        else:
            for m in majors:
                with st.expander(m["name"]):
                    if m.get("required_100"):
                        st.markdown("**100-level:** " + " | ".join(m["required_100"]))
                    if m.get("required_200"):
                        st.markdown("**200-level:** " + " | ".join(m["required_200"]))
                    if m.get("required_300"):
                        st.markdown("**300-level:** " + " | ".join(m["required_300"]))
                    if m.get("honours_req"):
                        st.caption(f"Honours: {m['honours_req']}")
                    if m.get("notes"):
                        st.caption(m["notes"])

    elif "disciplines" in entry:
        discs = entry["disciplines"]
        st.header(f"Engineering Disciplines ({len(discs)})")
        rows = []
        for d in discs:
            rows.append({
                "degree" if TABLE_MODE else "Discipline": selected_deg if TABLE_MODE else d["name"],
                "name" if TABLE_MODE else "Places": d["name"] if TABLE_MODE else d.get("places", "?"),
                "places" if TABLE_MODE else "Year 1 Extras": d.get("places", "—") if TABLE_MODE else ", ".join(d.get("first_year_extras", [])),
                "first_year_extras" if TABLE_MODE else "Minors": ", ".join(d.get("first_year_extras", [])) if TABLE_MODE else (", ".join(d.get("minors", [])) or "—"),
            })
            if TABLE_MODE:
                rows[-1]["minors"] = ", ".join(d.get("minors", [])) or "—"
        st.dataframe(rows, width="stretch", hide_index=True)

    elif "endorsements" in entry:
        endrs = entry["endorsements"]
        st.header(f"Endorsements ({len(endrs)})")
        if TABLE_MODE:
            rows = [{"degree": selected_deg, "name": e["name"], "group": e.get("group", "—"), "notes": e.get("notes", "")} for e in endrs]
            st.dataframe(rows, width="stretch", hide_index=True)
        else:
            for e in endrs:
                with st.expander(e["name"]):
                    if e.get("notes"):
                        st.write(e["notes"])
                    if e.get("group"):
                        st.caption(f"Group: {e['group']}")

    elif "group1_minors" in entry:
        minors = entry["group1_minors"]
        st.header(f"Group 1 Minors ({len(minors)})")
        if TABLE_MODE:
            rows = [{"degree": selected_deg, "name": m["name"], "notes": m.get("notes", "")} for m in minors]
            st.dataframe(rows, width="stretch", hide_index=True)
        else:
            for m in minors:
                st.markdown(f"- **{m['name']}**" + (f" — {m.get('notes', '')}" if m.get("notes") else ""))

    else:
        st.header(f"{selected_deg} — Fixed Programme")
        if TABLE_MODE:
            rows = [{"key": k, "value": _list_to_str(v)} for k, v in entry.items()]
            st.dataframe(rows, width="stretch", hide_index=True)
        else:
            st.info(f"{selected_deg} has a fixed programme (no major selection).")
            for k, v in entry.items():
                st.markdown(f"**{k.replace('_', ' ').title()}:** {_list_to_str(v)}")

    if "specialisations" in entry:
        st.divider()
        specs = entry["specialisations"]
        st.subheader(f"Specialisations ({len(specs)})")
        if TABLE_MODE:
            rows = [{"degree": selected_deg, "name": s["name"], "min_points": s.get("min_points", "—")} for s in specs]
            st.dataframe(rows, width="stretch", hide_index=True)
        else:
            for s in specs:
                st.markdown(f"- **{s['name']}** ({s.get('min_points', '?')} pts)")

    if "minors_only" in entry:
        st.divider()
        mo = entry["minors_only"]
        st.subheader(f"Minor-only Options ({len(mo)})")
        if TABLE_MODE:
            rows = [{"degree": selected_deg, "name": m["name"], "notes": m.get("notes", "")} for m in mo]
            st.dataframe(rows, width="stretch", hide_index=True)
        else:
            for m in mo:
                st.markdown(f"- **{m['name']}**" + (f" — {m.get('notes', '')}" if m.get("notes") else ""))


# ── Courses ──────────────────────────────────────────────────────────

elif selected == "Courses":
    st.header(f"Courses ({len(data)})")

    col1, col2 = st.columns(2)
    with col1:
        fac_filter = st.selectbox(
            "Filter by faculty:",
            ["All"] + sorted(set(c.get("faculty", "") for c in data.values() if c.get("faculty"))),
            key="c_fac",
        )
    with col2:
        lvl_filter = st.selectbox("Filter by level:", ["All", 100, 200, 300, 400], key="c_lvl")

    filtered = {}
    for code in sorted(data.keys()):
        c = data[code]
        if fac_filter != "All" and c.get("faculty") != fac_filter:
            continue
        if lvl_filter != "All" and c.get("level") != lvl_filter:
            continue
        filtered[code] = c

    st.caption(f"Showing {len(filtered)} of {len(data)} courses")

    rows = []
    for code, c in filtered.items():
        rows.append({
            "code": c["code"],
            "title": c["title"],
            "points": c["points"],
            "level": c["level"],
            "semesters": ", ".join(c.get("semesters", [])),
            "faculty": c.get("faculty", ""),
            "prerequisites": ", ".join(c.get("prerequisites", [])) or "—",
            "corequisites": ", ".join(c.get("corequisites", [])) or "—",
            "restrictions": ", ".join(c.get("restrictions", [])) or "—",
            "limited_entry": str(c["limited_entry"]) if c.get("limited_entry") else "—",
        })
    st.dataframe(rows, width="stretch", hide_index=True, height=500)

    if not TABLE_MODE and filtered:
        st.divider()
        detail_code = st.selectbox("View course details:", sorted(filtered.keys()), key="course_detail")
        c = filtered[detail_code]

        st.subheader(f"{c['code']} — {c['title']}")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Points", c["points"])
        m2.metric("Level", c["level"])
        m3.metric("Semesters", ", ".join(c.get("semesters", [])))
        m4.metric("Faculty", c.get("faculty", "").title())

        if c.get("prerequisites"):
            st.markdown("**Prerequisites:** " + ", ".join(c["prerequisites"]))
        if c.get("corequisites"):
            st.markdown("**Corequisites:** " + ", ".join(c["corequisites"]))
        if c.get("restrictions"):
            st.warning("**Restrictions:** " + ", ".join(c["restrictions"]))
        if c.get("limited_entry"):
            st.info(f"**Limited entry:** {c['limited_entry']} places")


# ── Triage Steps ─────────────────────────────────────────────────────

elif selected == "Triage Steps":
    st.header("Triage Decision Tree")

    if TABLE_MODE:
        tab_steps, tab_options, tab_cross = st.tabs(["steps", "step_options", "cross_faculty_subjects"])

        with tab_steps:
            steps = data.get("steps", [])
            st.caption(f"{len(steps)} rows")
            rows = [{"id": s["id"], "question": s["question"], "terminal": s.get("terminal", False), "option_count": len(s.get("options", []))} for s in steps]
            st.dataframe(rows, width="stretch", hide_index=True)

        with tab_options:
            rows = []
            for s in data.get("steps", []):
                for o in s.get("options", []):
                    rows.append({"step_id": s["id"], "value": o["value"], "label": o["label"], "faculty": o.get("faculty", "—"), "next_step": o.get("next", "—")})
            st.caption(f"{len(rows)} rows")
            st.dataframe(rows, width="stretch", hide_index=True, height=400)

        with tab_cross:
            cross = data.get("cross_faculty_subjects", {})
            rows = [{"subject": subj, "faculties": ", ".join(info.get("faculties", [])), "degrees": ", ".join(info.get("degrees", [])), "note": info.get("note", "")} for subj, info in cross.items()]
            st.caption(f"{len(rows)} rows")
            st.dataframe(rows, width="stretch", hide_index=True)
    else:
        tab_steps, tab_cross = st.tabs(["Decision Steps", "Cross-Faculty Subjects"])

        with tab_steps:
            for step in data.get("steps", []):
                with st.container(border=True):
                    st.markdown(f"**Step: `{step['id']}`**")
                    st.write(step["question"])
                    if step.get("terminal"):
                        st.error("Terminal step — conversation ends here.")
                    options = step.get("options", [])
                    if options:
                        rows = []
                        for o in options:
                            row = {"Label": o["label"], "Value": o["value"]}
                            if o.get("faculty"):
                                row["Faculty"] = o["faculty"]
                            if o.get("next"):
                                row["Next Step"] = o["next"]
                            rows.append(row)
                        st.dataframe(rows, width="stretch", hide_index=True)

        with tab_cross:
            cross = data.get("cross_faculty_subjects", {})
            for subject, info in cross.items():
                with st.expander(subject.replace("_", " ").title()):
                    st.markdown("**Faculties:** " + ", ".join(info.get("faculties", [])))
                    st.markdown("**Degrees:** " + ", ".join(f"`{d}`" for d in info.get("degrees", [])))
                    if info.get("note"):
                        st.info(info["note"])


# ── Sample Students ──────────────────────────────────────────────────

elif selected == "Sample Students":
    st.header(f"Sample Students ({len(data)})")

    if TABLE_MODE:
        tab_students, tab_plans, tab_alts = st.tabs(["students", "year1_plans", "alternative_paths"])

        with tab_students:
            rows = []
            for s in data:
                bg = s.get("background", {})
                rows.append({
                    "id": s["id"],
                    "name": s["name"],
                    "description": s["description"],
                    "qualification_type": bg.get("qualification_type", ""),
                    "has_ue": bg.get("has_ue", False),
                    "has_maths": bg.get("has_maths", False),
                    "has_physics": bg.get("has_physics", False),
                    "domestic": bg.get("domestic", True),
                    "interests": ", ".join(s.get("interests", [])),
                    "suggested_faculty": s.get("suggested_faculty", ""),
                    "suggested_degree": s.get("suggested_degree", ""),
                    "suggested_major": s.get("suggested_major") or "—",
                    "double_degree": s.get("double_degree") or "—",
                })
            st.caption(f"{len(rows)} rows")
            st.dataframe(rows, width="stretch", hide_index=True)

        with tab_plans:
            rows = []
            for s in data:
                for e in s.get("year1_plan", []):
                    rows.append({"student_id": s["id"], "student_name": s["name"], "course": e["course"], "semester": e["semester"], "points": e["points"], "note": e.get("note", "")})
            st.caption(f"{len(rows)} rows")
            st.dataframe(rows, width="stretch", hide_index=True, height=500)

        with tab_alts:
            rows = []
            for s in data:
                for alt in s.get("alternative_paths", []):
                    rows.append({"student_id": s["id"], "student_name": s["name"], "degree": alt.get("degree", ""), "faculty": alt.get("faculty", ""), "major": alt.get("major", "—"), "reason": alt.get("reason", "")})
            st.caption(f"{len(rows)} rows")
            st.dataframe(rows, width="stretch", hide_index=True)
    else:
        for student in data:
            with st.expander(f"**{student['name']}** — {student['description']}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Background:**")
                    bg = student.get("background", {})
                    st.markdown(
                        f"- Qualification: {bg.get('qualification_type', '?')}\n"
                        f"- UE: {'Yes' if bg.get('has_ue') else 'No'}\n"
                        f"- Maths: {'Yes' if bg.get('has_maths') else 'No'}\n"
                        f"- Physics: {'Yes' if bg.get('has_physics') else 'No'}\n"
                        f"- Domestic: {'Yes' if bg.get('domestic') else 'No'}"
                    )
                    st.markdown("**Interests:** " + ", ".join(student.get("interests", [])))

                with col2:
                    st.markdown("**Suggested Path:**")
                    st.markdown(
                        f"- Faculty: `{student.get('suggested_faculty', '?')}`\n"
                        f"- Degree: `{student.get('suggested_degree', '?')}`\n"
                        f"- Major: {student.get('suggested_major') or '—'}"
                    )
                    if student.get("double_degree"):
                        st.markdown(f"- Double degree: `{student['double_degree']}`")

                if student.get("alternative_paths"):
                    st.markdown("**Alternative Paths:**")
                    for alt in student["alternative_paths"]:
                        st.markdown(f"- `{alt.get('degree', '?')}` ({alt.get('faculty', '?')}) — {alt.get('reason', '')}")

                if student.get("year1_plan"):
                    st.markdown("**Year 1 Plan:**")
                    plan_rows = [{"Course": e["course"], "Semester": e["semester"], "Points": e["points"], "Note": e.get("note", "")} for e in student["year1_plan"]]
                    st.dataframe(plan_rows, width="stretch", hide_index=True)

                if student.get("demo_narrative"):
                    st.caption(f"Demo narrative: {student['demo_narrative']}")

render_theme_toggle()
