"""Web API tests use a mocked AI provider and never use real keys."""
from fastapi.testclient import TestClient

from api import index as web_api
from schemas import ExtractedOpportunity, EligibleCountries, RequiredDocument

client = TestClient(web_api.app)
PROFILE = {
    "country": "Nigeria",
    "academic_level": "Undergraduate",
    "course_of_study": "Computer Engineering",
    "cgpa": 4.5,
    "cgpa_scale": 5.0,
}
OPPORTUNITY = {
    "title": "Engineering scholarship",
    "eligible_countries": {"countries": ["Nigeria"]},
    "academic_level_requirements": ["Undergraduate"],
    "cgpa_requirement": {"minimum": 4.0, "scale": 5.0},
    "required_documents": [{"name": "Transcript"}],
}


def test_health():
    assert client.get("/api/health").json() == {
        "status": "ok", "service": "opportunity-lens",
    }


def test_assess_reuses_engine():
    response = client.post("/api/assess", json={
        "profile": PROFILE, "opportunity": OPPORTUNITY,
    })
    assert response.status_code == 200
    checks = response.json()["requirement_checks"]
    assert any(c["requirement"] == "CGPA" and c["status"] == "MET" for c in checks)
    assert any(c["requirement"] == "Country eligibility" and c["status"] == "MET" for c in checks)


def test_invalid_profile_rejected():
    assert client.post("/api/assess", json={
        "profile": "invalid", "opportunity": OPPORTUNITY,
    }).status_code == 422


def test_checklist_does_not_invent_requirements():
    response = client.post("/api/checklist", json={"opportunity": {
        "required_documents": [{"name": "Transcript"}],
        "application_deadline": "15 November 2026",
    }})
    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["id"] for item in items] == ["document-1", "verify-deadline"]
    assert all(item["completed"] is False for item in items)


def test_analyze_requires_personal_key():
    response = client.post("/api/analyze", json={
        "profile": PROFILE,
        "announcement_text": "Full announcement details. " * 8,
    })
    assert response.status_code == 400


def test_analyze_rejects_short_text():
    response = client.post(
        "/api/analyze",
        json={"profile": PROFILE, "announcement_text": "short"},
        headers={"X-Gemini-API-Key": "test"},
    )
    assert response.status_code == 422


def test_analyze_receives_key_without_echoing(monkeypatch):
    captured = {}

    def fake_extract(announcement_text, model=None, max_retries=2, api_key=None):
        captured["key"] = api_key
        return ExtractedOpportunity(
            title="Engineering scholarship",
            eligible_countries=EligibleCountries(countries=["Nigeria"]),
            required_documents=[RequiredDocument(name="Transcript")],
        ), "mock-model"

    monkeypatch.setattr(web_api, "extract_opportunity", fake_extract)
    response = client.post(
        "/api/analyze",
        json={"profile": PROFILE, "announcement_text": "Announcement details. " * 8},
        headers={"X-Gemini-API-Key": "private-test-key"},
    )
    assert response.status_code == 200
    assert captured["key"] == "private-test-key"
    assert response.json()["model_used"] == "mock-model"
    assert "private-test-key" not in response.text


def test_analyze_hides_provider_errors(monkeypatch):
    def fake_extract(*args, **kwargs):
        raise RuntimeError("secret-123")

    monkeypatch.setattr(web_api, "extract_opportunity", fake_extract)
    response = client.post(
        "/api/analyze",
        json={"profile": PROFILE, "announcement_text": "Announcement details. " * 8},
        headers={"X-Gemini-API-Key": "secret-123"},
    )
    assert response.status_code == 502
    assert "secret-123" not in response.text
