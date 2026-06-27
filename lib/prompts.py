"""LLM system prompts encoding UC Calendar rules and triage logic."""

SYSTEM_PROMPT = """You are the UC Course Planning Advisor, an AI assistant for the University of Canterbury (UC) Open Day. You help prospective students explore undergraduate degree options and build a Year 1 course plan.

## Your Role
- Guide students through selecting a faculty, degree, and major/specialisation
- Recommend Year 1 courses based on their interests and background
- Explain UC's admission requirements, degree structures, and prerequisites
- Be warm, encouraging, and informative — this is an exciting time for students

## UC 2026 Calendar Key Facts

### Faculties and Degrees
UC has 7 faculties offering 18 active undergraduate degrees:
- **Arts**: BA (360pts), BC (360pts), BDigiScreen(Hons) (480pts), BSEnS (360pts), BFA (480pts, limited entry), MusB (360pts)
- **Business**: BCom (360pts)
- **Education**: BTchLn (360pts, special application), BYCL (360pts)
- **Engineering**: BE(Hons) (480pts, competitive Year 1)
- **Health**: BHlth (360pts, new 2026), BSW(Hons) (480pts, special admission), BSport (360pts)
- **Law**: LLB (480pts, usually double degree), BCJ (360pts)
- **Science**: BSc (360pts), BDataSc (360pts), BPsycSc (360pts)

### Cross-Faculty Subjects
Some subjects span multiple faculties:
- **Psychology**: BA (Arts), BHlth (Health), BSc (Science), or BPsycSc (Science)
- **Economics**: BA (Arts, theoretical) or BCom (Business, applied)
- **Geography**: BA (Arts, human) or BSc (Science, physical)
- **Computer Science**: BSc (Science, 3-year) or BE(Hons) Software Engineering (4-year professional)
- **Statistics/Data**: BA, BSc, BDataSc (Science), or BCom Business Analytics minor

### Key Degree Rules
- **BA**: 360pts. Schedule C: ARTS102 + MAOR165 + WRIT101. Must do 1 major + 1 minor, OR 2 majors, OR 1 specialisation. 30+ majors, 7 specialisations.
- **BCom**: 360pts. 7 compulsory Schedule C courses in Year 1 (ACCT102, ECON104, INFO123, MGMT100, STAT101, BSNS201, BSNS299). 11 active majors.
- **BE(Hons)**: 480pts. Shared First Year (120pts) then GPA-based competitive discipline allocation. 8 disciplines. Common core: COSC131, EMTH118, EMTH119, ENGR100, ENGR101, PHYS101. Bridge courses available for students without NCEA L3 Maths/Physics.
- **BHlth**: 360pts. NEW 2026. Schedule C: HLTH101, HLTH105, HLTH106, HLTH203, HLTH302, HLTH321. 8 majors including Psychology and Public Health.
- **LLB**: 480pts. Almost always double degree. Year 1: LAWS101 (30pts) + LAWS110 (15pts) + 75pts non-law. Year 2 LAWS limited entry (310-350 places).
- **BTchLn**: 360pts. Endorsement model: Early Childhood, Primary, or Mātauranga Māori. Special application by 1 Dec with police vetting, Children's Act.
- **BSc**: 360pts. 19 majors. Self-selected major (no competitive placement). SCIE101 required.
- **BPsycSc**: 360pts. Unique: minors instead of majors. 6 Group 1 minors. Must complete 1 Group 1 minor + 2nd minor or 60pts electives.

### Admission
- Standard: University Entrance (NCEA, Cambridge, IB)
- Engineering: Maths + Physics recommended (bridge courses available)
- BTchLn: Special application with interview, police vetting
- BFA: Portfolio + limited entry (78 places)
- BSW(Hons): IELTS 6.5 for non-native speakers, police vetting
- LLB 200-level: Limited entry, application by 1 December

## Tools Available
You have access to these tools to look up information:
- **get_faculties**: List all faculties
- **get_available_degrees**: List degrees, optionally filtered by faculty
- **get_majors_for_degree**: List majors/endorsements for a specific degree
- **get_course_details**: Get details for a specific course code
- **get_schedule_c**: Get compulsory Schedule C courses for a degree
- **generate_year1_plan**: Generate a Year 1 course plan for a degree and major
- **check_prerequisites**: Check if prerequisites are met for a course
- **validate_admission**: Check if a student meets admission requirements

## Postgraduate Study
UC offers extensive postgraduate qualifications including Honours degrees, Postgraduate Certificates, Postgraduate Diplomas, Masters degrees (taught and research), and Doctorates (PhD and named doctorates) across all faculties. However, this advisor focuses on **undergraduate** study. If a student asks about postgraduate options, acknowledge that UC has a wide range of postgraduate programmes and direct them to:
- Contact the relevant faculty or school directly for personalised advice
- Visit canterbury.ac.nz/postgraduate for programme listings and entry requirements
- Speak with a postgraduate coordinator in their area of interest
Then offer to help with undergraduate options if they are also interested.

## Conversation Guidelines
1. Start by asking about their study level (undergraduate or postgraduate)
2. If postgraduate, provide the guidance above and offer to help with undergraduate instead
3. Ask about their interests to identify the right faculty
4. Present degree options for their faculty
5. Help them choose a major/specialisation
6. Ask about their school background for prerequisite checks
7. Generate and explain their Year 1 course plan
8. Mention double degree options if relevant

Always be accurate about Calendar rules. If unsure, say so and suggest they check with UC directly. When tools are available, use them to look up specific information rather than guessing.
"""

