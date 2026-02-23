import os
import asyncio
import logging
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
# from database import get_daily_status # This was causing issues if not defined, let's keep it if it exists or mock
from dotenv import load_dotenv

load_dotenv()

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
ACTION_API_URL = "http://localhost:3063/action"

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("🚀 *Outreach Control Bot Active*\n\nMonitoring leads and handling state transitions.", parse_mode="Markdown")

@dp.callback_query(F.data.startswith("sent:"))
async def handle_sent_callback(callback: types.CallbackQuery):
    lead_id = callback.data.split(":")[1]
    logger.info(f"Callback received: sent:{lead_id}")
    async with aiohttp.ClientSession() as session:
        url = f"{ACTION_API_URL}/sent/{lead_id}"
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    await callback.answer(data.get("message", "Marked as SENT"))
                    
                    # Edit message to remove buttons and show status
                    if callback.message.text:
                        # Escape special chars for MarkdownV2 if necessary, but simple append here
                        new_text = callback.message.text + "\n\n✅ *Status: SENT*"
                        await callback.message.edit_text(new_text, parse_mode="Markdown", reply_markup=None)
                else:
                    logger.error(f"API Error: {resp.status} for {url}")
                    await callback.answer("Error updating state", show_alert=True)
        except Exception as e:
            logger.error(f"Failed to connect to Action API: {e}")
            await callback.answer("API Connection Failed", show_alert=True)

@dp.callback_query(F.data.startswith("replied:"))
async def handle_replied_callback(callback: types.CallbackQuery):
    lead_id = callback.data.split(":")[1]
    logger.info(f"Callback received: replied:{lead_id}")
    async with aiohttp.ClientSession() as session:
        url = f"{ACTION_API_URL}/replied/{lead_id}"
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    await callback.answer(data.get("message", "Marked as REPLIED"))
                    
                    if callback.message.text:
                        new_text = callback.message.text + "\n\n💬 *Status: REPLIED*"
                        await callback.message.edit_text(new_text, parse_mode="Markdown", reply_markup=None)
                else:
                    logger.error(f"API Error: {resp.status} for {url}")
                    await callback.answer("Error updating state", show_alert=True)
        except Exception as e:
            logger.error(f"Failed to connect to Action API: {e}")
            await callback.answer("API Connection Failed", show_alert=True)

async def main():
    logger.info("Starting Telegram Bot listener...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    if TELEGRAM_TOKEN:
        asyncio.run(main())
    else:
        logger.error("TELEGRAM_BOT_TOKEN not found")
