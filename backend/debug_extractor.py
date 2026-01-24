import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import os

async def debug_maps_html(query: str, output_dir: str = "debug_output"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        stealth = Stealth()
        await stealth.apply_stealth_async(page)
        
        url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
        print(f"Navigating to: {url}")
        
        await page.goto(url, timeout=90000)
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(10000)
        
        # Click the first result if it exists to open the details panel
        first_result = await page.query_selector('div[role="article"]')
        if first_result:
            print("Clicking first result...")
            await first_result.click()
            await page.wait_for_timeout(5000)
            
            # Take a screenshot of the whole page
            await page.screenshot(path=f"{output_dir}/full_page.png")
            print(f"Screenshot saved to {output_dir}/full_page.png")
            
            # Save the HTML of the details panel
            # Google Maps details panel is typically in a specific div
            # We'll try to find the container that contains 'h1'
            main_content = await page.query_selector('div[role="main"]')
            if main_content:
                html_content = await main_content.inner_html()
                with open(f"{output_dir}/details_panel.html", "w", encoding="utf-8") as f:
                    f.write(html_content)
                print(f"HTML dump saved to {output_dir}/details_panel.html")
            else:
                # Capture whole body if specific panel not found
                html_content = await page.content()
                with open(f"{output_dir}/page_full.html", "w", encoding="utf-8") as f:
                    f.write(html_content)
                print(f"Full page HTML dump saved to {output_dir}/page_full.html")
                
        else:
            print("No results found to inspect.")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_maps_html("Doveland International Schools, Abuja"))
