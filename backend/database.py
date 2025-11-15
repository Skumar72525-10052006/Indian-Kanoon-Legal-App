"""
Database module for storing and retrieving search results.
Uses MongoDB for persistent storage.
"""
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, OperationFailure
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import json
import asyncio

# Load environment variables
load_dotenv()

# MongoDB configuration
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "indian_kanoon_cache")
COLLECTION_NAME = "search_results"
SUMMARIES_COLLECTION_NAME = "document_summaries"

CACHE_TTL_DAYS = 7  # Results expire after 7 days
SUMMARY_CACHE_TTL_DAYS = 30  # Summaries expire after 30 days (longer since they're expensive to generate)

# Global MongoDB client
_client: Optional[AsyncIOMotorClient] = None
_database = None
_collection = None


async def get_database():
    """Get or create MongoDB database connection with retry logic"""
    global _client, _database, _collection
    
    # Check if client exists and is still connected
    if _client is not None:
        try:
            # Quick health check
            await asyncio.wait_for(_client.admin.command('ping'), timeout=2.0)
            return _database, _collection
        except (asyncio.TimeoutError, ServerSelectionTimeoutError, ConnectionFailure):
            # Connection is dead, reset and reconnect
            print("⚠ MongoDB connection lost, reconnecting...")
            try:
                _client.close()
            except:
                pass
            _client = None
            _database = None
            _collection = None
    
    if _client is None:
        try:
            # Configure connection with better timeout and pool settings
            _client = AsyncIOMotorClient(
                MONGODB_URI,
                serverSelectionTimeoutMS=10000,  # Increased timeout
                connectTimeoutMS=10000,
                socketTimeoutMS=30000,  # 30 seconds for operations
                maxPoolSize=50,  # Connection pool size
                minPoolSize=10,  # Minimum connections
                maxIdleTimeMS=45000,  # Close idle connections after 45s
                retryWrites=True,
                retryReads=True
            )
            # Test connection
            await _client.admin.command('ping')
            _database = _client[DATABASE_NAME]
            _collection = _database[COLLECTION_NAME]
            
            # Create indexes for better performance
            # Check if indexes exist before creating to avoid conflicts
            existing_indexes = await _collection.list_indexes().to_list(length=None)
            index_names = [idx['name'] for idx in existing_indexes]
            
            if "query_1" not in index_names:
                await _collection.create_index("query", unique=True)
            
            # Handle TTL index - drop old one if exists and recreate with correct options
            if "created_at_1" in index_names:
                try:
                    await _collection.drop_index("created_at_1")
                except:
                    pass
            
            try:
                await _collection.create_index([("created_at", 1)], expireAfterSeconds=CACHE_TTL_DAYS * 24 * 3600)
            except Exception as e:
                # If index creation fails, try without TTL
                try:
                    await _collection.create_index("created_at")
                except:
                    pass
            
            print(f"✓ Connected to MongoDB: {DATABASE_NAME}")
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            print(f"✗ Failed to connect to MongoDB: {e}")
            _client = None
            _database = None
            _collection = None
            raise
    
    return _database, _collection


async def init_db():
    """Initialize the database connection"""
    try:
        await get_database()
    except Exception as e:
        print(f"Warning: MongoDB initialization failed: {e}")
        print("The app will continue but database features won't work.")


async def get_from_db(query: str) -> Optional[List[Dict]]:
    """
    Retrieve search results from MongoDB.
    Returns None if not found or expired.
    """
    try:
        _, collection = await get_database()
        
        # Find document by query
        document = await collection.find_one({"query": query})
        
        if document:
            # Check if result is expired (MongoDB TTL index should handle this, but double-check)
            created_at = document.get("created_at")
            if created_at:
                age = datetime.now() - created_at
                if age > timedelta(days=CACHE_TTL_DAYS):
                    # Expired, delete it
                    await collection.delete_one({"query": query})
                    return None
            
            # Update access count and last accessed time
            await collection.update_one(
                {"query": query},
                {
                    "$inc": {"access_count": 1},
                    "$set": {"updated_at": datetime.now()}
                }
            )
            
            # Return results
            return document.get("results", [])
        
        return None
    except (ConnectionFailure, ServerSelectionTimeoutError, OperationFailure) as e:
        print(f"Error reading from MongoDB: {e}")
        # Reset connection on error
        global _client
        if _client:
            try:
                _client.close()
            except:
                pass
            _client = None
        return None
    except Exception as e:
        print(f"Error reading from MongoDB: {e}")
        return None


