# Indian Kanoon Legal App  Product Overview

## 1. Overview

Indian Kanoon Legal App is a web application that lets citizens and lawyers:
- Search Indian Kanoon for judgments and orders
- Open full documents on indiankanoon.org
- Generate AI summaries in simple language (citizen view) or with legal detail (lawyer view)
- Save time by avoiding reading the entire judgment for every query

The current implementation is **FastAPI + Python backend**, a **static HTML/CSS/JS frontend**, and **MongoDB** for caching and user data.

## 2. Core Features

- **Search interface** on the web UI with pagination over Indian Kanoon results
- **3tier search caching**:
  - Inmemory cache for the current process
  - MongoDB cache for previously scraped search pages
  - Live Playwright scraping when cache is cold
- **AI summarization** via Google Gemini
  - Citizenfriendly summary (plain language)
  - Lawyer summary (professional legal tone)
- **User authentication** (email / username / mobile)
  - OTPbased signup and password reset
  - JWT access tokens for protected endpoints
- **Rate limiting** on search and summarization endpoints
- **Monitoring endpoint** (`/stats`) for cache + DB statistics

## 3. Tech Stack

**Frontend**
- Static files: `frontend/index.html`, `styles.css`, `script.js`, `auth.js`
- Plain JavaScript for UI, modals, and API calls

**Backend**
- Python 3.8+
- FastAPI (ASGI), Uvicorn
- Playwright (Chromium) for scraping Indian Kanoon
- Google Gemini (`google-generativeai`) for summaries
- Async MongoDB (`motor` + `pymongo`)

**Database**
- MongoDB database (local or Atlas)
- Collections:
  - `search_results`  cached search pages with TTL
  - `document_summaries`  cached AI summaries with TTL
  - `users`  auth users
  - `otps`  OTP codes with TTL

## 4. HighLevel Architecture

1. Browser sends search request to backend `/search?forminput=...&pagenum=...`.
2. Backend checks inmemory cache  MongoDB cache  Playwright scraper.
3. Results are returned to the browser and stored in cache + MongoDB.
4. Authenticated users can call `/summarize` with a document URL or id.
5. Backend fetches the full document, calls Gemini, stores summaries in MongoDB, and returns roleappropriate text (citizen or lawyer).

## 5. Repository Structure (prodrelevant)

- `frontend/`  Static web UI
- `backend/`  FastAPI app, scraping, summaries, auth, MongoDB
- `prd/`  Product/design docs (`README.md`, `HLD.md`, `LLD.md`)
- `SETUP.md`  Endtoend setup & deployment guide

## 6. Deployment Summary

**Database (recommended: MongoDB Atlas)**
- Create free/shared cluster
- Create database user and connection string
- Configure in backend `.env`:
  - `MONGODB_URI`
  - `DATABASE_NAME`

**Backend (FastAPI)**
- Package as a Uvicorn app: `uvicorn main:app --host 0.0.0.0 --port 8000`
- Suitable deployment targets:
  - Railway / Render / Fly.io / EC2 / any Dockercapable host
- Configure environment variables (see `SETUP.md` + backend docs):
  - MongoDB settings, JWT secret, GEMINI_API_KEY, SMTP settings
- Enable HTTPS via the platform (managed certs) or Nginx/Traefik in front.

**Frontend (static)**
- Deploy `frontend/` as static site:
  - Netlify, Vercel, GitHub Pages, Nginx, or S3+CloudFront
- Ensure API base URL in `auth.js` / `script.js` points to the deployed backend (e.g. `https://api.example.com`).

## 7. Production Readiness Checklist

- [ ] MongoDB Atlas or managed MongoDB cluster configured with backups
- [ ] FastAPI backend deployed behind HTTPS with health checks
- [ ] GEMINI_API_KEY configured and rate limits understood
- [ ] SMTP credentials configured for OTP emails
- [ ] CORS restricted to your frontend origin in `main.py`
- [ ] Strong `JWT_SECRET_KEY` set and kept secret
- [ ] `/stats` endpoint secured (e.g. allowed only from admin IP or behind auth)
- [ ] Frontend hosted on a reliable HTTPS domain

This PRD file intentionally stays **highlevel**. Implementation details live in `prd/HLD.md`, `prd/LLD.md`, and the backend markdown guides.
