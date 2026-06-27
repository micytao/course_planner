"""Local data layer — reads UC course data from knowledge/ JSON files.

Used in two modes:
  - Directly by the MCP server (lib/mcp_server.py) as its data backend
  - In-process by Streamlit pages when the Remote MCP toggle is OFF

In production, the MCP server would connect to real UC CMS APIs instead
of reading JSON files. The interface (CoursePlannerMCP) stays identical.
"""

from __future__ import annotations

import json
from pathlib import Path
from functools import lru_cache

from .models import (
    Course,
    CoursePlan,
    CoursePlanEntry,
    Degree,
    Faculty,
    Major,
    PrereqResult,
    ProgressResult,
    SampleStudent,
    StudentBackground,
)

_KB = Path(__file__).resolve().parent.parent / "knowledge"


@lru_cache(maxsize=1)
def _load_json(filename: str) -> dict | list:
    with open(_KB / filename, encoding="utf-8") as f:
        return json.load(f)


class CoursePlannerMCP:
    """Local data layer for UC course planning backed by JSON files."""

    # ------------------------------------------------------------------
    # Faculty helpers
    # ------------------------------------------------------------------

    def get_faculties(self) -> list[Faculty]:
        return [Faculty(**f) for f in _load_json("faculties.json")]

    def get_faculty(self, code: str) -> Faculty | None:
        for f in _load_json("faculties.json"):
            if f["code"] == code:
                return Faculty(**f)
        return None

    # ------------------------------------------------------------------
    # Degree helpers
    # ------------------------------------------------------------------

    def get_available_degrees(self, faculty: str | None = None) -> list[Degree]:
        degrees = [Degree(**d) for d in _load_json("degrees.json")]
        if faculty:
            degrees = [d for d in degrees if d.faculty == faculty]
        return degrees

    def get_degree(self, code: str) -> Degree | None:
        for d in _load_json("degrees.json"):
            if d["code"] == code:
                return Degree(**d)
        return None

    # ------------------------------------------------------------------
    # Major / minor / endorsement helpers
    # ------------------------------------------------------------------

    def get_majors_for_degree(self, degree_code: str) -> list[Major]:
        data = _load_json("majors.json")
        entry = data.get(degree_code, {})

        if "majors" in entry:
            return [Major(**m) for m in entry["majors"]]
        if "disciplines" in entry:
            return [Major(name=d["name"], notes=f"Places: {d.get('places', '?')}") for d in entry["disciplines"]]
        if "endorsements" in entry:
            return [Major(name=e["name"], notes=e.get("notes", "")) for e in entry["endorsements"]]
        if "group1_minors" in entry:
            return [Major(name=m["name"]) for m in entry["group1_minors"]]
        return []

    def get_specialisations(self, degree_code: str) -> list[dict]:
        data = _load_json("majors.json")
        return data.get(degree_code, {}).get("specialisations", [])

    def get_engineering_disciplines(self) -> list[dict]:
        data = _load_json("majors.json")
        return data.get("BE(Hons)", {}).get("disciplines", [])

    def get_endorsements(self, degree_code: str) -> list[dict]:
        data = _load_json("majors.json")
        return data.get(degree_code, {}).get("endorsements", [])

    # ------------------------------------------------------------------
    # Course helpers
    # ------------------------------------------------------------------

    def get_course_details(self, course_code: str) -> Course | None:
        courses = _load_json("courses.json")
        c = courses.get(course_code)
        return Course(**c) if c else None

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

        courses_db = _load_json("courses.json")
        result = []
        for code in codes:
            if code in courses_db:
                c = Course(**courses_db[code])
                if level is None or c.level == level:
                    result.append(c)
        return sorted(result, key=lambda c: (c.level, c.code))

    def get_schedule_c(self, degree_code: str) -> list[Course]:
        degree = self.get_degree(degree_code)
        if not degree:
            return []
        courses_db = _load_json("courses.json")
        result = []
        for code in degree.schedule_c_courses:
            if code in courses_db:
                result.append(Course(**courses_db[code]))
        return result

    def get_all_scheduled_courses(self, degree_code: str) -> dict[str, list[Course]]:
        """Return courses from all schedule types (C, E, S) for a degree."""
        degree = self.get_degree(degree_code)
        if not degree:
            return {}
        courses_db = _load_json("courses.json")
        result: dict[str, list[Course]] = {}
        for sched_name, codes in [
            ("Schedule C", degree.schedule_c_courses),
            ("Schedule E", degree.schedule_e_courses),
            ("Schedule S", degree.schedule_s_courses),
        ]:
            if codes:
                found = [Course(**courses_db[c]) for c in codes if c in courses_db]
                if found:
                    result[sched_name] = found
        return result

    # ------------------------------------------------------------------
    # Prerequisite check
    # ------------------------------------------------------------------

    def check_prerequisites(
        self, course_code: str, completed_courses: list[str]
    ) -> PrereqResult:
        course = self.get_course_details(course_code)
        if not course:
            return PrereqResult(course_code=course_code, met=False, message="Course not found.")

        completed = set(completed_courses)
        missing = []
        for prereq in course.prerequisites:
            if " or " in prereq.lower():
                options = [p.strip() for p in prereq.split(" or ")]
                course_options = [o for o in options if len(o) >= 7 and o[:4].isalpha()]
                if course_options and not any(o in completed for o in course_options):
                    missing.append(prereq)
            else:
                parts = prereq.replace(",", " ").split()
                for p in parts:
                    if len(p) >= 7 and p[:4].isalpha() and p[4:].isdigit():
                        if p not in completed:
                            missing.append(p)

        met = len(missing) == 0
        msg = "All prerequisites met." if met else f"Missing: {', '.join(missing)}"
        return PrereqResult(course_code=course_code, met=met, missing=missing, message=msg)

    # ------------------------------------------------------------------
    # Degree progress
    # ------------------------------------------------------------------

    def validate_degree_progress(
        self, degree_code: str, major: str | None, completed_courses: list[str]
    ) -> ProgressResult:
        degree = self.get_degree(degree_code)
        if not degree:
            return ProgressResult(degree_code=degree_code)

        courses_db = _load_json("courses.json")
        total_completed = 0
        for code in completed_courses:
            if code in courses_db:
                total_completed += courses_db[code]["points"]

        remaining = max(0, degree.points - total_completed)
        pct = min(100.0, (total_completed / degree.points) * 100) if degree.points > 0 else 0

        missing = []
        for sc in degree.schedule_c_courses:
            if sc not in completed_courses:
                missing.append(f"Schedule C: {sc}")
        for se in degree.schedule_e_courses:
            if se not in completed_courses:
                missing.append(f"Schedule E: {se}")
        for ss in degree.schedule_s_courses:
            if ss not in completed_courses:
                missing.append(f"Schedule S: {ss}")

        return ProgressResult(
            degree_code=degree_code,
            major=major,
            completed_points=total_completed,
            remaining_points=remaining,
            percentage=round(pct, 1),
            missing_requirements=missing,
        )

    # ------------------------------------------------------------------
    # Year 1 plan generation
    # ------------------------------------------------------------------

    def generate_year1_plan(
        self, degree_code: str, major: str | None, background: StudentBackground
    ) -> CoursePlan:
        degree = self.get_degree(degree_code)
        if not degree:
            return CoursePlan(degree=degree_code, notes="Degree not found.")

        entries: list[CoursePlanEntry] = []
        courses_db = _load_json("courses.json")

        all_scheduled = (
            [(code, "Core") for code in degree.schedule_c_courses]
            + [(code, "Schedule E") for code in degree.schedule_e_courses]
            + [(code, "Schedule S") for code in degree.schedule_s_courses]
        )
        for code, label in all_scheduled:
            if code in courses_db:
                c = courses_db[code]
                if c["level"] <= 100:
                    sem = c["semesters"][0] if c["semesters"] else "S1"
                    entries.append(CoursePlanEntry(
                        course=code, semester=sem, points=c["points"],
                        note=f"{label} — {c['title']}"
                    ))

        if degree_code == "BE(Hons)" and major:
            disciplines = self.get_engineering_disciplines()
            for d in disciplines:
                if d["name"] == major:
                    for extra in d["first_year_extras"]:
                        actual_code = extra.split(" or ")[0].strip()
                        if actual_code in courses_db:
                            c = courses_db[actual_code]
                            entries.append(CoursePlanEntry(
                                course=actual_code, semester="S2",
                                points=c["points"],
                                note=f"Discipline — {c['title']}"
                            ))
                    break

            if not background.has_maths:
                entries.append(CoursePlanEntry(
                    course="EMTH117", semester="S1", points=15,
                    note="Bridge — Engineering Maths (no NCEA L3 Maths)"
                ))
            if not background.has_physics:
                entries.append(CoursePlanEntry(
                    course="PHYS111", semester="S1", points=15,
                    note="Bridge — Physics (no NCEA L3 Physics)"
                ))

        seen = {e.course for e in entries}
        total = sum(e.points for e in entries)

        if total < 120 and major:
            major_courses = self.get_courses_for_major(degree_code, major, level=100)
            for mc in major_courses:
                if mc.code not in seen and total < 120:
                    sem = mc.semesters[0] if mc.semesters else "S1"
                    entries.append(CoursePlanEntry(
                        course=mc.code, semester=sem, points=mc.points,
                        note=f"Major — {mc.title}"
                    ))
                    seen.add(mc.code)
                    total += mc.points

        total = sum(e.points for e in entries)
        notes_parts = [f"Year 1 plan for {degree.name}"]
        if major:
            notes_parts.append(f"({major})")
        notes_parts.append(f"— {total} points across {len(entries)} courses.")

        return CoursePlan(
            degree=degree_code,
            major=major,
            entries=entries,
            total_points=total,
            notes=" ".join(notes_parts),
        )

    # ------------------------------------------------------------------
    # Triage
    # ------------------------------------------------------------------

    def get_triage_data(self) -> dict:
        return _load_json("triage.json")

    # ------------------------------------------------------------------
    # Demo personas
    # ------------------------------------------------------------------

    def get_sample_students(self) -> list[SampleStudent]:
        return [SampleStudent(**s) for s in _load_json("sample_students.json")]

    def get_sample_student(self, student_id: str) -> SampleStudent | None:
        for s in _load_json("sample_students.json"):
            if s["id"] == student_id:
                return SampleStudent(**s)
        return None
