from fastapi import FastAPI, Query, HTTPException, Depends, Request, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any
import asyncio
import time
from datetime import datetime, timedelta
import uuid
import motor.motor_asyncio
import os
from pydantic import BaseModel, Field
from bson import ObjectId

# MongoDB setup
MONGODB_URL = os.getenv('MONGODB_URL', 'mongodb://localhost:27017')
DATABASE_NAME = os.getenv('DATABASE_NAME', 'indian_kanoon_db')

# Global database connection
mongodb_client = None
db = None

async def init_chat_db():
    """Initialize MongoDB connection for chat functionality"""
    global mongodb_client, db
    try:
        mongodb_client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
        db = mongodb_client[DATABASE_NAME]
        
        # Initialize collections for chat
        await db.chat_sessions.create_index("user_id")
        await db.chat_sessions.create_index("updated_at")
        await db.chat_messages.create_index("session_id")
        await db.chat_messages.create_index("created_at")
        
        print("✓ Chat database initialized")
    except Exception as e:
        print(f"❌ Failed to initialize chat database: {e}")
        raise

async def close_chat_db():
    """Close MongoDB connection"""
    global mongodb_client
    if mongodb_client:
        mongodb_client.close()
        print("✓ Chat database connection closed")

# Pydantic models
class ChatSessionCreate(BaseModel):
    title: Optional[str] = "New Chat"
    context: Optional[str] = None

class ChatSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    title: str
    context: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    role: str  # 'user' or 'assistant'
    content: str
    references: Optional[List[Dict[str, str]]] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ChatMessageSend(BaseModel):
    message: str
    include_references: Optional[bool] = True

# Import get_current_user from auth_routes
try:
    from auth_routes import get_current_user
except ImportError:
    # Fallback for testing
    async def get_current_user(request: Request):
        return {"id": "test_user", "username": "test"}

# Create chat router
chat_router = APIRouter(prefix="/api/chat", tags=["chat"])

@chat_router.get("/sessions")
async def get_chat_sessions(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get all chat sessions for the current user"""
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found")
        
        sessions = await db.chat_sessions.find(
            {"user_id": user_id}
        ).sort("updated_at", -1).to_list(length=50)
        
        # Convert ObjectId to string and format response
        formatted_sessions = []
        for session in sessions:
            formatted_session = {
                "id": str(session["_id"]),
                "title": session.get("title", "New Chat"),
                "context": session.get("context"),
                "created_at": session.get("created_at"),
                "updated_at": session.get("updated_at"),
                "last_message": ""
            }
            
            # Get last message
            last_message = await db.chat_messages.find_one(
                {"session_id": str(session["_id"])},
                sort=[("created_at", -1)]
            )
            
            if last_message:
                formatted_session["last_message"] = last_message.get("content", "")[:50] + "..."
            
            formatted_sessions.append(formatted_session)
        
        return formatted_sessions
        
    except Exception as e:
        print(f"Error fetching chat sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch chat sessions")

@chat_router.post("/sessions")
async def create_chat_session(
    session_data: ChatSessionCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Create a new chat session"""
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found")
        
        session = ChatSession(
            user_id=user_id,
            title=session_data.title or "New Chat",
            context=session_data.context
        )
        
        # Save to database
        result = await db.chat_sessions.insert_one(session.dict())
        
        return {
            "id": str(result.inserted_id),
            "title": session.title,
            "context": session.context,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "last_message": ""
        }
        
    except Exception as e:
        print(f"Error creating chat session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create chat session")

@chat_router.get("/sessions/{session_id}/messages")
async def get_chat_messages(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get messages for a chat session"""
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found")
        
        # Verify session belongs to user
        session = await db.chat_sessions.find_one({
            "_id": ObjectId(session_id),
            "user_id": user_id
        })
        
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        # Get messages
        messages = await db.chat_messages.find(
            {"session_id": session_id}
        ).sort("created_at", 1).to_list(length=100)
        
        # Format messages
        formatted_messages = []
        for message in messages:
            formatted_messages.append({
                "id": str(message["_id"]),
                "session_id": message["session_id"],
                "role": message["role"],
                "content": message["content"],
                "references": message.get("references", []),
                "created_at": message.get("created_at")
            })
        
        return formatted_messages
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching chat messages: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch chat messages")

@chat_router.post("/sessions/{session_id}/message")
async def send_chat_message(
    session_id: str,
    message_data: ChatMessageSend,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Send a message to a chat session and get AI response"""
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found")
        
        # Verify session belongs to user
        session = await db.chat_sessions.find_one({
            "_id": ObjectId(session_id),
            "user_id": user_id
        })
        
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        # Create user message
        user_message = ChatMessage(
            session_id=session_id,
            role="user",
            content=message_data.message
        )
        
        # Save user message
        user_result = await db.chat_messages.insert_one(user_message.dict())
        
        # Update session
        await db.chat_sessions.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {"updated_at": datetime.utcnow()}}
        )
        
        # Generate AI response (placeholder - integrate with Gemini API)
        ai_response = await generate_ai_response(message_data.message, session.get("context"))
        
        # Create assistant message
        assistant_message = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=ai_response["content"],
            references=ai_response.get("references", [])
        )
        
        # Save assistant message
        assistant_result = await db.chat_messages.insert_one(assistant_message.dict())
        
        return {
            "user_message": {
                "id": str(user_result.inserted_id),
                "session_id": session_id,
                "role": "user",
                "content": user_message.content,
                "references": [],
                "created_at": user_message.created_at
            },
            "assistant_message": {
                "id": str(assistant_result.inserted_id),
                "session_id": session_id,
                "role": "assistant",
                "content": assistant_message.content,
                "references": assistant_message.references or [],
                "created_at": assistant_message.created_at
            },
            "session": {
                "id": session_id,
                "title": session.get("title", "New Chat"),
                "updated_at": datetime.utcnow()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error sending chat message: {e}")
        raise HTTPException(status_code=500, detail="Failed to send chat message")

async def generate_ai_response(user_message: str, context: Optional[str] = None) -> Dict[str, Any]:
    """Generate AI response using Gemini API (placeholder implementation)"""
    try:
        # Placeholder response - integrate with actual Gemini API
        response_text = f"Thank you for your question about Indian law. This is a placeholder response to: '{user_message}'"
        
        if context:
            response_text += f"\n\nContext: {context}"
        
        # Simulate references for now
        references = []
        
        return {
            "content": response_text,
            "references": references
        }
        
    except Exception as e:
        print(f"Error generating AI response: {e}")
        return {
            "content": "I apologize, but I'm having trouble processing your request right now. Please try again later.",
            "references": []
        }