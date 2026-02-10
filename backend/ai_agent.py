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
GEMINI_CALLS_PER_MINUTE = 15  # Gemini has higher limits
ONE_MINUTE = 60

# Configure API clients
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

gemini_client = None

if GEMINI_API_KEY:
    try:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        logger.info("Gemini client initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize Gemini client: {e}")

# Company branding
COMPANY_NAME = "Anchor Digitals"
SENDER_NAME = "Peter"
COMPANY_DESCRIPTION = "a tech company specializing in digital solutions for local Nigerian businesses"

def build_email_prompt(lead_data: Dict) -> str:
    """Builds the AI prompt for dynamic email generation."""
    business_name = lead_data.get("name", "your business")
    category = lead_data.get("category", "business")
    city = lead_data.get("city") or "Abuja"
    has_website = bool(lead_data.get("website"))
    rating = lead_data.get("rating")
    
    # Build context based on available data
    context_notes = []
    if has_website:
        context_notes.append(f"I noticed you have a website at {lead_data.get('website')}")
    else:
        context_notes.append("I noticed you don't currently have a website")
    
    if rating and rating != "0":
        context_notes.append(f"and I saw your {rating}-star rating on Google")
    
    context_statement = " ".join(context_notes) + "."
    
    prompt = f"""You are {SENDER_NAME} from {COMPANY_NAME}, {COMPANY_DESCRIPTION}.

You are writing a VERY DIRECT and ACTIONABLE outreach email to a {category} business in {city}, Nigeria.

Business Details:
- Name: {business_name}
- Location: {city}
- Category: {category}
- Has Website: {"Yes" if has_website else "No"}

Research Context:
{context_statement}

Your Task:
1. Analyze this business type ({category}) and identify its most likely bottleneck (e.g., manual appointment tracking, poor online presence, or competition density in {city}).
2. Write a punchy, high-conversion email (MAX 150 words) that:
   - Skips the "I hope you are well" fluff.
   - Identifies a specific gap based on your analysis.
   - Offers a specific result local to {city} (e.g. "filling chairs" for salons, "securing bookings" for clinics).
   - Clear Call to Action: Ask for a brief chat or mention you'll be in the area.
   - Tone: Confident, Abuja-local, and professional.

Rules:
- NO passive language.
- Use active language ("I saw", "We solve", "Let's chat").
- Reference their {city} location.
- Do not speak pidgin be stricly professional.

Return ONLY valid JSON:
{{
  "subject": "Quick question for {business_name}",
  "message": "email body here"
}}
"""
    return prompt

def build_whatsapp_prompt(lead_data: Dict) -> str:
    """Builds the AI prompt for dynamic WhatsApp generation."""
    business_name = lead_data.get("name", "your business")
    category = lead_data.get("category", "business")
    city = lead_data.get("city") or "Abuja"
    has_website = bool(lead_data.get("website"))
    rating = lead_data.get("rating")
    
    prompt = f"""You are {SENDER_NAME} from {COMPANY_NAME}, {COMPANY_DESCRIPTION}.

You are writing a DIRECT WhatsApp message to {business_name}, a {category} in {city}.

Research Context:
- They {"have" if has_website else "don't have"} a website
- Found on Google Maps{f' with a {rating} rating' if rating and rating != "0" else ''}

Your Task:
1. Identify a quick pain point relevant to a {category} in {city}.
2. Write a brief, high-impact WhatsApp message (MAX 180 characters) that:
   - "Abuja Local" opener: "Hi! Peter from Anchor Digitals here in Abuja."
   - The Hook: Direct mention of a gap or their Maps presence.
   - The Value: "We help local {category}s automate their appointments/lead flow."
   - The CTA: "Can we chat for 2 mins?"

Rules:
- NO fluff. NO links.
- Use Nigerian English nuances (Abuja local).
- Under 180 chars.
- Do not speak pidgin ,be strictly professional.

Return ONLY valid JSON:
{{
  "message": "whatsapp message here"
}}
"""
    return prompt

