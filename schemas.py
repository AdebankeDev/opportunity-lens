"""
schemas.py — Pydantic data models for OpportunityLens.
All structured data exchanged with Gemma 4 is validated here.
"""

from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Student profile
# ---------------------------------------------------------------------------

class StudentProfile(BaseModel):
    """Student academic profile used for eligibility comparison."""
    full_name: str = ""
    country: str = ""
    institution: str = ""
    course_of_study: str = ""
    academic_level: str = ""           # e.g. "Undergraduate", "Masters", "PhD"
    cgpa: Optional[float] = None
    cgpa_scale: Optional[float] = None  # e.g. 4.0, 5.0, 7.0
    qualifications: str = ""           # free-text achievements / awards
    age: Optional[int] = None          # optional


# ---------------------------------------------------------------------------
# Opportunity extraction schema (returned by Gemma 4)
# ---------------------------------------------------------------------------

class EligibleCountries(BaseModel):
    countries: List[str] = Field(default_factory=list)
    is_open_to_all: bool = False
    raw_text: Optional[str] = None


class CGPARequirement(BaseModel):
    minimum: Optional[float] = None
    scale: Optional[float] = None        # e.g. 4.0, 5.0
    raw_text: Optional[str] = None


class AgeRequirement(BaseModel):
    minimum_age: Optional[int] = None
    maximum_age: Optional[int] = None
    raw_text: Optional[str] = None


class RequiredDocument(BaseModel):
    name: str
    description: Optional[str] = None
    is_mandatory: bool = True


class ExtractedOpportunity(BaseModel):
    """Structured representation of a scholarship/opportunity announcement."""

    # Core identity
    title: Optional[str] = None
    organizing_institution: Optional[str] = None
    category: Optional[str] = None          # scholarship / internship / fellowship / grant / training
    description: Optional[str] = None

    # Eligibility
    eligible_countries: EligibleCountries = Field(default_factory=EligibleCountries)
    academic_level_requirements: List[str] = Field(default_factory=list)
    course_restrictions: List[str] = Field(default_factory=list)
    cgpa_requirement: CGPARequirement = Field(default_factory=CGPARequirement)
    age_requirement: AgeRequirement = Field(default_factory=AgeRequirement)
    other_eligibility_conditions: List[str] = Field(default_factory=list)

    # Documents & logistics
    required_documents: List[RequiredDocument] = Field(default_factory=list)
    application_deadline: Optional[str] = None   # kept as string; may be "Not specified"
    benefits: List[str] = Field(default_factory=list)
    application_instructions: Optional[str] = None
    official_url: Optional[str] = None

    # Trust & evidence
    extraction_notes: Optional[str] = None      # any caveats the model noted
    raw_announcement_length: Optional[int] = None


# ---------------------------------------------------------------------------
# Eligibility result
# ---------------------------------------------------------------------------

class RequirementStatus(BaseModel):
    """The result of checking one eligibility criterion."""
    requirement: str
    status: str                  # "MET" | "NOT_MET" | "NEEDS_VERIFICATION" | "NOT_SPECIFIED"
    student_value: Optional[str] = None
    required_value: Optional[str] = None
    explanation: str
    source_excerpt: Optional[str] = None  # from the original announcement


class EligibilityAssessment(BaseModel):
    """Overall eligibility assessment produced by the eligibility engine."""
    overall_status: str          # "LIKELY_ELIGIBLE" | "POTENTIALLY_ELIGIBLE" | "LIKELY_INELIGIBLE" | "INSUFFICIENT_INFORMATION"
    overall_explanation: str
    requirement_checks: List[RequirementStatus] = Field(default_factory=list)
    met_count: int = 0
    not_met_count: int = 0
    needs_verification_count: int = 0
    not_specified_count: int = 0
    disclaimer: str = (
        "This assessment is preliminary and does not guarantee acceptance. "
        "Always verify requirements directly with the awarding institution."
    )


# ---------------------------------------------------------------------------
# Checklist
# ---------------------------------------------------------------------------

class ChecklistItem(BaseModel):
    """A single item in the application preparation checklist."""
    id: str
    category: str               # "document" | "action" | "verification"
    description: str
    detail: Optional[str] = None
    completed: bool = False

