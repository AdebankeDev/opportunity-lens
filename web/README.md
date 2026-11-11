# OpportunityLens web preview

This React/Vite interface is an additive preview alongside the existing Streamlit app.

Run the FastAPI service from the repository root with `uvicorn api.index:app --reload`, then run `npm install && npm run dev` from this directory. Vite proxies `/api` to localhost:8000. On Vercel, this web project rewrites `/api` calls to a separate OpportunityLens FastAPI deployment.

Features available in this preview: guest academic profile, AI-assisted analysis with a request-scoped Google AI Studio key, manual rule-based eligibility checks, explainable results, source links and an application checklist.

Limitations: guest information is held only in browser memory (not persistent); there is no user authentication, current scholarship feed, automated opportunity retrieval, or email alerts. The interface shows no fictional scholarship records. The API connection must be publicly accessible from the deployed frontend to analyze announcements.
