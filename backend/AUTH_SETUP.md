# Authentication Setup Guide

This guide explains how to configure and operate the **emailOTP + JWT** authentication system used by the Indian Kanoon Legal App.

## 1. Prerequisites

- Python backend installed (`pip install -r requirements.txt`)
- MongoDB (local or Atlas)
- SMTP account (Gmail or production email provider)

## 2. Environment Variables

Create or update `.env` in the `backend/` directory and set:

```env
# Database
MONGODB_URI=mongodb://localhost:27017
DATABASE_NAME=indian_kanoon_cache

# JWT
JWT_SECRET_KEY=your-strong-random-secret

# Email (example: Gmail)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-16-digit-app-password
FROM_EMAIL=your-email@gmail.com
FROM_NAME=Indian Kanoon Legal App
```

For production, prefer a provider like SendGrid / SES / Mailgun and rotate credentials regularly.

## 3. Auth Flows & Endpoints

All endpoints are under prefix `/api/auth` (see `backend/auth_routes.py`).

### Signup (with OTP)
1. Frontend collects full name, username, email, mobile, user type, password.
2. `POST /api/auth/send-otp` with `{ email }`.
3. User receives OTP via email.
4. `POST /api/auth/verify-otp` with `{ email, otp }`.
5. `POST /api/auth/signup` with full registration payload.
6. Backend creates user, marks `is_verified=True`, sends welcome email, and returns JWT token + user info.

### Login
- `POST /api/auth/login` with:
  ```json
  { "identifier": "email-or-username-or-mobile", "password": "..." }
  ```
- Backend looks up user by email/username/mobile (supports `+91XXXXXXXXXX` and `XXXXXXXXXX`).
- On success returns JWT token and user profile.

### Forgot / Reset Password
1. `POST /api/auth/forgot-password` with `{ identifier }`.
2. If account exists, OTP is stored and email is sent (response is generic either way).
3. `POST /api/auth/reset-password` with `{ identifier, otp, new_password }`.
4. Password is updated after OTP validation.

### Profile
- `GET /api/auth/me`  Returns current user (requires `Authorization: Bearer <token>`)
- `PUT /api/auth/me`  Update `full_name`, `mobile_number`, `user_type` for current user.

## 4. Security Behaviour

- Passwords are hashed with `bcrypt`.
- Password policy enforced in validation (min length + complexity).
- OTPs:
  - Stored in `otps` collection with purpose (`signup`, `forgot_password`).
  - Expire automatically using a TTL index (~10 minutes).
  - Limited number of verification attempts per OTP.
- JWT access tokens:
  - Signed with `JWT_SECRET_KEY`.
  - Expire after several days (see `auth_utils.py`).
- Inactive users (`is_active=False`) are blocked from logging in.

## 5. Production Recommendations

- Use HTTPS endtoend; never send tokens or OTPs over plain HTTP.
- Restrict CORS in `main.py` to your production frontend origin.
- Store secrets in your hosting providers **secret manager**, not directly in `.env` committed to git.
- Monitor auth logs (container logs / hosted logging) for repeated failures.

If authentication is misbehaving, enable debug logging and check traces in `auth_routes.py`, `auth_utils.py`, and `user_db.py`.
