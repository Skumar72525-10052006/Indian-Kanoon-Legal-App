# HighLevel Design (HLD)  Indian Kanoon Legal App

## 1. System Goals

- Make Indian court judgments easier to discover and understand
- Provide AI summaries tailored to citizens and lawyers
- Avoid paid thirdparty APIs by scraping Indian Kanoon directly
- Stay performant and costefficient using caching and rate limiting

Primary users:
- Lawyers and law students
- Citizens who want plainlanguage explanations

## 2. Architecture Overview

Overall style: **threetier web architecture** with a single backend service.

- **Presentation layer**  Static HTML/CSS/JS served from any static host
- **Application layer**  FastAPI (`backend/main.py`) running behind Uvicorn
- **Data layer**  MongoDB for users, OTPs, cached search results, and cached summaries

### 2.1 Logical Architecture

```text
Browser (Frontend)
  - Search UI
  - Auth modals (login/signup/reset)
  - AI summary modal
        |
        | HTTPS (JSON)
        v
FastAPI Backend (Application Layer)
  - /search
  - /summarize   (auth required)
  - /api/auth/*  (signup/login/OTP/password reset/profile)
  - /stats
        |
        +--> MongoDB (search_results, document_summaries, users, otps)
        |
        +--> Playwright (scrape indiankanoon.org)
        |
        +--> Google Gemini API (summaries)
        |
        +--> SMTP (OTP + welcome emails)
```

## 3. Major Components

### 3.1 Frontend (Static)

- Search page with query box and results list
- Modals for signup, login, forgot password, and password reset
- Calls backend APIs using `fetch` from `script.js` and `auth.js`
- Stores JWT token in `localStorage` and sends it as `Authorization: Bearer <token>`

### 3.2 Backend Services

**Search service** (`/search`)
- Validates query + page
- Checks inmemory cache (per process)
- Falls back to MongoDB cache if present
- If cache miss: calls Playwright scraper to fetch results from Indian Kanoon
- Persists search results in MongoDB with TTL

**Summarization service** (`/summarize`)
- Authenticated route (JWT, `get_current_user`)
- Accepts `document_url` or `doc_id + query`
- Fetches full judgment HTML, extracts text
- Calls Gemini twice (citizen + lawyer prompts) with retry + timeouts
- Saves raw summaries to `document_summaries` collection
- Returns roleappropriate summary based on `user_type`

**Authentication service** (`/api/auth/*`)
- Signup flow with email OTP verification
- Login via email / username / mobile
- Forgot + reset password using OTP
- Profile fetch (`/me`) and update (`/me` PUT)
- Issues JWTs (7day expiry) using a shared secret

**Rate limiting** (`rate_limiter.py`)
- Inmemory slidingwindow limiter
- Global 100 req / 60s
- Search 20 req / 60s
- Summarize 6 req / 60s (protects Gemini quota)

## 4. Data Design (High Level)

Collections (MongoDB):

- `users`
  - Auth users, unique on `email`, `username`, `mobile_number`
- `otps`
  - OTP codes with purpose (`signup`, `forgot_password`), expiry, attempt counters
- `search_results`
  - Cached search pages by `{query,page}` with 7day TTL
- `document_summaries`
  - Cached summaries by `doc_id` with 30day TTL, stores both citizen + lawyer text

Indexes & TTL behavior are documented in `backend/MONGODB_SETUP.md`.

## 5. External Integrations

- **Indian Kanoon**  Source of legal documents (readonly scraping)
- **MongoDB**  Primary data store + cache
- **Google Gemini**  AI summarization service
- **SMTP (Gmail or provider)**  Sends OTP and welcome emails

## 6. Deployment Architecture (Production)

Recommended production setup:

- **MongoDB Atlas** in a region close to backend
- **Backend** deployed as a containerized FastAPI/Uvicorn app on Railway/Render/Fly.io/EC2
  - Exposed over HTTPS
  - Environment variables configured for DB, JWT, SMTP, Gemini
- **Frontend** deployed as static site on Netlify/Vercel/Nginx
  - Configured to call the backend base URL (e.g. `https://api.example.com`)
- Optional: reverse proxy (Nginx/Cloudflare) in front of backend for TLS, caching, and WAF.

More detailed class and functionlevel behavior is described in `prd/LLD.md`.
