"""
gemma_service.py — Gemma 4 API integration for OpportunityLens.

This module is the only place that communicates with the Google Gen AI API.
Model configuration lives here so it can be changed in one place.
"""

from __future__ import annotations
import json
import os
import re
import time
from pathlib import Path
from typing import Optional, Tuple

# ── Ensure .env is loaded from explicit path relative to this file ─────────────
ENV_PATH = Path(__file__).resolve().parent / ".env"
try:
    from dotenv import load_dotenv
    if ENV_PATH.exists():
        load_dotenv(dotenv_path=ENV_PATH, override=True)
except ImportError:
    pass

from google import genai
from google.genai import types

from schemas import (
    ExtractedOpportunity,
    EligibleCountries,
    CGPARequirement,
    AgeRequirement,
    RequiredDocument,
)

# ---------------------------------------------------------------------------
# Model configuration — change here only
# ---------------------------------------------------------------------------

PRIMARY_MODEL = "gemma-4-26b-a4b-it"
FALLBACK_MODELS = [
    "gemma-4-12b-it",
    "gemma-3-27b-it",
]

# ---------------------------------------------------------------------------
# System instruction
# ---------------------------------------------------------------------------

EXTRACTION_SYSTEM_INSTRUCTION = """You are an expert scholarship and opportunity analyst.
Your task is to extract structured information from an opportunity announcement (scholarship, internship, fellowship, grant or training programme).

STRICT RULES:
1. Only extract information explicitly stated in the announcement. Do NOT invent or infer requirements not present in the text.
2. Return null (JSON null) for any field where information is absent. Do NOT guess.
3. Distinguish "not stated" (null) from "open to all" (is_open_to_all: true for countries).
4. Preserve important conditions and exceptions exactly as stated.
5. For CGPA, record both the minimum value AND the grading scale if stated (e.g. 3.0/4.0).
6. For deadlines, extract the exact text as stated. If no deadline is mentioned, return null.
7. For URLs, only include URLs explicitly present in the text.
8. In extraction_notes, record any ambiguities, conflicts or limitations you encountered.
9. Do NOT fabricate quotations, page numbers, or URLs.
10. Do NOT assume the student is eligible — your job is only to extract requirements.

Return ONLY a valid JSON object matching the schema. No markdown, no commentary outside the JSON.

JSON Schema:
{
  "title": string | null,
  "organizing_institution": string | null,
  "category": "scholarship" | "internship" | "fellowship" | "grant" | "training" | "other" | null,
  "description": string | null,
  "eligible_countries": {
    "countries": [string],
    "is_open_to_all": boolean,
    "raw_text": string | null
  },
  "academic_level_requirements": [string],
  "course_restrictions": [string],
  "cgpa_requirement": {
    "minimum": number | null,
    "scale": number | null,
    "raw_text": string | null
  },
  "age_requirement": {
    "minimum_age": integer | null,
    "maximum_age": integer | null,
    "raw_text": string | null
  },
  "other_eligibility_conditions": [string],
  "required_documents": [
    {
      "name": string,
      "description": string | null,
      "is_mandatory": boolean
    }
  ],
  "application_deadline": string | null,
  "benefits": [string],
  "application_instructions": string | null,
  "official_url": string | null,
  "extraction_notes": string | null
}"""


EXTRACTION_USER_TEMPLATE = """Analyze the following opportunity announcement and extract all structured information according to the schema.

ANNOUNCEMENT:
{announcement_text}

Remember: Return ONLY the JSON object. No markdown formatting, no preamble, no explanation."""


# ---------------------------------------------------------------------------
# Client factory & API key resolution
# ---------------------------------------------------------------------------

def get_api_key() -> Optional[str]:
    """
    Consistently resolve the Gemini API key:
    1. Check os.environ ("GEMINI_API_KEY" or "GOOGLE_API_KEY")
    2. Explicitly load .env relative to this file with override=True
    3. Check streamlit.secrets if available
    """
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if key and key.strip():
        os.environ["GEMINI_API_KEY"] = key.strip()
        return key.strip()

    try:
        from dotenv import load_dotenv
        if ENV_PATH.exists():
            load_dotenv(dotenv_path=ENV_PATH, override=True)
            key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if key and key.strip():
                os.environ["GEMINI_API_KEY"] = key.strip()
                return key.strip()
    except Exception:
        pass

    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
                key = str(st.secrets["GEMINI_API_KEY"]).strip()
                os.environ["GEMINI_API_KEY"] = key
                return key
            if "GOOGLE_API_KEY" in st.secrets and st.secrets["GOOGLE_API_KEY"]:
                key = str(st.secrets["GOOGLE_API_KEY"]).strip()
                os.environ["GEMINI_API_KEY"] = key
                return key
    except Exception:
        pass

    return None


