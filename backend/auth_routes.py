"""
Authentication routes for user signup, login, OTP verification, and password reset.
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from datetime import datetime
from auth_models import (
    UserSignup, OTPRequest, OTPVerification, UserLogin,
    ForgotPasswordRequest, ResetPasswordRequest,
    TokenResponse, UserResponse, UserInDB, UserProfileUpdate
)
from auth_utils import (
    verify_password, get_password_hash, create_access_token,
    decode_access_token, generate_otp
)
from user_db import (
    create_user, get_user_by_email, get_user_by_identifier,
    update_user_verification, update_user_password,
    store_otp, verify_otp, update_user_profile
)
from notification_service import send_otp_notification, send_welcome_email
from database import get_database

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Dependency to get current authenticated user"""
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    
    user = await get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="User account is inactive")
    
    return user


@router.post("/send-otp", status_code=200)
async def send_otp_endpoint(request: OTPRequest):
    """
    Send OTP to email for signup verification.
    """
    try:
        # Check if user already exists
        existing_user = await get_user_by_email(request.email)
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")

        # Generate OTP
        otp = generate_otp()

        # Store OTP in database
        stored = await store_otp(request.email, otp, "signup")
        if not stored:
            raise HTTPException(status_code=500, detail="Failed to store OTP")

        # Send OTP via email
        result = await send_otp_notification(
            request.email,
            otp,
            "signup verification"
        )

        # If email sending fails (e.g., SMTP not configured), don't fail the request.
        # OTP is already stored in the database and can still be verified.
        if not result["success"]:
            print(f"Warning: Failed to send OTP email to {request.email}, but OTP is stored in DB.")

        return {
            "message": "OTP sent successfully to your email" if result["email_sent"] else "OTP generated; email could not be sent",
            "email_sent": result["email_sent"]
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error sending OTP: {e}")
        raise HTTPException(status_code=500, detail="Failed to send OTP")


@router.post("/verify-otp", status_code=200)
async def verify_otp_endpoint(request: OTPVerification):
    """
    Verify OTP for signup.
    """
    try:
        is_valid = await verify_otp(request.email, request.otp, "signup")
        
        if not is_valid:
            raise HTTPException(status_code=400, detail="Invalid or expired OTP")
        
        return {"message": "OTP verified successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error verifying OTP: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify OTP")


@router.post("/signup", response_model=TokenResponse, status_code=201)
async def signup(user_data: UserSignup):
    """
    Register a new user after OTP verification.
    Note: OTP must be verified before calling this endpoint.
    """
    try:
        # Check if user already exists
        existing_user = await get_user_by_email(user_data.email)
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create user in database
        user_in_db = UserInDB(
            full_name=user_data.full_name,
            username=user_data.username.lower(),
            email=user_data.email.lower(),
            mobile_number=user_data.mobile_number,
            hashed_password=get_password_hash(user_data.password),
            user_type=user_data.user_type,
            is_verified=True,  # Already verified via OTP
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        user_id = await create_user(user_in_db)
        if not user_id:
            raise HTTPException(status_code=500, detail="Failed to create user")
        
        # Send welcome email
        await send_welcome_email(user_data.email, user_data.full_name)
        
        # Create access token
        access_token = create_access_token(data={"sub": user_data.email})
        
        # Return token and user info
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user={
                "id": user_id,
                "full_name": user_data.full_name,
                "username": user_data.username,
                "email": user_data.email,
                "mobile_number": user_data.mobile_number,
                "user_type": user_data.user_type,
                "is_verified": True
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error during signup: {e}")
        raise HTTPException(status_code=500, detail="Failed to create account")


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """
    Login with email/username/mobile and password.
    """
    try:
        # Find user by identifier (email, username, or mobile)
        user = await get_user_by_identifier(credentials.identifier)
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Verify password
        if not verify_password(credentials.password, user['hashed_password']):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Check if user is active
        if not user.get('is_active', True):
            raise HTTPException(status_code=403, detail="Account is inactive")
        
        # Create access token
        access_token = create_access_token(data={"sub": user['email']})
        
        # Return token and user info
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user={
                "id": user['id'],
                "full_name": user['full_name'],
                "username": user['username'],
                "email": user['email'],
                "mobile_number": user['mobile_number'],
                "user_type": user['user_type'],
                "is_verified": user.get('is_verified', False)
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error during login: {e}")
        raise HTTPException(status_code=500, detail="Login failed")


@router.post("/forgot-password", status_code=200)
async def forgot_password(request: ForgotPasswordRequest):
    """
    Request password reset OTP.
    """
    try:
        # Find user
        user = await get_user_by_identifier(request.identifier)

        if not user:
            # Don't reveal if user exists or not
            return {"message": "If the account exists, an OTP has been sent to your email"}

        # Generate OTP
        otp = generate_otp()

        # Store OTP
        stored = await store_otp(user['email'], otp, "forgot_password")
        if not stored:
            raise HTTPException(status_code=500, detail="Failed to store OTP")

        # Send OTP via email
        result = await send_otp_notification(
            user['email'],
            otp,
            "password reset"
        )

        return {"message": "If the account exists, an OTP has been sent to your email"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in forgot password: {e}")
        raise HTTPException(status_code=500, detail="Failed to process request")


@router.post("/reset-password", status_code=200)
async def reset_password(request: ResetPasswordRequest):
    """
    Reset password using OTP.
    """
    try:
        # Find user
        user = await get_user_by_identifier(request.identifier)
        
        if not user:
            raise HTTPException(status_code=400, detail="Invalid request")
        
        # Verify OTP
        is_valid = await verify_otp(user['email'], request.otp, "forgot_password")
        if not is_valid:
            raise HTTPException(status_code=400, detail="Invalid or expired OTP")
        
        # Update password
        updated = await update_user_password(user['email'], request.new_password)
        if not updated:
            raise HTTPException(status_code=500, detail="Failed to update password")
        
        return {"message": "Password reset successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error resetting password: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset password")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user information."""
    return UserResponse(
        id=current_user['id'],
        full_name=current_user['full_name'],
        username=current_user['username'],
        email=current_user['email'],
        mobile_number=current_user['mobile_number'],
        user_type=current_user['user_type'],
        is_verified=current_user.get('is_verified', False),
        created_at=current_user['created_at']
    )


@router.put("/me", response_model=UserResponse)
async def update_current_user_info(
    profile_update: UserProfileUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update current authenticated user's profile (full_name, mobile_number, user_type)."""
    try:
        updates = profile_update.dict(exclude_unset=True)
        # Never allow changing email or username from this endpoint
        updates.pop("email", None)
        updates.pop("username", None)

        updated_user = await update_user_profile(current_user["email"], updates)
        if not updated_user:
            raise HTTPException(status_code=400, detail="Failed to update profile")

        return UserResponse(
            id=updated_user['id'],
            full_name=updated_user['full_name'],
            username=updated_user['username'],
            email=updated_user['email'],
            mobile_number=updated_user['mobile_number'],
            user_type=updated_user['user_type'],
            is_verified=updated_user.get('is_verified', False),
            created_at=updated_user['created_at']
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to update profile")

