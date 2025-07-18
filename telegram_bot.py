import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
import os

# Configure logging
logging.basicConfig(level=logging.INFO)

# Bot token and chat ID
BOT_TOKEN = "7542441675:AAHp4-AhVVydGsuSutxwJKVEp6EpJkQ-brk"
CHAT_ID = -1002717964198  # Updated with -100 prefix for channels

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Handle /start command"""
    await message.answer("Bot is running! Use /send_hello to send a message to the channel.")

@dp.message(Command("send_hello"))
async def cmd_send_hello(message: Message):
    """Send hello message to the specified channel"""
    try:
        await bot.send_message(chat_id=CHAT_ID, text="Hello from the bot! 👋")
        await message.answer("✅ Hello message sent successfully to the channel!")
    except Exception as e:
        await message.answer(f"❌ Error sending message: {str(e)}")

async def send_test_message():
    """Send a test hello message to the channel"""
    try:
        await bot.send_message(chat_id=CHAT_ID, text="Hello! This is a test message from the bot. 🚀")
        print("✅ Test message sent successfully!")
        return True
    except Exception as e:
        print(f"❌ Error sending test message: {str(e)}")
        return False

async def main():
    """Main function to run the bot"""
    print("🤖 Starting Telegram Bot...")
    print(f"📱 Bot Token: {BOT_TOKEN[:20]}...")
    print(f"💬 Target Chat ID: {CHAT_ID}")
    
    # Test connection by sending a hello message
    print("\n📤 Sending test message...")
    success = await send_test_message()
    
    if success:
        print("✅ Bot is working correctly!")
        print("🔄 Starting bot polling...")
        print("💡 You can now send /start or /send_hello to interact with the bot")
        
        # Start the bot
        await dp.start_polling(bot)
    else:
        print("❌ Bot failed to send test message. Please check your token and chat ID.")

if __name__ == "__main__":
    asyncio.run(main()) 