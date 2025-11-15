# Backend  FastAPI Service

This directory contains the **FastAPI backend** for the Indian Kanoon Legal App. It:
- Scrapes Indian Kanoon search results using Playwright
- Caches results in MongoDB
- Generates AI summaries via Google Gemini
- Provides authentication, OTP, and profile APIs

## 1. Requirements

- Python 3.8+
- MongoDB (local or Atlas)
- Node.js only for installing Playwright browsers (runtime is Python)

## 2. Local Development Setup

1. **Create virtual environment & install dependencies**
   ```bash
   cd backend
   python -m venv venv
   # Windows
   .\\venv\\Scripts\\activate
   # Linux/macOS
   source venv/bin/activate

   pip install -r requirements.txt
   playwright install chromium
   ```

2. **Configure environment variables**

   Create `.env` (or copy from `.env.example`) and set at minimum:
   ```env
   MONGODB_URI=your-mongodb-connection-string
   DATABASE_NAME=indian_kanoon_cache
   JWT_SECRET_KEY=your-strong-secret
   GEMINI_API_KEY=your-gemini-api-key
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your-email@gmail.com
   SMTP_PASSWORD=your-app-password
   ```

   More detailed DB / auth / Gemini configuration is documented in:
   - `AUTH_SETUP.md`
   - `MONGODB_SETUP.md`
   - `GEMINI_SETUP.md`

3. **Run the backend**
   ```bash
   python main.py
   # or
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

   API root: `http://localhost:8000/`

## 3. Main Endpoints

- `GET /`  Health check
- `GET /search`  Scrape + cache Indian Kanoon search results
- `GET /summarize`  AI summary (requires JWT auth)
- `GET /stats`  Cache and DB statistics

Authentication API (`/api/auth`):
- `POST /api/auth/send-otp`  Send signup OTP
- `POST /api/auth/verify-otp`  Verify signup OTP
- `POST /api/auth/signup`  Register user
- `POST /api/auth/login`  Login with email/username/mobile
- `POST /api/auth/forgot-password`  Request password reset OTP
- `POST /api/auth/reset-password`  Reset password using OTP
- `GET /api/auth/me`  Get current user
- `PUT /api/auth/me`  Update current user profile

## 4. Production Deployment (Summary)

Typical production setup:

- Run the app with Uvicorn or Gunicorn+Uvicorn workers, e.g.:
  ```bash
  uvicorn main:app --host 0.0.0.0 --port 8000
  ```
- Place an HTTPSterminating reverse proxy in front (Nginx, Cloudflare, or platformmanaged)
- Host on a platform like **Railway**, **Render**, **Fly.io**, or **AWS EC2**
- Use **MongoDB Atlas** with:
  - Proper network rules (IP allowlist / VPC peering)
  - Backups turned on
- Set `allow_origins` in `main.py` to your production frontend origin instead of `"*"`
- Keep `.env` out of version control; use the platforms secret management instead.

See `SETUP.md` for an endtoend deployment guide covering frontend + backend + database.
