import re

def normalize_phone(phone_str: str) -> str:
    """Cleans and normalizes Nigerian phone numbers to international format."""
    if not phone_str or phone_str == "N/A":
        return ""
    
    # Remove all non-numeric characters
    digits = re.sub(r'\D', '', phone_str)
    
    # Handle Nigeria local formats
    if digits.startswith('0') and len(digits) == 11:
        return '234' + digits[1:]
    elif digits.startswith('234'):
        return digits
    elif len(digits) == 10:
        return '234' + digits
    
    return digits
