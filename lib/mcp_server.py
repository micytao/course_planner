"""UC Course Planner MCP Server — standards-compliant MCP with Streamable HTTP.

Run standalone:
    uvicorn lib.mcp_server:app --host 0.0.0.0 --port 8100 --reload
"""

from __future__ import annotations

import contextlib
import json
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from .data_layer import CoursePlannerMCP, _load_json
from .course_engine import CourseEngine
from .models import StudentBackground

# ── Data layer (in-process) ──────────────────────────────────────────

_planner = CoursePlannerMCP()
_engine = CourseEngine(_planner)

# ── FastMCP server ───────────────────────────────────────────────────

from mcp.server.transport_security import TransportSecuritySettings

mcp_server = FastMCP(
    "UC Course Planner",
    stateless_http=True,
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)

# ── Tools ────────────────────────────────────────────────────────────


def _json(data: Any) -> str:
    return json.dumps(data)


@mcp_server.tool()
def get_faculties() -> str:
    """List all 7 UC faculties with descriptions and interest keywords."""
    return _json([f.model_dump() for f in _planner.get_faculties()])


@mcp_server.tool()
def get_faculty(code: str) -> str:
    """Get a single faculty by its code (e.g. 'science')."""
    f = _planner.get_faculty(code)
    return _json(f.model_dump() if f else None)


@mcp_server.tool()
def get_available_degrees(faculty: str | None = None) -> str:
    """List degrees, optionally filtered by faculty code."""
    return _json([d.model_dump() for d in _planner.get_available_degrees(faculty)])


@mcp_server.tool()
def get_degree(code: str) -> str:
    """Get a single degree by its code (e.g. 'BA', 'BSc')."""
    d = _planner.get_degree(code)
    return _json(d.model_dump() if d else None)


@mcp_server.tool()
def get_majors_for_degree(degree_code: str) -> str:
    """List majors/endorsements/disciplines for a degree."""
    return _json([m.model_dump() for m in _planner.get_majors_for_degree(degree_code)])


@mcp_server.tool()
def get_specialisations(degree_code: str) -> str:
    """List specialisations available for a degree (e.g. BA)."""
    return _json(_planner.get_specialisations(degree_code))


@mcp_server.tool()
def get_course_details(course_code: str) -> str:
    """Get full details for a single course by code (e.g. 'COSC131')."""
    c = _planner.get_course_details(course_code)
    return _json(c.model_dump() if c else None)


@mcp_server.tool()
def get_schedule_c(degree_code: str) -> str:
    """Get compulsory Schedule C courses for a degree."""
    return _json([c.model_dump() for c in _planner.get_schedule_c(degree_code)])


@mcp_server.tool()
def get_all_scheduled_courses(degree_code: str) -> str:
    """Get courses from all schedule types (C, E, S) for a degree."""
    result = _planner.get_all_scheduled_courses(degree_code)
    return _json({k: [c.model_dump() for c in v] for k, v in result.items()})


@mcp_server.tool()
def generate_year1_plan(
    degree_code: str,
    major: str | None = None,
    qualification_type: str = "NCEA",
    has_ue: bool = True,
    has_maths: bool = False,
    has_physics: bool = False,
    has_chemistry: bool = False,
    domestic: bool = True,
) -> str:
    """Generate a Year 1 course plan for a degree + major + student background."""
    bg = StudentBackground(
        qualification_type=qualification_type,
        has_ue=has_ue,
        has_maths=has_maths,
        has_physics=has_physics,
        has_chemistry=has_chemistry,
        domestic=domestic,
    )
    return _json(_planner.generate_year1_plan(degree_code, major, bg).model_dump())


@mcp_server.tool()
def check_prerequisites(
    course_code: str, completed_courses: list[str] | None = None
) -> str:
    """Check if prerequisites are met for a course given completed courses."""
    return _json(_planner.check_prerequisites(
        course_code, completed_courses or []
    ).model_dump())


@mcp_server.tool()
def validate_degree_progress(
    degree_code: str,
    major: str | None = None,
    completed_courses: list[str] | None = None,
) -> str:
    """Validate progress toward completing a degree."""
    return _json(_planner.validate_degree_progress(
        degree_code, major, completed_courses or []
    ).model_dump())


@mcp_server.tool()
def validate_admission(
    degree_code: str,
    qualification_type: str = "NCEA",
    has_ue: bool = True,
    has_maths: bool = False,
    has_physics: bool = False,
    has_chemistry: bool = False,
    domestic: bool = True,
) -> str:
    """Validate admission eligibility for a degree based on student background."""
    bg = StudentBackground(
        qualification_type=qualification_type,
        has_ue=has_ue,
        has_maths=has_maths,
        has_physics=has_physics,
        has_chemistry=has_chemistry,
        domestic=domestic,
    )
    vr = _engine.validate_admission(degree_code, bg)
    return _json({
        "valid": vr.valid,
        "messages": [{"level": m.level, "message": m.message} for m in vr.messages],
    })


@mcp_server.tool()
def get_triage_data() -> str:
    """Get the triage decision tree for interest-to-faculty mapping."""
    return _json(_planner.get_triage_data())


@mcp_server.tool()
def get_sample_students() -> str:
    """List all demo student personas."""
    return _json([s.model_dump() for s in _planner.get_sample_students()])


@mcp_server.tool()
def get_sample_student(student_id: str) -> str:
    """Get a single demo student persona by ID."""
    s = _planner.get_sample_student(student_id)
    return _json(s.model_dump() if s else None)


# ── Resources (read-only JSON data) ─────────────────────────────────


@mcp_server.resource("data://faculties")
def read_faculties() -> str:
    """All UC faculties with descriptions, schools, and interest keywords."""
    return json.dumps(_load_json("faculties.json"), indent=2)


@mcp_server.resource("data://degrees")
def read_degrees() -> str:
    """All qualifications (bachelors, certificates, diplomas) with schedule data."""
    return json.dumps(_load_json("degrees.json"), indent=2)


@mcp_server.resource("data://majors")
def read_majors() -> str:
    """Majors, endorsements, disciplines, and specialisations per degree."""
    return json.dumps(_load_json("majors.json"), indent=2)


@mcp_server.resource("data://courses")
def read_courses() -> str:
    """Course catalog with prerequisites, points, semesters, and levels."""
    return json.dumps(_load_json("courses.json"), indent=2)


@mcp_server.resource("data://triage")
def read_triage() -> str:
    """Triage decision tree mapping student interests to faculties and degrees."""
    return json.dumps(_load_json("triage.json"), indent=2)


@mcp_server.resource("data://sample-students")
def read_sample_students() -> str:
    """Demo student personas for testing course planning scenarios."""
    return json.dumps(_load_json("sample_students.json"), indent=2)


# ── Starlette app with /health + MCP ────────────────────────────────


async def _health(request):
    tools = len(list(mcp_server._tool_manager._tools.values()))
    return JSONResponse({
        "status": "ok",
        "service": "uc-course-planner-mcp",
        "transport": "streamable-http",
        "tools": tools,
        "resources": 6,
    })


@contextlib.asynccontextmanager
async def _lifespan(a: Starlette):
    async with mcp_server.session_manager.run():
        yield


_starlette = Starlette(
    routes=[
        Route("/health", _health),
        Mount("/", app=mcp_server.streamable_http_app()),
    ],
    lifespan=_lifespan,
)

app = CORSMiddleware(
    _starlette,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
    expose_headers=["Mcp-Session-Id"],
)

# ── Standalone runner ────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("lib.mcp_server:app", host="0.0.0.0", port=8100, reload=True)