def _get_client(api_key: Optional[str] = None) -> genai.Client:
    """Make a client without storing request-supplied credentials globally."""
    resolved_key = api_key.strip() if api_key else get_api_key()
    if not resolved_key:
        raise ValueError(
            "API key not found. Set GEMINI_API_KEY in your .env file or Streamlit secrets."
        )
    return genai.Client(api_key=resolved_key)


# ---------------------------------------------------------------------------
# Model availability check
# ---------------------------------------------------------------------------

def check_model_availability(client: genai.Client) -> Tuple[str, bool, str]:
    """
    Check which Gemma 4 model is available.

    Returns:
        (model_name, is_available, message)
    """
    # Try to list models and find an available Gemma 4 variant
    try:
        models = client.models.list()
        available_names = [m.name for m in models]

        # Check primary model
        for name in available_names:
            if PRIMARY_MODEL in name:
                return (PRIMARY_MODEL, True, f"Model '{PRIMARY_MODEL}' is available.")

        # Check fallbacks
        for fallback in FALLBACK_MODELS:
            for name in available_names:
                if fallback in name:
                    return (
                        fallback,
                        True,
                        f"Primary model '{PRIMARY_MODEL}' not found. Using '{fallback}'.",
                    )

        # Model not found in list — attempt to use primary anyway (list may be incomplete)
        return (
            PRIMARY_MODEL,
            True,
            f"Could not verify '{PRIMARY_MODEL}' in model list. Attempting to use it directly.",
        )

    except Exception as exc:
        # If listing fails, try using the primary model directly
        return (
            PRIMARY_MODEL,
            True,
            f"Model list unavailable ({exc}). Attempting '{PRIMARY_MODEL}' directly.",
        )


# ---------------------------------------------------------------------------
# Core extraction function
# ---------------------------------------------------------------------------

def extract_opportunity(
    announcement_text: str,
    model: Optional[str] = None,
    max_retries: int = 2,
    api_key: Optional[str] = None,
) -> Tuple[ExtractedOpportunity, str]:
    """
    Send the announcement to Gemma 4 and return a validated ExtractedOpportunity.

    Returns:
        (opportunity, model_used)

    Raises:
        ValueError  — API key missing
        RuntimeError — all retries failed
    """
    client = _get_client(api_key=api_key)
    model_name = model or PRIMARY_MODEL

    prompt = EXTRACTION_USER_TEMPLATE.format(announcement_text=announcement_text)

    last_error: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=EXTRACTION_SYSTEM_INSTRUCTION,
                    temperature=0.1,        # low temperature for factual extraction
                    max_output_tokens=4096,
                ),
            )

            raw_text = response.text.strip() if response.text else ""
            opportunity = _parse_and_validate(raw_text, announcement_text)
            opportunity.raw_announcement_length = len(announcement_text)
            return opportunity, model_name

        except ValueError:
            raise  # API key errors — don't retry

        except Exception as exc:
            last_error = exc
            if attempt < max_retries:
                wait = 2 ** attempt  # exponential backoff: 1s, 2s
                time.sleep(wait)
                continue

    raise RuntimeError(
        f"Gemma 4 analysis failed after {max_retries + 1} attempts. "
        f"Last error: {last_error}"
    )


# ---------------------------------------------------------------------------
# Response parsing and validation
# ---------------------------------------------------------------------------

def _parse_and_validate(raw_text: str, announcement_text: str) -> ExtractedOpportunity:
    """Parse the model's JSON response and validate it with Pydantic."""

    if not raw_text:
        raise RuntimeError("The model returned an empty response.")

    # Strip markdown code fences if present
    json_text = _strip_markdown(raw_text)

    # Attempt JSON parse
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as exc:
        # Try to extract JSON object from surrounding text
        extracted = _extract_json_object(raw_text)
        if extracted:
            try:
                data = json.loads(extracted)
            except json.JSONDecodeError:
                raise RuntimeError(
                    f"Could not parse the model's response as JSON. "
                    f"JSON error: {exc}. "
                    f"Raw response (first 500 chars): {raw_text[:500]}"
                )
        else:
            raise RuntimeError(
                f"The model did not return valid JSON. "
                f"Error: {exc}. "
                f"Raw response (first 500 chars): {raw_text[:500]}"
            )

    # Validate with Pydantic
    try:
        return ExtractedOpportunity(**data)
    except Exception as exc:
        raise RuntimeError(f"Extracted data failed schema validation: {exc}")


