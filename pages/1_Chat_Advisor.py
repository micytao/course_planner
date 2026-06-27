"""Conversational chatbot page for course planning advice."""

import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.llm_client import LLMClient
from lib.skill_loader import load_skill
from lib.theme import inject_theme_css, render_theme_toggle
from lib.mcp_factory import get_mcp_client

inject_theme_css()

mcp = get_mcp_client()

_ASSETS = Path(__file__).resolve().parent.parent / "assets"

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "llm_client" not in st.session_state:
    st.session_state.llm_client = None
if "llm_configured" not in st.session_state:
    st.session_state.llm_configured = False
if "available_models" not in st.session_state:
    st.session_state.available_models = []


def fetch_models(base_url: str, api_key: str) -> list[str]:
    """Fetch available models from an OpenAI-compatible endpoint."""
    from openai import OpenAI
    try:
        client = OpenAI(api_key=api_key or "demo-key", base_url=base_url or None)
        models = client.models.list()
        return sorted([m.id for m in models.data])
    except Exception:
        return []


def _load_skill_context() -> str | None:
    """Load the SKILL.md body content for injection into the system prompt."""
    skill_path = _ASSETS / "SKILL.md"
    if not skill_path.exists():
        return None
    data = load_skill(skill_path)
    return data["body"]


st.title("Chat with the UC Course Advisor")
st.caption("Ask me anything about UC degrees, majors, courses, and planning your studies.")

# ── Sidebar: LLM Configuration ───────────────────────────────────────
with st.sidebar:
    st.header("AI Configuration")

    use_ai = st.toggle("Enable AI Chat", value=False, help="Connect to an OpenAI-compatible endpoint for natural language conversation.")

    if use_ai:
        base_url = st.text_input(
            "Endpoint URL",
            value="https://maas-rhdp.apps.maas.redhatworkshops.io/v1",
            help="OpenAI-compatible API endpoint (e.g. MaaS, vLLM, Ollama).",
        )
        api_key = st.text_input("API Key", type="password", value="", help="Your API key for the endpoint.")

        if st.button("Fetch Models", key="fetch_models"):
            with st.spinner("Fetching models..."):
                models = fetch_models(base_url, api_key)
            if models:
                st.session_state.available_models = models
                st.success(f"Found {len(models)} model(s)")
            else:
                st.session_state.available_models = []
                st.error("Could not fetch models. Check endpoint URL and API key.")

        if st.session_state.available_models:
            model = st.selectbox(
                "Select Model",
                st.session_state.available_models,
                key="model_selector",
                help="Choose a model from the available models on this endpoint.",
            )
        else:
            model = st.text_input("Model", value="", help="Enter a model name, or use Fetch Models above.")

        if st.button("Connect", key="connect_llm"):
            if not model:
                st.warning("Please select or enter a model name first.")
            else:
                try:
                    client = LLMClient(
                        api_key=api_key or "demo-key",
                        base_url=base_url or None,
                        model=model,
                        mcp_client=mcp,
                    )
                    st.session_state.llm_client = client
                    st.session_state.llm_configured = True
                    st.success(f"Connected to **{model}**")
                    if client.tools_source == "mcp_server":
                        st.success(f"Discovered {len(client.tool_definitions)} tools from MCP server")
                    else:
                        st.info("Using built-in tool definitions (MCP server not reachable)")
                except Exception as e:
                    st.error(f"Connection failed: {e}")

        # ── Skills & MCP Toggles ─────────────────────────────────────
        if st.session_state.llm_configured:
            st.divider()
            st.subheader("Integrations")

            use_skills = st.toggle(
                "Skills (SKILL.md)",
                value=True,
                key="toggle_skills",
                help="Inject UC Calendar rules from SKILL.md into the LLM context for more accurate answers.",
            )

            use_mcp = st.toggle(
                "MCP Tools",
                value=True,
                key="toggle_mcp",
                help="Enable function-calling so the LLM can look up faculties, degrees, courses, and generate plans.",
            )

            active = []
            if use_skills:
                active.append("Skills")
            if use_mcp:
                active.append("MCP")
            if active:
                st.caption(f"Active: {' + '.join(active)}")
            else:
                st.caption("No integrations active — plain LLM chat only.")

    else:
        st.session_state.llm_configured = False
        st.session_state.available_models = []
        st.info("AI chat is off. Use the suggestion buttons below for guided exploration, or enable AI chat for natural conversation.")

    st.divider()
    st.header("Quick Info")
    with st.expander("Faculties"):
        for f in mcp.get_faculties():
            st.markdown(f"**{f.short_name}**")
            st.caption(f.description)

    if st.button("Clear Chat"):
        st.session_state.chat_messages = []
        st.rerun()


