from fastapi import FastAPI, Query, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Optional
import asyncio
import time
from scraper import scrape_indian_kanoon
from database import (
    init_db, get_from_db, save_to_db, cleanup_old_results, close_connection,
    get_summary_from_db, save_summary_to_db, get_summary_stats
)
from document_fetcher import fetch_document_content
from summarizer import summarize_document
from rate_limiter import SlidingWindowRateLimiter
from auth_routes import router as auth_router, get_current_user
from user_db import init_user_collections

# Simple in-memory cache (fastest - for current session)
cache = {}
CACHE_TTL = 3600  # Cache for 1 hour (in-memory cache)

# Rate limiters (simple in-memory sliding window)
global_rate_limiter = SlidingWindowRateLimiter(
    limit=100,
    window_seconds=60,
    identifier="global",
    error_message="Too many requests from your IP. Please wait and try again.",
)
search_rate_limiter = SlidingWindowRateLimiter(
    limit=20,
    window_seconds=60,
    identifier="search",
    error_message="Too many search requests. Please slow down.",
)
summarize_rate_limiter = SlidingWindowRateLimiter(
    limit=6,
    window_seconds=60,
    identifier="summarize",
    error_message="Too many summary requests. Please wait before retrying.",
)

# Lifespan event handler (replaces deprecated on_event)
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown"""
    # Startup
    await init_db()
    await init_user_collections()
    await cleanup_old_results()
    print("✓ Application started")
    yield
    # Shutdown
    await close_connection()
    print("✓ Application shutdown")

app = FastAPI(
    title="Indian Kanoon Scraper API",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include authentication routes
app.include_router(auth_router)


@app.get("/")
async def root(
    request: Request,
    _: None = Depends(global_rate_limiter),
):
    return {"message": "Indian Kanoon Scraper API", "status": "running"}


@app.get("/stats")
async def get_stats(
    request: Request,
    _: None = Depends(global_rate_limiter),
):
    """Get cache and database statistics"""
    from database import get_db_stats
    db_stats = await get_db_stats()
    summary_stats = await get_summary_stats()
    return {
        "memory_cache_size": len(cache),
        "database": db_stats,
        "summaries": summary_stats
    }


@app.get("/search")
async def search(
    request: Request,
    forminput: str = Query(..., description="Search query (spaces will be replaced with +)"),
    pagenum: int = Query(1, ge=1, description="Page number (starts from 1)"),
    _: None = Depends(global_rate_limiter),
    __: None = Depends(search_rate_limiter),
):
    """
    Search Indian Kanoon for legal documents.

    - **forminput**: The search query (e.g., "article 370")
    - **pagenum**: Page number (1-indexed, defaults to 1)
    - Returns: List of search results with title, headline, and metadata, plus pagination info
    """
    if not forminput or not forminput.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty")

    try:
        # Normalize query: replace spaces with + (handles both cases)
        query = forminput.strip().replace(" ", "+")
        # Convert pagenum to 0-indexed for internal use (URL is 1-indexed)
        page_index = pagenum - 1
        cache_key = f"search:{query}:page:{pagenum}"

        # Tier 1: Check in-memory cache (fastest - < 1ms)
        if cache_key in cache:
            cached_data, cached_time = cache[cache_key]
            if time.time() - cached_time < CACHE_TTL:
                return cached_data  # Already includes pagination info

        # Tier 2: Check database (fast - ~10-50ms)
        # Note: For pagination, we'll cache per page
        db_key = f"{query}:page:{pagenum}"
        db_results = await get_from_db(db_key)
        if db_results:
            # Store in memory cache for next time
            cache[cache_key] = (db_results, time.time())
            return db_results

        # Tier 3: Scrape with Playwright (slowest - 2-5 seconds)
        print(f"Cache miss for '{query}' page {pagenum}, scraping with Playwright...")
        result_data = await scrape_indian_kanoon(query, page_index)

        # Store in both cache and database
        cache[cache_key] = (result_data, time.time())
        await save_to_db(db_key, result_data)

        # Clean old cache entries (simple cleanup)
        current_time = time.time()
        keys_to_delete = [k for k, (_, t) in cache.items() if current_time - t > CACHE_TTL]
        for k in keys_to_delete:
            del cache[k]

        return result_data
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error in search endpoint: {error_trace}")  # Log to console
        raise HTTPException(
            status_code=500,
            detail=f"Error scraping data: {str(e)}"
        )


@app.get("/summarize")
async def summarize(
    request: Request,
    document_url: str = Query(None, description="Full URL of the document to summarize"),
    doc_id: str = Query(None, description="Document ID (alternative to document_url)"),
    query: str = Query("", description="Search query for constructing docfragment URL"),
    title: str = Query("", description="Optional title of the document"),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(global_rate_limiter),
    __: None = Depends(summarize_rate_limiter),
):
    """
    Fetch and summarize a legal document using Gemini API.
    Returns both citizen-friendly and lawyer versions.

    **Authentication Required**: User must be logged in to access AI summaries.

    - **document_url**: Full URL to the Indian Kanoon document page (optional if doc_id provided)
    - **doc_id**: Document ID (alternative to document_url)
    - **query**: Search query for constructing docfragment URL (required if doc_id provided)
    - **title**: Optional title of the document for context
    - Returns: Dictionary with 'citizen_summary' and 'lawyer_summary'
    """
    # Construct document URL if doc_id is provided
    if doc_id and not document_url:
        if not query:
            raise HTTPException(status_code=400, detail="Query parameter is required when using doc_id")
        from urllib.parse import quote
        encoded_query = quote(query.replace("+", " "))
        # Use docfragment URL format: /docfragment/{docid}/?formInput={query}
        document_url = f"https://indiankanoon.org/docfragment/{doc_id}/?formInput={encoded_query}"
    elif not document_url:
        raise HTTPException(status_code=400, detail="Either document_url or doc_id must be provided")

    # Extract doc_id from URL if not provided
    if not doc_id and document_url:
        import re
        match = re.search(r'/(?:docfragment|doc)/(\d+)', document_url)
        if match:
            doc_id = match.group(1)


    # Determine which summary to return based on the logged-in user's role
    user_type = current_user.get("user_type", "citizen")

    try:
        # Tier 1: Check database cache for summary (fastest - ~10-50ms)
        if doc_id:
            cached_summary = await get_summary_from_db(doc_id)
            if cached_summary:
                print(f"✓ Summary found in database cache for doc_id: {doc_id}")

                # Raw summaries from DB (may be missing for some older entries)
                db_citizen_summary = cached_summary.get("citizen_summary", "") or ""
                db_lawyer_summary = cached_summary.get("lawyer_summary", "") or ""

                # Role-aware selection with graceful fallback:
                # - Citizens see citizen summary if available, otherwise lawyer summary if that exists
                # - Lawyers see lawyer summary if available, otherwise citizen summary if that exists
                if user_type == "lawyer":
                    lawyer_summary = db_lawyer_summary or db_citizen_summary
                    citizen_summary = ""
                else:  # default to citizen behaviour
                    citizen_summary = db_citizen_summary or db_lawyer_summary
                    lawyer_summary = ""

                return {
                    "success": True,
                    "title": cached_summary.get("title", title),
                    "document_url": cached_summary.get("document_url", document_url),
                    "content_length": cached_summary.get("content_length", 0),
                    "citizen_summary": citizen_summary,
                    "lawyer_summary": lawyer_summary,
                    "cached": True,
                    "error": None
                }

        # Tier 2: Fetch document content and generate summaries (slowest - 5-15 seconds)
        print(f"Cache miss for doc_id: {doc_id or 'N/A'}, fetching and generating summaries...")
        print(f"Fetching document content from: {document_url}")
        document_content = await fetch_document_content(document_url)

        if not document_content:
            raise HTTPException(
                status_code=404,
                detail="Could not fetch document content. The document may not be accessible."
            )

        if len(document_content) < 50:
            raise HTTPException(
                status_code=400,
                detail="Document content is too short or empty."
            )

        print(f"Document content fetched ({len(document_content)} characters). Generating summaries...")

        # Generate summaries using Gemini
        summaries = await summarize_document(document_content, title)

        raw_citizen_summary = summaries.get("citizen_summary", "")
        raw_lawyer_summary = summaries.get("lawyer_summary", "")

        # Prepare summaries to return based on user role with graceful fallback
        if user_type == "lawyer":
            lawyer_summary = raw_lawyer_summary or raw_citizen_summary
            citizen_summary = ""
        else:  # default to citizen behaviour
            citizen_summary = raw_citizen_summary or raw_lawyer_summary
            lawyer_summary = ""

        # Check for errors in summary generation
        if summaries.get("error"):
            return {
                "success": False,
                "title": title,
                "document_url": document_url,
                "content_length": len(document_content),
                "citizen_summary": citizen_summary,
                "lawyer_summary": lawyer_summary,
                "error": summaries.get("error"),
                "cached": False
            }

        # Store full summaries in database for future use
        if doc_id:
            try:
                await save_summary_to_db(
                    doc_id=doc_id,
                    title=title,
                    document_url=document_url,
                    content_length=len(document_content),
                    citizen_summary=raw_citizen_summary,
                    lawyer_summary=raw_lawyer_summary
                )
            except Exception as save_error:
                print(f"Warning: Failed to save summary to database: {save_error}")
                # Continue even if save fails

        return {
            "success": True,
            "title": title,
            "document_url": document_url,
            "content_length": len(document_content),
            "citizen_summary": citizen_summary,
            "lawyer_summary": lawyer_summary,
            "error": None,
            "cached": False
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error in summarize endpoint: {error_trace}")
        raise HTTPException(
            status_code=500,
            detail=f"Error summarizing document: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

