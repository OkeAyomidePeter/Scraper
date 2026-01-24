import asyncio
import random
import re
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import pandas as pd
from processor import normalize_phone, filter_leads, calculate_priority

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
        
        print(f"Searching for: {search_query}")
        try:
            # Use 'commit' to ensure we at least start leading, then wait manually
            await page.goto(url, timeout=90000)
            print("Page navigation initiated...")
            await page.wait_for_load_state("domcontentloaded")
            print("DOM content loaded.")
            await page.wait_for_timeout(5000)
        except Exception as e:
            print(f"Navigation error: {e}")
            await browser.close()
            return []
        
        leads = []
        
        # Scrolling logic
        # Google Maps results are usually in a scrollable div
        scrollable_div_selector = 'div[role="feed"]'
        
        processed_count = 0
        
        while processed_count < max_results:
            # Find all result items
            results = await page.query_selector_all('div[role="article"]')
            
            if not results:
                break
                
            for result in results[processed_count:]:
                if processed_count >= max_results:
                    break
                
                try:
                    # Click on the result to open details
                    await result.scroll_into_view_if_needed()
                    await result.click()
                    await page.wait_for_timeout(random.randint(2000, 4000))
                    
                    # Extract data
                    # Extract data from the list item first (it's faster and more reliable)
                    name_el = await result.query_selector('.qBF1Pd')
                    name = await name_el.inner_text() if name_el else "N/A"
                    
                    # Try to get phone and website directly from the list item
                    phone = "N/A"
                    phone_el = await result.query_selector('.UsdlK')
                    if phone_el:
                        phone = await phone_el.inner_text()
                        
                    website = ""
                    website_el = await result.query_selector('a[aria-label*="website"]')
                    if website_el:
                        website = await website_el.get_attribute('href')
                    
                    # If data is missing, CLICK to get more details
                    if phone == "N/A" or not website:
                        try:
                            await result.scroll_into_view_if_needed()
                            await result.click()
                            await page.wait_for_timeout(random.randint(2000, 3000))
                            
                            # Re-check details panel
                            details_container = await page.query_selector('div[role="main"]')
                            if details_container:
                                # Name in details
                                if name == "N/A":
                                    h1_el = await details_container.query_selector('h1')
                                    if h1_el:
                                        name = await h1_el.inner_text()
                                
                                # Phone in details
                                if phone == "N/A":
                                    phone_btn = await details_container.query_selector('button[data-item-id^="phone:"]')
                                    if phone_btn:
                                        phone = await phone_btn.inner_text()
                                
                                # Website in details
                                if not website:
                                    web_btn = await details_container.query_selector('button[data-item-id^="authority"], a[data-item-id^="authority"]')
                                    if web_btn:
                                        website = await web_btn.get_attribute('href') or await web_btn.inner_text()
                        except Exception as e:
                            print(f"Error clicking for details: {e}")

                    # Rating and reviews
                    rating = "0"
                    reviews = "0"
                    rating_el = await result.query_selector('span[aria-label*="stars"]')
                    if rating_el:
                        aria_label = await rating_el.get_attribute('aria-label')
                        if aria_label:
                            parts = aria_label.split(' ')
                            rating = parts[0]
                            # Often looks like "4.7 stars 123 Reviews"
                            review_match = re.search(r'(\d+)\s+Reviews', aria_label)
                            if review_match:
                                reviews = review_match.group(1)
                    
                    lead = {
                        "name": name,
                        "phone": phone,
                        "normalized_phone": normalize_phone(phone),
                        "website": website,
                        "rating": rating,
                        "reviews": reviews,
                        "maps_url": page.url
                    }
                    
                    leads.append(lead)
                    processed_count += 1
                    print(f"Scraped {processed_count}/{max_results}: {name} | Phone: {phone} | Web: {'Yes' if website else 'No'}")
                    
                except Exception as e:
                    print(f"Error scraping listing: {e}")
                    continue
            
            # Scroll down to load more results
            await page.evaluate(f"document.querySelector('{scrollable_div_selector}').scrollBy(0, 5000)")
            await page.wait_for_timeout(3000)
            
            # Check if we've reached the end
            end_text = await page.query_selector('span:has-text("You\'ve reached the end of the list.")')
            if end_text:
                break
                
        await browser.close()
        
        # Post-processing
        filtered_leads = filter_leads(leads)
        for lead in filtered_leads:
            lead['priority_score'] = calculate_priority(lead)
            
        # Sort by priority
        filtered_leads.sort(key=lambda x: x['priority_score'], reverse=True)
        
        return filtered_leads

if __name__ == "__main__":
    # Test run
    # Use a wider search to potentially find businesses without websites in the test batch
    results = asyncio.run(scrape_google_maps("handyman", "Ikeja Lagos", max_results=10))
    
    # Export ALL leads for debugging website detection
    df_raw = pd.DataFrame(results)
    print("Scraped Raw Leads:")
    print(df_raw[['name', 'phone', 'website']])
    df_raw.to_csv("debug_all_leads.csv", index=False)
    
    # Filter and export for the final target
    filtered = filter_leads(results)
    df_filtered = pd.DataFrame(filtered)
    print("\nFiltered Leads (No Website):")
    if not df_filtered.empty:
        print(df_filtered[['name', 'phone']])
    df_filtered.to_csv("test_leads.csv", index=False)