async def save_to_db(query: str, results: List[Dict]):
    """
    Save search results to MongoDB.
    Updates if query already exists.
    """
    try:
        _, collection = await get_database()
        
        # Check if document exists
        existing_doc = await collection.find_one({"query": query})
        
        if existing_doc:
            # Update existing document
            await collection.update_one(
                {"query": query},
                {
                    "$set": {
                        "results": results,
                        "updated_at": datetime.now()
                    },
                    "$inc": {"access_count": 1}
                }
            )
        else:
            # Insert new document
            document = {
                "query": query,
                "results": results,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "access_count": 1
            }
            await collection.insert_one(document)
    except (ConnectionFailure, ServerSelectionTimeoutError, OperationFailure) as e:
        print(f"Error saving to MongoDB: {e}")
        # Reset connection on error
        global _client
        if _client:
            try:
                _client.close()
            except:
                pass
            _client = None
    except Exception as e:
        print(f"Error saving to MongoDB: {e}")


async def cleanup_old_results():
    """Remove expired results from MongoDB (TTL index handles this automatically, but manual cleanup for safety)"""
    try:
        _, collection = await get_database()
        cutoff_date = datetime.now() - timedelta(days=CACHE_TTL_DAYS)
        
        result = await collection.delete_many({"created_at": {"$lt": cutoff_date}})
        if result.deleted_count > 0:
            print(f"Cleaned up {result.deleted_count} expired results from MongoDB")
    except Exception as e:
        print(f"Error cleaning up MongoDB: {e}")


async def get_db_stats() -> Dict:
    """Get MongoDB database statistics"""
    try:
        _, collection = await get_database()
        
        total_queries = await collection.count_documents({})
        
        # Get total access count
        pipeline = [
            {"$group": {"_id": None, "total_access": {"$sum": "$access_count"}}}
        ]
        cursor = collection.aggregate(pipeline)
        result = await cursor.to_list(length=1)
        total_access = result[0]["total_access"] if result else 0
        
        return {
            "total_queries": total_queries,
            "total_accesses": total_access,
            "database": DATABASE_NAME,
            "collection": COLLECTION_NAME
        }
    except Exception as e:
        print(f"Error getting MongoDB stats: {e}")
        return {
            "total_queries": 0,
            "total_accesses": 0,
            "database": DATABASE_NAME,
            "collection": COLLECTION_NAME,
            "error": str(e)
        }


async def get_summary_from_db(doc_id: str) -> Optional[Dict]:
    """
    Retrieve document summary from MongoDB.
    Returns None if not found or expired.
    
    Args:
        doc_id: Document ID (unique identifier)
    
    Returns:
        Dictionary with citizen_summary, lawyer_summary, title, etc. or None
    """
    try:
        database, _ = await get_database()
        summaries_collection = database[SUMMARIES_COLLECTION_NAME]
        
        # Find document by doc_id
        document = await summaries_collection.find_one({"doc_id": doc_id})
        
        if document:
            # Check if result is expired
            created_at = document.get("created_at")
            if created_at:
                age = datetime.now() - created_at
                if age > timedelta(days=SUMMARY_CACHE_TTL_DAYS):
                    # Expired, delete it
                    await summaries_collection.delete_one({"doc_id": doc_id})
                    return None
            
            # Update access count and last accessed time
            await summaries_collection.update_one(
                {"doc_id": doc_id},
                {
                    "$inc": {"access_count": 1},
                    "$set": {"updated_at": datetime.now()}
                }
            )
            
            # Return summary data
            return {
                "citizen_summary": document.get("citizen_summary", ""),
                "lawyer_summary": document.get("lawyer_summary", ""),
                "title": document.get("title", ""),
                "document_url": document.get("document_url", ""),
                "content_length": document.get("content_length", 0),
                "cached": True
            }
        
        return None
    except (ConnectionFailure, ServerSelectionTimeoutError, OperationFailure) as e:
        print(f"Error reading summary from MongoDB: {e}")
        # Reset connection on error
        global _client
        if _client:
            try:
                _client.close()
            except:
                pass
            _client = None
        return None
    except Exception as e:
        print(f"Error reading summary from MongoDB: {e}")
        return None


