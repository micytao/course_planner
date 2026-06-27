"""Skills Manager — view and edit SKILL.md rules for UC course planning."""

import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.skill_loader import list_skill_files, load_skill, save_skill, validate_skill
from lib.theme import inject_theme_css, render_theme_toggle, get_theme


inject_theme_css()

t = get_theme()

st.title("Skills Manager")
st.caption("Browse and edit the SKILL.md rules that guide the AI course advisor.")

# ── Sidebar: File Selector ───────────────────────────────────────────

skill_files = list_skill_files()

if not skill_files:
    st.warning("No markdown files found in the `assets/` directory.")
    st.stop()

with st.sidebar:
    st.header("Skill Files")
    file_options = {f.name: f for f in skill_files}
    selected_name = st.radio(
        "Select a file to view or edit:",
        list(file_options.keys()),
        key="skill_file_selector",
    )

selected_path = file_options[selected_name]
skill_data = load_skill(selected_path)

# ── Frontmatter Info Card ────────────────────────────────────────────

fm = skill_data["frontmatter"]
if fm:
    with st.container(border=True):
        cols = st.columns([1, 3])
        with cols[0]:
            st.markdown("**Skill Name**")
            st.code(fm.get("name", "N/A"))
        with cols[1]:
            st.markdown("**Description**")
            st.write(fm.get("description", "No description provided."))

        meta_cols = st.columns(3)
        with meta_cols[0]:
            st.metric("Lines", skill_data["line_count"])
        with meta_cols[1]:
            status = "OK" if skill_data["line_count"] <= 500 else "Over limit"
            st.metric("Line Limit (500)", status)
        with meta_cols[2]:
            st.metric("File", selected_name)

# ── Tabs: Viewer / Editor / Validation ───────────────────────────────

tab_view, tab_edit, tab_validate = st.tabs(["Viewer", "Editor", "Validation"])

# ── Viewer Tab ───────────────────────────────────────────────────────

with tab_view:
    st.markdown(skill_data["body"], unsafe_allow_html=False)

# ── Editor Tab ───────────────────────────────────────────────────────

with tab_edit:
    editor_key = f"editor_{selected_name}"

    if editor_key not in st.session_state:
        st.session_state[editor_key] = skill_data["raw"]

    edited = st.text_area(
        "Edit file content:",
        value=st.session_state[editor_key],
        height=600,
        key=f"ta_{editor_key}",
    )

    col_save, col_reset, col_spacer = st.columns([1, 1, 4])

    with col_save:
        if st.button("Save Changes", type="primary", key="save_skill"):
            if edited == skill_data["raw"]:
                st.info("No changes detected.")
            else:
                warnings = validate_skill(edited)
                if warnings:
                    st.warning("Validation warnings (saving anyway):")
                    for w in warnings:
                        st.write(f"- {w}")

                if save_skill(selected_path, edited):
                    st.session_state[editor_key] = edited
                    st.success(f"Saved {selected_name} successfully.")
                    st.rerun()
                else:
                    st.error("Failed to save the file. Check file permissions.")

    with col_reset:
        if st.button("Reset", key="reset_skill"):
            st.session_state[editor_key] = skill_data["raw"]
            st.rerun()

    if edited != skill_data["raw"]:
        with st.expander("Preview Changes", expanded=True):
            original_lines = skill_data["raw"].splitlines()
            edited_lines = edited.splitlines()

            added = 0
            removed = 0
            for i, line in enumerate(edited_lines):
                if i >= len(original_lines) or line != original_lines[i]:
                    added += 1
            for i, line in enumerate(original_lines):
                if i >= len(edited_lines) or line != edited_lines[i]:
                    removed += 1

            st.write(f"**+{added} lines changed**, **-{removed} lines changed** "
                     f"(original: {len(original_lines)} lines, edited: {len(edited_lines)} lines)")

# ── Validation Tab ───────────────────────────────────────────────────

with tab_validate:
    content_to_validate = edited if "edited" in dir() else skill_data["raw"]
    warnings = validate_skill(content_to_validate)

    if not warnings:
        st.success("All validation checks passed.")
        st.markdown("""
**Checks performed:**
- Frontmatter present with `---` delimiters
- Required `name` field exists and follows conventions
- Required `description` field exists
- File is under 500 lines
        """)
    else:
        st.error(f"{len(warnings)} validation issue(s) found:")
        for w in warnings:
            st.write(f"- {w}")

    st.divider()
    st.markdown("### Skill Authoring Guidelines")
    st.markdown("""
- **name**: Max 64 characters, lowercase letters/numbers/hyphens only
- **description**: Specific, third-person, includes WHAT the skill does and WHEN to use it
- **Body**: Keep under 500 lines; use progressive disclosure (link to reference files)
- **Terminology**: Be consistent throughout (pick one term and stick with it)
- **Examples**: Include concrete examples, not abstract descriptions
    """)

render_theme_toggle()
