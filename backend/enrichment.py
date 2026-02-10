import asyncio
import re
import logging
from typing import List, Set
from playwright.async_api import async_playwright, Page, BrowserContext

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

EMAIL_REGEX = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-0.-]+\.[a-zA-Z]{2,}'
FORBIDDEN_DOMAINS = {'sentry.io', 'example.com', 'google.com', 'wixpress.com', 'png', 'jpg', 'jpeg', 'gif'}

async def extract_emails_from_page(page: Page) -> Set[str]:
    """Extracts all emails from the current page content."""
    try:
        content = await page.content()
        emails = re.findall(EMAIL_REGEX, content)
        # Filter out common false positives and image extensions mistakenly caught
        filtered_emails = {
            e.lower() for e in emails 
            if not any(domain in e.lower() for domain in FORBIDDEN_DOMAINS)
            and not e.lower().endswith(tuple(FORBIDDEN_DOMAINS))
        }
        return filtered_emails
    except Exception as e:
        logger.error(f"Error extracting emails from page: {e}")
        return set()

async def find_contact_links(page: Page) -> List[str]:
    """Finds links that likely lead to a contact or about page."""
    contact_keywords = ['contact', 'about', 'get in touch', 'reach us', 'support']
    links = []
    try:
        elements = await page.query_selector_all('a')
        for el in elements:
            href = await el.get_attribute('href')
            text = await el.inner_text()
            if href and any(kw in (href.lower() + text.lower()) for kw in contact_keywords):
                # Ensure it's a relative link or same-domain link
                if href.startswith('/') or page.url.split('/')[2] in href:
                    links.append(href)
        return list(set(links))
    except Exception as e:
        logger.error(f"Error finding contact links: {e}")
        return []

async def enrich_lead_with_email(url: str) -> List[str]:
    """
    Crawls a website to find email addresses.
    Starts at the home page, then follows likely contact/about links.
    """
    if not url or not url.startswith('http'):
        logger.warning(f"Invalid URL for enrichment: {url}")
        return []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        found_emails: Set[str] = set()
        visited_urls: Set[str] = set()

        try:
            logger.info(f"Enriching from Home: {url}")
            await page.goto(url, timeout=30000, wait_until="networkidle")
            visited_urls.add(page.url)
            
            # Extract from Home Page
            home_emails = await extract_emails_from_page(page)
            found_emails.update(home_emails)
            
            # Find Contact/About links
            contact_links = await find_contact_links(page)
            
            # Limit to top 3 likely links to avoid infinite crawling
            for link in contact_links[:3]:
                # Construct full URL if relative
                if link.startswith('/'):
                    base_url = "/".join(url.split('/')[:3])
                    full_url = f"{base_url}{link}"
                elif not link.startswith('http'):
                    base_url = "/".join(url.split('/')[:3])
                    full_url = f"{base_url}/{link}"
                else:
                    full_url = link
                
                if full_url not in visited_urls:
                    logger.info(f"Checking Contact Page: {full_url}")
                    try:
                        await page.goto(full_url, timeout=15000, wait_until="domcontentloaded")
                        visited_urls.add(full_url)
                        emails = await extract_emails_from_page(page)
                        found_emails.update(emails)
                    except Exception as e:
                        logger.error(f"Failed to load {full_url}: {e}")

        except Exception as e:
            logger.error(f"Error during enrichment for {url}: {e}")
        finally:
            await browser.close()
            
        return list(found_emails)

if __name__ == "__main__":
    import sys
    
    async def manual_test():
        test_url = sys.argv[1] if len(sys.argv) > 1 else "https://www.example.com"
        print(f"\n--- Testing Enrichment for: {test_url} ---")
        emails = await enrich_lead_with_email(test_url)
        print(f"Results: {emails}")
        print("-------------------------------------------\n")

    asyncio.run(manual_test())
