"""Stateless HTTP API for the existing OpportunityLens scholarship engine."""
from __future__ import annotations

import os

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from document_processor import validate_pasted_text
from eligibility_engine import run_eligibility_check
from gemma_service import extract_opportunity
from schemas import ChecklistItem, EligibilityAssessment, ExtractedOpportunity, StudentProfile

app = FastAPI(
    title="OpportunityLens API",
    description="Explainable eligibility results from the established Python engine.",
    version="0.1.0",
)

origins = [
    origin.strip()
    for origin in os.getenv(
        "OPPORTUNITYLENS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:5173",
    ).split(",")
    if origin.strip() and origin.strip() != "*"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Gemini-API-Key"],
)


class AssessmentRequest(BaseModel):
    profile: StudentProfile
    opportunity: ExtractedOpportunity


class AnnouncementRequest(BaseModel):
    profile: StudentProfile
    announcement_text: str = Field(min_length=100, max_length=100_000)


class AnalysisResult(BaseModel):
    opportunity: ExtractedOpportunity
    assessment: EligibilityAssessment
    model_used: str


class ChecklistRequest(BaseModel):
    opportunity: ExtractedOpportunity


class ChecklistResponse(BaseModel):
    items: list[ChecklistItem]


def prepare_checklist(opportunity: ExtractedOpportunity) -> list[ChecklistItem]:
    """Derive checklist items without inventing document requirements."""
    items = [
        ChecklistItem(
            id=f"document-{index}",
            category="document",
            description=doc.name,
            detail=doc.description,
        )
        for index, doc in enumerate(opportunity.required_documents, 1)
    ]
    for index, condition in enumerate(opportunity.other_eligibility_conditions, 1):
        items.append(ChecklistItem(
            id=f"verify-{index}",
            category="verification",
            description=condition,
            detail="Confirm this condition with the awarding institution.",
        ))
    if opportunity.application_deadline:
        items.append(ChecklistItem(
            id="verify-deadline",
            category="verification",
            description="Confirm the application deadline",
            detail=opportunity.application_deadline,
        ))
    if opportunity.official_url:
        items.append(ChecklistItem(
            id="official-page",
            category="action",
            description="Review the official application page",
            detail=opportunity.official_url,
        ))
    return items


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "opportunity-lens"}


@app.post("/api/assess", response_model=EligibilityAssessment)
def assess(payload: AssessmentRequest) -> EligibilityAssessment:
    """Assess a structured opportunity without AI or external services."""
    return run_eligibility_check(payload.profile, payload.opportunity)


@app.post("/api/checklist", response_model=ChecklistResponse)
def checklist(payload: ChecklistRequest) -> ChecklistResponse:
    return ChecklistResponse(items=prepare_checklist(payload.opportunity))


@app.post("/api/analyze", response_model=AnalysisResult)
def analyze(
    payload: AnnouncementRequest,
    x_gemini_api_key: str | None = Header(default=None, alias="X-Gemini-API-Key"),
) -> AnalysisResult:
    """Extract using a request-specific key, then run deterministic checks."""
    if not x_gemini_api_key or not x_gemini_api_key.strip():
        raise HTTPException(
            status_code=400,
            detail="Send a Google AI Studio key in X-Gemini-API-Key.",
        )
    checked = validate_pasted_text(payload.announcement_text)
    if not checked.success:
        raise HTTPException(status_code=422, detail=checked.error)
    try:
        opportunity, model_used = extract_opportunity(
            checked.text, max_retries=0, api_key=x_gemini_api_key.strip()
        )
    except (RuntimeError, ValueError):
        raise HTTPException(
            status_code=502,
            detail="Analysis failed. Check the key, quota and announcement text.",
        ) from None
    return AnalysisResult(
        opportunity=opportunity,
        assessment=run_eligibility_check(payload.profile, opportunity),
        model_used=model_used,
    )
