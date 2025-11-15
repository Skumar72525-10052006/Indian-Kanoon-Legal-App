"""
Authentication models and schemas for user management.
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Literal, Optional
from datetime import datetime
import re


def validate_password_complexity(v):
    """Reusable password complexity validation"""
    if not re.search(r'[A-Z]', v):
        raise ValueError('Password must contain at least one uppercase letter')
    if not re.search(r'[a-z]', v):
        raise ValueError('Password must contain at least one lowercase letter')
    if not re.search(r'\d', v):
        raise ValueError('Password must contain at least one digit')
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
        raise ValueError('Password must contain at least one special character')
    
    # ✨ NEW FIX: Check byte length for bcrypt compatibility
    if len(v.encode('utf-8')) > 72:
        raise ValueError('Password is too long (max 72 bytes)')
    
    return v


class UserSignup(BaseModel):
    """User signup request model"""
    full_name: str = Field(..., min_length=2, max_length=100)
    username: str = Field(..., min_length=3, max_length=30)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    mobile_number: str = Field(..., pattern=r'^\+?[1-9]\d{9,14}$')
    user_type: Literal["citizen", "lawyer"]
    
    @validator('username')
    def validate_username(cls, v):
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username can only contain letters, numbers, and underscores')
        return v.lower()
    
    @validator('password')
    def validate_password(cls, v):
        # Use the reusable validation function
        return validate_password_complexity(v)


class OTPRequest(BaseModel):
    """OTP request model"""
    email: EmailStr


class OTPVerification(BaseModel):
    """OTP verification model"""
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)


class UserLogin(BaseModel):
    """User login request model"""
    identifier: str = Field(..., description="Email, username, or mobile number")
    password: str


class ForgotPasswordRequest(BaseModel):
    """Forgot password request model"""
    identifier: str = Field(..., description="Email, username, or mobile number")


class ResetPasswordRequest(BaseModel):
    """Reset password request model"""
    identifier: str
    otp: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=8, max_length=100)
    
    @validator('new_password')
    def validate_new_password(cls, v):
        # Use the reusable validation function
        return validate_password_complexity(v)


class TokenResponse(BaseModel):
    """JWT token response model"""
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    """User response model"""
    id: str
    full_name: str
    username: str
    email: str
    mobile_number: str
    user_type: Literal["citizen", "lawyer"]
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserProfileUpdate(BaseModel):
    """Profile update request model"""
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    mobile_number: Optional[str] = Field(None, pattern=r'^\+?[1-9]\d{9,14}$')
    user_type: Optional[Literal["citizen", "lawyer"]] = None


class UserInDB(BaseModel):
    """User model in database"""
    full_name: str
    username: str
    email: str
    mobile_number: str
    hashed_password: str
    user_type: Literal["citizen", "lawyer"]
    is_verified: bool = False
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class OTPInDB(BaseModel):
    """OTP model in database"""
    email: str
    otp: str
    purpose: Literal["signup", "forgot_password"]
    created_at: datetime
    expires_at: datetime
    attempts: int = 0