"""MCP Dashboard — server status, tool explorer, resource browser, and interactive testing."""

import asyncio
import json
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.theme import inject_theme_css, render_theme_toggle, get_theme


inject_theme_css()

t = get_theme()

st.title("MCP Dashboard")
st.caption("Monitor the Course Planner MCP server and test tools interactively.")

MCP_BASE = st.sidebar.text_input("MCP Server URL", value="http://localhost:8100", key="mcp_url")
MCP_ENDPOINT = MCP_BASE.rstrip("/") + "/mcp"

# ── Async helpers ─────────────────────────────────────────────────────


def _run_async(coro):
    """Run an async coroutine from Streamlit's sync context."""
    try:
        asyncio.get_running_loop()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result(timeout=30)
    except RuntimeError:
        return asyncio.run(coro)


def _check_health() -> dict | None:
    """Check the /health endpoint (plain HTTP, not MCP)."""
    try:
        import httpx
        with httpx.Client(timeout=10) as client:
            resp = client.get(f"{MCP_BASE}/health")
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        return {"_error": str(e)}


async def _list_tools():
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client
    async with streamable_http_client(MCP_ENDPOINT) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return await session.list_tools()


async def _call_tool(name: str, arguments: dict):
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client
    async with streamable_http_client(MCP_ENDPOINT) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return await session.call_tool(name, arguments)


async def _list_resources():
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client
    async with streamable_http_client(MCP_ENDPOINT) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return await session.list_resources()


async def _read_resource(uri: str):
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client
    async with streamable_http_client(MCP_ENDPOINT) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return await session.read_resource(uri)


# ── Server Status ────────────────────────────────────────────────────

st.header("Server Status")

col_status, col_refresh = st.columns([5, 1])
with col_refresh:
    refresh = st.button("Refresh", key="refresh_status")

health = _check_health()

if health is None:
    st.stop()

server_online = "_error" not in health

if not server_online:
    with st.container(border=True):
        st.error(f"Cannot reach MCP server at `{MCP_BASE}`")
        st.code(health["_error"])
        st.markdown("""
**To start the MCP server**, run in a terminal:
```bash
cd course_planner
uvicorn lib.mcp_server:app --host 0.0.0.0 --port 8100 --reload
```
        """)
    st.divider()
    st.info("Start the MCP server to access the Tool Explorer and Resource Browser below.")
    st.stop()

with st.container(border=True):
    cols = st.columns(4)
    with cols[0]:
        st.metric("Status", health.get("status", "unknown").upper())
    with cols[1]:
        st.metric("Transport", health.get("transport", "unknown"))
    with cols[2]:
        st.metric("Tools", health.get("tools", "?"))
    with cols[3]:
        st.metric("Resources", health.get("resources", "?"))

# ── Tool Catalog ─────────────────────────────────────────────────────

st.header("Tool Catalog")

try:
    tools_result = _run_async(_list_tools())
    tools_list = tools_result.tools if tools_result else []
except Exception as e:
    st.error(f"Failed to list tools: {e}")
    tools_list = []

if tools_list:
    for tool in tools_list:
        with st.expander(f"**{tool.name}** — {tool.description or ''}"):
            if tool.inputSchema and tool.inputSchema.get("properties"):
                st.markdown("**Parameters:**")
                props = tool.inputSchema["properties"]
                required = tool.inputSchema.get("required", [])
                for pname, pspec in props.items():
                    ptype = pspec.get("type", "string")
                    is_req = pname in required
                    badge = " *(required)*" if is_req else ""
                    desc = pspec.get("description", "")
                    default = pspec.get("default")
                    default_str = f" [default: `{default}`]" if default is not None and not is_req else ""
                    st.markdown(f"- `{pname}` ({ptype}){badge}{default_str} {f'— {desc}' if desc else ''}")
            else:
                st.write("No parameters required.")
else:
    st.warning("Could not load tool catalog.")

# ── Tool Explorer ────────────────────────────────────────────────────

st.header("Tool Explorer")
st.markdown("Select a tool, fill in parameters, and call it interactively.")

if tools_list:
    tool_names = [t.name for t in tools_list]
    tool_map = {t.name: t for t in tools_list}

    selected_tool = st.selectbox("Select a tool:", tool_names, key="tool_selector")
    tool_info = tool_map[selected_tool]

    props = {}
    required = []
    if tool_info.inputSchema:
        props = tool_info.inputSchema.get("properties", {})
        required = tool_info.inputSchema.get("required", [])

    arguments: dict = {}

    if props:
        st.markdown("**Fill in parameters:**")
        for pname, pspec in props.items():
            ptype = pspec.get("type", "string")
            is_req = pname in required
            default = pspec.get("default")
            desc = pspec.get("description", pname)
            label = f"{pname}{'*' if is_req else ''}"

            if ptype == "boolean":
                val = st.checkbox(label, value=bool(default) if default is not None else False,
                                  key=f"param_{pname}", help=desc)
                arguments[pname] = val
            elif ptype == "array":
                val = st.text_input(label, value="", key=f"param_{pname}",
                                    help=f"{desc} (comma-separated)")
                if val.strip():
                    arguments[pname] = [v.strip() for v in val.split(",")]
            elif ptype in ("integer", "number"):
                val = st.number_input(label, value=int(default) if default is not None else 0,
                                      key=f"param_{pname}", help=desc)
                arguments[pname] = val
            else:
                val = st.text_input(label, value=str(default) if default is not None else "",
                                    key=f"param_{pname}", help=desc)
                if val.strip():
                    arguments[pname] = val.strip()

    col_call, col_clear = st.columns([1, 5])
    with col_call:
        call_clicked = st.button("Call Tool", type="primary", key="call_tool")

    if call_clicked:
        with st.spinner(f"Calling `{selected_tool}`..."):
            try:
                result = _run_async(_call_tool(selected_tool, arguments))
                if result.isError:
                    st.error(f"Tool returned an error")
                else:
                    st.success(f"Tool `{selected_tool}` executed successfully.")

                for content_item in result.content:
                    if hasattr(content_item, "text"):
                        try:
                            parsed = json.loads(content_item.text)
                            st.json(parsed)
                        except (json.JSONDecodeError, TypeError):
                            st.code(content_item.text)
            except Exception as e:
                st.error(f"Request failed: {e}")

# ── Resource Browser ─────────────────────────────────────────────────

st.header("Resource Browser")
st.markdown("Browse the raw JSON datasets exposed by the MCP server.")

try:
    resources_result = _run_async(_list_resources())
    resources_list = resources_result.resources if resources_result else []
except Exception as e:
    st.error(f"Failed to list resources: {e}")
    resources_list = []

if resources_list:
    resource_names = [f"{r.name} ({r.uri})" for r in resources_list]
    resource_map = {f"{r.name} ({r.uri})": r for r in resources_list}

    selected_resource = st.selectbox("Select a resource:", resource_names, key="resource_selector")
    res_info = resource_map[selected_resource]

    if res_info.description:
        st.caption(res_info.description)

    if st.button("Read Resource", type="primary", key="read_resource"):
        with st.spinner(f"Reading `{res_info.uri}`..."):
            try:
                read_result = _run_async(_read_resource(res_info.uri))
                for content_item in read_result.contents:
                    if hasattr(content_item, "text"):
                        try:
                            parsed = json.loads(content_item.text)
                            st.json(parsed)
                        except (json.JSONDecodeError, TypeError):
                            st.code(content_item.text)
            except Exception as e:
                st.error(f"Failed to read resource: {e}")
else:
    st.info("No resources found. Make sure the MCP server is running.")

render_theme_toggle()
