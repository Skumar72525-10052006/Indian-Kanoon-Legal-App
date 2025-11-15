"""
Gemini API integration for summarizing legal documents.
Provides both citizen-friendly and lawyer versions of summaries.
"""
import os
import re
import asyncio
from typing import Dict, Optional
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Initialize Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("⚠ Warning: GEMINI_API_KEY not found in environment variables")

# Default models
# Note: Free tier allows 2 requests per minute per model
# Using flash for both avoids quota issues. For paid tier, you can use pro for lawyer summaries.
DEFAULT_CITIZEN_MODEL = "models/gemini-2.5-flash"
DEFAULT_LAWYER_MODEL = "models/gemini-2.5-flash"  # Changed to flash to avoid free tier quota issues

GEMINI_CITIZEN_MODEL = os.getenv("GEMINI_CITIZEN_MODEL", DEFAULT_CITIZEN_MODEL)
GEMINI_LAWYER_MODEL = os.getenv("GEMINI_LAWYER_MODEL", DEFAULT_LAWYER_MODEL)


async def summarize_document(content: str, title: str = "") -> Dict[str, str]:
    """
    Summarize a legal document using Gemini API.
    Returns both citizen-friendly and lawyer versions.
    
    Args:
        content: The full text content of the legal document
        title: Optional title of the document
    
    Returns:
        Dictionary with 'citizen_summary' and 'lawyer_summary' keys
    """
    if not GEMINI_API_KEY:
        return {
            "citizen_summary": "Error: Gemini API key not configured. Please set GEMINI_API_KEY in your .env file.",
            "lawyer_summary": "Error: Gemini API key not configured. Please set GEMINI_API_KEY in your .env file.",
            "error": "API key not configured"
        }
    
    try:
        # Limit content to avoid token limits (keep content concise for faster responses)
        content_limit = min(len(content), 8000)
        content_to_summarize = content[:content_limit]
        
        # Prepare the prompt for citizen-friendly summary
        citizen_prompt = f"""You are a helpful assistant explaining Indian legal documents to ordinary citizens with no legal background.

Document Title: {title}

Document Content:
{content_to_summarize}

Please provide a clear, comprehensive summary of this legal document that:
1. Uses simple, everyday language - NO legal jargon or technical terms
2. Explains what happened in the case in plain, understandable terms
3. Explains what the court decided and why, in simple language
4. Highlights the key points that matter to ordinary people
5. If sections like IPC 302, 323, 324 are mentioned, explain what they mean in simple terms
6. Make it easy to understand for someone without any legal training
7. Keep it between 300-500 words
8. Use plain text only - NO markdown formatting, NO asterisks, NO bold/italic symbols
9. Use simple bullet points with dashes (-) or numbers, not markdown symbols
10. IGNORE and EXCLUDE any advertisements, promotional content, or service offers from the document
11. Focus ONLY on the actual legal content, case details, and court decisions

Write the summary as if you're explaining to a friend who has no legal knowledge. Use plain text formatting only:

Summary:"""

        # Prepare the prompt for lawyer summary
        lawyer_prompt = f"""You are a legal expert analyzing an Indian legal document for professional use.

Document Title: {title}

Document Content:
{content_to_summarize}

Please provide a comprehensive legal summary that:
1. Uses proper legal terminology, jargon, and technical language
2. Identifies key legal principles, precedents, and case citations
3. Analyzes the legal implications, reasoning, and significance
4. References relevant IPC sections, articles, or case law with proper citations
5. Discusses the legal framework, statutory provisions, and judicial reasoning
6. Provides professional legal analysis suitable for lawyers and legal professionals
7. Keep it between 400-600 words
8. Use plain text only - NO markdown formatting, NO asterisks, NO bold/italic symbols
9. Use simple formatting with dashes (-) or numbers for lists, not markdown symbols
10. IGNORE and EXCLUDE any advertisements, promotional content, or service offers from the document
11. Focus ONLY on the actual legal content, case details, and court decisions

Write the summary as a professional legal brief. Use plain text formatting only:

Summary:"""

        citizen_model = genai.GenerativeModel(GEMINI_CITIZEN_MODEL)
        lawyer_model = genai.GenerativeModel(GEMINI_LAWYER_MODEL)

        # Generate both summaries with retry logic
        async def generate_with_retry(model, prompt, max_retries=4, initial_delay=3, timeout=120):
            """Generate content with exponential backoff retry logic and timeout."""
            last_error = None
            for attempt in range(max_retries):
                try:
                    # Configure generation with timeout
                    generation_config = {
                        "temperature": 0.7,
                        "top_p": 0.8,
                        "top_k": 40,
                    }
                    # Run synchronous generate_content in thread pool with timeout
                    response = await asyncio.wait_for(
                        asyncio.to_thread(
                            model.generate_content,
                            prompt,
                            generation_config=generation_config
                        ),
                        timeout=timeout
                    )
                    return response
                except Exception as e:
                    last_error = e
                    error_str = str(e).lower()
                    
                    # Check if it's a retryable error
                    is_retryable = (
                        isinstance(e, asyncio.TimeoutError) or
                        "503" in error_str or 
                        "504" in error_str or
                        "overloaded" in error_str or 
                        "timeout" in error_str or
                        "timed out" in error_str or
                        "429" in error_str or  # Rate limit
                        "quota" in error_str or  # Quota exceeded
                        "500" in error_str or  # Server error
                        "502" in error_str     # Bad gateway
                    )
                    
                    if not is_retryable or attempt == max_retries - 1:
                        raise
                    
                    # Calculate delay based on error type
                    if "429" in error_str or "quota" in error_str:
                        # For quota/rate limit errors, try to extract suggested retry delay
                        delay = 15  # Default 15 seconds for quota errors
                        try:
                            # Try to extract "Please retry in X.XXs" from error message
                            retry_match = re.search(r'retry in ([\d.]+)s', str(e), re.IGNORECASE)
                            if retry_match:
                                extracted_delay = float(retry_match.group(1))
                                # Add buffer (1.2x) to be safe
                                delay = max(15, int(extracted_delay * 1.2))
                                print(f"📊 Extracted retry delay: {extracted_delay}s, using {delay}s with buffer")
                        except:
                            pass  # Use default delay if extraction fails
                    elif "503" in error_str or "504" in error_str or "overloaded" in error_str or "timed out" in error_str:
                        # For overloaded errors, use longer delays: 5s, 10s, 20s, 40s
                        delay = initial_delay * (2 ** attempt) * 2  # Double the exponential backoff
                        delay = min(delay, 60)  # Cap at 60 seconds
                        print(f"⚠ Service overloaded, using longer delay: {delay}s")
                    else:
                        # Exponential backoff for other errors: 3s, 6s, 12s, 24s
                        delay = initial_delay * (2 ** attempt)
                    
                    print(f"⚠ Retry attempt {attempt + 1}/{max_retries} after {delay}s delay. Error: {str(e)[:100]}")
                    await asyncio.sleep(delay)
            
            # If all retries failed
            raise last_error
        
        # Generate summaries with retry logic
        # For free tier (2 requests/min per model), generate sequentially to avoid quota issues
        # For paid tier, can generate in parallel
        print("Generating summaries...")
        
        # Check if using free tier models (both flash) - can try parallel
        # If using pro model, generate sequentially to respect per-model limits
        use_parallel = (GEMINI_CITIZEN_MODEL == GEMINI_LAWYER_MODEL and "flash" in GEMINI_CITIZEN_MODEL.lower())
        
        if use_parallel:
            try:
                # Try to generate both in parallel for speed (only if same model)
                print("Generating both summaries in parallel...")
                citizen_task = generate_with_retry(citizen_model, citizen_prompt)
                lawyer_task = generate_with_retry(lawyer_model, lawyer_prompt)
                citizen_response, lawyer_response = await asyncio.gather(
                    citizen_task, 
                    lawyer_task,
                    return_exceptions=True
                )
                
                # Check for exceptions
                if isinstance(citizen_response, Exception):
                    raise citizen_response
                if isinstance(lawyer_response, Exception):
                    raise lawyer_response
            except Exception as e:
                # If parallel fails, try sequential as fallback
                print("⚠ Parallel generation failed, trying sequential...")
                use_parallel = False
        
        if not use_parallel:
            # Generate sequentially to respect rate limits (especially for free tier)
            print("Generating citizen-friendly summary...")
            try:
                citizen_response = await generate_with_retry(citizen_model, citizen_prompt)
            except Exception as e:
                error_str = str(e).lower()
                # If citizen summary fails with timeout/overload, try with flash model as fallback
                if ("timeout" in error_str or "timed out" in error_str or "503" in error_str or "504" in error_str or "overloaded" in error_str) and "flash" not in GEMINI_CITIZEN_MODEL.lower():
                    print("⚠ Citizen summary failed, trying with flash model as fallback...")
                    fallback_model = genai.GenerativeModel("models/gemini-2.5-flash")
                    citizen_response = await generate_with_retry(fallback_model, citizen_prompt, max_retries=2, timeout=90)
                else:
                    raise
            
            # Add delay between requests for free tier to avoid quota issues
            # Free tier: 2 requests per minute per model = 30 seconds between requests
            if "pro" in GEMINI_LAWYER_MODEL.lower() or "pro" in GEMINI_CITIZEN_MODEL.lower():
                print("⏳ Waiting 30 seconds before generating lawyer summary (free tier rate limit)...")
                await asyncio.sleep(30)
            
            print("Generating lawyer summary...")
            try:
                lawyer_response = await generate_with_retry(lawyer_model, lawyer_prompt)
            except Exception as e:
                error_str = str(e).lower()
                # If lawyer summary fails with timeout/overload, try with flash model as fallback
                if ("timeout" in error_str or "timed out" in error_str or "503" in error_str or "504" in error_str or "overloaded" in error_str) and "flash" not in GEMINI_LAWYER_MODEL.lower():
                    print("⚠ Lawyer summary failed, trying with flash model as fallback...")
                    fallback_model = genai.GenerativeModel("models/gemini-2.5-flash")
                    lawyer_response = await generate_with_retry(fallback_model, lawyer_prompt, max_retries=2, timeout=90)
                else:
                    raise
    
        # Clean up markdown formatting from summaries
        def clean_markdown(text: str) -> str:
            """Remove markdown formatting symbols from text."""
            # Remove bold/italic markdown (**, __, *)
            text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **bold** -> bold
            text = re.sub(r'__([^_]+)__', r'\1', text)  # __bold__ -> bold
            text = re.sub(r'\*([^*]+)\*', r'\1', text)  # *italic* -> italic
            text = re.sub(r'_([^_]+)_', r'\1', text)  # _italic_ -> italic
            # Remove markdown headers (# ## ###)
            text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
            # Remove markdown links [text](url) -> text
            text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
            # Remove markdown code blocks
            text = re.sub(r'```[^`]*```', '', text, flags=re.DOTALL)
            text = re.sub(r'`([^`]+)`', r'\1', text)  # `code` -> code
            # Remove excessive asterisks (common in Gemini output)
            text = re.sub(r'\*{2,}', '', text)  # Multiple asterisks
            # Clean up multiple spaces
            text = re.sub(r' {2,}', ' ', text)
            # Clean up multiple newlines
            text = re.sub(r'\n{3,}', '\n\n', text)
            return text.strip()
        
        citizen_summary = clean_markdown(citizen_response.text.strip())
        lawyer_summary = clean_markdown(lawyer_response.text.strip())
    
        return {
            "citizen_summary": citizen_summary,
            "lawyer_summary": lawyer_summary,
            "error": None
        }
        
    except Exception as e:
        error_str = str(e).lower()
        error_msg = f"Error generating summary: {str(e)}"
        print(error_msg)
        
        # Provide user-friendly error messages
        if isinstance(e, asyncio.TimeoutError) or "timeout" in error_str:
            user_msg = "The request took too long to process. This may be due to high demand. Please try again in a few moments."
        elif "503" in error_str or "504" in error_str or "overloaded" in error_str or "timed out" in error_str:
            user_msg = "The AI service is currently overloaded or timed out. Please wait 20-30 seconds and try again."
        elif "429" in error_str or "quota" in error_str or "rate limit" in error_str:
            # Extract retry time if available
            retry_time = "30-60 seconds"
            try:
                retry_match = re.search(r'retry in ([\d.]+)s', str(e), re.IGNORECASE)
                if retry_match:
                    retry_seconds = float(retry_match.group(1))
                    retry_time = f"{int(retry_seconds)} seconds"
            except:
                pass
            user_msg = f"API quota/rate limit exceeded. The free tier allows 2 requests per minute per model. Please wait {retry_time} and try again, or consider using the same model for both summaries to reduce quota usage."
        elif "api key" in error_str or "authentication" in error_str:
            user_msg = "API authentication error. Please check your API key configuration."
        else:
            user_msg = "An error occurred while generating the summary. Please try again later."
        
        return {
            "citizen_summary": user_msg,
            "lawyer_summary": user_msg,
            "error": str(e)
        }