def _strip_markdown(text: str) -> str:
    """Remove ```json ... ``` fences."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (``` or ```json) and last line (```)
        if lines[-1].strip() == "```":
            lines = lines[1:-1]
        elif lines[0].strip().startswith("```"):
            lines = lines[1:]
        text = "\n".join(lines).strip()
    return text


def _extract_json_object(text: str) -> Optional[str]:
    """Try to find a JSON object within a larger text response."""
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return None


# ---------------------------------------------------------------------------
# Precomputed Sample Data for Instant Quick Demo (No LLM Call)
# ---------------------------------------------------------------------------

SAMPLE_EXTRACTED_OPPORTUNITY = ExtractedOpportunity(
    title="Northgate University Global Excellence Fellowship 2025",
    organizing_institution="Northgate University Graduate School of Science and Technology",
    category="fellowship",
    description=(
        "A prestigious postgraduate funding programme designed to support outstanding "
        "international students from developing nations who wish to pursue a Master's or PhD "
        "degree at Northgate University's Graduate School of Science and Technology."
    ),
    eligible_countries=EligibleCountries(
        countries=[
            "Nigeria", "Ghana", "Kenya", "Ethiopia", "Rwanda", "Uganda", "Tanzania",
            "Cameroon", "Senegal", "Côte d'Ivoire", "South Africa", "Egypt", "Morocco",
            "Bangladesh", "Pakistan", "Sri Lanka", "Nepal", "Myanmar", "Cambodia",
            "Laos", "Bolivia", "Ecuador", "Paraguay", "Honduras", "Guatemala"
        ],
        is_open_to_all=False,
        raw_text=(
            "Applications are open to citizens of: Nigeria, Ghana, Kenya, Ethiopia, Rwanda, Uganda, "
            "Tanzania, Cameroon, Senegal, Côte d'Ivoire, South Africa, Egypt, Morocco, Bangladesh, "
            "Pakistan, Sri Lanka, Nepal, Myanmar, Cambodia, Laos, Bolivia, Ecuador, Paraguay, "
            "Honduras, and Guatemala."
        ),
    ),
    academic_level_requirements=["Masters", "PhD"],
    course_restrictions=[
        "Computer Science", "Data Science", "Artificial Intelligence",
        "Electrical Engineering", "Mechanical Engineering", "Environmental Science",
        "Public Health", "Agricultural Sciences"
    ],
    cgpa_requirement=CGPARequirement(
        minimum=3.5,
        scale=4.0,
        raw_text="Minimum CGPA: 3.5 on a 4.0 scale (or equivalent, as assessed by Northgate's Graduate Admissions Office)."
    ),
    age_requirement=AgeRequirement(
        maximum_age=35,
        raw_text="Applicants must be no older than 35 years of age at the time of application."
    ),
    other_eligibility_conditions=[
        "Applicants must not hold citizenship of a high-income country (as classified by the World Bank).",
        "The fellowship may not be held concurrently with any other scholarship or funding award exceeding USD 500 per month.",
        "Recipients must maintain satisfactory academic progress throughout the award period.",
        "Applicants must demonstrate financial need through a statement of household income."
    ],
    required_documents=[
        RequiredDocument(
            name="Completed online application form",
            description="Available on the fellowship portal",
            is_mandatory=True,
        ),
        RequiredDocument(
            name="Academic transcripts",
            description="Certified copies of all university degrees and diplomas",
            is_mandatory=True,
        ),
        RequiredDocument(
            name="Two academic reference letters",
            description="From university professors or academic supervisors",
            is_mandatory=True,
        ),
        RequiredDocument(
            name="Personal statement",
            description="Maximum 800 words describing your research interests and career goals",
            is_mandatory=True,
        ),
        RequiredDocument(
            name="Valid passport",
            description="Minimum 18 months validity from the date of application",
            is_mandatory=True,
        ),
        RequiredDocument(
            name="Proof of English language proficiency",
            description="IELTS Academic (minimum 6.5 overall) or TOEFL iBT (minimum 90)",
            is_mandatory=True,
        ),
        RequiredDocument(
            name="Research proposal",
            description="For PhD applicants only; maximum 1,500 words",
            is_mandatory=False,
        ),
    ],
    application_deadline="30 April 2025 at 11:59 PM (GMT+0)",
    benefits=[
        "Full tuition waiver for the duration of the programme",
        "Monthly living stipend of USD 1,200",
        "Annual research allowance of USD 1,000",
        "Return economy-class airfare upon commencement of studies",
        "Health insurance coverage",
        "Access to Northgate's research library and digital resources"
    ],
    application_instructions="All applications must be submitted through the Northgate University Fellowship Portal: https://fellowships.northgate-example.edu/global-excellence",
    official_url="https://fellowships.northgate-example.edu/global-excellence",
    extraction_notes="Precomputed illustrative sample for quick demonstration without external API latency.",
    raw_announcement_length=1850,
)


def get_sample_extracted_opportunity() -> ExtractedOpportunity:
    """Return precomputed validated ExtractedOpportunity for the sample fellowship."""
    return SAMPLE_EXTRACTED_OPPORTUNITY.model_copy(deep=True)

