"""
tests/test_eligibility_engine.py — Tests for the rule-based eligibility engine.
"""
import pytest
from schemas import (
    StudentProfile,
    ExtractedOpportunity,
    EligibleCountries,
    CGPARequirement,
    AgeRequirement,
    RequiredDocument,
)
from eligibility_engine import run_eligibility_check


def make_profile(**kwargs) -> StudentProfile:
    defaults = dict(
        full_name="Test Student",
        country="Nigeria",
        institution="University of Lagos",
        course_of_study="Computer Science",
        academic_level="Masters",
        cgpa=3.7,
        cgpa_scale=4.0,
    )
    defaults.update(kwargs)
    return StudentProfile(**defaults)


def make_opportunity(**kwargs) -> ExtractedOpportunity:
    defaults = dict(
        title="Test Fellowship",
        eligible_countries=EligibleCountries(countries=["Nigeria", "Ghana"], is_open_to_all=False),
        academic_level_requirements=["Masters", "PhD"],
        cgpa_requirement=CGPARequirement(minimum=3.5, scale=4.0),
        required_documents=[RequiredDocument(name="Passport", is_mandatory=True)],
    )
    defaults.update(kwargs)
    return ExtractedOpportunity(**defaults)


class TestCountryCheck:
    def test_eligible_country(self):
        profile = make_profile(country="Nigeria")
        opp = make_opportunity()
        result = run_eligibility_check(profile, opp)
        country_check = next(c for c in result.requirement_checks if "Country" in c.requirement)
        assert country_check.status == "MET"

    def test_ineligible_country(self):
        profile = make_profile(country="France")
        opp = make_opportunity()
        result = run_eligibility_check(profile, opp)
        country_check = next(c for c in result.requirement_checks if "Country" in c.requirement)
        assert country_check.status == "NOT_MET"

    def test_open_to_all(self):
        profile = make_profile(country="Antarctica")
        opp = make_opportunity(
            eligible_countries=EligibleCountries(is_open_to_all=True, countries=[])
        )
        result = run_eligibility_check(profile, opp)
        country_check = next(c for c in result.requirement_checks if "Country" in c.requirement)
        assert country_check.status == "MET"

    def test_no_country_in_profile(self):
        profile = make_profile(country="")
        opp = make_opportunity()
        result = run_eligibility_check(profile, opp)
        country_check = next(c for c in result.requirement_checks if "Country" in c.requirement)
        assert country_check.status == "NEEDS_VERIFICATION"

    def test_not_specified(self):
        profile = make_profile()
        opp = make_opportunity(
            eligible_countries=EligibleCountries(countries=[], is_open_to_all=False)
        )
        result = run_eligibility_check(profile, opp)
        country_check = next(c for c in result.requirement_checks if "Country" in c.requirement)
        assert country_check.status == "NOT_SPECIFIED"


class TestAcademicLevelCheck:
    def test_matching_level(self):
        profile = make_profile(academic_level="Masters")
        opp = make_opportunity(academic_level_requirements=["Masters"])
        result = run_eligibility_check(profile, opp)
        level_check = next(c for c in result.requirement_checks if "Academic level" in c.requirement)
        assert level_check.status == "MET"

    def test_non_matching_level(self):
        profile = make_profile(academic_level="Undergraduate (Final Year)")
        opp = make_opportunity(academic_level_requirements=["PhD"])
        result = run_eligibility_check(profile, opp)
        level_check = next(c for c in result.requirement_checks if "Academic level" in c.requirement)
        assert level_check.status == "NOT_MET"

    def test_no_requirement(self):
        profile = make_profile()
        opp = make_opportunity(academic_level_requirements=[])
        result = run_eligibility_check(profile, opp)
        level_check = next(c for c in result.requirement_checks if "Academic level" in c.requirement)
        assert level_check.status == "NOT_SPECIFIED"


