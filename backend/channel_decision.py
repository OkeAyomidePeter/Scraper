import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

def decide_channels(lead_data: Dict) -> List[str]:
    """
    Decides the outreach channels based on available contact information.
    
    Logic:
    - If website exists: Generate both EMAIL and WHATSAPP
    - If no website but has phone: Generate only WHATSAPP
    - Otherwise: NONE
    
    Args:
        lead_data: Dictionary containing lead information
    
    Returns:
        List of channels: ["EMAIL", "WHATSAPP"], ["WHATSAPP"], or []
    """
    website = lead_data.get("website", "").strip()
    # Ensure it's not an ad link or an internal google link
    has_website = bool(website) and not any(term in website for term in ["/aclk", "googleadservices", "google.com/maps"])
    
    phone = (lead_data.get("normalized_phone") or lead_data.get("phone", "")).strip()
    
    channels = []
    
    # If they have a website, generate both channels
    if has_website:
        channels.append("EMAIL")
        channels.append("WHATSAPP")
        logger.info(f"Channel decision for {lead_data.get('name')}: EMAIL + WHATSAPP (has website)")
    # If no website but have any phone number, only WhatsApp
    elif phone and phone != "N/A":
        channels.append("WHATSAPP")
        logger.info(f"Channel decision for {lead_data.get('name')}: WHATSAPP only (no website)")
    else:
        logger.warning(f"No viable channel for {lead_data.get('name')}")
    
    return channels
