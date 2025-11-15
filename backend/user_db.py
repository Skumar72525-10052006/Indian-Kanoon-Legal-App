"""
User database operations for authentication and user management.
"""
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import DuplicateKeyError
from typing import Optional, Dict
from datetime import datetime, timedelta
from auth_models import UserInDB, OTPInDB
from auth_utils import get_password_hash, generate_otp
from database import get_database
import os
from dotenv import load_dotenv

load_dotenv()

USERS_COLLECTION = "users"
OTP_COLLECTION = "otps"
OTP_EXPIRY_MINUTES = 10
MAX_OTP_ATTEMPTS = 5


async def init_user_collections():
    """Initialize user-related collections and indexes"""
    try:
        database, _ = await get_database()
        users_collection = database[USERS_COLLECTION]
        otp_collection = database[OTP_COLLECTION]

        # Create indexes for users collection
        existing_indexes = await users_collection.list_indexes().to_list(length=None)
        index_names = [idx['name'] for idx in existing_indexes]

        if "email_1" not in index_names:
            await users_collection.create_index("email", unique=True)
        if "username_1" not in index_names:
            await users_collection.create_index("username", unique=True)
        if "mobile_number_1" not in index_names:
            await users_collection.create_index("mobile_number", unique=True)

        # Create indexes for OTP collection
        existing_otp_indexes = await otp_collection.list_indexes().to_list(length=None)
        otp_index_names = [idx['name'] for idx in existing_otp_indexes]

        if "email_1_purpose_1" not in otp_index_names:
            await otp_collection.create_index([("email", 1), ("purpose", 1)])

        # TTL index for OTP expiration
        if "expires_at_1" in otp_index_names:
            try:
                await otp_collection.drop_index("expires_at_1")
            except:
                pass

        await otp_collection.create_index("expires_at", expireAfterSeconds=0)

        print("✓ User collections initialized")
    except Exception as e:
        print(f"Error initializing user collections: {e}")


async def create_user(user_data: UserInDB) -> Optional[str]:
    """
    Create a new user in the database.

    Returns:
        User ID if successful, None otherwise
    """
    try:
        database, _ = await get_database()
        users_collection = database[USERS_COLLECTION]

        user_dict = user_data.dict()
        result = await users_collection.insert_one(user_dict)

        print(f"✓ User created: {user_data.email}")
        return str(result.inserted_id)
    except DuplicateKeyError as e:
        # Extract which field caused the duplicate
        if "email" in str(e):
            raise ValueError("Email already registered")
        elif "username" in str(e):
            raise ValueError("Username already taken")
        elif "mobile_number" in str(e):
            raise ValueError("Mobile number already registered")
        else:
            raise ValueError("User already exists")
    except Exception as e:
        print(f"Error creating user: {e}")
        raise


async def get_user_by_email(email: str) -> Optional[Dict]:
    """Get user by email"""
    try:
        database, _ = await get_database()
        users_collection = database[USERS_COLLECTION]

        user = await users_collection.find_one({"email": email.lower()})
        if user:
            user['id'] = str(user['_id'])
        return user
    except Exception as e:
        print(f"Error getting user by email: {e}")
        return None


async def get_user_by_username(username: str) -> Optional[Dict]:
    """Get user by username"""
    try:
        database, _ = await get_database()
        users_collection = database[USERS_COLLECTION]

        user = await users_collection.find_one({"username": username.lower()})
        if user:
            user['id'] = str(user['_id'])
        return user
    except Exception as e:
        print(f"Error getting user by username: {e}")
        return None


async def get_user_by_mobile(mobile: str) -> Optional[Dict]:
    """Get user by mobile number.

    Accepts numbers with or without country code (e.g., 9876543210 or +919876543210).
    """
    try:
        database, _ = await get_database()
        users_collection = database[USERS_COLLECTION]

        # Build possible representations for this mobile number
        cleaned_input = mobile.strip()
        variants = set()

        # Original input as-is
        if cleaned_input:
            variants.add(cleaned_input)

        # Digits-only version (remove spaces, dashes, plus, etc.)
        digits_only = "".join(ch for ch in cleaned_input if ch.isdigit())
        if digits_only:
            variants.add(digits_only)

        # If it's a plain 10-digit number (likely Indian local mobile), also try +91 prefix
        if len(digits_only) == 10:
            variants.add(f"+91{digits_only}")

        # If it looks like it includes a country code (length > 10), also try the last 10 digits
        if len(digits_only) > 10:
            local_10 = digits_only[-10:]
            variants.add(local_10)

        query = {"mobile_number": {"$in": list(variants)}}

        user = await users_collection.find_one(query)
        if user:
            user["id"] = str(user["_id"])
        return user
    except Exception as e:
        print(f"Error getting user by mobile: {e}")
        return None


