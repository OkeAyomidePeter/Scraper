import asyncio
import os
import logging
import time
from datetime import datetime, timedelta
from sqlalchemy import and_, or_
from database import init_db, SessionLocal, save_lead
from models import Lead
from scraper import scrape_google_maps
from enrichment import enrich_lead_with_email
from channel_decision import decide_channels
from ai_agent import generate_message
from telegram_queue import process_telegram_queue

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Polling and Rate Limiting Configuration
POLLING_INTERVAL = 10 * 60  # 10 minutes between search cycles
SCRAPER_DELAY = 2  # seconds between scraper calls
ENRICHMENT_DELAY = 3  # seconds between enrichment calls

async def run_pipeline_cycle(db, processed_leads_cache):
    """Runs a single cycle of scraping, enrichment, and drafting."""
    # 1. Stop early if queue is already full/large to prevent spam
    queue_count = db.query(Lead).filter(Lead.state == 'QUEUED').count()
    draft_count = db.query(Lead).filter(Lead.state == 'DRAFTED').count()
    if (queue_count + draft_count) >= 30: # 2 days worth of budget
        logger.info(f"Queue is currently at {queue_count+draft_count} leads. Skipping discovery cycle to prevent backlog.")
        return 0, 0

    # 2. Read queries from search.txt
    search_file = os.path.join(os.path.dirname(__file__), "search.txt")
    if not os.path.exists(search_file):
        logger.error(f"search.txt not found at {search_file}")
        return 0, 0

    with open(search_file, "r") as f:
        queries = [line.strip() for line in f if line.strip()]

    total_leads_processed = 0
    total_messages_generated = 0

    for query in queries:
        logger.info(f"--- Processing Query: {query} ---")
        
        # Determine location from query (heuristic)
        if " in " in query:
            parts = query.split(" in ")
            business_type = parts[0]
            location = parts[1]
        else:
            business_type = query
            location = "Abuja"

        # 3. Scrape with rate limiting
        logger.info(f"Scraping: {business_type} in {location}")
        try:
            # Only ask for a few leads per query to keep diversity high
            leads = await scrape_google_maps(business_type, location, max_results=10)
        except Exception as e:
            logger.error(f"Scraper error: {e}")
            continue
        
        logger.info(f"Found {len(leads)} leads for '{query}'")
        
        for lead_data in leads:
            # Check unique URL in DB
            maps_url = lead_data.get('maps_url')
            db_lead = db.query(Lead).filter(Lead.maps_url == maps_url).first()
            if db_lead:
                # Already exists, skip
                continue

            logger.info(f"New business discovered: {lead_data['name']}")
            lead_data['city'] = location
            
            # 4. Enrich if website exists
            if lead_data.get('website'):
                logger.info(f"Enriching {lead_data['name']} via {lead_data['website']}...")
                await asyncio.sleep(ENRICHMENT_DELAY)
                try:
                    emails = await enrich_lead_with_email(lead_data['website'])
                    if emails:
                        lead_data['email'] = ", ".join(emails)
                        lead_data['state'] = 'ENRICHED'
                    else:
                        lead_data['state'] = 'DISCOVERED'
                except Exception:
                    lead_data['state'] = 'DISCOVERED'
            else:
                lead_data['state'] = 'DISCOVERED'

            # 5. Channel Decision
            channels = decide_channels(lead_data)
            if not channels:
                save_lead(db, lead_data)
                total_leads_processed += 1
                continue
            
            # 6. AI Message Generation
            all_generated = True
            for channel in channels:
                logger.info(f"Generating {channel} message for {lead_data['name']}...")
                message_result = generate_message(lead_data, channel=channel)
                
                if message_result:
                    if channel == "EMAIL":
                        lead_data['email_subject'] = message_result.get('subject')
                        lead_data['email_draft'] = message_result.get('message')
                    elif channel == "WHATSAPP":
                        lead_data['whatsapp_draft'] = message_result.get('message')
                    total_messages_generated += 1
                else:
                    logger.warning(f"AI Failed for {lead_data['name']} on {channel}")
                    all_generated = False
                    break # Stop if one channel fails
            
            # Update lead data state
            if all_generated:
                lead_data['primary_channel'] = channels[0]
                lead_data['state'] = 'DRAFTED'
            else:
                # If AI fails, mark for human review instead of generic template
                lead_data['state'] = 'NEEDS_REVIEW'

            # 7. Store in DB
            save_lead(db, lead_data)
            total_leads_processed += 1
            logger.info(f"Processed and saved: {lead_data['name']} (State: {lead_data['state']})")
        
        # 8. Check Telegram queue after EACH query for real-time delivery
        logger.info(f"Checking Telegram queue after query: {query}")
        queued = await process_telegram_queue(db)
        if queued > 0:
            logger.info(f"Real-time delivery: Queued {queued} leads to Telegram.")
        
        await asyncio.sleep(SCRAPER_DELAY)

    return total_leads_processed, total_messages_generated