# ── Chat helper for non-AI responses ─────────────────────────────────

def handle_guided_query(user_input: str) -> str:
    """Handle queries without AI by pattern-matching and using MCP directly."""
    lower = user_input.lower()

    if any(w in lower for w in ["faculty", "faculties", "what can i study"]):
        faculties = mcp.get_faculties()
        lines = ["Here are the 7 faculties at UC:\n"]
        for f in faculties:
            lines.append(f"**{f.short_name}** — {f.description}\n")
        return "\n".join(lines)

    if "degree" in lower:
        for fac in mcp.get_faculties():
            if fac.code in lower or fac.short_name.lower() in lower:
                degrees = mcp.get_available_degrees(fac.code)
                lines = [f"Degrees in {fac.short_name}:\n"]
                for d in degrees:
                    lines.append(f"- **{d.code}** — {d.name} ({d.points} pts, {d.duration_years} years)")
                return "\n".join(lines)

        degrees = mcp.get_available_degrees()
        lines = ["All undergraduate degrees at UC:\n"]
        for d in degrees:
            lines.append(f"- **{d.code}** — {d.name} ({d.points} pts) — {d.faculty.title()}")
        return "\n".join(lines)

    for code in ["BA", "BCom", "BSc", "BE(Hons)", "BHlth", "LLB", "BCJ", "BTchLn",
                  "BYCL", "BSport", "BSW(Hons)", "BFA", "MusB", "BC", "BDigiScreen(Hons)",
                  "BSEnS", "BDataSc", "BPsycSc"]:
        if code.lower() in lower or code.lower().replace("(", "").replace(")", "") in lower:
            majors = mcp.get_majors_for_degree(code)
            degree = mcp.get_degree(code)
            if degree:
                lines = [f"**{degree.name} ({degree.code})**\n"]
                lines.append(f"- Points: {degree.points} | Duration: {degree.duration_years} years")
                lines.append(f"- Faculty: {degree.faculty.title()}")
                if degree.pathway_options:
                    lines.append(f"- Pathways: {', '.join(degree.pathway_options)}")
                if degree.admission:
                    lines.append(f"- Admission: {degree.admission}")
                if majors:
                    lines.append(f"\nAvailable majors/options ({len(majors)}):")
                    for m in majors:
                        lines.append(f"- {m.name}")
                return "\n".join(lines)

    course_codes = [w.upper() for w in user_input.split() if len(w) >= 7 and w[:4].isalpha()]
    for code in course_codes:
        course = mcp.get_course_details(code)
        if course:
            return (
                f"**{course.code} — {course.title}**\n\n"
                f"- Points: {course.points}\n"
                f"- Level: {course.level}\n"
                f"- Semesters: {', '.join(course.semesters)}\n"
                f"- Prerequisites: {', '.join(course.prerequisites) or 'None'}\n"
                f"- Restrictions: {', '.join(course.restrictions) or 'None'}"
            )

    return (
        "I can help you explore UC's degrees and courses! Try asking about:\n\n"
        "- **Faculties** — \"What faculties does UC have?\"\n"
        "- **Degrees** — \"What degrees are in Engineering?\" or \"Tell me about the BA\"\n"
        "- **Courses** — Type a course code like \"COSC131\" or \"LAWS101\"\n"
        "- **Majors** — \"What majors are in BCom?\"\n\n"
        "For a richer conversation, enable **AI Chat** in the sidebar and connect to an OpenAI-compatible endpoint."
    )


# ── Suggestion Chips ──────────────────────────────────────────────────
if not st.session_state.chat_messages:
    st.markdown("### Get Started")
    st.write("Try one of these questions, or type your own below:")

    suggestions = [
        "What faculties does UC have?",
        "What degrees are available in Engineering?",
        "Tell me about the Bachelor of Commerce",
        "What majors can I do in a BSc?",
        "Tell me about LAWS101",
        "What's new in 2026?",
    ]

    cols = st.columns(3)
    for i, s in enumerate(suggestions):
        with cols[i % 3]:
            if st.button(s, key=f"sug_{i}", use_container_width=True):
                st.session_state.chat_messages.append({"role": "user", "content": s})
                st.rerun()


