"""
eligibility_engine.py — Rule-based eligibility comparison for OpportunityLens.

The engine compares a student profile against extracted opportunity requirements.
It NEVER delegates eligibility decisions entirely to an LLM — every check is
implemented in Python with explicit logic. This makes results transparent,
testable and trustworthy.
"""

from __future__ import annotations
import re
from typing import Optional, List, Tuple
from schemas import (
    StudentProfile,
    ExtractedOpportunity,
    RequirementStatus,
    EligibilityAssessment,
)

# ---------------------------------------------------------------------------
# Academic level normalisation
# ---------------------------------------------------------------------------

LEVEL_HIERARCHY = {
    "high school": 0,
    "secondary school": 0,
    "pre-university": 0,
    "undergraduate": 1,
    "bachelor": 1,
    "bachelors": 1,
    "bsc": 1,
    "ba": 1,
    "honours": 1,
    "postgraduate": 2,
    "masters": 2,
    "master": 2,
    "msc": 2,
    "ma": 2,
    "mba": 2,
    "phd": 3,
    "doctoral": 3,
    "doctorate": 3,
}


def _normalise_level(level: str) -> Optional[int]:
    """Return numeric tier for an academic level string, or None."""
    low = level.lower().strip()
    for key, val in LEVEL_HIERARCHY.items():
        if key in low:
            return val
    return None


# ---------------------------------------------------------------------------
# Individual requirement checks
# ---------------------------------------------------------------------------

def _check_country(
    student: StudentProfile, opp: ExtractedOpportunity
) -> RequirementStatus:
    ec = opp.eligible_countries

    if ec.is_open_to_all:
        return RequirementStatus(
            requirement="Country eligibility",
            status="MET",
            student_value=student.country,
            required_value="Open to all countries",
            explanation="This opportunity is open to applicants from all countries.",
            source_excerpt=ec.raw_text,
        )

    if not ec.countries:
        return RequirementStatus(
            requirement="Country eligibility",
            status="NOT_SPECIFIED",
            student_value=student.country,
            required_value=None,
            explanation="No country restriction was found in the announcement.",
            source_excerpt=ec.raw_text,
        )

    if not student.country:
        return RequirementStatus(
            requirement="Country eligibility",
            status="NEEDS_VERIFICATION",
            student_value=None,
            required_value=", ".join(ec.countries),
            explanation="Your country has not been set in your profile. Please update it.",
            source_excerpt=ec.raw_text,
        )

    student_country_low = student.country.lower().strip()
    match = any(
        student_country_low in c.lower() or c.lower() in student_country_low
        for c in ec.countries
    )

    if match:
        return RequirementStatus(
            requirement="Country eligibility",
            status="MET",
            student_value=student.country,
            required_value=", ".join(ec.countries),
            explanation=f"Your country ({student.country}) is in the list of eligible countries.",
            source_excerpt=ec.raw_text,
        )
    else:
        return RequirementStatus(
            requirement="Country eligibility",
            status="NOT_MET",
            student_value=student.country,
            required_value=", ".join(ec.countries),
            explanation=(
                f"Your country ({student.country}) does not appear in the eligible countries: "
                f"{', '.join(ec.countries)}."
            ),
            source_excerpt=ec.raw_text,
        )


def _check_academic_level(
    student: StudentProfile, opp: ExtractedOpportunity
) -> RequirementStatus:
    reqs = opp.academic_level_requirements

    if not reqs:
        return RequirementStatus(
            requirement="Academic level",
            status="NOT_SPECIFIED",
            student_value=student.academic_level,
            required_value=None,
            explanation="No specific academic level requirement was found.",
        )

    if not student.academic_level:
        return RequirementStatus(
            requirement="Academic level",
            status="NEEDS_VERIFICATION",
            student_value=None,
            required_value=", ".join(reqs),
            explanation="Your academic level has not been set. Please update your profile.",
        )

    student_tier = _normalise_level(student.academic_level)
    matched_any = False

    for req in reqs:
        req_tier = _normalise_level(req)
        if req_tier is None:
            # Cannot parse — fall back to substring check
            if student.academic_level.lower() in req.lower() or req.lower() in student.academic_level.lower():
                matched_any = True
                break
        else:
            if student_tier == req_tier:
                matched_any = True
                break

    if matched_any:
        return RequirementStatus(
            requirement="Academic level",
            status="MET",
            student_value=student.academic_level,
            required_value=", ".join(reqs),
            explanation=f"Your academic level ({student.academic_level}) meets the requirement.",
        )
    else:
        return RequirementStatus(
            requirement="Academic level",
            status="NOT_MET",
            student_value=student.academic_level,
            required_value=", ".join(reqs),
            explanation=(
                f"Your academic level ({student.academic_level}) does not match "
                f"the required level(s): {', '.join(reqs)}."
            ),
        )


