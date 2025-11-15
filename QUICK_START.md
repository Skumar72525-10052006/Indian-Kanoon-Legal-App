# Quick Start Guide - Authentication System

## 🚀 Get Started in 5 Minutes

### Step 1: Install Dependencies (1 min)

```bash
cd backend
pip install -r requirements.txt
```

### Step 2: Configure Environment (2 min)

Create `.env` file in `backend` directory:

```bash
# Copy example file
cp backend/.env.example backend/.env
```

**Minimum configuration for testing:**

```env
# MongoDB (use default local instance)
MONGODB_URI=mongodb://localhost:27017
DATABASE_NAME=indian_kanoon_cache

# JWT Secret (generate a random string)
JWT_SECRET_KEY=my-super-secret-key-for-testing-only

# Email (use your Gmail - see setup below)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-16-digit-app-password
FROM_EMAIL=your-email@gmail.com
FROM_NAME=Indian Kanoon Legal App

# Gemini API (if you have it)
GEMINI_API_KEY=your-gemini-api-key
```

**Gmail App Password Setup (30 seconds):**
1. Go to https://myaccount.google.com/apppasswords
2. Create app password for "Mail"
3. Copy the 16-digit password to `.env`

### Step 3: Start Services (1 min)

**Terminal 1 - MongoDB:**
```bash
mongod
```

**Terminal 2 - Backend:**
```bash
cd backend
python main.py
```

**Terminal 3 - Frontend:**
```bash
cd frontend
python -m http.server 5500
```

### Step 4: Test the App (1 min)

1. Open http://localhost:5500
2. Click "Login / Sign Up"
3. Click "Sign up"
4. Fill the form:
   - Full Name: Test User
   - Username: testuser
   - Email: your-email@gmail.com
   - Mobile: +919876543210
   - Click "Send OTP"
   - Check your email for OTP
   - Enter OTP
   - Password: Test@123
   - User Type: Citizen
5. Click "Sign Up"
6. You're logged in! 🎉

### Step 5: Test AI Summary Protection

1. Search for "Article 370"
2. Click "AI Summary" on any result
3. Summary should load (you're authenticated!)
4. Click logout
5. Try "AI Summary" again
6. Should prompt you to login ✅

## 🎯 What You Get

✅ **User Registration** with OTP verification  
✅ **Login** with email/username/mobile  
✅ **Password Reset** with OTP  
✅ **Google OAuth** (if configured)  
✅ **Protected AI Summaries** (login required)  
✅ **Public Search** (no login needed)  

## 📝 Test Accounts

After signup, you can login with:
- Email: your-email@gmail.com
- Username: testuser
- Mobile: +919876543210
- Password: Test@123

## 🔧 Troubleshooting

### Email not sending?
- Check Gmail App Password is correct
- Ensure 2FA is enabled on Gmail
- Check spam folder

### MongoDB connection failed?
```bash
# Install MongoDB if not installed
# Windows: Download from mongodb.com
# Mac: brew install mongodb-community
# Linux: sudo apt install mongodb

# Start MongoDB
mongod
```

### Port already in use?
```bash
# Backend (change port in main.py)
uvicorn.run(app, host="0.0.0.0", port=8001)

# Frontend (use different port)
python -m http.server 5501
```

### Import errors?
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

## 📚 Next Steps

1. **Read Full Documentation**
   - `AUTHENTICATION.md` - Complete feature documentation
   - `backend/AUTH_SETUP.md` - Detailed setup guide
   - `IMPLEMENTATION_SUMMARY.md` - Technical details

## 🎨 Features to Try

1. **Signup Flow**
   - OTP sent to email
   - Password strength validation
   - User type selection

2. **Login Flow**
   - Login with email
   - Login with username
   - Login with mobile

3. **Forgot Password**
   - Request OTP
   - Reset password
   - Login with new password

4. **Access Control**
   - Search without login ✅
   - AI summary requires login 🔒

5. **User Menu**
   - View user info
   - Logout

## 💡 Tips

- **OTP expires in 10 minutes** - Request new one if expired
- **JWT token valid for 7 days** - Auto-logout after expiry
- **Max 5 OTP attempts** - Request new OTP if exceeded
- **Password requirements**: Min 8 chars, 1 uppercase, 1 lowercase, 1 digit, 1 special char

## 🆘 Need Help?

Check the logs in the terminal where backend is running for detailed error messages.

Common issues:
- MongoDB not running → Start `mongod`
- Email not configured → Check `.env` file
- Port in use → Change port number
- Dependencies missing → Run `pip install -r requirements.txt`

## ✨ You're All Set!

The authentication system is fully functional. Enjoy exploring the features!

For production deployment, see `backend/AUTH_SETUP.md` for security best practices.

