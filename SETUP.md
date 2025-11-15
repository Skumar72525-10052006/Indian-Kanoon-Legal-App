# Indian Kanoon Web App  Setup & Deployment Guide

This guide explains how to run the project locally and how to deploy it to production.

## 1. Local Development

### 1.1 Backend

1. Create and activate virtual env, install deps:
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

2. Create `.env` in `backend/` (see `.env.example`):
   ```env
   MONGODB_URI=mongodb://localhost:27017
   DATABASE_NAME=indian_kanoon_cache
   JWT_SECRET_KEY=your-strong-secret
   GEMINI_API_KEY=your-gemini-api-key
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your-email@gmail.com
   SMTP_PASSWORD=your-app-password
   ```

3. Start backend:
   ```bash
   python main.py
   # or
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

Backend API will be at `http://localhost:8000`.

### 1.2 Frontend

1. From project root:
   ```bash
   cd frontend
   # Simple dev server (Python)
   python -m http.server 8080
   # or any static server (e.g. npx serve .)
   ```

2. Open `http://localhost:8080` (or the port you chose).
3. Make sure the frontend JS points to `http://localhost:8000` as the API base URL.

## 2. EndtoEnd Production Deployment

### 2.1 Database  MongoDB Atlas

1. Create an Atlas cluster.
2. Create DB user and note username/password.
3. Allow access only from your backend hosting IP/VPC.
4. Set in backend environment:
   ```env
   MONGODB_URI=mongodb+srv://<user>:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
   DATABASE_NAME=indian_kanoon_cache
   ```

### 2.2 Backend  FastAPI

1. Choose a host (Railway, Render, Fly.io, EC2, etc.).
2. Build container or use `uvicorn` start command:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```
3. Configure environment variables on the platform:
   - MongoDB (`MONGODB_URI`, `DATABASE_NAME`)
   - JWT (`JWT_SECRET_KEY`)
   - Gemini (`GEMINI_API_KEY`, optional model overrides)
   - SMTP (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`)
4. Ensure HTTPS is enabled (platformmanaged TLS or reverse proxy).
5. In `main.py`, change CORS `allow_origins` from `"*"` to your production frontend URL.

### 2.3 Frontend  Static Hosting

1. Deploy contents of `frontend/` to a static host:
   - Netlify, Vercel, GitHub Pages, Nginx, S3+CloudFront, etc.
2. Update `auth.js`/`script.js` API base URL to your backend, e.g.:
   ```js
   const API_BASE_URL = 'https://api.example.com';
   ```
3. Make sure site is served over HTTPS.

## 3. Production Checklist

- [ ] MongoDB Atlas configured with backups and restricted network access
- [ ] Backend deployed behind HTTPS with proper env vars
- [ ] `GEMINI_API_KEY` set and quotas monitored
- [ ] SMTP/email configured and tested for OTP and welcome emails
- [ ] CORS restricted to the production frontend origin
- [ ] Frontend deployed as static site with correct API base URL
- [ ] `/stats` endpoint accessible only to admin/dev team

For deeper details, see:
- `prd/README.md`, `prd/HLD.md`, `prd/LLD.md`  product and design docs
- `backend/README.md`, `AUTH_SETUP.md`, `MONGODB_SETUP.md`, `GEMINI_SETUP.md`  backend and infra docs.