# ── Helper: render data sources ───────────────────────────────────────

def _format_source_data(tool: str, data) -> None:
    """Render tool result data in a human-friendly format."""
    if data is None:
        return

    if isinstance(data, dict) and "error" in data:
        st.warning(data["error"])
        return

    if tool == "get_faculties" and isinstance(data, list):
        for f in data:
            st.markdown(f"- **{f.get('short_name', f.get('name', '?'))}** — {f.get('description', '')[:80]}")

    elif tool == "get_available_degrees" and isinstance(data, list):
        rows = []
        for d in data:
            rows.append({
                "Code": d.get("code", ""),
                "Name": d.get("name", ""),
                "Points": d.get("points", ""),
                "Years": d.get("duration_years", ""),
            })
        if rows:
            st.dataframe(rows, width="stretch", hide_index=True)

    elif tool == "get_majors_for_degree" and isinstance(data, list):
        names = [m.get("name", "?") for m in data]
        st.markdown(f"**{len(names)} options:** " + ", ".join(names))

    elif tool == "get_course_details" and isinstance(data, dict):
        c = data
        st.markdown(
            f"**{c.get('code', '?')} — {c.get('title', '?')}**\n\n"
            f"| Field | Value |\n|---|---|\n"
            f"| Points | {c.get('points', '?')} |\n"
            f"| Level | {c.get('level', '?')} |\n"
            f"| Semesters | {', '.join(c.get('semesters', []))} |\n"
            f"| Prerequisites | {', '.join(c.get('prerequisites', [])) or 'None'} |\n"
            f"| Restrictions | {', '.join(c.get('restrictions', [])) or 'None'} |"
        )

    elif tool == "get_schedule_c" and isinstance(data, list):
        rows = []
        for c in data:
            rows.append({
                "Code": c.get("code", ""),
                "Title": c.get("title", ""),
                "Points": c.get("points", ""),
                "Semesters": ", ".join(c.get("semesters", [])),
            })
        if rows:
            st.dataframe(rows, width="stretch", hide_index=True)

    elif tool == "generate_year1_plan" and isinstance(data, dict):
        st.markdown(f"**{data.get('notes', '')}**")
        entries = data.get("entries", [])
        if entries:
            rows = [{"Course": e.get("course", ""), "Semester": e.get("semester", ""), "Points": e.get("points", ""), "Note": e.get("note", "")} for e in entries]
            st.dataframe(rows, width="stretch", hide_index=True)
        st.markdown(f"**Total: {data.get('total_points', 0)} points**")

    elif tool == "check_prerequisites" and isinstance(data, dict):
        if data.get("met"):
            st.success(data.get("message", "Prerequisites met."))
        else:
            st.warning(data.get("message", "Missing prerequisites."))

    elif tool == "validate_admission" and isinstance(data, dict):
        msgs = data.get("messages", [])
        if not msgs:
            st.success("Admission requirements met.")
        for m in msgs:
            level = m.get("level", "info")
            text = m.get("message", "")
            if level == "error":
                st.error(text)
            elif level == "warning":
                st.warning(text)
            else:
                st.info(text)

    else:
        st.json(data, expanded=False)


_TOOL_LABELS = {
    "get_faculties": "Faculties",
    "get_available_degrees": "Degrees",
    "get_majors_for_degree": "Majors",
    "get_course_details": "Course Details",
    "get_schedule_c": "Schedule C Courses",
    "generate_year1_plan": "Year 1 Plan",
    "check_prerequisites": "Prerequisite Check",
    "validate_degree_progress": "Degree Progress",
    "validate_admission": "Admission Check",
    "get_triage_data": "Triage Data",
    "get_sample_students": "Sample Students",
}


def _render_sources(sources: list[dict]) -> None:
    """Display data sources as an expandable reference section."""
    if not sources:
        return
    with st.expander(f"Data Sources ({len(sources)})", expanded=False):
        for i, src in enumerate(sources):
            tool = src.get("tool", "?")
            args = src.get("args", "{}")
            data = src.get("data")
            label = _TOOL_LABELS.get(tool, tool)
            st.caption(f"Source {i+1}: **{label}** — `{tool}({args})`")
            _format_source_data(tool, data)
            if i < len(sources) - 1:
                st.divider()