async def get_user_by_identifier(identifier: str) -> Optional[Dict]:
    """
    Get user by email, username, or mobile number.

    Args:
        identifier: Email, username, or mobile number

    Returns:
        User document or None
    """
    # Try email first
    user = await get_user_by_email(identifier)
    if user:
        return user

    # Try username
    user = await get_user_by_username(identifier)
    if user:
        return user

    # Try mobile number
    user = await get_user_by_mobile(identifier)
    return user


async def update_user_verification(email: str, is_verified: bool = True) -> bool:
    """Update user verification status"""
    try:
        database, _ = await get_database()
        users_collection = database[USERS_COLLECTION]

        result = await users_collection.update_one(
            {"email": email.lower()},
            {
                "$set": {
                    "is_verified": is_verified,
                    "updated_at": datetime.now()
                }
            }
        )

        return result.modified_count > 0
    except Exception as e:
        print(f"Error updating user verification: {e}")
        return False


async def update_user_password(email: str, new_password: str) -> bool:
    """Update user password"""
    try:
        database, _ = await get_database()
        users_collection = database[USERS_COLLECTION]

        hashed_password = get_password_hash(new_password)

        result = await users_collection.update_one(
            {"email": email.lower()},
            {
                "$set": {
                    "hashed_password": hashed_password,
                    "updated_at": datetime.now()
                }
            }
        )

        return result.modified_count > 0
    except Exception as e:
        print(f"Error updating user password: {e}")
        return False


async def update_user_profile(email: str, updates: Dict) -> Optional[Dict]:
    """Update user profile fields like full_name, mobile_number, and user_type."""
    try:
        database, _ = await get_database()
        users_collection = database[USERS_COLLECTION]

        # Remove None values and prevent empty updates
        updates = {k: v for k, v in updates.items() if v is not None}
        if not updates:
            # Nothing to update; return current user
            user = await users_collection.find_one({"email": email.lower()})
            if user:
                user["id"] = str(user["_id"])
            return user

        updates["updated_at"] = datetime.now()

        result = await users_collection.update_one(
            {"email": email.lower()},
            {"$set": updates}
        )

        if result.matched_count == 0:
            return None

        user = await users_collection.find_one({"email": email.lower()})
        if user:
            user["id"] = str(user["_id"])
        return user
    except DuplicateKeyError as e:
        # Handle unique constraint violations similar to create_user
        if "mobile_number" in str(e):
            raise ValueError("Mobile number already registered")
        else:
            raise ValueError("Profile update violates a uniqueness constraint")
    except Exception as e:
        print(f"Error updating user profile: {e}")
        raise



async def store_otp(email: str, otp: str, purpose: str) -> bool:
    """Store OTP in database"""
    try:
        database, _ = await get_database()
        otp_collection = database[OTP_COLLECTION]

        # Delete any existing OTPs for this email and purpose
        await otp_collection.delete_many({"email": email.lower(), "purpose": purpose})

        otp_data = {
            "email": email.lower(),
            "otp": otp,
            "purpose": purpose,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(minutes=OTP_EXPIRY_MINUTES),
            "attempts": 0
        }

        await otp_collection.insert_one(otp_data)
        print(f"✓ OTP stored for {email}")
        return True
    except Exception as e:
        print(f"Error storing OTP: {e}")
        return False


async def verify_otp(email: str, otp: str, purpose: str) -> bool:
    """Verify OTP"""
    try:
        database, _ = await get_database()
        otp_collection = database[OTP_COLLECTION]

        otp_doc = await otp_collection.find_one({
            "email": email.lower(),
            "purpose": purpose
        })

        if not otp_doc:
            return False

        # Check if OTP is expired
        if datetime.now() > otp_doc['expires_at']:
            await otp_collection.delete_one({"_id": otp_doc['_id']})
            return False

        # Check attempts
        if otp_doc['attempts'] >= MAX_OTP_ATTEMPTS:
            await otp_collection.delete_one({"_id": otp_doc['_id']})
            return False

        # Verify OTP
        if otp_doc['otp'] == otp:
            # Delete OTP after successful verification
            await otp_collection.delete_one({"_id": otp_doc['_id']})
            return True
        else:
            # Increment attempts
            await otp_collection.update_one(
                {"_id": otp_doc['_id']},
                {"$inc": {"attempts": 1}}
            )
            return False
    except Exception as e:
        print(f"Error verifying OTP: {e}")
        return False

