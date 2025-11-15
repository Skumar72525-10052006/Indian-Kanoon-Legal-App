"""
Fetch full document content from Indian Kanoon for summarization.
"""
from playwright.async_api import async_playwright, Browser, BrowserContext
from bs4 import BeautifulSoup
from typing import Optional
import asyncio
import re
from scraper import get_browser


async def fetch_document_content(document_url: str) -> Optional[str]:
    """
    Fetch the full text content of a legal document from Indian Kanoon.
    
    Args:
        document_url: Full URL to the document page
    
    Returns:
        Full text content of the document, or None if failed
    """
    browser, context = await get_browser()
    page = await context.new_page()
    
    try:
        # Navigate to the document page
        await page.goto(document_url, wait_until="domcontentloaded", timeout=30000)
        
        # Wait for content to load
        await asyncio.sleep(2)
        
        # Try to wait for main content
        try:
            await page.wait_for_selector(".judgments, .doc_content, .document, .content", timeout=10000)
        except:
            pass  # Continue even if selector not found
        
        # Get page content
        content = await page.content()
        soup = BeautifulSoup(content, "lxml")
        
        # Try multiple selectors to find document content
        document_text = ""
        
        # Strategy 1: Look for expanded_headline with fragments (primary method for Indian Kanoon)
        expanded_headline = soup.find("div", class_="expanded_headline")
        if expanded_headline:
            # Find all fragment divs within expanded_headline
            fragments = expanded_headline.find_all("div", class_="fragment")
            if fragments:
                for fragment in fragments:
                    # Get all paragraphs within fragment
                    paragraphs = fragment.find_all("p")
                    for p in paragraphs:
                        # Get text but preserve structure
                        text = p.get_text(separator=" ", strip=True)
                        if len(text) > 20:  # Skip very short paragraphs
                            document_text += text + "\n\n"
                    # Also get blockquotes if present
                    blockquotes = fragment.find_all("blockquote")
                    for bq in blockquotes:
                        text = bq.get_text(separator=" ", strip=True)
                        if len(text) > 20:
                            document_text += text + "\n\n"
        
        # Strategy 2: If no expanded_headline, look for judgment content
        if not document_text or len(document_text) < 200:
            judgment_divs = soup.find_all(["div", "section"], class_=lambda x: x and (
                "judgment" in x.lower() or 
                "doc_content" in x.lower() or 
                "document" in x.lower() or
                "content" in x.lower()
            ))
            
            if judgment_divs:
                for div in judgment_divs:
                    text = div.get_text(separator="\n", strip=True)
                    if len(text) > 100:  # Only use substantial content
                        document_text += text + "\n\n"
        
        # Strategy 3: If still no content, get all paragraph text
        if not document_text or len(document_text) < 200:
            paragraphs = soup.find_all("p")
            for p in paragraphs:
                text = p.get_text(strip=True)
                if len(text) > 20:  # Skip very short paragraphs
                    document_text += text + "\n\n"
        
        # Strategy 4: Get main content area as last resort
        if not document_text or len(document_text) < 200:
            main_content = soup.find("main") or soup.find("article") or soup.find("div", id="content")
            if main_content:
                document_text = main_content.get_text(separator="\n", strip=True)
        
        # Clean up the text
        if document_text:
            # Remove excessive whitespace
            lines = [line.strip() for line in document_text.split("\n") if line.strip()]
            document_text = "\n".join(lines)
            
            # Filter out ads and promotional content
            ad_keywords = [
                "virtual legal assistant",
                "query alert service",
                "premium member services",
                "premium membership",
                "free trial",
                "sign up",
                "subscribe",
                "advertisement",
                "advertise",
                "promotional",
                "marketing",
                "click here",
                "learn more",
                "get started",
                "join now",
                "become a member",
                "upgrade to premium",
                "try premium",
                "unlock premium features"
            ]
            
            # Remove lines containing ad keywords (case-insensitive)
            filtered_lines = []
            for line in document_text.split("\n"):
                line_lower = line.lower()
                # Skip lines that are primarily ads
                if any(keyword in line_lower for keyword in ad_keywords):
                    # Check if the line is mostly ad content (more than 50% ad keywords)
                    ad_word_count = sum(1 for keyword in ad_keywords if keyword in line_lower)
                    if ad_word_count > 0 and len(line.split()) < 20:  # Short lines with ad keywords are likely ads
                        continue
                filtered_lines.append(line)
            
            document_text = "\n".join(filtered_lines)
            
            # Remove common ad patterns
            # Remove email subscription prompts
            document_text = re.sub(r'[Ss]ubscribe\s+to\s+[^\n]+', '', document_text)
            # Remove "Click here" patterns
            document_text = re.sub(r'[Cc]lick\s+here[^\n]*', '', document_text)
            # Remove "Learn more" patterns
            document_text = re.sub(r'[Ll]earn\s+more[^\n]*', '', document_text)
            
            # Clean up multiple blank lines
            document_text = re.sub(r'\n{3,}', '\n\n', document_text)
            
            # Limit to reasonable length (to avoid token limits)
            if len(document_text) > 10000:
                document_text = document_text[:10000] + "... [Content truncated]"
            
            return document_text
        
        return None
        
    except Exception as e:
        print(f"Error fetching document content: {e}")
        return None
    finally:
        await page.close()