def build_follow_up_prompt(lead_data: Dict) -> str:
    """Builds the AI prompt for dynamic follow-up generation."""
    business_name = lead_data.get("name", "your business")
    category = lead_data.get("category", "business")
    city = lead_data.get("city") or "Abuja"
    channel = lead_data.get("follow_up_channel", "WHATSAPP")
    
    prompt = f"""You are {SENDER_NAME} from {COMPANY_NAME}, {COMPANY_DESCRIPTION}.

You are writing a RESPECTFUL FOLLOW-UP (Nudge) message to {business_name}, a {category} in {city}.
You contacted them a few days ago regarding digital solutions/automation but haven't heard back.

Your Task:
1. Write a brief, non-intrusive nudge (Email: MAX 80 words, WhatsApp: MAX 140 chars).
2. Tone: Helpful, low-pressure, Abuja-local.
3. Hook: "Just circling back" or "Checking if you saw my last message."
4. Call to Action: "Is this something you'd be open to discussing briefly?"

Rules:
- NO guilt-tripping.
- Keep it extremely short.
- For WhatsApp, keep it under 140 characters.

Return ONLY valid JSON:
{{
  "message": "follow-up message here",
  "subject": "Quick follow up (if email)"
}}
"""
    return prompt

@sleep_and_retry
@limits(calls=GEMINI_CALLS_PER_MINUTE, period=ONE_MINUTE)
def generate_with_gemini(prompt: str, channel: str) -> Optional[Dict]:
    """Attempts to generate message using Gemini with rate limiting."""
    if not gemini_client:
        return None
    
    try:
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=prompt
        )
        
        response_text = response.text.strip()
        
        # Remove markdown code blocks
        if response_text.startswith("```"):
            lines = response_text.splitlines()
            if lines[0].startswith("```"):
                response_text = "\n".join(lines[1:-1])
        
        result = json.loads(response_text.strip())
        logger.info(f"Generated {channel} message via Gemini")
        return result
        
    except Exception as e:
        logger.warning(f"Gemini generation failed: {e}")
        return None

def generate_message_fallback(lead_data: Dict, channel: str) -> Dict:
    """Fallback template-based message generator."""
    business_name = lead_data.get("name", "your business")
    category = lead_data.get("category", "business")
    
    if channel == "EMAIL":
        return {
            "subject": f"Quick question about {business_name}",
            "message": f"Hi there,\n\nI noticed {business_name} on Google Maps and wanted to reach out. I'm Peter from Anchor Digitals in Abuja.\n\nWe help local {category}s automate their systems so they don't miss out on clients. Are you free for a 5-minute call this week?\n\nBest,\nPeter"
        }
    elif channel == "WHATSAPP":
        return {
            "message": f"Hi! Peter from Anchor Digitals here. Found {business_name} on Maps. We help Abuja {category}s automate appointments. Open to a 2 min chat?"
        }
    return None

def generate_message(lead_data: Dict, channel: str = "EMAIL") -> Optional[Dict]:
    """Generates message using Gemini with dynamic analysis."""
    try:
        # Build prompt based on channel
        if channel == "EMAIL":
            prompt = build_email_prompt(lead_data)
        elif channel == "WHATSAPP":
            prompt = build_whatsapp_prompt(lead_data)
        elif channel == "FOLLOW_UP":
            prompt = build_follow_up_prompt(lead_data)
        else:
            logger.error(f"Unsupported channel: {channel}")
            return None
        
        # Try Gemini as primary
        result = generate_with_gemini(prompt, channel)
        if result:
            # Validate character limits
            if channel == "WHATSAPP":
                message = result.get("message", "")
                if len(message) > 180:
                    logger.warning(f"WhatsApp message exceeds 180 chars: {len(message)}")
                    result["message"] = message[:177] + "..."
            return result
        
        # Use template fallback
        logger.info(f"Using template fallback for {channel} message")
        result = generate_message_fallback(lead_data, channel)
        return result
        
    except Exception as e:
        logger.error(f"Error generating message: {e}")
        return None

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