class TestCGPACheck:
    def test_meets_cgpa(self):
        profile = make_profile(cgpa=3.8, cgpa_scale=4.0)
        opp = make_opportunity(cgpa_requirement=CGPARequirement(minimum=3.5, scale=4.0))
        result = run_eligibility_check(profile, opp)
        cgpa_check = next((c for c in result.requirement_checks if "CGPA" in c.requirement), None)
        assert cgpa_check is not None
        assert cgpa_check.status == "MET"

    def test_fails_cgpa(self):
        profile = make_profile(cgpa=2.9, cgpa_scale=4.0)
        opp = make_opportunity(cgpa_requirement=CGPARequirement(minimum=3.5, scale=4.0))
        result = run_eligibility_check(profile, opp)
        cgpa_check = next((c for c in result.requirement_checks if "CGPA" in c.requirement), None)
        assert cgpa_check is not None
        assert cgpa_check.status == "NOT_MET"

    def test_scale_mismatch_needs_verification(self):
        """NEVER invent a CGPA conversion. Different scales → NEEDS_VERIFICATION."""
        profile = make_profile(cgpa=4.5, cgpa_scale=5.0)
        opp = make_opportunity(cgpa_requirement=CGPARequirement(minimum=3.5, scale=4.0))
        result = run_eligibility_check(profile, opp)
        cgpa_check = next((c for c in result.requirement_checks if "CGPA" in c.requirement), None)
        assert cgpa_check is not None
        assert cgpa_check.status == "NEEDS_VERIFICATION"

    def test_no_cgpa_in_profile(self):
        profile = make_profile(cgpa=None, cgpa_scale=None)
        opp = make_opportunity(cgpa_requirement=CGPARequirement(minimum=3.5, scale=4.0))
        result = run_eligibility_check(profile, opp)
        cgpa_check = next((c for c in result.requirement_checks if "CGPA" in c.requirement), None)
        assert cgpa_check is not None
        assert cgpa_check.status == "NEEDS_VERIFICATION"

    def test_no_cgpa_requirement(self):
        profile = make_profile()
        opp = make_opportunity(cgpa_requirement=CGPARequirement(minimum=None))
        result = run_eligibility_check(profile, opp)
        cgpa_checks = [c for c in result.requirement_checks if "CGPA" in c.requirement]
        assert len(cgpa_checks) == 0  # No CGPA check generated


class TestAgeCheck:
    def test_within_age_range(self):
        profile = make_profile(age=28)
        opp = make_opportunity(age_requirement=AgeRequirement(maximum_age=35))
        result = run_eligibility_check(profile, opp)
        age_check = next((c for c in result.requirement_checks if "Age" in c.requirement), None)
        assert age_check is not None
        assert age_check.status == "MET"

    def test_exceeds_max_age(self):
        profile = make_profile(age=40)
        opp = make_opportunity(age_requirement=AgeRequirement(maximum_age=35))
        result = run_eligibility_check(profile, opp)
        age_check = next((c for c in result.requirement_checks if "Age" in c.requirement), None)
        assert age_check is not None
        assert age_check.status == "NOT_MET"

    def test_no_age_in_profile(self):
        profile = make_profile(age=None)
        opp = make_opportunity(age_requirement=AgeRequirement(maximum_age=35))
        result = run_eligibility_check(profile, opp)
        age_check = next((c for c in result.requirement_checks if "Age" in c.requirement), None)
        assert age_check is not None
        assert age_check.status == "NEEDS_VERIFICATION"

    def test_no_age_requirement(self):
        profile = make_profile(age=30)
        opp = make_opportunity()
        result = run_eligibility_check(profile, opp)
        age_checks = [c for c in result.requirement_checks if "Age" in c.requirement]
        assert len(age_checks) == 0


class TestOverallAssessment:
    def test_all_met_is_likely_eligible(self):
        profile = make_profile(country="Nigeria", cgpa=3.8, cgpa_scale=4.0, academic_level="Masters")
        opp = make_opportunity(
            eligible_countries=EligibleCountries(countries=["Nigeria"]),
            academic_level_requirements=["Masters"],
            cgpa_requirement=CGPARequirement(minimum=3.5, scale=4.0),
            required_documents=[],
            other_eligibility_conditions=[],
        )
        result = run_eligibility_check(profile, opp)
        assert result.overall_status == "LIKELY_ELIGIBLE"

    def test_not_met_item_is_likely_ineligible(self):
        profile = make_profile(country="France")  # France not in eligible countries
        opp = make_opportunity()
        result = run_eligibility_check(profile, opp)
        assert result.overall_status == "LIKELY_INELIGIBLE"
        assert result.not_met_count > 0

    def test_counts_correct(self):
        profile = make_profile(country="Nigeria", cgpa=2.9, cgpa_scale=4.0, academic_level="Masters")
        opp = make_opportunity()
        result = run_eligibility_check(profile, opp)
        assert result.met_count + result.not_met_count + result.needs_verification_count + result.not_specified_count == len(result.requirement_checks)

