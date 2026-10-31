"""
tests/test_schemas.py — Tests for Pydantic schema validation.
"""
import pytest
from pydantic import ValidationError
from schemas import (
    StudentProfile,
    ExtractedOpportunity,
    EligibleCountries,
    CGPARequirement,
    AgeRequirement,
    RequiredDocument,
    EligibilityAssessment,
    RequirementStatus,
    ChecklistItem,
)


class TestStudentProfile:
    def test_empty_profile_valid(self):
        p = StudentProfile()
        assert p.full_name == ""
        assert p.cgpa is None
        assert p.age is None

    def test_full_profile(self):
        p = StudentProfile(
            full_name="Jane Doe",
            country="Ghana",
            institution="KNUST",
            course_of_study="Engineering",
            academic_level="Masters",
            cgpa=3.9,
            cgpa_scale=4.0,
            qualifications="Dean's list",
            age=26,
        )
        assert p.full_name == "Jane Doe"
        assert p.cgpa == 3.9
        assert p.age == 26


class TestExtractedOpportunity:
    def test_defaults_valid(self):
        opp = ExtractedOpportunity()
        assert opp.title is None
        assert opp.eligible_countries.countries == []
        assert opp.required_documents == []

    def test_full_construction(self):
        opp = ExtractedOpportunity(
            title="Test Scholarship",
            organizing_institution="Test Uni",
            category="scholarship",
            eligible_countries=EligibleCountries(
                countries=["Nigeria", "Ghana"],
                is_open_to_all=False,
                raw_text="Open to citizens of Nigeria and Ghana",
            ),
            academic_level_requirements=["Undergraduate"],
            cgpa_requirement=CGPARequirement(minimum=3.0, scale=4.0),
            age_requirement=AgeRequirement(maximum_age=30),
            required_documents=[
                RequiredDocument(name="Transcript", description="Official copy", is_mandatory=True)
            ],
            application_deadline="31 December 2025",
            official_url="https://example.com/apply",
        )
        assert opp.title == "Test Scholarship"
        assert len(opp.eligible_countries.countries) == 2
        assert opp.cgpa_requirement.minimum == 3.0
        assert opp.application_deadline == "31 December 2025"

    def test_none_values_acceptable(self):
        opp = ExtractedOpportunity(
            title=None,
            application_deadline=None,
            official_url=None,
        )
        assert opp.title is None
        assert opp.application_deadline is None


class TestRequirementStatus:
    def test_valid_statuses(self):
        for status in ["MET", "NOT_MET", "NEEDS_VERIFICATION", "NOT_SPECIFIED"]:
            r = RequirementStatus(
                requirement="Country",
                status=status,
                explanation="Test explanation",
            )
            assert r.status == status

    def test_optional_fields_default_none(self):
        r = RequirementStatus(
            requirement="Test",
            status="NOT_SPECIFIED",
            explanation="No info",
        )
        assert r.student_value is None
        assert r.required_value is None
        assert r.source_excerpt is None


class TestEligibilityAssessment:
    def test_full_assessment(self):
        a = EligibilityAssessment(
            overall_status="LIKELY_ELIGIBLE",
            overall_explanation="All requirements met.",
            requirement_checks=[
                RequirementStatus(requirement="Country", status="MET", explanation="OK"),
            ],
            met_count=1,
            not_met_count=0,
            needs_verification_count=0,
            not_specified_count=0,
        )
        assert a.overall_status == "LIKELY_ELIGIBLE"
        assert a.met_count == 1
        assert "preliminary" in a.disclaimer.lower()


class TestChecklistItem:
    def test_checklist_item_defaults(self):
        item = ChecklistItem(
            id="test-id",
            category="document",
            description="Obtain transcript",
        )
        assert not item.completed
        assert item.detail is None

    def test_can_mark_complete(self):
        item = ChecklistItem(
            id="test-id-2",
            category="action",
            description="Submit application",
            completed=True,
        )
        assert item.completed

