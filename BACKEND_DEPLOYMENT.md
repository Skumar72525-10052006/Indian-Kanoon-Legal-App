# Backend Deployment & Linking Guide

This document explains **how to deploy the backend** (FastAPI + MongoDB) and **link it to your deployed frontend** (Netlify/Vercel).

## 1. High-Level Architecture

- **Frontend**
  - Deployed as a static site on Netlify/Vercel (from `frontend/` folder)
  - Calls backend via `fetch` using a base URL, e.g. `https://api.example.com`

- **Backend**
  - FastAPI app (`backend/main.py`) running on a Linux server
  - Served by Uvicorn (or Gunicorn+Uvicorn workers)
  - Managed as a `systemd` service (auto-start on boot)

- **Database**
  - MongoDB (local on the same server or MongoDB Atlas)

---

## 2. Prepare the Linux Server

These steps assume a Debian/Ubuntu-like environment.

1. **Update packages:**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

2. **Install Python & tools** (if not already):
   ```bash
   sudo apt install -y python3 python3-venv python3-pip
   ```

3. (Optional) **Create a directory** for the app:
   ```bash
   sudo mkdir -p /opt/indian-kanoon-web-app
   sudo chown "$USER" /opt/indian-kanoon-web-app
   ```

4. **Copy your repo** to `/opt/indian-kanoon-web-app` (via git clone, scp, etc.).

---

## 3. Deploy MongoDB

### Option A: Local MongoDB on the same server

1. Install MongoDB Community/Enterprise using MongoDB's official instructions.
2. Enable and start the service:
   ```bash
   sudo systemctl enable --now mongod
   ```
3. Keep it bound to localhost (`127.0.0.1`) for security.
4. Use this in backend env:
   ```env
   MONGODB_URI=mongodb://127.0.0.1:27017
   DATABASE_NAME=indian_kanoon_cache
   ```

### Option B: MongoDB Atlas (hosted)

1. Create a cluster in MongoDB Atlas.
2. Create a database user with strong password.
3. Allow access from your backend server IP.
4. Use the Atlas connection string in backend env:
   ```env
   MONGODB_URI=mongodb+srv://<user>:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
   DATABASE_NAME=indian_kanoon_cache
   ```

For more details see `backend/MONGODB_SETUP.md`.

---

## 4. Install and Configure the Backend

1. Go to the backend directory:
   ```bash
   cd /opt/indian-kanoon-web-app/backend
   ```

2. Create & activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install Python dependencies and Playwright browser:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

4. Create a production environment file, e.g. `prod.env` in `backend/`:
   ```env
   MONGODB_URI=mongodb://127.0.0.1:27017
   DATABASE_NAME=indian_kanoon_cache
   JWT_SECRET_KEY=your-strong-secret
   GEMINI_API_KEY=your-gemini-api-key
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your-email@gmail.com
   SMTP_PASSWORD=your-app-password
   ```

   Adjust values for your actual MongoDB, Gmail/SMTP, and keys. See
   `backend/AUTH_SETUP.md` and `backend/GEMINI_SETUP.md` for details.

5. Test run the backend manually:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```
   Visit `http://<server-ip>:8000/` to confirm it works.

---

## 5. Run Backend as a Systemd Service (Linux)

Create a systemd unit so the backend auto-starts on boot.

1. Create `/etc/systemd/system/indiankanoon.service` with contents:

   ```ini
   [Unit]
   Description=Indian Kanoon FastAPI backend
   After=network.target mongod.service

   [Service]
   WorkingDirectory=/opt/indian-kanoon-web-app/backend
   EnvironmentFile=/opt/indian-kanoon-web-app/backend/prod.env
   ExecStart=/opt/indian-kanoon-web-app/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

2. Reload systemd and start the service:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable indiankanoon
   sudo systemctl start indiankanoon
   ```

3. Check status and logs:
   ```bash
   sudo systemctl status indiankanoon
   journalctl -u indiankanoon -f
   ```

---

## 6. Expose Backend over HTTPS (Reverse Proxy)

For production, you typically put Nginx (or similar) in front of Uvicorn.

1. Install Nginx:
   ```bash
   sudo apt install -y nginx
   ```

2. Configure a server block (e.g. `/etc/nginx/sites-available/indiankanoon`):
   ```nginx
   server {
       listen 80;
       server_name api.example.com;

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

3. Enable the site and reload Nginx:
   ```bash
   sudo ln -s /etc/nginx/sites-available/indiankanoon /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl reload nginx
   ```

4. Point your DNS (e.g. `api.example.com`) to the server's IP.

5. Add HTTPS using Let's Encrypt (Certbot) or your platform's method.

After this, your backend will be accessible at `https://api.example.com`.

---

## 7. Configure CORS in the Backend

When the frontend is deployed to Netlify/Vercel, its domain must be allowed by CORS.

In `backend/main.py`, configure:

```python
from fastapi.middleware.cors import CORSMiddleware

origins = [
    "https://your-site.netlify.app",
    "https://your-site.vercel.app",
    "https://app.example.com",  # your custom frontend domain
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Restart the backend service after updating this file:

```bash
sudo systemctl restart indiankanoon
```

---

## 8. Link Deployed Frontend to Backend

**Goal:** frontend (Netlify/Vercel) calls backend `https://api.example.com`.

1. In your frontend code (`frontend/auth.js` and `frontend/script.js`), set:

   ```js
   const API_BASE_URL = 'https://api.example.com';
   ```

2. Use `API_BASE_URL` in all `fetch` calls:

   ```js
   fetch(`${API_BASE_URL}/api/auth/login`, { ... })
   fetch(`${API_BASE_URL}/search?forminput=...`, { ... })
   ```

3. Deploy the frontend to Netlify or Vercel (see `FRONTEND_DEPLOYMENT.md`).

4. Open the deployed frontend URL and test:
   - Signup / login
   - Search
   - Summarize

If you see CORS errors, check:
- The frontend is calling the correct domain (`api.example.com`).
- That domain is listed in `origins` in `main.py`.

---

## 9. End-to-End Checklist

- [ ] MongoDB running (local `mongod` or Atlas)
- [ ] Backend dependencies installed, `uvicorn main:app` works manually
- [ ] `indiankanoon` systemd service running and enabled on boot
- [ ] Nginx (or other reverse proxy) forwarding `api.example.com` to `127.0.0.1:8000`
- [ ] Valid HTTPS certificate on `api.example.com`
- [ ] CORS configured with your frontend domain(s)
- [ ] Frontend deployed to Netlify/Vercel and using `API_BASE_URL = 'https://api.example.com'`
- [ ] All main flows (auth, search, summarize) working from the deployed frontend

