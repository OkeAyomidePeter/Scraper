import os
import logging
import asyncio
from datetime import datetime
from sqlalchemy import and_
from models import Lead
from dotenv import load_dotenv
import aiohttp
import urllib.parse
import re

load_dotenv()

logger = logging.getLogger(__name__)

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
DAILY_SENT_LIMIT = 15
# Use PUBLIC_URL for Telegram buttons (e.g. EC2 IP), fallback to localhost
ACTION_API_BASE_URL = os.getenv("ACTION_API_PUBLIC_URL", "http://localhost:3063")

def escape_markdown_v2(text: str, is_code: bool = False) -> str:
    """Escapes characters for Telegram MarkdownV2."""
    if not text:
        return ""
    if is_code:
        return text.replace("\\", "\\\\").replace("`", "\\`")
    
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{c}" if c in escape_chars else c for c in text)

async def send_to_telegram(lead: Lead):
    """Sends separate messages for Email and WhatsApp drafts to Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("Telegram credentials missing in .env")
        return False

    success = True
    
    # Common Buttons for State Transitions (using callback_data instead of URL)
    # format: action:lead_id
    action_buttons = [
        {"text": "✅ Mark Sent", "callback_data": f"sent:{lead.id}"},
        {"text": "💬 Replied", "callback_data": f"replied:{lead.id}"}
    ]

    # 1. Send Email Draft if present
    if lead.email_draft:
        email_msg = f"📧 *EMAIL DRAFT for* {escape_markdown_v2(lead.business_name)}\n"
        email_msg += f"📍 *Category:* {escape_markdown_v2(lead.category or 'Business')}\n"
        email_msg += f"📧 *To:* `{escape_markdown_v2(lead.email or 'N/A')}`\n\n"
        email_msg += f"📋 *Subject:* `{escape_markdown_v2(lead.email_subject or 'Outreach')}`\n\n"
        email_msg += f"📝 *Copy Message \\(Tap to copy\\):*\n`{escape_markdown_v2(lead.email_draft, is_code=True)}`"
        
        keyboard = {"inline_keyboard": []}
        if lead.email:
            subject_enc = urllib.parse.quote(lead.email_subject or "Outreach")
            body_enc = urllib.parse.quote(lead.email_draft or "")
            mailto_link = f"mailto:{lead.email}?subject={subject_enc}&body={body_enc}"
            keyboard["inline_keyboard"].append([{"text": "📧 Open Mail App", "url": mailto_link}])
        
        keyboard["inline_keyboard"].append(action_buttons)
        
        res = await _call_telegram_api(email_msg, keyboard)
        if not res: success = False
        await asyncio.sleep(1)

    # 2. Send WhatsApp Draft if present
    if lead.whatsapp_draft:
        wa_msg = f"🟢 *WHATSAPP DRAFT for* {escape_markdown_v2(lead.business_name)}\n"
        wa_msg += f"📱 *To:* `{escape_markdown_v2(lead.phone_number or 'N/A')}`\n\n"
        wa_msg += f"📝 *Copy Message \\(Tap to copy\\):*\n`{escape_markdown_v2(lead.whatsapp_draft, is_code=True)}`"
        
        keyboard = {"inline_keyboard": []}
        if lead.phone_number and lead.phone_number != "N/A":
            hp = re.sub(r'\D', '', lead.phone_number)
            if len(hp) >= 10:
                if not hp.startswith('234'): hp = '234' + hp.lstrip('0')
                msg_enc = urllib.parse.quote(lead.whatsapp_draft or "")
                wa_link = f"https://wa.me/{hp}?text={msg_enc}"
                keyboard["inline_keyboard"].append([{"text": "💬 Open WhatsApp", "url": wa_link}])
            
        keyboard["inline_keyboard"].append(action_buttons)
            
        res = await _call_telegram_api(wa_msg, keyboard)
        if not res: success = False

    return success

async def _call_telegram_api(text: str, reply_markup: dict = None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "MarkdownV2",
        "reply_markup": reply_markup
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    return True
                else:
                    err_text = await response.text()
                    logger.error(f"Telegram API Error: {err_text}")
                    return False
    except Exception as e:
        logger.error(f"Telegram request failed: {e}")
        return False

async def process_telegram_queue(db):
    """Checks the budget and sends drafted leads to Telegram."""
    try:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        sent_today = db.query(Lead).filter(
            and_(Lead.is_queued == True, Lead.queued_at >= today_start)
        ).count()
        
        remaining = DAILY_SENT_LIMIT - sent_today
        if remaining <= 0:
            logger.info("Daily budget reached.")
            return 0

        drafts = db.query(Lead).filter(
            and_(Lead.state == 'DRAFTED', Lead.is_queued == False)
        ).order_by(Lead.created_at.asc()).limit(remaining).all()

        sent_count = 0
        for lead in drafts:
            if await send_to_telegram(lead):
                lead.is_queued = True
                lead.queued_at = datetime.utcnow()
                lead.state = 'QUEUED'
                sent_count += 1
                await asyncio.sleep(1)
        
        db.commit()
        return sent_count
    except Exception as e:
        logger.error(f"Queue processing error: {e}")
        db.rollback()
        return 0
