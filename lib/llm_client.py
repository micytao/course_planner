"""OpenAI SDK wrapper for LLM integration with function-calling for MCP tools."""

from __future__ import annotations

import json
import os
from typing import Generator

from openai import OpenAI

from .models import StudentBackground
from .course_engine import CourseEngine
from .prompts import SYSTEM_PROMPT, TOOL_DEFINITIONS


class LLMClient:
    """Wraps the OpenAI SDK and routes tool calls to the MCP client."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        mcp_client=None,
    ):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "demo-key")
        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL")
        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

        if mcp_client is not None:
            self.mcp = mcp_client
        else:
            from .data_layer import CoursePlannerMCP
            self.mcp = CoursePlannerMCP()
        self.engine = CourseEngine(self.mcp)

        client_kwargs: dict = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        self.client = OpenAI(**client_kwargs)

        self.tool_definitions: list[dict] = TOOL_DEFINITIONS
        self.tools_source: str = "fallback"
        if hasattr(self.mcp, "discover_openai_tools"):
            discovered = self.mcp.discover_openai_tools()
            if discovered:
                self.tool_definitions = discovered
                self.tools_source = "mcp_server"

    _TOOLS_SECTION_HEADER = "## Tools Available"

    def _build_system_prompt(
        self,
        skill_context: str | None = None,
        use_tools: bool = True,
    ) -> str:
        """Build the system prompt, optionally enriched with SKILL.md content.

        When use_tools is False, the "## Tools Available" section is stripped
        so the model doesn't hallucinate tool-call tokens.
        """
        prompt = SYSTEM_PROMPT
        if not use_tools:
            idx = prompt.find(self._TOOLS_SECTION_HEADER)
            if idx != -1:
                next_section = prompt.find("\n## ", idx + len(self._TOOLS_SECTION_HEADER))
                prompt = prompt[:idx].rstrip() + (prompt[next_section:] if next_section != -1 else "")
            prompt += (
                "\n\nIMPORTANT: You do NOT have access to any tools or functions in this "
                "conversation. Answer questions using ONLY the knowledge provided in this "
                "prompt. Do not attempt to call any functions, tools, or generate code to "
                "simulate tool calls. Respond in plain, conversational language."
            )

        if not skill_context:
            return prompt

        tool_guidance = ""
        if use_tools:
            tool_guidance = (
                "IMPORTANT: The skill knowledge provides summary-level context only. "
                "When a student asks for specific data — such as listing majors, "
                "course details, prerequisites, or generating a plan — you MUST call "
                "the MCP tools (get_majors_for_degree, get_course_details, etc.) to "
                "get accurate data. NEVER fabricate or guess lists of majors, courses, "
                "or other specifics from the skill text. Always use the tools.\n\n"
            )

        return (
            prompt
            + "\n\n## Additional Skill Knowledge\n\n"
            + "The following rules from SKILL.md describe the advising workflow, "
            + "admission rules, degree structures, and conversation guidelines. "
            + "Use them to understand HOW to guide students and WHAT rules apply.\n\n"
            + tool_guidance
            + skill_context
        )

    def _execute_tool(self, name: str, arguments: dict) -> str:
        """Route a tool call to the appropriate MCP method and return JSON."""
        try:
            if name == "get_faculties":
                result = [f.model_dump() for f in self.mcp.get_faculties()]
            elif name == "get_available_degrees":
                result = [
                    d.model_dump()
                    for d in self.mcp.get_available_degrees(arguments.get("faculty"))
                ]
            elif name == "get_majors_for_degree":
                result = [
                    m.model_dump()
                    for m in self.mcp.get_majors_for_degree(arguments["degree_code"])
                ]
            elif name == "get_course_details":
                course = self.mcp.get_course_details(arguments["course_code"])
                result = course.model_dump() if course else {"error": "Course not found"}
            elif name == "get_schedule_c":
                result = [
                    c.model_dump()
                    for c in self.mcp.get_schedule_c(arguments["degree_code"])
                ]
            elif name == "generate_year1_plan":
                bg = StudentBackground(
                    qualification_type=arguments.get("qualification_type", "NCEA"),
                    has_ue=arguments.get("has_ue", True),
                    has_maths=arguments.get("has_maths", False),
                    has_physics=arguments.get("has_physics", False),
                    has_chemistry=arguments.get("has_chemistry", False),
                    domestic=arguments.get("domestic", True),
                )
                plan = self.mcp.generate_year1_plan(
                    arguments["degree_code"], arguments.get("major"), bg
                )
                result = plan.model_dump()
            elif name == "check_prerequisites":
                prereq = self.mcp.check_prerequisites(
                    arguments["course_code"],
                    arguments.get("completed_courses", []),
                )
                result = prereq.model_dump()
            elif name == "validate_admission":
                bg = StudentBackground(
                    qualification_type=arguments.get("qualification_type", "NCEA"),
                    has_ue=arguments.get("has_ue", True),
                    has_maths=arguments.get("has_maths", False),
                    has_physics=arguments.get("has_physics", False),
                    has_chemistry=arguments.get("has_chemistry", False),
                    domestic=arguments.get("domestic", True),
                )
                vr = self.engine.validate_admission(arguments["degree_code"], bg)
                result = {
                    "valid": vr.valid,
                    "messages": [
                        {"level": m.level, "message": m.message} for m in vr.messages
                    ],
                }
            else:
                result = {"error": f"Unknown tool: {name}"}
        except Exception as e:
            result = {"error": str(e)}

        return json.dumps(result, default=str)

    def chat(
        self,
        messages: list[dict],
        max_tool_rounds: int = 5,
        skill_context: str | None = None,
        use_tools: bool = True,
    ) -> str:
        """Send messages to the LLM, handle tool calls, return final text."""
        system = self._build_system_prompt(skill_context, use_tools=use_tools)
        full_messages = [{"role": "system", "content": system}] + messages

        tool_kwargs: dict = {}
        if use_tools:
            tool_kwargs["tools"] = self.tool_definitions
            tool_kwargs["tool_choice"] = "auto"

        for _ in range(max_tool_rounds):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=full_messages,
                    **tool_kwargs,
                )
            except Exception as e:
                return f"I'm sorry, I couldn't connect to the AI service. Error: {e}"

            choice = response.choices[0]

            if use_tools and (
                choice.finish_reason == "tool_calls"
                or (choice.message.tool_calls and len(choice.message.tool_calls) > 0)
            ):
                full_messages.append(choice.message)

                for tc in choice.message.tool_calls:
                    args = json.loads(tc.function.arguments)
                    tool_result = self._execute_tool(tc.function.name, args)
                    full_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": tool_result,
                        }
                    )
                continue

            return choice.message.content or ""

        return "I've reached the maximum number of lookups. Could you rephrase your question?"

    # Sentinel prefix for tool-call event markers yielded during streaming.
    TOOL_EVENT_PREFIX = "\x00TOOL_EVENT:"
    TOOL_EVENT_SUFFIX = "\x00"

    def chat_stream(
        self,
        messages: list[dict],
        max_tool_rounds: int = 5,
        skill_context: str | None = None,
        use_tools: bool = True,
    ) -> Generator[str, None, None]:
        """Streaming version that yields text chunks and handles tool calls.

        When MCP tools are invoked, yields special marker strings
        (prefixed with TOOL_EVENT_PREFIX) so the UI can display them.
        """
        system = self._build_system_prompt(skill_context, use_tools=use_tools)
        full_messages = [{"role": "system", "content": system}] + messages

        tool_kwargs: dict = {}
        if use_tools:
            tool_kwargs["tools"] = self.tool_definitions
            tool_kwargs["tool_choice"] = "auto"

        if skill_context:
            yield f"{self.TOOL_EVENT_PREFIX}skill_loaded{self.TOOL_EVENT_SUFFIX}"

        if use_tools:
            yield (
                f"{self.TOOL_EVENT_PREFIX}"
                f"tools_source:{self.tools_source}:{len(self.tool_definitions)}"
                f"{self.TOOL_EVENT_SUFFIX}"
            )

        for round_num in range(max_tool_rounds):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=full_messages,
                    stream=True,
                    **tool_kwargs,
                )
            except Exception as e:
                yield f"I'm sorry, I couldn't connect to the AI service. Error: {e}"
                return

            collected_content = ""
            tool_calls_data: dict[int, dict] = {}
            has_tool_calls = False

            for chunk in response:
                delta = chunk.choices[0].delta if chunk.choices else None
                if not delta:
                    continue

                if delta.content:
                    collected_content += delta.content
                    yield delta.content

                if delta.tool_calls:
                    has_tool_calls = True
                    for tc_chunk in delta.tool_calls:
                        idx = tc_chunk.index
                        if idx not in tool_calls_data:
                            tool_calls_data[idx] = {
                                "id": "",
                                "name": "",
                                "arguments": "",
                            }
                        if tc_chunk.id:
                            tool_calls_data[idx]["id"] = tc_chunk.id
                        if tc_chunk.function:
                            if tc_chunk.function.name:
                                tool_calls_data[idx]["name"] = tc_chunk.function.name
                            if tc_chunk.function.arguments:
                                tool_calls_data[idx]["arguments"] += (
                                    tc_chunk.function.arguments
                                )

            if not has_tool_calls or not use_tools:
                return

            assistant_msg = {"role": "assistant", "content": collected_content or None, "tool_calls": []}
            for idx in sorted(tool_calls_data.keys()):
                tc_data = tool_calls_data[idx]
                assistant_msg["tool_calls"].append(
                    {
                        "id": tc_data["id"],
                        "type": "function",
                        "function": {
                            "name": tc_data["name"],
                            "arguments": tc_data["arguments"],
                        },
                    }
                )
            full_messages.append(assistant_msg)

            for idx in sorted(tool_calls_data.keys()):
                tc_data = tool_calls_data[idx]
                args = json.loads(tc_data["arguments"])
                yield (
                    f"{self.TOOL_EVENT_PREFIX}"
                    f"mcp_call:{tc_data['name']}:{json.dumps(args, default=str)}"
                    f"{self.TOOL_EVENT_SUFFIX}"
                )
                tool_result = self._execute_tool(tc_data["name"], args)
                yield (
                    f"{self.TOOL_EVENT_PREFIX}"
                    f"mcp_result:{tc_data['name']}:{tool_result}"
                    f"{self.TOOL_EVENT_SUFFIX}"
                )
                full_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc_data["id"],
                        "content": tool_result,
                    }
                )
