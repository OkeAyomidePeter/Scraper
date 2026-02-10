import asyncio
import random
import re
import logging
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from utils import normalize_phone

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def scrape_google_maps(business_type: str, location: str, max_results: int = 50):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        stealth = Stealth()
        await stealth.apply_stealth_async(page)
        
        search_query = f"{business_type} in {location}"
        url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"
        
        logger.info(f"Searching for: {search_query}")
        try:
            await page.goto(url, timeout=90000)
            await page.wait_for_load_state("networkidle", timeout=60000)
        except Exception as e:
            logger.warning(f"Initial navigation timeout: {e}. Attempting to proceed.")
            
        # Bypass Consent Wall
        if "consent.google.com" in page.url or "Before you continue" in await page.title():
            try:
                await page.wait_for_selector('button', timeout=5000)
                buttons = await page.query_selector_all('button')
                for btn in buttons:
                    text = await btn.inner_text()
                    if any(term in text for term in ["Accept all", "I agree", "Godkänn alla", "Jag godkänner"]):
                        await btn.click()
                        await page.wait_for_load_state("networkidle")
                        break
            except Exception:
                pass

        leads = []
        scrollable_div_selector = 'div[role="feed"]'
        article_selector = 'div[role="article"]'
        
        # Wait for the feed to load
        try:
            await page.wait_for_selector(article_selector, timeout=15000)
        except Exception:
            logger.error("No results found or page blocked.")
            await browser.close()
            return []

        processed_ids = set()
        
        while len(leads) < max_results:
            # Scroll to load more
            await page.evaluate(f"document.querySelector('{scrollable_div_selector}').scrollBy(0, 3000)")
            await page.wait_for_timeout(2000)
            
            results = await page.query_selector_all(article_selector)
            if not results:
                break
                
            new_results_found = False
            for result in results:
                if len(leads) >= max_results:
                    break
                
                name_el = await result.query_selector('.qBF1Pd')
                if not name_el:
                    continue
                
                name = await name_el.inner_text()
                if name in processed_ids:
                    continue
                
                new_results_found = True
                processed_ids.add(name)
                
                try:
                    # Extract high-level data from list view
                    rating_el = await result.query_selector('span.MW4etd')
                    rating = await rating_el.inner_text() if rating_el else "0"
                    
                    review_el = await result.query_selector('span.UY7F9')
                    reviews = await review_el.inner_text() if review_el else "0"
                    
                    category_el = await result.query_selector('.W4Efsd span:nth-child(1) span')
                    category = ""
                    if category_el:
                        category_text = await category_el.inner_text()
                        # Reject if it's just a number (rating)
                        if not re.match(r'^\d+\.?\d*$', category_text.strip()):
                            category = category_text
                    
                    phone_el = await result.query_selector('span.UsdlK')
                    phone = await phone_el.inner_text() if phone_el else "N/A"
                    
                    website = ""
                    website_el = await result.query_selector('a.lcr4fd')
                    if website_el:
                        href = await website_el.get_attribute('href')
                        # Reject ad links and internal google links
                        if href and not any(term in href for term in ["/aclk", "googleadservices", "google.com/maps"]):
                            website = href

                    lead = {
                        "name": name,
                        "category": category,
                        "phone": phone,
                        "normalized_phone": normalize_phone(phone),
                        "website": website,
                        "rating": rating,
                        "reviews": reviews,
                        "maps_url": page.url
                    }
                    
                    leads.append(lead)
                    logger.info(f"Scraped {len(leads)}: {name}")
                    
                except Exception as e:
                    logger.error(f"Error extracting listing: {e}")

            # Check for end of list
            end_of_list = await page.query_selector('span:has-text("You\'ve reached the end of the list.")')
            if end_of_list or not new_results_found:
                break

        await browser.close()
        return leads


if __name__ == "__main__":
    import os
    import sys
    
    async def main():
        search_file = os.path.join(os.path.dirname(__file__), "search.txt")
        if len(sys.argv) > 1:
            queries = [sys.argv[1]]
            loc = sys.argv[2] if len(sys.argv) > 2 else "Nigeria"
        elif os.path.exists(search_file):
            with open(search_file, "r") as f:
                queries = [line.strip() for line in f if line.strip()]
            loc = "Nigeria"
        else:
            queries = ["Plumbers"]
            loc = "Lagos"
            
        for query in queries:
            logger.info(f"Test scrape for: {query} in {loc}")
            results = await scrape_google_maps(query, loc, max_results=5)
            for r in results:
                print(f"- {r['name']} ({r['phone']})")

    asyncio.run(main())
