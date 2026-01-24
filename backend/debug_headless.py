import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def debug_scrape():
    async with async_playwright() as p:
        print("Launching browser...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        
        url = "https://www.google.com/maps/search/handyman+in+Ikeja+Lagos"
        print(f"Navigating to: {url}")
        
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
            print("Navigation finished. Waiting 5s...")
            await asyncio.sleep(5)
            
            # Capture state
            await page.screenshot(path="debug_headless.png")
            content = await page.content()
            with open("debug_source.html", "w") as f:
                f.write(content)
            
            print(f"Page title: {await page.title()}")
            
            # Check for selectors
            items = await page.query_selector_all('div[role="article"]')
            print(f"Found {len(items)} article items.")
            
            feed = await page.query_selector('div[role="feed"]')
            print(f"Found feed: {'Yes' if feed else 'No'}")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_scrape())
