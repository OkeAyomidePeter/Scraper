import os
import logging
import json
import time
from typing import Dict, Optional
from google import genai
from dotenv import load_dotenv
from ratelimit import limits, sleep_and_retry

load_dotenv()

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Rate limiting configuration
GEMINI_CALLS_PER_MINUTE = 5
GEMINI_CALLS_PER_DAY = 25
ONE_MINUTE = 60
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DAILY_USAGE_FILE = os.path.join(DATA_DIR, "usage.json")

def get_daily_usage() -> Dict:
    """Loads daily usage per key from a persistent file."""
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(DAILY_USAGE_FILE):
        return {"keys": {}, "date": time.strftime("%Y-%m-%d")}
    
    with open(DAILY_USAGE_FILE, "r") as f:
        try:
            usage = json.load(f)
            # Reset if it's a new day
            if usage.get("date") != time.strftime("%Y-%m-%d"):
                return {"keys": {}, "date": time.strftime("%Y-%m-%d")}
            return usage
        except:
            return {"keys": {}, "date": time.strftime("%Y-%m-%d")}

def increment_usage(key_index: int):
    """Increments the daily usage counter for a specific key."""
    usage = get_daily_usage()
    key_str = str(key_index)
    usage["keys"][key_str] = usage["keys"].get(key_str, 0) + 1
    with open(DAILY_USAGE_FILE, "w") as f:
        json.dump(usage, f)

# Configure API clients
GEMINI_KEYS = []
# Support GEMINI_API_KEY, GEMINI_API_KEY_1, GEMINI_API_KEY_2...
if os.getenv("GEMINI_API_KEY"):
    GEMINI_KEYS.append(os.getenv("GEMINI_API_KEY"))

for i in range(1, 10):
    k = os.getenv(f"GEMINI_API_KEY_{i}")
    if k: GEMINI_KEYS.append(k)

logger.info(f"Initialized with {len(GEMINI_KEYS)} Gemini API keys")

# Company branding
COMPANY_NAME = "Anchor Digitals"
SENDER_NAME = "Peter"
COMPANY_DESCRIPTION = "a specialized tech partner for small businesses in Nigeria"

def build_email_prompt(lead_data: Dict) -> str:
    """Builds the AI prompt for extremely personalized email generation."""
    business_name = lead_data.get("name", "your business")
    category = lead_data.get("category", "business")
    city = lead_data.get("city") or "Abuja"
    has_website = bool(lead_data.get("website"))
    rating = lead_data.get("rating")
    reviews = lead_data.get("reviews") or "0"
    
    prompt = f"""You are {SENDER_NAME} from {COMPANY_NAME}. We help {city} businesses automate their growth.
    
Write a HIGH-STAKES outreach email to {business_name} (a {category} in {city}).

CONTEXT:
- They {"have" if has_website else "don't have"} a website.
- Google Maps Rating: {rating}/5 (based on {reviews} reviews).
- Location: {city}, Nigeria.

STRICT GUIDELINES:
1. NO generic openings like "I saw you on Maps." Instead, reference a specific pain point for a {category} in {city}.
2. Use "Abuja-local" professional tone (not pidgin).
3. Identify a specific GAP:
   - If low rating: Focus on reputation management.
   - If no website: Focus on digital visibility.
   - If clinic/salon: Focus on automated appointment booking.
4. Your goal is a 15-minute meeting.
5. MAX 120 words. Be remarkably direct.

Return ONLY valid JSON:
{{
  "subject": "Question for {business_name}",
  "message": "email body"
}}
"""
    return prompt

def build_whatsapp_prompt(lead_data: Dict) -> str:
    """Builds the AI prompt for unique WhatsApp generation."""
    business_name = lead_data.get("name", "your business")
    category = lead_data.get("category", "business")
    city = lead_data.get("city") or "Abuja"
    rating = lead_data.get("rating")
    
    prompt = f"""You are {SENDER_NAME} from {COMPANY_NAME}, Abuja.
    
Write a brief, unique WhatsApp message to {business_name} (a {category} in {city}).

CONTEXT:
- Rating: {rating} on Google Maps.
- Niche: {category}.
- Location: {city}.

STRICT RULES:
1. Opener: "Hi! Peter here from Anchor Digitals in {city}."
2. The Hook: DO NOT use a template. Mention {business_name} and one specific challenge for {category} in Nigeria (e.g. manual bookings, missed calls).
3. The Value: "We help {category}s here in Abuja automate their client flow."
4. Call to Action: "Can we chat for 2 mins?"
5. Under 180 characters.
6. NO robotic language. Must sound human.

Return ONLY valid JSON:
{{
  "message": "whatsapp message"
}}
"""
    return prompt

