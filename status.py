"""
Status script for AI News Scraper
Shows current system status and statistics
"""

import asyncio
from database import NewsDatabase
from telegram_publisher import TelegramPublisher
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

async def show_status():
    """Display system status"""
    print("🤖 AI News Scraper - System Status")
    print("=" * 50)
    
    # Database status
    db = NewsDatabase()
    total_articles = db.get_processed_count()
    recent_articles = db.get_recent_articles(5)
    
    print(f"📊 Database Statistics:")
    print(f"   Total articles processed: {total_articles}")
    
    if recent_articles:
        print(f"\n📰 Recent Articles:")
        for i, (url, title, source, timestamp) in enumerate(recent_articles, 1):
            print(f"   {i}. {title[:60]}... ({source})")
    
    # Test Telegram connection
    print(f"\n📱 Telegram Status:")
    publisher = TelegramPublisher()
    try:
        if await publisher.test_connection():
            print("   ✅ Bot connected successfully")
            print(f"   📋 Bot: AI_info_parser (@AI_info_parser_bot)")
            print(f"   💬 Channel ID: {TELEGRAM_CHAT_ID}")
        else:
            print("   ❌ Bot connection failed")
    except Exception as e:
        print(f"   ❌ Error testing connection: {e}")
    finally:
        await publisher.close()
    
    print(f"\n🔧 System Configuration:")
    print(f"   Sources: VentureBeat AI, TechCrunch AI, SCMP Tech")
    print(f"   Database: news_articles.db")
    print(f"   Log file: ai_news_scraper.log")
    
    print(f"\n🚀 Usage:")
    print(f"   Run once: python3 main.py --once")
    print(f"   Run scheduled: python3 main.py")
    print(f"   Test scraping: python3 test_scraping.py")

if __name__ == "__main__":
    asyncio.run(show_status()) 