# OpportunityLens web API (experimental)

This additive FastAPI app shares the original Pydantic schemas, eligibility engine, and Gemma extractor. The Streamlit application remains available.

## Local usage

Install requirements.txt, then run: uvicorn api.index:app --reload
Interactive endpoint reference: http://localhost:8000/docs

| Endpoint | Purpose | AI key required |
| --- | --- | --- |
| GET /api/health | API status | No |
| POST /api/assess | Evaluate profile + structured opportunity | No |
| POST /api/checklist | Return uncompleted application steps | No |
| POST /api/analyze | Extract announcement + evaluate profile | Yes |

Assessment JSON has profile and opportunity properties, using the existing StudentProfile and ExtractedOpportunity schemas.
Analysis JSON has profile and announcement_text (100 to 100000 characters). Supply a Google AI Studio key via X-Gemini-API-Key header on each analysis request.
Checklist JSON has an opportunity property.

No profiles or keys are persisted. Use HTTPS and do not log request headers or bodies. Configure OPPORTUNITYLENS_ALLOWED_ORIGINS with comma-separated frontend origins when cross-origin access is needed. The default allows localhost:3000 and localhost:5173.

## Vercel

The pyproject.toml tool.vercel entrypoint selects api.index:app instead of the root Streamlit app.py file.
Confirm the API route behavior in a Vercel preview before promoting production.

## MVP limitations

Authentication, discovery, persistent profiles, email alerts, abuse controls, and rate limiting are not yet implemented. Scholarship availability and eligibility must be verified at the official source. Do not deploy a publicly funded AI key.

Tests: pytest tests/ -v
