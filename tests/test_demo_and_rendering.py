"""
tests/test_demo_and_rendering.py — Tests for Quick Demo mode and HTML rendering safety.
"""
import html
import pytest
from schemas import (
    StudentProfile,
    ExtractedOpportunity,
    RequirementStatus,
    EligibilityAssessment,
)
import gemma_service
from eligibility_engine import run_eligibility_check
import app


class TestQuickDemo:
    def test_sample_opportunity_structure(self):
        """Verify precomputed sample opportunity is valid and populated."""
        sample = gemma_service.get_sample_extracted_opportunity()
        assert isinstance(sample, ExtractedOpportunity)
        assert sample.title == "Northgate University Global Excellence Fellowship 2025"
        assert len(sample.eligible_countries.countries) > 0
        assert sample.cgpa_requirement.minimum == 3.5
        assert sample.age_requirement.maximum_age == 35
        assert len(sample.required_documents) > 0
        assert len(sample.other_eligibility_conditions) > 0

    def test_quick_demo_eligibility_assessment(self):
        """Verify eligibility engine computes full assessment on sample data without API calls."""
        sample = gemma_service.get_sample_extracted_opportunity()
        profile = StudentProfile(
            full_name="Amara Osei",
            country="Nigeria",
            institution="University of Lagos",
            course_of_study="Computer Science",
            academic_level="Masters",
            cgpa=3.8,
            cgpa_scale=4.0,
            age=24,
        )
        assessment = run_eligibility_check(profile, sample)
        assert assessment.overall_status in (
            "LIKELY_ELIGIBLE",
            "POTENTIALLY_ELIGIBLE",
            "LIKELY_INELIGIBLE",
        )
        assert assessment.met_count > 0

        # Check all statuses are represented
        statuses = {check.status for check in assessment.requirement_checks}
        assert "MET" in statuses
        assert "NEEDS_VERIFICATION" in statuses


class TestHTMLRenderingSafety:
    def test_no_raw_tags_or_indented_blocks_in_requirement_card(self):
        """
        Verify that requirement cards do not produce blank lines or
        indented closing tags that CommonMark converts into <pre><code> blocks.
        """
        # Test case: NEEDS_VERIFICATION with None student_value and None source_excerpt
        check_verify = RequirementStatus(
            requirement="Document: Two academic reference letters",
            status="NEEDS_VERIFICATION",
            explanation="Please confirm you have: Two academic reference letters — from university professors",
            student_value=None,
            required_value="Two academic reference letters",
            source_excerpt=None,
        )

        badge_cfg = {
            "MET": ("ol-badge-met", "ol-req-card-met", "✓ Met"),
            "NOT_MET": ("ol-badge-notmet", "ol-req-card-notmet", "✗ Not Met"),
            "NEEDS_VERIFICATION": ("ol-badge-verify", "ol-req-card-verify", "⚠ Verify"),
            "NOT_SPECIFIED": ("ol-badge-na", "ol-req-card-na", "— N/A"),
        }
        badge_cls, card_cls, badge_label = badge_cfg[check_verify.status]
        req_name = html.escape(check_verify.requirement or "Requirement")
        req_expl = html.escape(check_verify.explanation or "")

        vals_parts = []
        if check_verify.student_value:
            vals_parts.append(f"<strong>Your value:</strong> <code>{html.escape(str(check_verify.student_value))}</code>")
        if check_verify.required_value:
            vals_parts.append(f"<strong>Required:</strong> <code>{html.escape(str(check_verify.required_value))}</code>")

        vals_html = f'<div class="ol-req-vals">{"&nbsp;&nbsp;".join(vals_parts)}</div>' if vals_parts else ""
        excerpt_html = (
            f'<div class="ol-excerpt">📝 From announcement: "{html.escape(str(check_verify.source_excerpt))}"</div>'
            if check_verify.source_excerpt else ""
        )

        card_html = (
            f'<div class="ol-req-card {card_cls}">'
            f'<div style="flex-shrink:0;padding-top:2px;"><span class="ol-badge {badge_cls}">{badge_label}</span></div>'
            f'<div style="flex:1;min-width:0;">'
            f'<div class="ol-req-name">{req_name}</div>'
            f'<div class="ol-req-expl">{req_expl}</div>'
            f'{vals_html}'
            f'{excerpt_html}'
            f'</div>'
            f'</div>'
        )

        # 1. Must be a single line or cleanly stripped without blank lines
        lines = [line for line in card_html.splitlines() if line.strip()]
        for line in lines:
            assert not line.startswith("    "), "No line should have 4+ space indentation"

        # 2. Must not contain escaped literal <div> or </div> inside text
        assert "&lt;div&gt;" not in card_html
        assert "&lt;/div&gt;" not in card_html

        # 3. Tags are properly paired
        assert card_html.count("<div") == card_html.count("</div>")
        assert card_html.count("<span") == card_html.count("</span>")

    def test_all_statuses_render_cleanly(self):
        """Ensure MET, NOT_MET, NEEDS_VERIFICATION, NOT_SPECIFIED all construct valid HTML."""
        checks = [
            RequirementStatus(
                requirement="Country eligibility",
                status="MET",
                student_value="Nigeria",
                required_value="Nigeria, Ghana",
                explanation="Your country is eligible",
                source_excerpt="Open to Nigeria",
            ),
            RequirementStatus(
                requirement="CGPA",
                status="NOT_MET",
                student_value="2.8",
                required_value="3.5 / 4.0",
                explanation="Below minimum",
                source_excerpt="Min 3.5",
            ),
            RequirementStatus(
                requirement="Other condition",
                status="NEEDS_VERIFICATION",
                student_value=None,
                required_value="No high-income citizenship",
                explanation="Verify income status",
                source_excerpt=None,
            ),
            RequirementStatus(
                requirement="Age requirement",
                status="NOT_SPECIFIED",
                student_value=None,
                required_value=None,
                explanation="No age condition specified",
                source_excerpt=None,
            ),
        ]

        for check in checks:
            req_name = html.escape(check.requirement or "")
            req_expl = html.escape(check.explanation or "")
            vals_parts = []
            if check.student_value:
                vals_parts.append(f"<strong>Your value:</strong> <code>{html.escape(str(check.student_value))}</code>")
            if check.required_value:
                vals_parts.append(f"<strong>Required:</strong> <code>{html.escape(str(check.required_value))}</code>")
            vals_html = f'<div class="ol-req-vals">{"&nbsp;&nbsp;".join(vals_parts)}</div>' if vals_parts else ""
            excerpt_html = (
                f'<div class="ol-excerpt">📝 From announcement: "{html.escape(str(check.source_excerpt))}"</div>'
                if check.source_excerpt else ""
            )
            card_html = (
                f'<div class="ol-req-card">'
                f'<div><span>{check.status}</span></div>'
                f'<div><div>{req_name}</div><div>{req_expl}</div>{vals_html}{excerpt_html}</div>'
                f'</div>'
            )
            assert card_html.count("<div") == card_html.count("</div>")
            assert "&lt;div&gt;" not in card_html

