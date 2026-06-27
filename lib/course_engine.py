"""Course rules engine — validates selections against UC Calendar regulations."""

from __future__ import annotations

from dataclasses import dataclass, field

from .data_layer import CoursePlannerMCP
from .models import StudentBackground


@dataclass
class ValidationMessage:
    level: str  # "error", "warning", "info"
    message: str


@dataclass
class ValidationResult:
    valid: bool = True
    messages: list[ValidationMessage] = field(default_factory=list)

    def add_error(self, msg: str) -> None:
        self.valid = False
        self.messages.append(ValidationMessage("error", msg))

    def add_warning(self, msg: str) -> None:
        self.messages.append(ValidationMessage("warning", msg))

    def add_info(self, msg: str) -> None:
        self.messages.append(ValidationMessage("info", msg))


class CourseEngine:
    """Validates degree/major/course selections against Calendar rules."""

    def __init__(self, mcp: CoursePlannerMCP | None = None):
        self.mcp = mcp or CoursePlannerMCP()

    def validate_admission(
        self, degree_code: str, background: StudentBackground
    ) -> ValidationResult:
        result = ValidationResult()
        degree = self.mcp.get_degree(degree_code)

        if not degree:
            result.add_error(f"Unknown degree code: {degree_code}")
            return result

        if not background.has_ue:
            if background.qualification_type == "Mature student (20+)":
                result.add_info(
                    "You may be eligible for discretionary or special admission. "
                    "Contact UC Enrolments for assessment."
                )
            else:
                result.add_error(
                    "University Entrance (UE) is required. "
                    "Consider Foundation Studies or a bridging programme."
                )

        if degree_code == "BE(Hons)":
            if not background.has_maths:
                result.add_warning(
                    "Engineering requires Year 13 Maths. You will need to take "
                    "the bridge course EMTH117 before EMTH118."
                )
            if not background.has_physics:
                result.add_warning(
                    "Engineering requires Year 13 Physics. You will need to take "
                    "the bridge course PHYS111 before PHYS101."
                )

        if degree_code == "BTchLn":
            result.add_info(
                "BTchLn requires a special application by 1 December (domestic) "
                "or 31 October (international). Includes interview, literacy/"
                "numeracy tests, referee reports, police vetting, and Children's "
                "Act 2014 compliance."
            )

        if degree_code == "BFA":
            result.add_info(
                "BFA is limited entry (78 places). A portfolio submission and "
                "special application by 15 November is required."
            )

        if degree_code == "BSW(Hons)":
            if not background.domestic:
                result.add_warning(
                    "BSW(Hons) requires IELTS 6.5 overall (no band below 6.5) "
                    "for non-native English speakers."
                )
            result.add_info(
                "BSW(Hons) involves police vetting and suitability assessment "
                "at multiple progression points."
            )

        if degree_code == "LLB":
            result.add_info(
                "LAWS 200-level courses are limited entry (310–350 places). "
                "Application by 1 December. Competitive GPA from Year 1 "
                "determines entry."
            )

        return result

    def validate_degree_major_combination(
        self, degree_code: str, major_name: str
    ) -> ValidationResult:
        result = ValidationResult()

        degree = self.mcp.get_degree(degree_code)
        if not degree:
            result.add_error(f"Unknown degree: {degree_code}")
            return result

        available_majors = self.mcp.get_majors_for_degree(degree_code)
        major_names = [m.name for m in available_majors]

        if not major_names:
            if degree_code in ("LLB", "BCJ", "BSW(Hons)", "BYCL"):
                result.add_info(
                    f"{degree.name} is a fixed programme with no major selection."
                )
            else:
                result.add_warning(f"No majors found for {degree.name}.")
            return result

        if major_name not in major_names:
            result.add_error(
                f"'{major_name}' is not a valid major for {degree.name}. "
                f"Available: {', '.join(major_names)}"
            )
        else:
            target = next(m for m in available_majors if m.name == major_name)
            if target.notes:
                result.add_info(target.notes)

        return result

    def check_engineering_discipline_fit(
        self, discipline: str, background: StudentBackground
    ) -> ValidationResult:
        result = ValidationResult()

        disciplines = self.mcp.get_engineering_disciplines()
        disc_names = [d["name"] for d in disciplines]
        if discipline not in disc_names:
            result.add_error(
                f"'{discipline}' is not a valid BE(Hons) discipline. "
                f"Available: {', '.join(disc_names)}"
            )
            return result

        target = next(d for d in disciplines if d["name"] == discipline)

        result.add_info(
            f"{discipline} has {target['places']} places. "
            "Allocation is competitive based on First Year GPA."
        )

        extras = target.get("first_year_extras", [])
        if extras:
            result.add_info(
                f"Year 1 discipline-specific courses: {', '.join(extras)}"
            )

        minors = target.get("minors", [])
        if minors:
            result.add_info(f"Available engineering minors: {', '.join(minors)}")

        return result

    def check_double_degree_eligibility(
        self, degree1: str, degree2: str, background: StudentBackground
    ) -> ValidationResult:
        result = ValidationResult()

        conjoint_engineering = {
            "BA", "BCom", "BDataSc", "BProdDesign", "BSc", "BSEnS", "BSport"
        }

        if degree1 == "BE(Hons)" or degree2 == "BE(Hons)":
            other = degree2 if degree1 == "BE(Hons)" else degree1
            if other not in conjoint_engineering:
                result.add_error(
                    f"BE(Hons) conjoint is not available with {other}. "
                    f"Available: {', '.join(sorted(conjoint_engineering))}"
                )
            else:
                result.add_info(
                    f"BE(Hons)/{other} conjoint is 675 points (approx. 5 years). "
                    "Requires NCEA Merit/Excellence endorsement or GPA ≥ 6.0."
                )

        llb_combos = {"BA", "BCom", "BSc"}
        if degree1 == "LLB" or degree2 == "LLB":
            other = degree2 if degree1 == "LLB" else degree1
            if other not in llb_combos and other != "BCJ":
                result.add_warning(
                    f"LLB is most commonly combined with BA, BCom, or BSc. "
                    f"{other} is less typical — check with the Faculty of Law."
                )
            else:
                result.add_info(
                    f"LLB/{other} double degree: a common and well-supported "
                    "combination."
                )

        return result

    def get_cross_faculty_options(self, subject: str) -> list[dict]:
        triage = self.mcp.get_triage_data()
        cross = triage.get("cross_faculty_subjects", {})
        subject_lower = subject.lower().replace(" ", "_")

        if subject_lower in cross:
            return [cross[subject_lower]]

        for key, val in cross.items():
            if subject.lower() in key:
                return [val]

        return []
