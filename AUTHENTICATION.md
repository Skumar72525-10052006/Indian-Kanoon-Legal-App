# Authentication System Documentation

## Overview

The Indian Kanoon Legal App features a comprehensive authentication system with the following capabilities:

- **Email/Username/Mobile Login** - Users can login with any of their credentials
- **OTP Verification** - Secure signup with OTP sent to email
- **Password Reset** - Forgot password flow with OTP verification
- **JWT Authentication** - Secure token-based authentication
- **Role-Based Access** - Support for Citizen and Lawyer user types
- **Protected AI Summaries** - AI summary feature requires authentication

## Features

### 1. User Signup
- Full name, username, email, mobile number, password
- Username validation (letters, numbers, underscores only)
- Password strength requirements:
  - Minimum 8 characters
  - At least 1 uppercase letter
  - At least 1 lowercase letter
  - At least 1 digit
  - At least 1 special character
- Mobile number with country code (e.g., +919876543210)
- OTP verification via email
- User type selection (Citizen or Lawyer)
- Automatic login after successful signup

### 2. User Login
- Login with email, username, or mobile number
- Password authentication
- JWT token generation (7-day validity)
- Persistent session (stored in localStorage)

### 4. Forgot Password
- Request password reset via email/username/mobile
- OTP sent to registered email
- Secure password reset with OTP verification
- Same password strength requirements

### 5. OTP System
- 6-digit numeric OTP
- Sent via email
- 10-minute expiration
- Maximum 5 verification attempts
- Automatic cleanup of expired OTPs

### 6. Access Control
- Public access to search functionality
- Protected AI summary feature (requires login)
- User-friendly login prompts for unauthenticated users
- Automatic token refresh

## Architecture

### Backend (FastAPI)

#### Files Created:
1. **auth_models.py** - Pydantic models for request/response validation
2. **auth_utils.py** - JWT, password hashing, OTP generation utilities
3. **auth_routes.py** - Authentication API endpoints
4. **user_db.py** - User database operations
5. **notification_service.py** - Email sending service

#### Database Collections:
1. **users** - User accounts with indexes on email, username, mobile
2. **otps** - OTP storage with TTL index for auto-expiration

#### Security Features:
- Bcrypt password hashing
- JWT with HS256 algorithm
- Rate limiting on all endpoints
- CORS protection
- Input validation with Pydantic
- SQL injection prevention (MongoDB)
- XSS protection

### Frontend (Vanilla JavaScript)

#### Files Created/Modified:
1. **auth.js** - Authentication logic and API calls
2. **index.html** - Authentication modals and UI
3. **styles.css** - Modal and form styling
4. **script.js** - Integration with search and summary features

#### UI Components:
1. **Login Modal** - Email/username/mobile + password login
2. **Signup Modal** - Full registration form with OTP verification
3. **Forgot Password Modal** - Password reset request
4. **Reset Password Modal** - New password with OTP
5. **User Menu** - Logged-in user dropdown with logout
6. **Notifications** - Toast notifications for success/error messages

## API Endpoints

### Authentication Endpoints

#### POST /api/auth/send-otp
Send OTP for signup verification.

**Request:**
```json
{
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "message": "OTP sent successfully to your email",
  "email_sent": true
}
```

#### POST /api/auth/verify-otp
Verify OTP before signup.

**Request:**
```json
{
  "email": "user@example.com",
  "otp": "123456"
}
```

**Response:**
```json
{
  "message": "OTP verified successfully"
}
```

#### POST /api/auth/signup
Register a new user (after OTP verification).

**Request:**
```json
{
  "full_name": "John Doe",
  "username": "johndoe",
  "email": "user@example.com",
  "mobile_number": "+919876543210",
  "password": "SecurePass123!",
  "user_type": "citizen"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": "507f1f77bcf86cd799439011",
    "full_name": "John Doe",
    "username": "johndoe",
    "email": "user@example.com",
    "mobile_number": "+919876543210",
    "user_type": "citizen",
    "is_verified": true
  }
}
```