async def save_summary_to_db(doc_id: str, title: str, document_url: str, content_length: int, 
                             citizen_summary: str, lawyer_summary: str):
    """
    Save document summary to MongoDB.
    Updates if doc_id already exists.
    
    Args:
        doc_id: Document ID (unique identifier)
        title: Document title
        document_url: Full URL to the document
        content_length: Length of original content
        citizen_summary: Citizen-friendly summary
        lawyer_summary: Lawyer version summary
    """
    try:
        database, _ = await get_database()
        summaries_collection = database[SUMMARIES_COLLECTION_NAME]
        
        # Create index on doc_id if it doesn't exist
        existing_indexes = await summaries_collection.list_indexes().to_list(length=None)
        index_names = [idx['name'] for idx in existing_indexes]
        
        if "doc_id_1" not in index_names:
            await summaries_collection.create_index("doc_id", unique=True)
        
        # Handle TTL index for summaries
        if "created_at_1" in index_names:
            try:
                await summaries_collection.drop_index("created_at_1")
            except:
                pass
        
        try:
            await summaries_collection.create_index(
                [("created_at", 1)], 
                expireAfterSeconds=SUMMARY_CACHE_TTL_DAYS * 24 * 3600
            )
        except Exception as e:
            try:
                await summaries_collection.create_index("created_at")
            except:
                pass
        
        # Check if document exists
        existing_doc = await summaries_collection.find_one({"doc_id": doc_id})
        
        if existing_doc:
            # Update existing document
            await summaries_collection.update_one(
                {"doc_id": doc_id},
                {
                    "$set": {
                        "title": title,
                        "document_url": document_url,
                        "content_length": content_length,
                        "citizen_summary": citizen_summary,
                        "lawyer_summary": lawyer_summary,
                        "updated_at": datetime.now()
                    },
                    "$inc": {"access_count": 1}
                }
            )
        else:
            # Insert new document
            document = {
                "doc_id": doc_id,
                "title": title,
                "document_url": document_url,
                "content_length": content_length,
                "citizen_summary": citizen_summary,
                "lawyer_summary": lawyer_summary,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "access_count": 1
            }
            await summaries_collection.insert_one(document)
            print(f"✓ Saved summary to database for doc_id: {doc_id}")
    except (ConnectionFailure, ServerSelectionTimeoutError, OperationFailure) as e:
        print(f"Error saving summary to MongoDB: {e}")
        # Reset connection on error
        global _client
        if _client:
            try:
                _client.close()
            except:
                pass
            _client = None
    except Exception as e:
        print(f"Error saving summary to MongoDB: {e}")


async def get_summary_stats() -> Dict:
    """Get summary collection statistics"""
    try:
        database, _ = await get_database()
        summaries_collection = database[SUMMARIES_COLLECTION_NAME]
        
        total_summaries = await summaries_collection.count_documents({})
        
        # Get total access count
        pipeline = [
            {"$group": {"_id": None, "total_access": {"$sum": "$access_count"}}}
        ]
        cursor = summaries_collection.aggregate(pipeline)
        result = await cursor.to_list(length=1)
        total_access = result[0]["total_access"] if result else 0
        
        return {
            "total_summaries": total_summaries,
            "total_accesses": total_access,
            "collection": SUMMARIES_COLLECTION_NAME
        }
    except Exception as e:
        print(f"Error getting summary stats: {e}")
        return {
            "total_summaries": 0,
            "total_accesses": 0,
            "collection": SUMMARIES_COLLECTION_NAME,
            "error": str(e)
        }


async def close_connection():
    """Close MongoDB connection gracefully"""
    global _client, _database, _collection
    if _client:
        try:
            # Wait a bit for any pending operations to complete
            await asyncio.sleep(0.5)
            # Close the client (this will close all connections in the pool)
            _client.close()
            # Wait for connections to close
            await asyncio.sleep(0.5)
            _client = None
            _database = None
            _collection = None
            print("MongoDB connection closed")
        except Exception as e:
            print(f"Error closing MongoDB connection: {e}")
            # Force close even if there's an error
            try:
                _client.close()
            except:
                pass
            _client = None
            _database = None
            _collection = None
