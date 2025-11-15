# Frontend Deployment Guide (Vercel / Netlify)

This guide explains **only what you need to change in the project** when you deploy the **frontend** to a static hosting platform like **Vercel** or **Netlify**.

Your stack:
- **Frontend**: `frontend/` (pure HTML/CSS/JS)
- **Backend**: FastAPI (exposed on some URL, e.g. `https://api.example.com`)
- **Database**: MongoDB (local or Atlas)  used only by backend

---

## 1. Preconditions

Before deploying the frontend, you should already have:

1. **Backend deployed** somewhere and reachable on the internet:
   - e.g. `https://api.example.com` or `https://<your-backend-host>:8000`
2. **CORS configured on the backend** to allow your frontend domain (Netlify/Vercel URL):
   - Example origins you might eventually allow:
     - `https://your-site.netlify.app`
     - `https://your-site.vercel.app`
     - Your custom domain (e.g. `https://app.example.com`)

CORS change happens in `backend/main.py` (not in the frontend). In production, you should **not** keep `allow_origins=["*"]`.

---

## 2. Update the frontend API base URL

Your frontend JS files (`frontend/script.js` and `frontend/auth.js`) call the backend using `fetch`. For development, you are likely using something like:

```js
const API_BASE_URL = 'http://localhost:8000';
```

For production (Vercel/Netlify), change this to your **real backend URL**:

```js
const API_BASE_URL = 'https://api.example.com'; // your deployed backend
```

### 2.1 Where to change

1. Open `frontend/auth.js`.
   - Look for any hard-coded URLs such as `http://localhost:8000` or `http://127.0.0.1:8000`.
   - Replace them with `API_BASE_URL` or your final backend URL.

2. Open `frontend/script.js`.
   - Do the same: search for `localhost:8000` and update.

If your code already uses a variable like `API_BASE_URL`, just change that constant in **one place** and keep using it everywhere.

### 2.2 Example pattern (recommended)

In both `auth.js` and `script.js` you can standardize to:

```js
// PRODUCTION: use your deployed backend URL
const API_BASE_URL = 'https://api.example.com';

// DEV (local): uncomment this while developing locally
// const API_BASE_URL = 'http://localhost:8000';

// Then use API_BASE_URL in fetch calls, for example:
// fetch(`${API_BASE_URL}/api/auth/login`, { ... })
```

This makes it easy to switch between local and production without hunting many URLs.

---

## 3. Deploying to Netlify (static frontend)

You only deploy the **contents of the `frontend/` folder**.

### 3.1 Quick deploy (drag & drop)

1. Build/prepare: ensure `frontend/index.html`, `styles.css`, `script.js`, `auth.js`, `image.png` are correct.
2. Zip or keep the `frontend/` folder.
3. In the Netlify UI:
   - Click **"Add new site" → "Deploy manually"**.
   - Drag & drop the **contents of `frontend/`** (or the folder itself if Netlify accepts it).
4. Netlify will host them at a URL like `https://your-site.netlify.app`.

### 3.2 Git repo deployment

If using GitHub/GitLab/Bitbucket:

1. Connect your repository to Netlify.
2. Set **build command** = `None` (static site) or leave empty if allowed.
3. Set **publish directory** = `frontend`.
4. Deploy.

No environment variables are needed on Netlify because the frontend uses a **hard-coded API base URL** in `auth.js` / `script.js`.

---

## 4. Deploying to Vercel (static frontend)

Vercel is similar: it will just serve static files.

### 4.1 Project setup

1. Create a new project in Vercel.
2. Connect to your Git repo.
3. In the project settings:
   - **Framework preset**: `Other` or `Static`.
   - **Root directory**: `frontend`.
   - **Build command**: leave empty (or `echo "no build"` if required).
   - **Output directory**: `.` (the files in `frontend` itself).
4. Deploy.

Vercel will give you a URL like `https://your-site.vercel.app`.

Again, no Vercel env vars are required if the API URL is hard-coded in JS.

---

## 5. Backend CORS configuration (important)

After you know your Netlify/Vercel URL, you **must** update CORS on the backend so that the browser is allowed to call your API from that origin.

In `backend/main.py` (this is an example pattern):

```python
from fastapi.middleware.cors import CORSMiddleware

origins = [
    "https://your-site.netlify.app",
    "https://your-site.vercel.app",
    "https://your-custom-domain.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Replace the URLs above with your **actual** frontend domains. Avoid `"*"` in production.

---

## 6. Post-deployment checklist

After deploying the frontend to Netlify/Vercel and the backend somewhere else:

- [ ] `API_BASE_URL` (or equivalent) in `auth.js`/`script.js` points to the production backend (`https://api.example.com`).
- [ ] Backend is reachable over HTTPS from your browser.
- [ ] CORS `allow_origins` in `main.py` includes your Netlify/Vercel URL(s).
- [ ] Login / signup / reset password work from the deployed frontend.
- [ ] Search and summarize calls succeed from the deployed frontend.
- [ ] Favicon (`image.png`) appears correctly in the browser tab.

If any API calls fail with CORS errors or `NetworkError` in the browser console, check:
- The **exact URL** the frontend is calling (network tab).
- Whether that URL is correct and reachable.
- Whether the backend CORS `allow_origins` list includes the frontend origin.

