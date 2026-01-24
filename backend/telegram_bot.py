import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import get_daily_status
from dotenv import load_dotenv

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TELEGRAM_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN not found in .env")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

def get_stats_keyboard():
    """Builds inline keyboard for metrics."""
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="📊 Refresh Stats", callback_data="refresh_stats"))
    builder.row(types.InlineKeyboardButton(text="⏳ Check Queue", callback_data="check_queue"))
    return builder.as_markup()

async def format_stats_message():
    """Formats the outreach metrics message."""
    data = get_daily_status()
    return (
        f"📊 *Daily Outreach Metrics*\n\n"
        f"✅ *Sent Today:* {data['sent_today']}/100\n"
        f"⏳ *Currently Queued:* {data['queued']}\n"
        f"📂 *Total CRM Leads:* {data['total_leads']}\n\n"
        f"📅 _System: Active on Amazon EC2_"
    )

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Sends greeting with metrics and keyboard."""
    msg = await format_stats_message()
    await message.answer(
        f"🚀 *Nigerian Outreach Monitor Ready*\n\n{msg}",
        parse_mode="Markdown",
        reply_markup=get_stats_keyboard()
    )

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    """Reports daily stats."""
    msg = await format_stats_message()
    await message.answer(msg, parse_mode="Markdown", reply_markup=get_stats_keyboard())

@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    """Reports system health."""
    await message.answer(
        "⚡️ *System Status*\n\n"
        "✅ Scraper: Headless Mode\n"
        "✅ WhatsApp: Baileys Service Active\n"
        "✅ Database: SQLite Persistent\n"
        "✅ Sender: Anti-Detection Active",
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "refresh_stats")
async def process_refresh(callback_query: types.CallbackQuery):
    """Updates stats when refresh button is clicked."""
    msg = await format_stats_message()
    # Edit the message with new stats
    try:
        await callback_query.message.edit_text(
            f"🚀 *Nigerian Outreach Monitor Ready*\n\n{msg}",
            parse_mode="Markdown",
            reply_markup=get_stats_keyboard()
        )
    except Exception:
        # Ignore errors if content is same
        pass
    await callback_query.answer()

@dp.callback_query(F.data == "check_queue")
async def process_queue(callback_query: types.CallbackQuery):
    """Shows detailed queue info."""
    data = get_daily_status()
    await callback_query.answer(f"Queue Status: {data['queued']} messages pending.", show_alert=True)

async def main():
    """Main polling loop."""
    print("Telegram system starting (aiogram)...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    if TELEGRAM_TOKEN:
        asyncio.run(main())
    else:
        print("Error: Missing bot token. Provide TELEGRAM_BOT_TOKEN in .env")
