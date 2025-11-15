# Gemini API Setup Guide

The backend uses **Google Gemini** to generate two versions of summaries:
- Citizenfriendly summary (plain language)
- Lawyer summary (legal tone + citations)

Implementation lives in `backend/summarizer.py`.

## 1. Get an API Key

1. Go to [Google AI Studio](https://aistudio.google.com/).
2. Create or select a project and generate an API key.
3. Copy the key (it will not be fully shown again).

## 2. Configure Environment Variables

In `backend/.env` set:

```env
GEMINI_API_KEY=your_actual_api_key
# Optional overrides (default is gemini-2.5-flash for both)
GEMINI_CITIZEN_MODEL=models/gemini-2.5-flash
GEMINI_LAWYER_MODEL=models/gemini-2.5-flash
```

On startup `summarizer.py` calls `genai.configure(api_key=...)` and logs a warning if the key is missing.

## 3. Install Dependencies

From `backend/`:

```bash
pip install -r requirements.txt
```

The `google-generativeai` package must be installed (already listed in `requirements.txt`).

## 4. How Summaries Are Generated

- `/summarize` endpoint in `main.py`:
  - Validates input and authentication
  - Fetches document text via `document_fetcher.py`
  - Calls `summarize_document(content, title)`
- `summarize_document`:
  - Trims content to ~8000 characters
  - Builds two custom prompts (citizen + lawyer)
  - Calls Gemini models with retry + timeout logic
  - Cleans markdown formatting from responses
  - Returns both summaries and optional error info
- Backend stores both summaries in MongoDB (`document_summaries` collection) with TTL.

## 5. Quotas & Cost

- Free tier has **rate limits** (roughly 2 requests/min per model).
- Code uses:
  - Exponential backoff on errors/timeouts
  - Optional parallel generation when both prompts use the same `flash` model
  - Longer delays and retries when quota errors occur
- To control cost and avoid throttling:
  - Keep `summarize` rate limits in `rate_limiter.py` low (default 6 req / 60s)
  - Rely on MongoDB summary cache to serve repeated requests

## 6. Production Recommendations

- Treat `GEMINI_API_KEY` as a secret; store it only in your hosting providers secret manager.
- Keep an eye on usage and billing in Google AI Studio.
- Prefer `gemini-2.5-flash` for most traffic; use heavier models only if needed.
- Implement businesslevel limits (per user / per day) if you expect heavy usage.

If you see errors like "API key not configured" or quotarelated failures, check `.env`, restart the backend, and inspect logs from `summarizer.py`.