def _check_course(
    student: StudentProfile, opp: ExtractedOpportunity
) -> Optional[RequirementStatus]:
    reqs = opp.course_restrictions
    if not reqs:
        return None  # No restriction — skip

    if not student.course_of_study:
        return RequirementStatus(
            requirement="Course / discipline",
            status="NEEDS_VERIFICATION",
            student_value=None,
            required_value=", ".join(reqs),
            explanation="Your course of study has not been set. Please update your profile.",
        )

    student_course_low = student.course_of_study.lower()
    matched = any(
        r.lower() in student_course_low or student_course_low in r.lower()
        for r in reqs
    )

    if matched:
        return RequirementStatus(
            requirement="Course / discipline",
            status="MET",
            student_value=student.course_of_study,
            required_value=", ".join(reqs),
            explanation=f"Your course ({student.course_of_study}) matches the required disciplines.",
        )
    else:
        return RequirementStatus(
            requirement="Course / discipline",
            status="NEEDS_VERIFICATION",
            student_value=student.course_of_study,
            required_value=", ".join(reqs),
            explanation=(
                f"Your course ({student.course_of_study}) may not be in the eligible disciplines "
                f"({', '.join(reqs)}). Verify with the awarding institution."
            ),
        )


def _check_cgpa(
    student: StudentProfile, opp: ExtractedOpportunity
) -> Optional[RequirementStatus]:
    req = opp.cgpa_requirement

    if req.minimum is None:
        return None  # No CGPA requirement

    if student.cgpa is None:
        return RequirementStatus(
            requirement="CGPA",
            status="NEEDS_VERIFICATION",
            student_value=None,
            required_value=_cgpa_label(req.minimum, req.scale),
            explanation="Your CGPA has not been set. Please update your profile.",
            source_excerpt=req.raw_text,
        )

    # ── Scale compatibility check ────────────────────────────────────────────
    if req.scale is not None and student.cgpa_scale is not None:
        if abs(req.scale - student.cgpa_scale) > 0.05:
            return RequirementStatus(
                requirement="CGPA",
                status="NEEDS_VERIFICATION",
                student_value=f"{student.cgpa:.2f} / {student.cgpa_scale:.1f}",
                required_value=_cgpa_label(req.minimum, req.scale),
                explanation=(
                    f"Your CGPA grading scale ({student.cgpa_scale}) differs from the "
                    f"required scale ({req.scale}). Reliable conversion is not possible. "
                    f"Please verify with the awarding institution."
                ),
                source_excerpt=req.raw_text,
            )

    # ── Same (or undetermined) scale — direct comparison ─────────────────────
    if student.cgpa >= req.minimum:
        return RequirementStatus(
            requirement="CGPA",
            status="MET",
            student_value=f"{student.cgpa:.2f}",
            required_value=_cgpa_label(req.minimum, req.scale),
            explanation=f"Your CGPA ({student.cgpa:.2f}) meets the minimum requirement ({req.minimum:.2f}).",
            source_excerpt=req.raw_text,
        )
    else:
        return RequirementStatus(
            requirement="CGPA",
            status="NOT_MET",
            student_value=f"{student.cgpa:.2f}",
            required_value=_cgpa_label(req.minimum, req.scale),
            explanation=f"Your CGPA ({student.cgpa:.2f}) is below the minimum requirement ({req.minimum:.2f}).",
            source_excerpt=req.raw_text,
        )


def _cgpa_label(minimum: float, scale: Optional[float]) -> str:
    if scale:
        return f"{minimum:.2f} / {scale:.1f}"
    return f"{minimum:.2f}"


def _check_age(
    student: StudentProfile, opp: ExtractedOpportunity
) -> Optional[RequirementStatus]:
    req = opp.age_requirement
    if req.minimum_age is None and req.maximum_age is None:
        return None

    if student.age is None:
        return RequirementStatus(
            requirement="Age requirement",
            status="NEEDS_VERIFICATION",
            student_value=None,
            required_value=_age_label(req),
            explanation=(
                "This opportunity has an age requirement but your age is not in your profile. "
                "Add your age to get a definitive check."
            ),
            source_excerpt=req.raw_text,
        )

    age = student.age
    meets_min = req.minimum_age is None or age >= req.minimum_age
    meets_max = req.maximum_age is None or age <= req.maximum_age

    if meets_min and meets_max:
        return RequirementStatus(
            requirement="Age requirement",
            status="MET",
            student_value=str(age),
            required_value=_age_label(req),
            explanation=f"Your age ({age}) is within the allowed range.",
            source_excerpt=req.raw_text,
        )
    else:
        return RequirementStatus(
            requirement="Age requirement",
            status="NOT_MET",
            student_value=str(age),
            required_value=_age_label(req),
            explanation=f"Your age ({age}) falls outside the required range ({_age_label(req)}).",
            source_excerpt=req.raw_text,
        )


