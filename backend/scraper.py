from playwright.async_api import async_playwright, Browser, BrowserContext
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import re
import asyncio
import random

# Global browser instance for reuse
_browser: Optional[Browser] = None
_browser_context: Optional[BrowserContext] = None
_playwright_instance = None


def clean_title(title: str) -> str:
    """
    Clean up title text by fixing spacing issues.
    Handles cases like:
    - "Article370in" -> "Article 370 in"
    - "TheIndianPenalCode" -> "The Indian Penal Code"
    - "Section360" -> "Section 360"
    """
    if not title:
        return title
    
    # Step 1: Add space between lowercase letter and uppercase letter (e.g., "theIndian" -> "the Indian")
    title = re.sub(r'([a-z])([A-Z])', r'\1 \2', title)
    
    # Step 2: Add space between uppercase letter followed by uppercase then lowercase
    # This handles "TheIndianPenalCode" -> "The Indian Penal Code"
    # Pattern: uppercase letter, then uppercase letter followed by lowercase (start of new word)
    title = re.sub(r'([A-Z])([A-Z][a-z])', r'\1 \2', title)
    
    # Step 3: Add space between letter and number (e.g., "Article370" -> "Article 370")
    title = re.sub(r'([a-zA-Z])(\d+)', r'\1 \2', title)
    
    # Step 4: Add space between number and any lowercase word (handles "370in" -> "370 in")
    title = re.sub(r'(\d+)([a-z]+)(?=\s|[A-Z]|$)', r'\1 \2', title)
    
    # Step 5: Add space between number and uppercase letter (e.g., "370Constitution" -> "370 Constitution")
    title = re.sub(r'(\d+)([A-Z])', r'\1 \2', title)
    
    # Step 6: Clean up multiple spaces
    title = re.sub(r'\s+', ' ', title)
    
    return title.strip()


# Pool of realistic user agents to rotate
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
]


def parse_results(result_divs) -> List[Dict]:
    """Parse result divs into structured data"""
    results = []
    
    for result_div in result_divs:
        try:
            # Extract title and link
            title_elem = result_div.find("div", class_="result_title")
            title_link = None
            title_text = ""
            
            if title_elem:
                title_link_elem = title_elem.find("a")
                if title_link_elem:
                    title_link = title_link_elem.get("href", "")
                    title_text = title_link_elem.get_text(strip=True)
                    # Clean up the title to fix spacing issues
                    title_text = clean_title(title_text)
            
            # Extract headline
            headline_elem = result_div.find("div", class_="headline")
            headline_text = ""
            if headline_elem:
                # Get HTML and preserve <b> tags for highlighting, but clean up the structure
                inner_content = headline_elem.decode_contents()
                headline_text = inner_content.strip()
            
            # Extract metadata from hlbottom
            hlbottom_elem = result_div.find("div", class_="hlbottom")
            doc_source = ""
            cites = ""
            cited_by = ""
            author = ""
            full_doc_link = ""
            
            if hlbottom_elem:
                # Document source
                docsource_elem = hlbottom_elem.find("span", class_="docsource")
                if docsource_elem:
                    doc_source = docsource_elem.get_text(strip=True)
                
                # Cites
                cites_elem = hlbottom_elem.find("a", class_="cite_tag", href=lambda x: x and "cites:" in x)
                if cites_elem:
                    cites = cites_elem.get_text(strip=True)
                
                # Cited by
                cited_by_elem = hlbottom_elem.find("a", class_="cite_tag", href=lambda x: x and "citedby:" in x)
                if cited_by_elem:
                    cited_by = cited_by_elem.get_text(strip=True)
                
                # Author
                author_elem = hlbottom_elem.find("a", class_="cite_tag", href=lambda x: x and "authorid:" in x)
                if author_elem:
                    author = author_elem.get_text(strip=True)
                
                # Full document link
                full_doc_elem = hlbottom_elem.find("a", class_="cite_tag", href=lambda x: x and "/doc/" in x)
                if full_doc_elem:
                    full_doc_link = full_doc_elem.get("href", "")
            
            # Extract doc ID from links
            doc_id = None
            if title_link:
                # Extract doc ID from title_link (format: /docfragment/{docid}/ or /doc/{docid}/)
                import re
                match = re.search(r'/(?:docfragment|doc)/(\d+)', title_link)
                if match:
                    doc_id = match.group(1)
            elif full_doc_link:
                # Try to extract from full_doc_link
                import re
                match = re.search(r'/(?:docfragment|doc)/(\d+)', full_doc_link)
                if match:
                    doc_id = match.group(1)
            
            # Only add if we have at least a title
            if title_text:
                result_data = {
                    "title": title_text,
                    "title_link": f"https://indiankanoon.org{title_link}" if title_link else "",
                    "headline": headline_text,
                    "doc_source": doc_source,
                    "cites": cites,
                    "cited_by": cited_by,
                    "author": author,
                    "full_doc_link": f"https://indiankanoon.org{full_doc_link}" if full_doc_link else "",
                    "doc_id": doc_id  # Add doc ID for easier document fetching
                }
                results.append(result_data)
        
        except Exception as e:
            # Skip malformed results but continue processing
            print(f"Error parsing result: {e}")
            continue
    
    return results


