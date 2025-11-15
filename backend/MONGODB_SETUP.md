# MongoDB Setup Guide

This guide explains how the backend uses MongoDB and how to configure it for **development** and **production**.

## 1. What MongoDB is used for

The FastAPI backend stores:
- Cached search results (`search_results`)
- Cached AI summaries (`document_summaries`)
- Users (`users`)
- OTPs for signup and password reset (`otps`)

Caching collections use **TTL indexes**, so old records are autodeleted.

## 2. Choose Your Deployment

- **Local MongoDB**  easiest for development
- **MongoDB Atlas**  recommended for staging/production

### Local MongoDB (dev)

1. Install MongoDB Community Edition from https://www.mongodb.com/try/download/community
2. Start the service (varies by OS  Windows service, `systemctl start mongod`, or `brew services start mongodb-community`).
3. Test with `mongosh`.
4. Set env vars in `backend/.env`:
   ```env
   MONGODB_URI=mongodb://localhost:27017
   DATABASE_NAME=indian_kanoon_cache
   ```

### MongoDB Atlas (prod)

1. Create a free/paid cluster at https://cloud.mongodb.com/
2. Create a **database user** (e.g. `kanoon_user` with strong password).
3. Add your backend server IP (or VPC) in **Network Access**.
4. From "Connect"  "Connect your application", copy the connection string.
5. Set env vars:
   ```env
   MONGODB_URI=mongodb+srv://kanoon_user:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
   DATABASE_NAME=indian_kanoon_cache
   ```
6. Enable **backups** and basic alerts (CPU, connections, storage).

## 3. Backend Behaviour

Implemented mainly in `backend/database.py` and `backend/user_db.py`:

- Uses `AsyncIOMotorClient` with connection pooling and timeouts.
- Creates indexes at startup:
  - Unique indexes on `users.email`, `users.username`, `users.mobile_number`.
  - TTL index on `otps.expires_at`.
  - TTL indexes on cache collections (`search_results`, `document_summaries`).
- Provides helpers for:
  - Caching search responses per `{query,page}`.
  - Caching summaries per `doc_id`.
  - Tracking stats via `/stats` endpoint.

If connection fails, startup will log errors and API calls will return 500s until fixed.

## 4. Production Best Practices

- Use Atlas or managed MongoDB; avoid selfhosted DB without ops experience.
- Restrict network access to **backend IPs only** (avoid `0.0.0.0/0` in production).
- Turn on **encryption at rest** and **TLS in transit** (Atlas does this by default).
- Keep credentials in secret manager; never hardcode in code.
- Monitor slow queries and create extra indexes if needed.
- Periodically verify TTL cleanup is working and storage is under control.

With MongoDB properly configured, the backends 3tier caching strategy (memory  MongoDB  Playwright) keeps search latency low and reduces load on Indian Kanoon and Gemini.