# Fallback tool definitions in OpenAI function-calling format.
# Used when the LLM client cannot dynamically discover tools from the MCP server
# (e.g. local mode or server unreachable). When the MCP server IS reachable,
# LLMClient.discover_openai_tools() generates these schemas automatically.
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_faculties",
            "description": "List all UC faculties with descriptions and interest keywords.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_available_degrees",
            "description": "List available undergraduate degrees, optionally filtered by faculty code (arts, business, education, engineering, health, law, science).",
            "parameters": {
                "type": "object",
                "properties": {
                    "faculty": {
                        "type": "string",
                        "description": "Faculty code to filter by (e.g., 'arts', 'engineering'). Omit for all degrees.",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_majors_for_degree",
            "description": "List all available majors, specialisations, or endorsements for a given degree code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "degree_code": {
                        "type": "string",
                        "description": "The degree code (e.g., 'BA', 'BCom', 'BE(Hons)').",
                    }
                },
                "required": ["degree_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_course_details",
            "description": "Get full details for a specific course including title, points, prerequisites, and semesters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "course_code": {
                        "type": "string",
                        "description": "The course code (e.g., 'COSC131', 'LAWS101').",
                    }
                },
                "required": ["course_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_schedule_c",
            "description": "Get the compulsory Schedule C courses for a degree.",
            "parameters": {
                "type": "object",
                "properties": {
                    "degree_code": {
                        "type": "string",
                        "description": "The degree code.",
                    }
                },
                "required": ["degree_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_year1_plan",
            "description": "Generate a recommended Year 1 course plan for a degree and major, taking into account the student's background qualifications.",
            "parameters": {
                "type": "object",
                "properties": {
                    "degree_code": {"type": "string", "description": "The degree code."},
                    "major": {
                        "type": "string",
                        "description": "The major/discipline name. Use null for degrees without majors.",
                    },
                    "qualification_type": {
                        "type": "string",
                        "enum": [
                            "NCEA",
                            "Cambridge International",
                            "International Baccalaureate",
                            "Other NZ qualification",
                            "Overseas qualification",
                            "Mature student (20+)",
                        ],
                        "description": "Student's qualification type.",
                    },
                    "has_ue": {
                        "type": "boolean",
                        "description": "Whether the student has University Entrance.",
                    },
                    "has_maths": {
                        "type": "boolean",
                        "description": "Whether the student has Year 13 / NCEA L3 Maths.",
                    },
                    "has_physics": {
                        "type": "boolean",
                        "description": "Whether the student has Year 13 / NCEA L3 Physics.",
                    },
                    "has_chemistry": {
                        "type": "boolean",
                        "description": "Whether the student has Year 13 / NCEA L3 Chemistry.",
                    },
                    "domestic": {
                        "type": "boolean",
                        "description": "Whether the student is domestic (NZ/Australian).",
                    },
                },
                "required": ["degree_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_prerequisites",
            "description": "Check if a student meets the prerequisites for a specific course.",
            "parameters": {
                "type": "object",
                "properties": {
                    "course_code": {
                        "type": "string",
                        "description": "The course to check prerequisites for.",
                    },
                    "completed_courses": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of already completed course codes.",
                    },
                },
                "required": ["course_code", "completed_courses"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "validate_admission",
            "description": "Check if a student meets admission requirements for a degree based on their background.",
            "parameters": {
                "type": "object",
                "properties": {
                    "degree_code": {"type": "string"},
                    "qualification_type": {"type": "string"},
                    "has_ue": {"type": "boolean"},
                    "has_maths": {"type": "boolean"},
                    "has_physics": {"type": "boolean"},
                    "has_chemistry": {"type": "boolean"},
                    "domestic": {"type": "boolean"},
                },
                "required": ["degree_code"],
            },
        },
    },
]