def extract_results_count_from_soup(soup) -> str:
    """
    Extract the exact results count text from the page HTML.
    Looks for patterns like "1 - 10 of 17014 (0.02 seconds)"
    """
    try:
        import re
        
        # Get all text from the page
        page_text = soup.get_text()
        
        # Pattern: "1 - 10 of 17014" or "1-10 of 17014" with optional time
        patterns = [
            r'\d+\s*-\s*\d+\s+of\s+\d{1,3}(?:,\d{3})*(?:\s*\([^)]+\))?',  # With optional time
            r'\d+\s*-\s*\d+\s+of\s+\d{1,3}(?:,\d{3})*',  # Without time
            r'Showing\s+\d+\s*-\s*\d+\s+of\s+\d{1,3}(?:,\d{3})*',  # "Showing X - Y of Z"
            r'Found\s+\d+\s*-\s*\d+\s+of\s+\d{1,3}(?:,\d{3})*',  # "Found X - Y of Z"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                return match.group(0).strip()
        
        # If no pattern found, try to find in specific elements
        # Look for divs/spans that might contain this info
        for tag in ['div', 'span', 'p', 'h3', 'h4']:
            elements = soup.find_all(tag)
            for elem in elements:
                text = elem.get_text(strip=True)
                for pattern in patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        return match.group(0).strip()
        
        return ""
    except Exception as e:
        print(f"Error extracting results count text from soup: {e}")
        return ""


def extract_total_results(soup) -> int:
    """
    Extract total number of results from the page.
    Looks for text patterns like "Showing 1-10 of 17014 results"
    """
    try:
        # Look for common patterns that show total results
        # Pattern 1: Look for text containing "of" followed by a number
        page_text = soup.get_text()
        
        # Try to find patterns like:
        # "of 17014"
        # "Total: 17014"
        # "17014 results"
        # "Found 17014"
        
        import re
        
        # Pattern 1: "of X" or "of X results"
        match = re.search(r'of\s+(\d{1,3}(?:,\d{3})*)\s*(?:results?)?', page_text, re.IGNORECASE)
        if match:
            total = int(match.group(1).replace(',', ''))
            return total
        
        # Pattern 2: "Total: X" or "Total X"
        match = re.search(r'total[:\s]+(\d{1,3}(?:,\d{3})*)', page_text, re.IGNORECASE)
        if match:
            total = int(match.group(1).replace(',', ''))
            return total
        
        # Pattern 3: "Found X results"
        match = re.search(r'found\s+(\d{1,3}(?:,\d{3})*)\s+results?', page_text, re.IGNORECASE)
        if match:
            total = int(match.group(1).replace(',', ''))
            return total
        
        # Pattern 4: Look for specific divs or spans that might contain the count
        count_elements = soup.find_all(['div', 'span', 'p'], string=re.compile(r'\d{1,3}(?:,\d{3})*\s*(?:results?|documents?)', re.IGNORECASE))
        for elem in count_elements:
            text = elem.get_text()
            match = re.search(r'(\d{1,3}(?:,\d{3})*)', text)
            if match:
                total = int(match.group(1).replace(',', ''))
                if total > 100:  # Reasonable threshold for total results
                    return total
        
        # If no pattern found, return 0 (will be handled by frontend)
        return 0
        
    except Exception as e:
        print(f"Error extracting total results: {e}")
        return 0


def extract_pagination_info(soup, current_page_index: int) -> Dict:
    """
    Extract pagination information from the page.
    Returns current page, total pages, and available page numbers.
    """
    pagination_info = {
        "current_page": current_page_index + 1,  # 1-indexed
        "total_pages": 1,
        "has_previous": False,
        "has_next": False,
        "page_numbers": []
    }
    
    try:
        # Find all links that could be pagination links
        all_links = soup.find_all("a", href=True)
        page_links = []
        
        for link in all_links:
            href = link.get("href", "")
            text = link.get_text(strip=True).lower()
            link_text = link.get_text(strip=True)
            
            # Check for Previous/Next
            if "previous" in text:
                pagination_info["has_previous"] = True
            if "next" in text:
                pagination_info["has_next"] = True
            
            # Check if it's a page number link
            # Indian Kanoon pagination links contain formInput in href and have numeric text
            if link_text.isdigit() and ("search" in href or "formInput" in href):
                page_num = int(link_text)
                page_links.append(page_num)
        
        if page_links:
            page_numbers = sorted(set(page_links))
            pagination_info["total_pages"] = max(page_numbers) if page_numbers else 1
            pagination_info["page_numbers"] = page_numbers
            pagination_info["has_previous"] = current_page_index > 0 or pagination_info["has_previous"]
            pagination_info["has_next"] = (current_page_index + 1 < pagination_info["total_pages"]) or pagination_info["has_next"]
        else:
            # If no page links found, check if there are results (might be only one page)
            results = soup.find_all("div", class_="result")
            if results:
                # Assume there might be more pages if we have exactly 10 results
                if len(results) >= 10:
                    pagination_info["has_next"] = True
                    pagination_info["total_pages"] = 2  # At least 2 pages
            else:
                pagination_info["total_pages"] = 1
                
    except Exception as e:
        print(f"Error extracting pagination info: {e}")
    
    return pagination_info


async def get_browser():
    """Get or create a reusable browser instance"""
    global _browser, _browser_context, _playwright_instance
    
    if _browser is None or not _browser.is_connected():
        _playwright_instance = await async_playwright().start()
        _browser = await _playwright_instance.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-images',
                '--disable-javascript-harmony-shipping',
                '--disable-background-networking',
                '--disable-background-timer-throttling',
                '--disable-renderer-backgrounding',
                '--disable-backgrounding-occluded-windows',
                '--disable-ipc-flooding-protection'
            ]
        )
        
        # Create context once
        random_ua = random.choice(USER_AGENTS)
        _browser_context = await _browser.new_context(
            user_agent=random_ua,
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
            timezone_id='America/New_York',
            permissions=[],
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0'
            }
        )
        
        # Add stealth script once
        await _browser_context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
            window.chrome = { runtime: {} };
        """)
    
    return _browser, _browser_context


async def scrape_indian_kanoon(query: str, page_index: int = 0) -> Dict:
    """
    Scrape search results from Indian Kanoon.
    Closes browser after each search.
    
    Args:
        query: Search query (spaces should be replaced with +)
        page_index: Page index (0-indexed, 0 = first page)
    
    Returns:
        Dictionary containing results, pagination info, and metadata
    """
    global _browser, _browser_context, _playwright_instance
    
    import time
    start_time = time.time()
    
    # Get browser instance (creates new one each time since we close after search)
    browser, context = await get_browser()
    page = await context.new_page()
    
    try:
        from urllib.parse import quote
        # Convert + back to space, then encode spaces as %20 (not +)
        # Indian Kanoon expects spaces as %20, not + or %2B
        query_with_spaces = query.replace("+", " ")
        encoded_query = quote(query_with_spaces, safe='')
        page_num = page_index + 1  # Convert to 1-indexed for URL
        
        # Always start by loading page 1 first (needed for pagination to work)
        base_url = f"https://indiankanoon.org/search/?formInput={encoded_query}"
        navigation_success = False
        
        print(f"Loading search results for query: {query}, target page: {page_num}")
        
        # Step 1: Load the first page
        try:
            await page.goto(base_url, wait_until="domcontentloaded", timeout=20000)
            
            # Wait for results to appear
            try:
                await page.wait_for_selector(".result", timeout=15000, state="attached")
                print(f"Page 1 loaded successfully")
            except:
                # Give JS more time to render
                await asyncio.sleep(2)
                try:
                    await page.wait_for_selector(".result", timeout=15000, state="attached")
                    print(f"Page 1 loaded successfully (after wait)")
                except:
                    # Check if page loaded but no results
                    content = await page.content()
                    if "result" in content.lower() or len(content) > 1000:
                        print(f"Page 1 loaded (content check passed)")
                    else:
                        raise Exception("No results found on page 1")
        except Exception as initial_error:
            print(f"Initial page load failed: {initial_error}")
            # Try form automation as fallback
            try:
                await page.goto("https://indiankanoon.org/", wait_until="networkidle", timeout=60000)
                await asyncio.sleep(2)
                
                search_box = None
                try:
                    search_box = page.get_by_role("textbox", name="Search laws, court judgments")
                    await search_box.wait_for(state="visible", timeout=10000)
                except Exception:
                    try:
                        search_box = page.locator('input[placeholder*="Search"]')
                        await search_box.wait_for(state="visible", timeout=10000)
                    except Exception:
                        search_box = page.locator('input[name="formInput"], input[id*="search"], input[type="text"]').first
                        await search_box.wait_for(state="visible", timeout=10000)
                
                if not search_box:
                    raise Exception("Could not find search textbox")
                
                await search_box.click()
                await asyncio.sleep(0.5)
                search_query = query.replace("+", " ")
                await search_box.fill(search_query)
                await asyncio.sleep(0.5)
                
                try:
                    search_button = page.get_by_role("button", name="Search")
                    await search_button.wait_for(state="visible", timeout=10000)
                    await search_button.click()
                except Exception:
                    try:
                        search_button = page.locator('button:has-text("Search"), input[type="submit"][value*="Search"]')
                        await search_button.wait_for(state="visible", timeout=10000)
                        await search_button.click()
                    except Exception:
                        await search_box.press("Enter")
                
                await page.wait_for_selector(".result, div.result", timeout=30000)
                print(f"Page 1 loaded via form automation")
            except Exception as form_error:
                raise Exception(f"Failed to load initial page: {form_error}")
        
        # Step 2: Navigate to target page if page_index > 0
        if page_index > 0:
            print(f"Navigating to page {page_num}...")
            await asyncio.sleep(1)  # Wait for page to stabilize
            
            # IMPORTANT: Indian Kanoon uses 0-indexed pagenum in URL
            # Link text "15" corresponds to pagenum=14 in URL
            # Link text "16" corresponds to pagenum=15 in URL
            # So we need to subtract 1 from page_num for the URL parameter
            pagenum_in_url = page_num - 1
            
            # Strategy 1: Build URL directly using pagenum parameter (FASTEST - works for any page)
            # This is the primary method since we know the URL format
            # URL format: /search/?formInput={query}&pagenum={pagenum}
            try:
                # Construct URL directly: formInput=user%20query&pagenum=14
                # Note: pagenum is 0-indexed in URL (page 15 = pagenum=14)
                direct_url = f"https://indiankanoon.org/search/?formInput={encoded_query}&pagenum={pagenum_in_url}"
                print(f"Attempting direct URL navigation (page {page_num} = pagenum {pagenum_in_url}): {direct_url}")
                await page.goto(direct_url, wait_until="domcontentloaded", timeout=20000)
                await asyncio.sleep(1)
                try:
                    await page.wait_for_selector(".result", timeout=10000, state="attached")
                    navigation_success = True
                    print(f"✓ Successfully navigated to page {page_num} via direct URL")
                except:
                    # Give it a bit more time
                    await asyncio.sleep(1)
                    await page.wait_for_selector(".result", timeout=10000, state="attached")
                    navigation_success = True
                    print(f"✓ Successfully navigated to page {page_num} via direct URL (after extended wait)")
            except Exception as direct_url_error:
                print(f"✗ Direct URL navigation failed: {direct_url_error}")
                navigation_success = False
            
            # Strategy 2: Parse HTML to find pagination link (only for pages likely visible, e.g., 1-15)
            if not navigation_success and page_num <= 15:
                try:
                    # Get current page content to find pagination links
                    current_content = await page.content()
                    current_soup = BeautifulSoup(current_content, "lxml")
                    
                    # Find all pagination links with pagenum parameter
                    pagination_links = current_soup.find_all("a", href=True)
                    target_url = None
                    
                    print(f"Searching for pagination link in HTML (found {len(pagination_links)} links)...")
                    for link in pagination_links:
                        href = link.get("href", "")
                        link_text = link.get_text(strip=True)
                        
                        # Check if this link has pagenum parameter and matches our target page
                        # Note: Link text is 1-indexed (shows "15"), but pagenum in URL is 0-indexed (pagenum=14)
                        if "pagenum" in href.lower() and link_text.isdigit():
                            link_page_num = int(link_text)
                            # Extract pagenum from href to verify
                            import re
                            pagenum_match = re.search(r'pagenum=(\d+)', href, re.IGNORECASE)
                            if pagenum_match:
                                href_pagenum = int(pagenum_match.group(1))
                                # Link text should be href_pagenum + 1 (1-indexed)
                                # So if we want page_num (1-indexed), we need href_pagenum = page_num - 1
                                if link_page_num == page_num and href_pagenum == pagenum_in_url:
                                    # Found the target page link!
                                    if href.startswith("/"):
                                        target_url = f"https://indiankanoon.org{href}"
                                    elif href.startswith("http"):
                                        target_url = href
                                    else:
                                        target_url = f"https://indiankanoon.org/search/{href}"
                                    print(f"Found pagination link for page {page_num} (pagenum={pagenum_in_url}): {target_url}")
                                    break
                            elif link_page_num == page_num:
                                # Fallback: if we can't extract pagenum, just match by link text
                                if href.startswith("/"):
                                    target_url = f"https://indiankanoon.org{href}"
                                elif href.startswith("http"):
                                    target_url = href
                                else:
                                    target_url = f"https://indiankanoon.org/search/{href}"
                                print(f"Found pagination link for page {page_num}: {target_url}")
                                break
                    
                    # If found, navigate directly to the URL
                    if target_url:
                        try:
                            await page.goto(target_url, wait_until="domcontentloaded", timeout=20000)
                            await asyncio.sleep(1)
                            await page.wait_for_selector(".result", timeout=10000, state="attached")
                            navigation_success = True
                            print(f"✓ Successfully navigated to page {page_num} via parsed link")
                        except Exception as nav_error:
                            print(f"✗ Parsed link navigation failed: {nav_error}")
                    else:
                        print(f"✗ Pagination link for page {page_num} not found in HTML")
                except Exception as parse_error:
                    print(f"✗ Error parsing pagination links: {parse_error}")
            
            # Strategy 3: Try clicking the page number link directly (only for visible pages)
            if not navigation_success and page_num <= 15:
                clicked = False
                try:
                    # Method 3a: get_by_role with exact match
                    try:
                        page_link = page.get_by_role("link", name=str(page_num), exact=True)
                        if await page_link.count() > 0:
                            await page_link.wait_for(state="visible", timeout=5000)
                            await page_link.click()
                            clicked = True
                            print(f"Clicked page {page_num} using get_by_role")
                    except:
                        pass
                    
                    # Method 3b: Locator with exact text match
                    if not clicked:
                        try:
                            page_link = page.locator(f'a:has-text("{page_num}")').filter(has_text=re.compile(f'^{page_num}$'))
                            if await page_link.count() > 0:
                                await page_link.first.wait_for(state="visible", timeout=5000)
                                await page_link.first.click()
                                clicked = True
                                print(f"Clicked page {page_num} using exact text locator")
                        except:
                            pass
                    
                    # Method 3c: Any link containing the page number with pagenum in href
                    if not clicked:
                        try:
                            all_links = await page.locator('a').all()
                            for link in all_links:
                                try:
                                    text = await link.inner_text()
                                    href = await link.get_attribute('href') or ''
                                    if text.strip() == str(page_num) and 'pagenum' in href.lower():
                                        await link.click()
                                        clicked = True
                                        print(f"Clicked page {page_num} using link search")
                                        break
                                except:
                                    continue
                        except:
                            pass
                    
                    if clicked:
                        await asyncio.sleep(1.5)
                        try:
                            await page.wait_for_selector(".result", timeout=10000, state="attached")
                            navigation_success = True
                            print(f"✓ Successfully navigated to page {page_num} via click")
                        except:
                            await asyncio.sleep(1)
                            await page.wait_for_selector(".result", timeout=10000, state="attached")
                            navigation_success = True
                            print(f"✓ Successfully navigated to page {page_num} via click (after wait)")
                except Exception as click_error:
                    print(f"✗ Page link click failed: {click_error}")
            
            if not navigation_success:
                print(f"⚠ Warning: Could not navigate to page {page_num}, will use current page results")
        else:
            # Page 1 - already loaded
            navigation_success = True
        
        # Get the page content
        content = await page.content()
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(content, "lxml")
        
        # Find all result divs
        result_divs = soup.find_all("div", class_="result")
        
        # Use shared parsing function
        results = parse_results(result_divs)
        
        # Extract pagination information
        pagination_info = extract_pagination_info(soup, page_index)
        
        # Extract the exact results count text from the website using Playwright
        results_count_text = ""
        try:
            import re
            
            # Use page.get_by_text() to find text containing "of" and numbers
            # Try with partial text match (exact=False)
            try:
                # Try to find text containing "of" pattern
                count_element = page.get_by_text("of", exact=False)
                if await count_element.count() > 0:
                    # Get all elements with "of" text
                    for i in range(await count_element.count()):
                        try:
                            text = await count_element.nth(i).inner_text()
                            # Check if it matches our pattern: "1 - 10 of 17014" or "1 - 10 of 17014 (0.02 seconds)"
                            match = re.search(r'\d+\s*-\s*\d+\s+of\s+\d{1,3}(?:,\d{3})*(?:\s*\([^)]+\))?', text, re.IGNORECASE)
                            if match:
                                results_count_text = match.group(0).strip()
                                break
                        except:
                            continue
            except:
                pass
            
            # Alternative: Use locator to search for text pattern
            if not results_count_text:
                try:
                    # Search in all text content
                    body_text = await page.locator('body').inner_text()
                    match = re.search(r'\d+\s*-\s*\d+\s+of\s+\d{1,3}(?:,\d{3})*(?:\s*\([^)]+\))?', body_text, re.IGNORECASE)
                    if match:
                        results_count_text = match.group(0).strip()
                except:
                    pass
            
            # If still not found, extract from BeautifulSoup
            if not results_count_text:
                results_count_text = extract_results_count_from_soup(soup)
                
        except Exception as e:
            print(f"Error extracting results count text: {e}")
            # Fallback to soup extraction
            results_count_text = extract_results_count_from_soup(soup)
        
        elapsed = time.time() - start_time
        print(f"Playwright completed in {elapsed:.2f} seconds (page {page_index + 1})")
        
        # Close page and browser after each search
        await page.close()
        await browser.close()
        if _playwright_instance:
            await _playwright_instance.stop()
        
        # Reset global browser instance
        _browser = None
        _browser_context = None
        _playwright_instance = None
        
        return {
            "query": query.replace("+", " "),
            "results": results,
            "count": len(results),
            "results_count_text": results_count_text,  # Exact text from website
            "current_page": page_index + 1,  # 1-indexed for frontend
            "pagination": pagination_info,
            "source": "playwright"
        }
        
    except Exception as e:
        # Close page and browser on error
        try:
            if 'page' in locals():
                await page.close()
        except:
            pass
        try:
            if 'browser' in locals():
                await browser.close()
        except:
            pass
        try:
            if _playwright_instance:
                await _playwright_instance.stop()
        except:
            pass
        
        # Reset global browser instance
        _browser = None
        _browser_context = None
        _playwright_instance = None
        
        import traceback
        error_details = traceback.format_exc()
        raise Exception(f"Error during scraping: {str(e)}\n\nTraceback:\n{error_details}")

