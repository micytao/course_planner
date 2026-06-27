"""MCP client factory — provides a Local/Remote toggle for the Streamlit sidebar."""

from __future__ import annotations

import streamlit as st

from .data_layer import CoursePlannerMCP
from .remote_mcp_client import RemoteMCPClient
from .course_engine import CourseEngine


def render_mcp_toggle() -> None:
    """Render the Local/Remote MCP toggle in the sidebar."""
    with st.sidebar:
        st.toggle("Remote MCP", key="mcp_remote_mode",
                   help="ON = call the standalone MCP server. OFF = use local data files.")
        if st.session_state.get("mcp_remote_mode"):
            st.text_input(
                "MCP Server URL",
                value="http://localhost:8100",
                key="mcp_server_url",
                help="Base URL only — the /mcp endpoint is appended automatically.",
            )
            st.caption(f"Endpoint: `{st.session_state.get('mcp_server_url', 'http://localhost:8100').rstrip('/')}/mcp`")


def get_mcp_client() -> CoursePlannerMCP | RemoteMCPClient:
    """Return the appropriate MCP client based on the sidebar toggle."""
    if st.session_state.get("mcp_remote_mode"):
        url = st.session_state.get("mcp_server_url", "http://localhost:8100")
        return RemoteMCPClient(mcp_url=url)
    return CoursePlannerMCP()


def get_engine(client: CoursePlannerMCP | RemoteMCPClient | None = None) -> CourseEngine:
    """Return a CourseEngine wired to the current MCP client."""
    c = client or get_mcp_client()
    return CourseEngine(c)
