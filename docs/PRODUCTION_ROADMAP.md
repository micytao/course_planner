# Production Roadmap: MCP Server + Streamlit UI

## Current Architecture

The UC Course Planner runs as two containerised services:

- **MCP Server** (`lib/mcp_server.py`) — standalone Streamable HTTP server exposing 16 tools and 6 resources, backed by JSON data files in `knowledge/`
- **Streamlit UI** (`app.py`) — multi-page frontend that connects to the MCP server via `RemoteMCPClient`, or falls back to in-process data access for local development

Both services are built on `ubi9/python-312-minimal` and deployed to OpenShift as separate pods.

### Key Files

| File | Role |
|---|---|
| `lib/mcp_server.py` | MCP server (FastMCP + Starlette + CORS) |
| `lib/data_layer.py` | Local data layer — reads `knowledge/*.json` |
| `lib/remote_mcp_client.py` | HTTP client for the remote MCP server |
| `lib/mcp_factory.py` | Factory: `get_mcp_client()` returns local or remote client |
| `lib/course_engine.py` | Validation rules (admission, prerequisites) |
| `lib/llm_client.py` | LLM integration with MCP tool calling |
| `assets/SKILL.md` | Agent skill definition for AI context |
| `deploy/Dockerfile.mcp` | Container image for the MCP server |
| `deploy/Dockerfile.ui` | Container image for the Streamlit UI |
| `deploy/.dockerignore.ui` | Build context exclusions for the UI image |
| `requirements-ui.txt` | UI-only Python dependencies (excludes fastapi/uvicorn) |

### Container Images

| Image | Registry |
|---|---|
| MCP Server | `quay.io/rh-ee-micyang/uc-mcp-server` |
| Streamlit UI | `quay.io/rh-ee-micyang/uc-course-planner-ui` |

### Running Locally with Podman Compose

```bash
podman-compose up --build
```

Or individually:

```bash
podman network create course-net

podman build -f deploy/Dockerfile.mcp -t quay.io/rh-ee-micyang/uc-mcp-server:latest .
podman build -f deploy/Dockerfile.ui --ignorefile deploy/.dockerignore.ui -t quay.io/rh-ee-micyang/uc-course-planner-ui:latest .

podman run --rm -d --name mcp-server \
  --network course-net -p 8100:8100 \
  quay.io/rh-ee-micyang/uc-mcp-server:latest

podman run --rm -d --name ui-app \
  --network course-net -p 8501:8501 \
  -e MCP_SERVER_URL=http://mcp-server:8100 \
  quay.io/rh-ee-micyang/uc-course-planner-ui:latest
```

### Environment Variables (UI container)

| Variable | Purpose |
|---|---|
| `MCP_SERVER_URL` | Base URL of the MCP server (default: `http://localhost:8100`) |
| `OPENAI_API_KEY` | API key for Chat Advisor LLM features |

## Phase 1: Demo (Complete)

- 7 faculties, 18+ degrees, course data from the UC 2026 Calendar
- MCP server with Streamable HTTP transport on port 8100
- Streamlit UI with Chat Advisor, Course Wizard, Sample Scenarios
- MCP Dashboard for live tool/resource inspection
- Cursor IDE integration via `.cursor/mcp.json`
- Containerised with `Dockerfile.mcp` (MCP server) and `Dockerfile.ui` (Streamlit UI) for OpenShift deployment
- DNS rebinding protection disabled on MCP server to allow container-to-container communication via service names

## Phase 2: Production Data Sources

Wire the MCP server to real UC systems instead of JSON files:

| MCP Tool | Production Source |
|---|---|
| `get_faculties` | UC Organisation API |
| `get_available_degrees` | Course Management System (CMS) |
| `get_majors_for_degree` | CMS Programme Structure API |
| `get_course_details` | CMS Course Catalogue API |
| `get_schedule_c` | CMS Degree Regulations API |
| `check_prerequisites` | Student Records + CMS |
| `validate_degree_progress` | Student Records (enrolled courses + GPA) |
| `generate_year1_plan` | CMS + Timetable System (live availability) |

The MCP tool interface stays identical — only the data backend in `lib/data_layer.py` changes.

## Phase 3: Additional Production Capabilities

These tools would be added to the MCP server for a full production system:

- `get_timetable(course_code, year, semester)` — live class schedules
- `check_timetable_clashes(courses)` — detect scheduling conflicts
- `get_seat_availability(course_code)` — real-time enrolment capacity
- `enrol_student(student_id, course_code)` — trigger enrolment
- `get_student_record(student_id)` — academic history

## Phase 4: Authentication and Security

- Student authentication via UC Single Sign-On (SSO)
- MCP server authenticates to CMS via service account / OAuth2
- Student data access governed by UC privacy policies
- MCP server deployed behind OpenShift service mesh with mTLS
