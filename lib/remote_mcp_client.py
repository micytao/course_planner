"""Remote MCP client — drop-in replacement for CoursePlannerMCP.

Calls the standalone MCP server via Streamable HTTP instead of reading
local JSON files. Every public method has the same signature and return
type as CoursePlannerMCP so existing page code works unchanged.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from .models import (
    Course,
    CoursePlan,
    Degree,
    Faculty,
    Major,
    PrereqResult,
    ProgressResult,
    SampleStudent,
    StudentBackground,
)


def _get_or_create_event_loop() -> asyncio.AbstractEventLoop:
    """Get the running event loop or create a new one (Streamlit-safe)."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool
    return None


class RemoteMCPClient:
    """Drop-in replacement for CoursePlannerMCP that calls a remote MCP server."""

    def __init__(self, mcp_url: str | None = None):
        base = mcp_url or os.environ.get("MCP_SERVER_URL", "http://localhost:8100")
        self.mcp_url = base.rstrip("/") + "/mcp"

    def _call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        """Call an MCP tool synchronously (wraps the async SDK client)."""
        return self._run_async(self._async_call_tool(name, arguments or {}))

    def _run_async(self, coro):
        """Run an async coroutine from sync context (handles Streamlit's event loop)."""
        try:
            asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, coro).result(timeout=30)
        except RuntimeError:
            return asyncio.run(coro)

    async def _async_call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        async with streamable_http_client(self.mcp_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(name, arguments)
                text = result.content[0].text
                return json.loads(text)

    async def _async_list_tools(self):
        async with streamable_http_client(self.mcp_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                return result.tools

    def discover_openai_tools(self) -> list[dict] | None:
        """Query the MCP server for its tool catalog and return OpenAI function-calling schemas.

        Returns None if the server is unreachable or discovery fails.
        """
        try:
            tools = self._run_async(self._async_list_tools())
            return [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description or "",
                        "parameters": t.inputSchema or {"type": "object", "properties": {}, "required": []},
                    },
                }
                for t in tools
            ]
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Faculty helpers
    # ------------------------------------------------------------------

    def get_faculties(self) -> list[Faculty]:
        return [Faculty(**f) for f in self._call_tool("get_faculties")]

    def get_faculty(self, code: str) -> Faculty | None:
        result = self._call_tool("get_faculty", {"code": code})
        return Faculty(**result) if result else None

    # ------------------------------------------------------------------
    # Degree helpers
    # ------------------------------------------------------------------

    def get_available_degrees(self, faculty: str | None = None) -> list[Degree]:
        args = {"faculty": faculty} if faculty else {}
        return [Degree(**d) for d in self._call_tool("get_available_degrees", args)]

    def get_degree(self, code: str) -> Degree | None:
        result = self._call_tool("get_degree", {"code": code})
        return Degree(**result) if result else None

    # ------------------------------------------------------------------
    # Major / minor / endorsement helpers
    # ------------------------------------------------------------------

    def get_majors_for_degree(self, degree_code: str) -> list[Major]:
        return [
            Major(**m)
            for m in self._call_tool("get_majors_for_degree", {"degree_code": degree_code})
        ]

    def get_specialisations(self, degree_code: str) -> list[dict]:
        return self._call_tool("get_specialisations", {"degree_code": degree_code})

    def get_engineering_disciplines(self) -> list[dict]:
        majors_data = self._call_tool("get_majors_for_degree", {"degree_code": "BE(Hons)"})
        return [{"name": m["name"], "notes": m.get("notes", "")} for m in majors_data]

    def get_endorsements(self, degree_code: str) -> list[dict]:
        majors_data = self._call_tool("get_majors_for_degree", {"degree_code": degree_code})
        return [{"name": m["name"], "notes": m.get("notes", "")} for m in majors_data]

    # ------------------------------------------------------------------
    # Course helpers
    # ------------------------------------------------------------------

    def get_course_details(self, course_code: str) -> Course | None:
        result = self._call_tool("get_course_details", {"course_code": course_code})
        return Course(**result) if result else None

    def get_schedule_c(self, degree_code: str) -> list[Course]:
        return [
            Course(**c)
            for c in self._call_tool("get_schedule_c", {"degree_code": degree_code})
        ]

    def get_all_scheduled_courses(self, degree_code: str) -> dict[str, list[Course]]:
        result = self._call_tool("get_all_scheduled_courses", {"degree_code": degree_code})
        return {k: [Course(**c) for c in v] for k, v in result.items()}

    def get_courses_for_major(
        self, degree_code: str, major_name: str, level: int | None = None
    ) -> list[Course]:
        majors = self.get_majors_for_degree(degree_code)
        target = None
        for m in majors:
            if m.name == major_name:
                target = m
                break
        if not target:
            return []

        codes: set[str] = set()
        for req_list in [target.required_100, target.required_200, target.required_300]:
            for item in req_list:
                parts = item.replace(",", " ").split()
                for p in parts:
                    if len(p) >= 7 and p[:4].isalpha() and p[4:].isdigit():
                        codes.add(p)

        result = []
        for code in codes:
            c = self.get_course_details(code)
            if c and (level is None or c.level == level):
                result.append(c)
        return sorted(result, key=lambda c: (c.level, c.code))

    # ------------------------------------------------------------------
    # Prerequisite check
    # ------------------------------------------------------------------

    def check_prerequisites(
        self, course_code: str, completed_courses: list[str]
    ) -> PrereqResult:
        result = self._call_tool("check_prerequisites", {
            "course_code": course_code,
            "completed_courses": completed_courses,
        })
        return PrereqResult(**result)

    # ------------------------------------------------------------------
    # Degree progress
    # ------------------------------------------------------------------

    def validate_degree_progress(
        self, degree_code: str, major: str | None, completed_courses: list[str]
    ) -> ProgressResult:
        result = self._call_tool("validate_degree_progress", {
            "degree_code": degree_code,
            "major": major,
            "completed_courses": completed_courses,
        })
        return ProgressResult(**result)

    # ------------------------------------------------------------------
    # Year 1 plan generation
    # ------------------------------------------------------------------

    def generate_year1_plan(
        self, degree_code: str, major: str | None, background: StudentBackground
    ) -> CoursePlan:
        args = {
            "degree_code": degree_code,
            "major": major,
            **background.model_dump(),
        }
        result = self._call_tool("generate_year1_plan", args)
        return CoursePlan(**result)

    # ------------------------------------------------------------------
    # Triage
    # ------------------------------------------------------------------

    def get_triage_data(self) -> dict:
        return self._call_tool("get_triage_data")

    # ------------------------------------------------------------------
    # Demo personas
    # ------------------------------------------------------------------

    def get_sample_students(self) -> list[SampleStudent]:
        return [SampleStudent(**s) for s in self._call_tool("get_sample_students")]

    def get_sample_student(self, student_id: str) -> SampleStudent | None:
        result = self._call_tool("get_sample_student", {"student_id": student_id})
        return SampleStudent(**result) if result else None
