import asyncio
import random
import requests
import time
from database import get_next_queued_message, mark_as_sent, mark_as_failed, get_daily_status

# Config
DAILY_MESSAGES_LIMIT = 100
WHATSAPP_SERVICE_URL = "http://localhost:3000/send"

async def slow_sender():
    """Continuously checks for queued messages and sends them with large random delays."""
    print("--- Anti-Detection Sender Started ---")
    
    while True:
        # 1. Check daily limit
        stats = get_daily_status()
        if stats['sent_today'] >= DAILY_MESSAGES_LIMIT:
            print(f"Daily limit of {DAILY_MESSAGES_LIMIT} reached. Resting...")
            await asyncio.sleep(3600) # Check again in an hour
            continue

        # 2. Get next queued message
        job = get_next_queued_message()
        
        if not job:
            # No work to do - wait a bit before checking again
            print("Queue empty. Waiting 5 minutes...")
            await asyncio.sleep(300)
            continue

        print(f"📦 [SENDER] Processing: {job['name']} ({job['phone']})")

        # 3. Send via WhatsApp Service
        try:
            payload = {"phone": job['phone'], "message": job['message']}
            response = requests.post(WHATSAPP_SERVICE_URL, json=payload, timeout=30)
            
            if response.status_code == 200:
                print(f"   ✅ [SUCCESS] Message delivered to {job['name']}")
                mark_as_sent(job['phone'])
                
                # 4. Anti-detection: THE SLOW DRIP 💧
                # Sleep for 5-15 minutes between messages
                delay = random.randint(300, 900) 
                print(f"   💤 Sleeping for {delay//60}m {delay%60}s to mimic human intervals...")
                await asyncio.sleep(delay)
            else:
                print(f"   ❌ [FAILED] WhatsApp Service Error ({response.status_code})")
                mark_as_failed(job['phone'])
                # Slight sleep before trying next
                await asyncio.sleep(30)
                
        except Exception as e:
            print(f"   ⚠️ [ERROR] Dispatch error: {e}")
            mark_as_failed(job['phone'])
            await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        asyncio.run(slow_sender())
    except KeyboardInterrupt:
        print("Sender stopped manually.")