#### POST /api/auth/login
Login with credentials.

**Request:**
```json
{
  "identifier": "johndoe",
  "password": "SecurePass123!"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user": { ... }
}
```

#### POST /api/auth/forgot-password
Request password reset OTP.

**Request:**
```json
{
  "identifier": "user@example.com"
}
```

**Response:**
```json
{
  "message": "If the account exists, an OTP has been sent to your email"
}
```

#### POST /api/auth/reset-password
Reset password with OTP.

**Request:**
```json
{
  "identifier": "user@example.com",
  "otp": "123456",
  "new_password": "NewSecurePass123!"
}
```

**Response:**
```json
{
  "message": "Password reset successfully"
}
```

#### GET /api/auth/me
Get current user information (requires authentication).

**Headers:**
```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**Response:**
```json
{
  "id": "507f1f77bcf86cd799439011",
  "full_name": "John Doe",
  "username": "johndoe",
  "email": "user@example.com",
  "mobile_number": "+919876543210",
  "user_type": "citizen",
  "is_verified": true,
  "created_at": "2024-01-01T00:00:00"
}
```

### Protected Endpoints

#### GET /summarize
Get AI summary of a legal document (requires authentication).

**Headers:**
```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**Query Parameters:**
- `document_url` or `doc_id` - Document identifier
- `query` - Search query (if using doc_id)
- `title` - Document title

**Response:**
```json
{
  "success": true,
  "title": "Document Title",
  "document_url": "https://...",
  "content_length": 5000,
  "citizen_summary": "Simple summary...",
  "lawyer_summary": "Legal analysis...",
  "cached": false,
  "error": null
}
```

## User Flow

### Signup Flow
1. User clicks "Login / Sign Up"
2. Clicks "Sign up"
3. Fills in full name, username, email, mobile, password, user type
4. Clicks "Send OTP"
5. Receives OTP via email
6. Enters OTP (auto-verifies when 6 digits entered)
7. Clicks "Sign Up"
8. Account created, JWT token issued
9. Automatically logged in
10. Welcome email sent

### Login Flow
1. User clicks "Login / Sign Up"
2. Enters email/username/mobile and password
3. Clicks "Login"
4. JWT token issued
5. Logged in, UI updated

### Forgot Password Flow
1. User clicks "Forgot password?"
2. Enters email/username/mobile
3. Clicks "Send OTP"
4. Receives OTP via email
5. Enters OTP and new password
6. Clicks "Reset Password"
7. Password updated
8. Redirected to login

### AI Summary Access Flow
1. User searches for legal documents (no auth required)
2. Results displayed
3. User clicks "AI Summary" button
4. **If not logged in**: Login modal appears with message
5. **If logged in**: Summary fetched and displayed

## Configuration

See `backend/AUTH_SETUP.md` for detailed setup instructions.

### Required Environment Variables:
- `JWT_SECRET_KEY` - Secret key for JWT signing
- `MONGODB_URI` - MongoDB connection string
- `SMTP_USER` - Email for sending OTPs
- `SMTP_PASSWORD` - Email app password

## Security Considerations

1. **Password Storage**: Passwords are hashed using bcrypt before storage
2. **JWT Tokens**: Signed with HS256, 7-day expiration
3. **OTP Security**: 10-minute expiration, max 5 attempts
4. **Rate Limiting**: All endpoints are rate-limited
5. **Input Validation**: Pydantic models validate all inputs
6. **CORS**: Configured to allow only specific origins in production
7. **HTTPS**: Should be enabled in production
8. **Sensitive Data**: Never logged or exposed in responses

## Future Enhancements

- [ ] Email verification link (alternative to OTP)
- [ ] Two-factor authentication (2FA)
- [ ] Social login (Facebook, LinkedIn)
- [ ] Role-based permissions (lawyer-specific features)
- [ ] Account deletion
- [ ] Profile picture upload
- [ ] Password change (while logged in)
- [ ] Session management (view active sessions)
- [ ] Login history
- [ ] Account recovery options

