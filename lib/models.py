from __future__ import annotations

from pydantic import BaseModel, Field


class Faculty(BaseModel):
    code: str
    name: str
    short_name: str
    description: str
    interest_keywords: list[str] = []
    schools: list[str] = []


class DegreeStructure(BaseModel):
    schedule_v_min: int | None = None
    schedule_c_min: int | None = None
    schedule_c_all: bool | None = None
    ba_schedule_v_min: int | None = None
    elective_max: int | None = None
    above_100_min: int | None = None
    at_100_max: int | None = None
    at_300_min: int | None = None
    at_400_min: int | None = None
    non_law_min: int | None = None
    endorsement_min: int | None = None
    schedule_e_min: int | None = None
    schedule_e_group1_min: int | None = None
    schedule_e_group2_min: int | None = None
    schedule_c_group1_min: int | None = None
    schedule_c_group2_min: int | None = None
    schedule_c_group3_min: int | None = None
    year1_min: int | None = None
    years_2_4_each: int | None = None
    at_200_plus_min: int | None = None


class MajorMinorStructure(BaseModel):
    min_points: int = 0
    at_300_min: int = 0
    at_200_plus_min: int = 0


class Degree(BaseModel):
    code: str
    name: str
    faculty: str
    points: int
    duration_years: int
    degree_type: str = "bachelor"
    structure: DegreeStructure = Field(default_factory=DegreeStructure)
    schedule_c_courses: list[str] = []
    schedule_c_note: str = ""
    schedule_e_courses: list[str] = []
    schedule_e_note: str = ""
    schedule_s_courses: list[str] = []
    schedule_s_note: str = ""
    pathway_options: list[str] = []
    major_structure: MajorMinorStructure | None = None
    minor_structure: MajorMinorStructure | None = None
    specialisation_structure: MajorMinorStructure | None = None
    admission: str = ""
    notes: str = ""


class Major(BaseModel):
    name: str
    required_100: list[str] = []
    required_200: list[str] = []
    required_300: list[str] = []
    honours_req: str = ""
    has_minor: bool = True
    notes: str = ""


class Specialisation(BaseModel):
    name: str
    min_points: int = 225


class EngineeringDiscipline(BaseModel):
    name: str
    first_year_extras: list[str] = []
    places: int = 0
    minors: list[str] = []


class Endorsement(BaseModel):
    name: str
    group: int = 0
    notes: str = ""


class Course(BaseModel):
    code: str
    title: str
    points: int
    level: int
    semesters: list[str] = []
    faculty: str = ""
    prerequisites: list[str] = []
    corequisites: list[str] = []
    restrictions: list[str] = []
    limited_entry: int | None = None


class StudentBackground(BaseModel):
    qualification_type: str = "NCEA"
    has_ue: bool = True
    has_maths: bool = False
    has_physics: bool = False
    has_chemistry: bool = False
    domestic: bool = True


class CoursePlanEntry(BaseModel):
    course: str
    semester: str
    points: int
    note: str = ""


class CoursePlan(BaseModel):
    degree: str
    major: str | None = None
    entries: list[CoursePlanEntry] = []
    total_points: int = 0
    notes: str = ""


class PrereqResult(BaseModel):
    course_code: str
    met: bool
    missing: list[str] = []
    message: str = ""


class ProgressResult(BaseModel):
    degree_code: str
    major: str | None = None
    completed_points: int = 0
    remaining_points: int = 0
    percentage: float = 0.0
    missing_requirements: list[str] = []


class SampleStudent(BaseModel):
    id: str
    name: str
    description: str
    demo_narrative: str = ""
    background: StudentBackground = Field(default_factory=StudentBackground)
    interests: list[str] = []
    suggested_faculty: str = ""
    suggested_degree: str = ""
    suggested_major: str | None = None
    double_degree: str | None = None
    double_degree_major: str | None = None
    alternative_paths: list[dict] = []
    year1_plan: list[CoursePlanEntry] = []
    notes: str = ""
