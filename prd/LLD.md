# LowLevel Design (LLD)  Indian Kanoon Legal App

This document focuses on how the current **FastAPI + MongoDB + Playwright + Gemini** implementation is structured. It intentionally ignores the older Node/React design.

## 1. Backend Modules

- `main.py`
  - Creates FastAPI app with lifespan handler
  - Configures CORS
  - Wires up rate limiters and includes `/api/auth` router
  - Exposes routes: `/`, `/stats`, `/search`, `/summarize`
- `scraper.py`
  - Uses Playwright (Chromium) to search Indian Kanoon
  - Handles pagination, useragent rotation, and HTML parsing
  - Returns normalized search results to `main.py`
- `document_fetcher.py`
  - Fetches full judgment HTML by URL
  - Extracts clean text content for summarization
- `summarizer.py`
  - Integrates with Google Gemini via `google-generativeai`
  - Builds two prompts: `citizen` (plain language) and `lawyer` (legal tone)
  - Implements retry + timeout logic and markdown cleanup
- `database.py`
  - Creates a global `AsyncIOMotorClient` from `MONGODB_URI`
  - Provides helpers to:
    - Initialize DB and indexes
    - Save/get search results
    - Save/get document summaries
    - Return `/stats` data
- `rate_limiter.py`
  - Slidingwindow limiter using inmemory counters keyed by IP + route group
- `auth_routes.py`
  - FastAPI router under prefix `/api/auth`
  - Endpoints: `send-otp`, `verify-otp`, `signup`, `login`, `forgot-password`, `reset-password`, `me` (GET/PUT)
- `auth_models.py`
  - Pydantic models for all auth requests/responses (e.g. `UserSignup`, `UserLogin`, `ResetPasswordRequest`, `TokenResponse`)
- `auth_utils.py`
  - Password hashing/verification using `bcrypt`
  - JWT creation and decoding using `JWT_SECRET_KEY`
  - OTP generation helper
- `user_db.py`
  - All user/OTP DB access:
    - `create_user`, `get_user_by_email`, `get_user_by_identifier`
    - `update_user_password`, `update_user_profile`, `update_user_verification`
    - `store_otp`, `verify_otp` with TTL and attempt limits
  - Special handling for Indian mobile numbers: accepts `+91XXXXXXXXXX` and `XXXXXXXXXX`
- `notification_service.py`
  - Sends OTP + welcome emails over SMTP (Gmail or other provider)

## 2. Key Flows

### 2.1 Search Flow (`GET /search`)

1. Validate `forminput` (query) and `pagenum`.
2. Normalize query (spaces  `+`) and derive `cache_key` + `db_key`.
3. Check **Tier 1**: inmemory cache dict.
4. If miss: check **Tier 2**: MongoDB (`search_results` collection).
5. If miss: call `scrape_indian_kanoon()` in `scraper.py`.
6. Save result to MongoDB and memory cache.
7. Periodically evict expired items from memory cache.

### 2.2 Summarization Flow (`GET /summarize`)

1. `get_current_user` dependency validates JWT and loads user from DB.
2. Accepts `document_url` or `doc_id + query`.
3. If only `doc_id` given, constructs canonical `docfragment` URL.
4. If `doc_id` is known, check `document_summaries` for cached summary.
5. If cache hit:
   - Build response with citizen or lawyer summary depending on `user_type`.
6. If cache miss:
   - Fetch full document via `document_fetcher.py`.
   - Call `summarize_document()` which talks to Gemini.
   - Save raw citizen + lawyer summaries in MongoDB.
   - Return roleappropriate summary.

## 3. Data Model (Simplified)

Example MongoDB documents (actual schema may contain more fields):

- `users`
  ```json
  {
    "email": "user@example.com",
    "username": "user1",
    "mobile_number": "+919876543210",
    "hashed_password": "...",
    "user_type": "citizen" | "lawyer",
    "is_verified": true,
    "is_active": true,
    "created_at": "2025-01-01T00:00:00Z"
  }
  ```

- `otps`
  ```json
  {
    "email": "user@example.com",
    "purpose": "signup" | "forgot_password",
    "otp": "123456",
    "expires_at": "2025-01-01T00:10:00Z",
    "attempts": 0
  }
  ```

- `search_results`
  ```json
  {
    "cache_key": "article+370:page:1",
    "results": [ ... ],
    "created_at": "2025-01-01T00:00:00Z"
  }
  ```

- `document_summaries`
  ```json
  {
    "doc_id": "105489743",
    "title": "State Bank Of India vs ...",
    "document_url": "https://indiankanoon.org/doc/.../",
    "content_length": 8000,
    "citizen_summary": "...",
    "lawyer_summary": "...",
    "created_at": "2025-01-01T00:00:00Z"
  }
  ```

TTL indexes ensure OTPs and cached data expire automatically.

## 4. Configuration & Security

Important environment variables (see `.env.example` and backend docs):
- `MONGODB_URI`, `DATABASE_NAME`
- `JWT_SECRET_KEY`
- `GEMINI_API_KEY`, `GEMINI_CITIZEN_MODEL`, `GEMINI_LAWYER_MODEL`
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`

Security highlights:
- Passwords hashed with bcrypt
- Minimum password complexity enforced via validation
- OTPs expire after ~10 minutes and have max attempt count
- JWT tokens expire after 7 days
- Rate limiting on all public endpoints

For deployment, see `SETUP.md` and backend `README.md` / `AUTH_SETUP.md` / `MONGODB_SETUP.md` / `GEMINI_SETUP.md`.