def build_follow_up_prompt(lead_data: Dict) -> str:
    """Builds the AI prompt for dynamic follow-up generation."""
    business_name = lead_data.get("name", "your business")
    category = lead_data.get("category", "business")
    city = lead_data.get("city") or "Abuja"
    
    prompt = f"""You are {SENDER_NAME}. Circling back to {business_name} ({category}, {city}).
    
Write a respectul, short check-in.
- Tone: Helpful, low pressure.
- Avoid "Just checking in." Use something like "Did you see my last message regarding the automation for {business_name}?"
- MAX 140 chars for WhatsApp, 80 words for Email.

Return ONLY valid JSON:
{{
  "message": "nudge message",
  "subject": "Follow up for {business_name}"
}}
"""
    return prompt

@sleep_and_retry
@limits(calls=GEMINI_CALLS_PER_MINUTE, period=ONE_MINUTE)
def call_gemini_api(client: genai.Client, prompt: str, channel: str) -> Optional[Dict]:
    """Single API call attempt with error analysis."""
    try:
        # Using gemini-2.5-flash-lite for cost-efficiency and high-volume stability
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=prompt
        )
        response_text = response.text.strip()
        if response_text.startswith("```"):
            lines = response_text.splitlines()
            if lines[0].startswith("```"):
                response_text = "\n".join(lines[1:-1])
        return json.loads(response_text.strip())
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            logger.warning(f"Quota issue detected: {error_msg}")
        else:
            logger.error(f"Gemini API error ({channel}): {error_msg}")
        return None

def generate_message(lead_data: Dict, channel: str = "EMAIL") -> Optional[Dict]:
    """Generates message with API key rotation and NO generic fallbacks."""
    if not GEMINI_KEYS:
        logger.error("No Gemini API keys configured.")
        return None

    # Step 1: Select Channel and Build Prompt
    if channel == "EMAIL": prompt = build_email_prompt(lead_data)
    elif channel == "WHATSAPP": prompt = build_whatsapp_prompt(lead_data)
    elif channel == "FOLLOW_UP": prompt = build_follow_up_prompt(lead_data)
    else: return None

    # Step 2: Try keys in rotation
    usage = get_daily_usage()
    
    for idx, key in enumerate(GEMINI_KEYS):
        key_str = str(idx)
        current_usage = usage["keys"].get(key_str, 0)
        
        if current_usage >= GEMINI_CALLS_PER_DAY:
            continue
        
        logger.info(f"Attempting generation with Key {idx} (Usage: {current_usage}/{GEMINI_CALLS_PER_DAY})")
        client = genai.Client(api_key=key)
        
        result = call_gemini_api(client, prompt, channel)
        if result:
            increment_usage(idx)
            return result
        
        # If we are here, this key failed. We'll wait a bit and try the next one.
        logger.warning(f"Key {idx} failed. Pacing rotation...")
        time.sleep(2)
    
    # Step 3: All keys failed or exhausted
    logger.error(f"All {len(GEMINI_KEYS)} keys failed or reached daily limit. Marking for review.")
    return None # We return None so main.py can set state to NEEDS_REVIEW

if __name__ == "__main__":
    # Test with sample lead data
    test_lead = {
        "name": "Sunrise Dental Clinic",
        "category": "Dental clinic",
        "city": "Abuja",
        "website": "",
        "rating": "4.5"
    }
    
    print("\n--- EMAIL TEST ---")
    print(generate_message(test_lead, channel="EMAIL"))
    
    print("\n--- WHATSAPP TEST ---")
    print(generate_message(test_lead, channel="WHATSAPP"))
