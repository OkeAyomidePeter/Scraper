import re

def normalize_phone(phone: str) -> str:
    """
    Normalizes a Nigerian phone number to +234XXXXXXXXXX format.
    """
    if not phone:
        return ""
    
    # Remove all non-numeric characters
    cleaned = re.sub(r'\D', '', phone)
    
    # If it starts with 0 and has 11 digits (e.g., 0803...)
    if cleaned.startswith('0') and len(cleaned) == 11:
        return "+234" + cleaned[1:]
    
    # If it starts with 234
    if cleaned.startswith('234') and len(cleaned) == 13:
        return "+" + cleaned
    
    # If it's already +234
    if phone.startswith('+234'):
        return "+" + cleaned
        
    return phone

def is_valid_whatsapp(phone: str) -> bool:
    """
    Checks if a normalized phone number is likely a WhatsApp-ready mobile number.
    Nigerian mobile prefixes: 080, 070, 090, 081, 091
    """
    normalized = normalize_phone(phone)
    if not normalized.startswith('+234'):
        return False
        
    # Standard Nigerian mobile number length is 14 including +234
    if len(normalized) != 14:
        return False
        
    return True

def filter_leads(leads: list) -> list:
    """
    Filters out leads that already have a website.
    Social media sites (FB, IG, WhatsApp) are NOT considered websites.
    """
    social_domains = ['facebook.com', 'instagram.com', 'wa.me', 'whatsapp.com']
    
    filtered = []
    for lead in leads:
        website = lead.get('website', '').lower()
        
        if not website:
            lead['has_website'] = False
            filtered.append(lead)
            continue
            
        # Check if it's just a social media link
        is_social = any(domain in website for domain in social_domains)
        if is_social:
            lead['has_website'] = False
            filtered.append(lead)
        else:
            # Has a real website, exclude
            pass
            
    return filtered

def calculate_priority(lead: str) -> int:
    """
    Simple scoring formula:
    - No website: +5 (already filtered but for future use)
    - Rating >= 3.5: +2
    - Reviews >= 5: +2
    """
    score = 0
    if not lead.get('website'):
        score += 5
    
    try:
        rating = float(lead.get('rating', 0))
        if rating >= 3.5:
            score += 2
    except (ValueError, TypeError):
        pass
        
    try:
        reviews = int(lead.get('reviews', 0))
        if reviews >= 5:
            score += 2
    except (ValueError, TypeError):
        pass
        
    return score
