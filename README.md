# UC Course Planner

AI-powered course planning assistant for the University of Canterbury.

## What is this?

A prototype tool that helps students explore degrees, choose a major, and build a personalised Year 1 course plan. It covers all **7 UC faculties** and **18 active undergraduate degrees** from the UC 2026 Calendar.

The system runs as two containerised services:

- **MCP Server** (port 8100) — a Model Context Protocol server exposing 16 tools and 6 resources over Streamable HTTP
- **Streamlit UI** (port 8501) — a multi-page frontend with a chatbot advisor, guided wizard, and sample scenarios

## Features

- **Triage flow** that maps student interests to the right faculty and degree
- **Cross-faculty disambiguation** for subjects like Psychology, Economics, and Computer Science
- **Prerequisite checking** and admission requirement validation
- **Year 1 course plan generation** tailored to each degree and major
- **Dual-mode interface** — conversational AI chatbot or step-by-step wizard
- **Sample scenarios** with pre-built student personas for live demonstrations

## Quickstart (local development)

```bash
pip install -r requirements.txt
streamlit run app.py
```

The UI starts at http://localhost:8501 in local mode (reads data directly from `knowledge/` files, no MCP server needed).

## Quickstart (containers)

Build and run both services with Podman Compose:

```bash
podman-compose up --build
```

Or manually:

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

Open http://localhost:8501 in your browser.

## Environment Variables

| Variable | Required | Purpose |
|---|---|---|
| `MCP_SERVER_URL` | No | Base URL of the MCP server (default: `http://localhost:8100`) |
| `OPENAI_API_KEY` | No | API key for the Chat Advisor's LLM features |

## Project Structure

```
course_planner/
├── app.py                  # Streamlit entry point
├── pages/                  # Multi-page UI (Home, Chat Advisor, Course Wizard, etc.)
├── lib/                    # Shared Python modules
│   ├── mcp_server.py       # MCP server (FastMCP + Starlette)
│   ├── data_layer.py       # Local JSON data access
│   ├── remote_mcp_client.py# HTTP client for remote MCP
│   ├── mcp_factory.py      # Local/Remote toggle factory
│   ├── course_engine.py    # Validation rules (admission, prerequisites)
│   ├── llm_client.py       # LLM integration with MCP tool calling
│   ├── prompts.py          # System prompts and tool definitions
│   ├── models.py           # Pydantic data models
│   ├── skill_loader.py     # SKILL.md parser
│   └── theme.py            # Dark/light theme CSS
├── knowledge/              # JSON knowledge base (faculties, degrees, courses, etc.)
├── assets/                 # Static assets (logo, agent skill, calendar rules)
├── deploy/                 # Container build files
│   ├── Dockerfile.mcp
│   ├── Dockerfile.ui
│   ├── .dockerignore.mcp
│   └── .dockerignore.ui
├── docs/                   # Documentation
│   ├── PRODUCTION_ROADMAP.md
│   └── USER_GUIDE.md
├── .streamlit/config.toml  # Streamlit theme and server config
├── podman-compose.yml      # One-command container orchestration
├── requirements.txt        # Full Python dependencies
└── requirements-ui.txt     # UI-only dependencies (excludes fastapi/uvicorn)
```

## Documentation

- [User Guide](docs/USER_GUIDE.md) — how to use the tool as a student
- [Production Roadmap](docs/PRODUCTION_ROADMAP.md) — architecture, container images, and future phases