# ── Display Chat History ──────────────────────────────────────────────
for msg in st.session_state.chat_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("sources"):
            _render_sources(msg["sources"])


# ── Determine if a response is needed ────────────────────────────────
needs_response = (
    st.session_state.chat_messages
    and st.session_state.chat_messages[-1]["role"] == "user"
)

user_input = st.chat_input("Ask about UC degrees, courses, or your study plan...")
if user_input:
    st.session_state.chat_messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
    needs_response = True

if needs_response:
    with st.chat_message("assistant"):
        if st.session_state.llm_configured and st.session_state.llm_client:
            client: LLMClient = st.session_state.llm_client
            use_skills = st.session_state.get("toggle_skills", True)
            use_mcp = st.session_state.get("toggle_mcp", True)

            skill_ctx = _load_skill_context() if use_skills else None

            api_messages = [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.chat_messages
            ]

            status_container = st.status("Reasoning...", expanded=True)
            response_placeholder = st.empty()
            sources_placeholder = st.empty()

            EVENT_PREFIX = LLMClient.TOOL_EVENT_PREFIX
            EVENT_SUFFIX = LLMClient.TOOL_EVENT_SUFFIX
            collected_text = ""
            events_log: list[str] = []
            data_sources: list[dict] = []
            _pending_tool: dict | None = None

            try:
                stream = client.chat_stream(
                    api_messages,
                    skill_context=skill_ctx,
                    use_tools=use_mcp,
                )

                for token in stream:
                    if token.startswith(EVENT_PREFIX) and token.endswith(EVENT_SUFFIX):
                        event_data = token[len(EVENT_PREFIX):-len(EVENT_SUFFIX)]

                        if event_data == "skill_loaded":
                            events_log.append("Injected **SKILL.md** rules into context")

                        elif event_data.startswith("tools_source:"):
                            parts = event_data.split(":", 2)
                            source = parts[1] if len(parts) > 1 else "?"
                            count = parts[2] if len(parts) > 2 else "?"
                            if source == "mcp_server":
                                events_log.append(f"Discovered **{count}** tools from MCP server")
                            else:
                                events_log.append(f"Using **{count}** built-in tool definitions")

                        elif event_data.startswith("mcp_call:"):
                            parts = event_data.split(":", 2)
                            tool_name = parts[1] if len(parts) > 1 else "?"
                            tool_args = parts[2] if len(parts) > 2 else "{}"
                            events_log.append(f"Called MCP tool: **{tool_name}**(`{tool_args}`)")
                            _pending_tool = {"tool": tool_name, "args": tool_args}

                        elif event_data.startswith("mcp_result:"):
                            parts = event_data.split(":", 2)
                            tool_name = parts[1] if len(parts) > 1 else "?"
                            result_json = parts[2] if len(parts) > 2 else "{}"
                            try:
                                import json as _json
                                parsed = _json.loads(result_json)
                            except Exception:
                                parsed = result_json
                            source_entry = {
                                "tool": tool_name,
                                "args": _pending_tool["args"] if _pending_tool else "{}",
                                "data": parsed,
                            }
                            data_sources.append(source_entry)
                            _pending_tool = None

                        with status_container:
                            for evt in events_log:
                                st.markdown(f"- {evt}")
                    else:
                        collected_text += token
                        response_placeholder.markdown(collected_text + "▌")

                response_placeholder.markdown(collected_text)
                response = collected_text

                if data_sources:
                    with sources_placeholder.container():
                        _render_sources(data_sources)

                if events_log:
                    status_container.update(
                        label=f"Done — {len(events_log)} step(s)",
                        state="complete",
                        expanded=False,
                    )
                else:
                    status_container.update(label="Done", state="complete", expanded=False)

            except Exception as e:
                response = f"Sorry, there was an error communicating with the AI: {e}"
                data_sources = []
                response_placeholder.markdown(response)
                status_container.update(label="Error", state="error", expanded=False)
        else:
            pending = st.session_state.chat_messages[-1]["content"]
            response = handle_guided_query(pending)
            data_sources = []
            st.markdown(response)

        st.session_state.chat_messages.append({
            "role": "assistant",
            "content": response,
            "sources": data_sources,
        })

render_theme_toggle()
