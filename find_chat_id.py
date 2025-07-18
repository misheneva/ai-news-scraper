import asyncio
from aiogram import Bot

# Bot token
BOT_TOKEN = "7542441675:AAHp4-AhVVydGsuSutxwJKVEp6EpJkQ-brk"

async def find_chat_info():
    """Find information about available chats"""
    bot = Bot(token=BOT_TOKEN)
    
    try:
        print("🤖 Bot Information:")
        bot_info = await bot.get_me()
        print(f"📋 Bot Name: {bot_info.first_name}")
        print(f"🆔 Bot Username: @{bot_info.username}")
        print(f"🆔 Bot ID: {bot_info.id}")
        
        print("\n💡 To find your chat ID:")
        print("1. Add the bot to your channel as an admin")
        print("2. Send a message in the channel")
        print("3. Visit: https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates")
        print("4. Look for 'chat' -> 'id' in the response")
        
        print(f"\n🔗 Direct link for your bot:")
        print(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates")
        
        print("\n📝 Common chat ID formats:")
        print("- Private chat: positive number (e.g., 123456789)")
        print("- Group: negative number starting with - (e.g., -123456789)")
        print("- Channel: negative number starting with -100 (e.g., -100123456789)")
        
        print(f"\n🎯 Your current chat ID: -2717964198")
        print("   This might need to be: -1002717964198 (with -100 prefix)")
        
        # Test with the -100 prefix
        test_chat_id = -1002717964198
        print(f"\n🧪 Testing with -100 prefix: {test_chat_id}")
        try:
            await bot.send_message(chat_id=test_chat_id, text="Test message with -100 prefix")
            print("✅ Success with -100 prefix!")
        except Exception as e:
            print(f"❌ Failed with -100 prefix: {str(e)}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(find_chat_info()) 