async def maintain_lead_states(db):
    """Maintains lead states and transitions them based on time."""
    now = datetime.utcnow()
    
    # 1. Transition SENT -> WAITING (immediate after being marked sent by user)
    # The API marks it SENT, we move it to WAITING for tracking
    sent_leads = db.query(Lead).filter(Lead.state == 'SENT').all()
    for lead in sent_leads:
        lead.state = 'WAITING'
        logger.info(f"Lead {lead.business_name} transitioned SENT -> WAITING")
    
    # 2. Transition WAITING -> NO_REPLY (after 48 hours)
    waiting_threshold = now - timedelta(days=2)
    stale_waiting = db.query(Lead).filter(
        and_(Lead.state == 'WAITING', Lead.last_interaction_at <= waiting_threshold)
    ).all()
    for lead in stale_waiting:
        lead.state = 'NO_REPLY'
        logger.info(f"Lead {lead.business_name} transitioned WAITING -> NO_REPLY")

    # 3. Transition NO_REPLY -> FOLLOW_UP_ELIGIBLE (after 5 days)
    followup_threshold = now - timedelta(days=5)
    eligible_for_followup = db.query(Lead).filter(
        and_(Lead.state == 'NO_REPLY', Lead.last_interaction_at <= followup_threshold, Lead.follow_up_count < 2)
    ).all()
    for lead in eligible_for_followup:
        lead.state = 'FOLLOW_UP_ELIGIBLE'
        logger.info(f"Lead {lead.business_name} transitioned NO_REPLY -> FOLLOW_UP_ELIGIBLE")

    # 4. Handle FOLLOW_UP_ELIGIBLE -> Generate Nudge Draft
    to_draft_followup = db.query(Lead).filter(Lead.state == 'FOLLOW_UP_ELIGIBLE').all()
    for lead in to_draft_followup:
        logger.info(f"Generating follow-up draft for {lead.business_name}")
        lead_data = {
            "name": lead.business_name,
            "category": lead.category,
            "city": "Abuja",
            "follow_up_channel": lead.primary_channel or "WHATSAPP"
        }
        draft = generate_message(lead_data, channel="FOLLOW_UP")
        if draft:
            if lead.primary_channel == "EMAIL":
                lead.email_draft = draft.get("message")
                lead.email_subject = draft.get("subject")
            else:
                lead.whatsapp_draft = draft.get("message")
            
            lead.state = 'DRAFTED' # Move back to drafted so it hits the Telegram queue
            lead.is_queued = False # Allow re-queueing
            lead.follow_up_count += 1
            logger.info(f"Follow-up draft created for {lead.business_name}")

    db.commit()

async def main():
    # 1. Initialize DB
    init_db()
    
    # Initialize cache from DB existing leads
    db = SessionLocal()
    existing_urls = [l.maps_url for l in db.query(Lead.maps_url).all()]
    processed_leads_cache = set(existing_urls)
    db.close()
    
    logger.info(f"Loaded {len(processed_leads_cache)} leads from cache.")
    logger.info(f"Bot starting... Polling every {POLLING_INTERVAL/60} minutes.")

    while True:
        cycle_start = time.time()
        logger.info("\n=== Starting Discovery Cycle ===")
        
        db = SessionLocal()
        try:
            # Maintain states first
            await maintain_lead_states(db)

            # Discovery Phase
            processed, messages = await run_pipeline_cycle(db, processed_leads_cache)
            logger.info(f"Cycle finished. Processed {processed} leads, generated {messages} messages.")
            
            # Queue Phase (Send to Telegram within budget)
            logger.info("Checking Telegram queue...")
            queued = await process_telegram_queue(db)
            if queued > 0:
                logger.info(f"Queued {queued} leads to Telegram.")
            
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        finally:
            db.close()

        # Calculate sleep time
        elapsed = time.time() - cycle_start
        sleep_time = max(0, POLLING_INTERVAL - elapsed)
        
        if sleep_time > 0:
            logger.info(f"Sleeping for {sleep_time/60:.1f} minutes until next cycle...")
            await asyncio.sleep(sleep_time)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
