import asyncio
import os
import random
import time
from datetime import date
import requests
from scraper import scrape_google_maps
from ai_agent import generate_outreach_message
from database import init_db, save_lead, is_lead_already_messaged, mark_as_sent, get_daily_status
from processor import filter_leads

# Config
DAILY_MESSAGES_LIMIT = 100
WHATSAPP_SERVICE_URL = "http://localhost:3000/send"
SEARCH_FILE = os.path.join(os.path.dirname(__file__), "search.txt")

async def process_campaign():
    """Runs a full outreach campaign based on search.txt."""
    init_db()
    
    if not os.path.exists(SEARCH_FILE):
        print(f"Error: {SEARCH_FILE} not found.")
        return

    with open(SEARCH_FILE, "r") as f:
        queries = [line.strip() for line in f if line.strip()]

    print(f"--- Starting Outreach Campaign ({len(queries)} queries) ---")
    
    for query in queries:
        # Check daily limit
        stats = get_daily_status()
        if stats['sent_today'] >= DAILY_MESSAGES_LIMIT:
            print(f"Daily limit of {DAILY_MESSAGES_LIMIT} reached. Stopping campaign.")
            break
            
        print(f"\n[ORCHESTRATOR] Processing Query: '{query}'")
        
        # 1. Scrape
        # Split query into type and location if possible, otherwise use full as type
        parts = query.split(" in ")
        b_type = parts[0]
        b_loc = parts[1] if len(parts) > 1 else ""
        
        # Scrape a small batch per query to rotate through search types
        leads = await scrape_google_maps(b_type, b_loc, max_results=10)
        
        # 2. Filter (No website + basic quality)
        filtered_leads = filter_leads(leads)
        
        # 3. Process each lead
        for lead in filtered_leads:
            # Check daily limit again inside the loop
            stats = get_daily_status()
            if stats['sent_today'] >= DAILY_MESSAGES_LIMIT:
                break
                
            normalized_phone = lead.get('normalized_phone')
            
            # Skip if no phone or already contacted
            if not normalized_phone or is_lead_already_messaged(normalized_phone):
                continue
                
            # Save to DB (returns True if new)
            is_new = save_lead(lead)
            if not is_new:
                continue # Already in DB

            print(f"   > Generating outreach for: {lead['name']} ({normalized_phone})")
            
            # 4. AI Message Generation
            message = generate_outreach_message(lead)
            if "Rate limit reached" in message:
                print("Gemini rate limit hit. Waiting 60 seconds...")
                await asyncio.sleep(60)
                message = generate_outreach_message(lead) # Retry once

            # 5. WhatsApp Dispatch
            try:
                payload = {"phone": normalized_phone, "message": message}
                response = requests.post(WHATSAPP_SERVICE_URL, json=payload, timeout=30)
                
                if response.status_code == 200:
                    print(f"   [SUCCESS] Message sent to {lead['name']}")
                    mark_as_sent(normalized_phone)
                    # Human-like delay between messages
                    await asyncio.sleep(random.randint(30, 45))
                else:
                    print(f"   [FAILED] WhatsApp Service Error ({response.status_code}) for {lead['name']}")
                    
            except Exception as e:
                print(f"   [ERROR] Dispatch failed for {lead['name']}: {e}")

    print("\n--- Campaign Cycle Finished ---")
    final_stats = get_daily_status()
    print(f"Total Sent Today: {final_stats['sent_today']}")

if __name__ == "__main__":
    asyncio.run(process_campaign())
