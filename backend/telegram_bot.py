import os
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from database import get_daily_status
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a greeting and help message."""
    await update.message.reply_text(
        "🚀 *Nigerian Outreach Monitor Ready*\n\n"
        "Commands:\n"
        "/stats - Show today's outreach metrics\n"
        "/status - Check current system state",
        parse_mode="Markdown"
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reports daily stats from the database."""
    data = get_daily_status()
    msg = (
        f"📊 *Daily Outreach Stats*\n\n"
        f"✅ *Messages Sent Today:* {data['sent_today']}/100\n"
        f"📂 *Total Unique Leads in DB:* {data['total_leads']}\n"
        f"📅 *Date:* {os.date if hasattr(os, 'date') else 'Today'}"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Placeholder for process status. In full deploy, would check service health."""
    await update.message.reply_text("✅ Service is running on Amazon EC2.")

async def send_notification(message: str):
    """Utility to send a message to the owner's chat ID."""
    if not TELEGRAM_TOKEN or not CHAT_ID:
        return
    
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    await app.bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown")

def run_bot():
    """Main entry point for the TG bot process."""
    if not TELEGRAM_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found in .env")
        return
        
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("status", status))
    
    print("Telegram bot polling...")
    app.run_polling()

if __name__ == "__main__":
    run_bot()
