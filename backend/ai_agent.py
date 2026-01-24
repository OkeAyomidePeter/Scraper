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

def generate_outreach_message(lead: dict) -> str:
    """
    Generates a personalized, "homely" outreach message using Google Gemini.
    Selects a specific prompt template based on business reputation.
    """
    if not limiter.wait_if_needed():
        return "Rate limit reached."

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
        # High Reputation
        reputation_focus = (
            f"Reference their exceptional {rating}-star reputation and {reviews} reviews on Google Maps. "
            "Congratulate them on being a top-rated business in their area. "
            "Highlight how a professional website will solidify this elite status."
        )
    elif rating > 0:
        # Mid Reputation
        reputation_focus = (
            f"Reference their {rating}-star rating as a great sign of trust. "
            "Encourage them that they are already doing well and a professional website "
            "is the missing piece to competing with the biggest names in the industry."
        )
    else:
        # No/Low Reputation
        reputation_focus = (
            "Acknowledge their presence on Google Maps as a visible business. "
            "Focus heavily on how a professional website establishes initial credibility and trust "
            "for new customers who don't see many reviews yet."
        )

    model = genai.GenerativeModel('gemini-2.5-flash-lite')
    
    prompt = f"""
    You are {sender_name}, representing {company_name}, a professional tech consultancy in Nigeria. 
    Your goal is to help reputable local businesses transition to a professional digital presence.
    
    Write a short, professional, yet warm WhatsApp message to a business owner.
    
    Business Details:
    - Name: {business_name}
    - Category: {category}
    - Google Maps Stats: {rating} stars, {reviews} reviews.
    
    Outreach Strategy:
    {reputation_focus}
    
    Trust-Building Context (Nigeria):
    Nigerian business owners are often skeptical of online outreach. To build trust:
    1. Introduce yourself clearly as {sender_name} from {company_name}.
    2. Reference their specific Google Maps achievements genuinely.
    3. Keep it "homely" (local professional tone/warmth) but strictly professional.
    4. NO 'Dear Sir/Ma'. Use a warm opening like 'Hello {business_name} team' or just 'Hi there!'.
    5. NO pidgin, NO excessive emojis. Keep it clean and high-value.
    
    Requirements:
    - Length: CONCISE (WhatsApp optimized).
    - Call to Action: Ask if they'd be open to a brief chat or call to discuss growth.
    - Important: Focus ONLY on {business_name}.
    - Important: NO placeholders like '[Your Name]'.
    """

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Error generating message with Gemini: {e}")
        # Homely fallback template
        return (
            f"Hello {business_name}! 👋 I'm {sender_name} from {company_name}. "
            f"I was checking your business on Google Maps and saw your {rating} rating. "
            "I noticed you don't have a website yet—I help local businesses in Nigeria "
            "build a professional digital home to establish more trust and reach more customers. "
            "Would you be open to a quick chat? 🚀"
        )

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