def _age_label(req) -> str:
    parts = []
    if req.minimum_age:
        parts.append(f"Min {req.minimum_age}")
    if req.maximum_age:
        parts.append(f"Max {req.maximum_age}")
    return " / ".join(parts)


def _check_other_conditions(
    opp: ExtractedOpportunity,
) -> List[RequirementStatus]:
    results = []
    for condition in opp.other_eligibility_conditions:
        results.append(
            RequirementStatus(
                requirement="Other condition",
                status="NEEDS_VERIFICATION",
                student_value=None,
                required_value=condition,
                explanation=(
                    f"This condition requires manual verification: {condition}"
                ),
            )
        )
    return results


def _check_documents(
    opp: ExtractedOpportunity,
) -> List[RequirementStatus]:
    results = []
    for doc in opp.required_documents:
        results.append(
            RequirementStatus(
                requirement=f"Document: {doc.name}",
                status="NEEDS_VERIFICATION",
                student_value=None,
                required_value=doc.name,
                explanation=(
                    f"Please confirm you have: {doc.name}"
                    + (f" — {doc.description}" if doc.description else "")
                ),
            )
        )
    return results


# ---------------------------------------------------------------------------
# Overall assessment logic
# ---------------------------------------------------------------------------

def _compute_overall(
    checks: List[RequirementStatus],
) -> Tuple[str, str]:
    met = sum(1 for c in checks if c.status == "MET")
    not_met = sum(1 for c in checks if c.status == "NOT_MET")
    needs_v = sum(1 for c in checks if c.status == "NEEDS_VERIFICATION")
    not_spec = sum(1 for c in checks if c.status == "NOT_SPECIFIED")
    total = len(checks)

    if total == 0:
        return (
            "INSUFFICIENT_INFORMATION",
            "No eligibility requirements could be extracted from the announcement.",
        )

    if not_met > 0:
        return (
            "LIKELY_INELIGIBLE",
            (
                f"You do not meet {not_met} requirement(s). "
                "Review the 'Not Met' items below — some may be deal-breakers. "
                "Verify directly with the awarding institution before deciding not to apply."
            ),
        )

    if needs_v > 0 or not_spec == total:
        if met == 0 and needs_v > 0:
            return (
                "INSUFFICIENT_INFORMATION",
                (
                    f"{needs_v} requirement(s) need verification and no requirements could be "
                    "confirmed as met. Complete your profile and review the items below."
                ),
            )
        return (
            "POTENTIALLY_ELIGIBLE",
            (
                f"You meet {met} requirement(s) but {needs_v} still need verification. "
                "Complete all verification steps before applying."
            ),
        )

    return (
        "LIKELY_ELIGIBLE",
        (
            f"You appear to meet all {met} identified requirement(s). "
            "Review the checklist and apply before the deadline."
        ),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_eligibility_check(
    student: StudentProfile,
    opportunity: ExtractedOpportunity,
) -> EligibilityAssessment:
    """
    Compare a student profile against an extracted opportunity and
    return a fully-explained EligibilityAssessment.
    """
    checks: List[RequirementStatus] = []

    checks.append(_check_country(student, opportunity))
    checks.append(_check_academic_level(student, opportunity))

    course_check = _check_course(student, opportunity)
    if course_check:
        checks.append(course_check)

    cgpa_check = _check_cgpa(student, opportunity)
    if cgpa_check:
        checks.append(cgpa_check)

    age_check = _check_age(student, opportunity)
    if age_check:
        checks.append(age_check)

    checks.extend(_check_other_conditions(opportunity))
    checks.extend(_check_documents(opportunity))

    overall_status, overall_explanation = _compute_overall(checks)

    met_count = sum(1 for c in checks if c.status == "MET")
    not_met_count = sum(1 for c in checks if c.status == "NOT_MET")
    needs_v_count = sum(1 for c in checks if c.status == "NEEDS_VERIFICATION")
    not_spec_count = sum(1 for c in checks if c.status == "NOT_SPECIFIED")

    return EligibilityAssessment(
        overall_status=overall_status,
        overall_explanation=overall_explanation,
        requirement_checks=checks,
        met_count=met_count,
        not_met_count=not_met_count,
        needs_verification_count=needs_v_count,
        not_specified_count=not_spec_count,
    )

