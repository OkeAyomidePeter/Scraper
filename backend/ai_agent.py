import os
import time
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

class RateLimiter:
    def __init__(self, rpm_limit=10, daily_limit=250):
        self.rpm_limit = rpm_limit
        self.daily_limit = daily_limit
        self.request_times = []
        self.daily_count = 0
        self.last_reset = time.time()

    def _reset_daily_if_needed(self):
        # Reset daily count every 24 hours
        if time.time() - self.last_reset > 86400:
            self.daily_count = 0
            self.last_reset = time.time()

    def wait_if_needed(self):
        self._reset_daily_if_needed()
        
        if self.daily_count >= self.daily_limit:
            print("Daily limit reached. 250/250 messages generated today.")
            return False

        now = time.time()
        # Filter requests from the last minute
        self.request_times = [t for t in self.request_times if now - t < 60]
        
        if len(self.request_times) >= self.rpm_limit:
            wait_time = 60 - (now - self.request_times[0])
            if wait_time > 0:
                print(f"Rate limit reached. Waiting {wait_time:.2f} seconds...")
                time.sleep(wait_time)
        
        self.request_times.append(time.time())
        self.daily_count += 1
        return True

# Global rate limiter
limiter = RateLimiter(rpm_limit=10, daily_limit=250)

def get_fallback_message(lead: dict) -> str:
    """Provides a high-quality, personalized fallback when AI fails."""
    business_name = lead.get("name", "there")
    sender_name = "Oke Ayomide Peter"
    company_name = "Invictus Global"
    
    # Simple logic to varied fallback
    try:
        rating = float(lead.get("rating", 0.0))
    except:
        rating = 0.0

    if rating >= 4.0:
        return (
            f"Hello {business_name}! 👋 I'm {sender_name} from {company_name}. "
            f"I saw your impressive {rating}-star rating on Google Maps. "
            "I noticed you don't have a website yet—I help top-rated Nigerian businesses "
            "build a professional digital home to reach even more customers. "
            "Would you be open to a quick chat? 🚀"
        )
    else:
        return (
            f"Hello {business_name}! 👋 I'm {sender_name} from {company_name}. "
            "I was looking at your business listing on Google Maps and noticed you "
            "don't have a professional website yet. I help local businesses in Nigeria "
            "build a digital presence that builds trust and brings in more customers. "
            "Would you be open to a brief chat about this? ✨"
        )

def generate_outreach_message(lead: dict) -> str:
    """
    Generates a personalized outreach message using Google Gemini.
    Returns a high-quality fallback if API fails or rate limit is reached.
    """
    if not limiter.wait_if_needed():
        print(f"Rate limit hit for {lead.get('name')}. Using fallback.")
        return get_fallback_message(lead)

    business_name = lead.get("name", "there")
    try:
        rating = float(lead.get("rating", 0) or 0)
    except (ValueError, TypeError):
        rating = 0.0
        
    try:
        reviews = int(lead.get("reviews", 0) or 0)
    except (ValueError, TypeError):
        reviews = 0
        
    category = lead.get("category", "business")
    
    sender_name = "Oke Ayomide Peter"
    company_name = "Invictus Global"

    # Reputation-aware Prompt Logic
    if rating >= 4.0 and reviews >= 5:
        reputation_focus = f"Reference their exceptional {rating}-star reputation and {reviews} reviews. Congratulate them."
    elif rating > 0:
        reputation_focus = f"Reference their {rating}-star rating as a great sign of trust."
    else:
        reputation_focus = "Focus on how a professional website establishes initial credibility."

    model = genai.GenerativeModel('gemini-1.5-flash-lite')
    
    prompt = f"""
    You are {sender_name}, representing {company_name}, a professional tech consultancy in Nigeria. 
    Write a short, professional, warm WhatsApp message to {business_name}.
    
    Details: {business_name}, {category}, {rating} stars, {reviews} reviews.
    Strategy: {reputation_focus}
    
    Trust-Building Context (Nigeria):
    1. Introduce yourself clearly as {sender_name} from {company_name}.
    2. Reference their specific Google Maps achievements genuinely.
    3. Keep it warm but strictly professional. No 'Dear Sir/Ma'.
    4. NO placeholders like '[Your Name]'.
    
    Length: CONCISE (WhatsApp optimized).
    """

    try:
        response = model.generate_content(prompt)
        # Verify response isn't empty or an error
        if response and response.text:
            return response.text.strip()
        else:
            raise ValueError("Empty AI response")
    except Exception as e:
        print(f"AI Generation failed for {business_name}: {e}. Using fallback.")
        return get_fallback_message(lead)

if __name__ == "__main__":
    # Test cases for different reputations
    test_leads = [
        {"name": "Elite Academy", "category": "School", "rating": "4.8", "reviews": "45"},
        {"name": "Local Shop", "category": "Retail", "rating": "3.5", "reviews": "2"},
        {"name": "New Business", "category": "Services", "rating": "0", "reviews": "0"}
    ]
    
    for lead in test_leads:
        print(f"\n--- Testing for: {lead['name']} ---")
        print(generate_outreach_message(lead))
        print("-" * 30)
