"""
AI News Scraper and Telegram Publisher - Main Application
"""

import asyncio
import logging
import sys
import json
from datetime import datetime
from typing import List, Dict

from config import LOG_LEVEL, LOG_FORMAT, X_USERNAME, X_USER_ID
from database import NewsDatabase
from scraper import NewsScraper, TwitterFetcher
from telegram_publisher import TelegramPublisher
from classifier import ContentClassifier
from summarizer import NewsSummarizer
import httpx

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler('ai_news_scraper.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class AINewsScraperApp:
    def __init__(self):
        self.database = NewsDatabase()
        self.scraper = NewsScraper()
        self.publisher = TelegramPublisher()
        self.classifier = ContentClassifier()
        self.summarizer = NewsSummarizer()
    
    async def process_articles(self, articles: List[Dict]) -> int:
        """Process and publish articles to Telegram"""
        published_count = 0
        
        for article in articles:
            # Check if article already processed
            if self.database.is_article_processed(article['url']):
                logger.info(f"Article already processed: {article['title']}")
                continue
            
            # Classify the article
            text_to_classify = f"{article['title']} {article['content'][:200]}"
            category, confidence = self.classifier.classify_content(text_to_classify)
            logger.info(f"Article classified as: {category} (confidence: {confidence:.3f})")
            
            # Summarize article if it's from news sources (not X/Twitter)
            content = article['content']
            if self.summarizer.should_summarize(article.get('source', '')):
                logger.info(f"Summarizing article: {article['title']}")
                content = self.summarizer.summarize_article(article['title'], article['content'])
            
            # Prepare article for publishing
            article_to_publish = {
                'title': article['title'],
                'content': content,
                'source': article['source'],
                'url': article['url'],
                'classification': category
            }
            
            # Send to Telegram
            success = await self.publisher.send_article(article_to_publish)
            
            if success:
                # Mark as processed in database
                self.database.mark_article_processed(article['url'], article['title'], article['source'])
                published_count += 1
                logger.info(f"Published article: {article['title']}")
            else:
                logger.error(f"Failed to publish article: {article['title']}")
            
            # Small delay between articles
            await asyncio.sleep(1)
        
        return published_count
    
    async def run_scraping_cycle(self) -> Dict:
        """Run a complete scraping and publishing cycle"""
        start_time = datetime.now()
        logger.info("🚀 Starting AI News Scraping Cycle")
        
        try:
            # Test Telegram connection
            if not await self.publisher.test_connection():
                logger.error("Failed to connect to Telegram")
                return {"success": False, "error": "Telegram connection failed"}
            
            # Scrape articles from all sources (10 articles per source)
            logger.info("📰 Scraping articles from all sources...")
            articles = self.scraper.scrape_all_sources(limit_per_source=10)
            
            if not articles:
                logger.warning("No articles found from any source")
                return {"success": True, "articles_found": 0, "published": 0}
            
            # Process and publish articles
            logger.info(f"📤 Processing {len(articles)} articles...")
            published_count = await self.process_articles(articles)
            
            # Send completion status
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            completion_msg = (
                f"✅ *Scraping Cycle Complete*\n\n"
                f"📊 *Statistics:*\n"
                f"• Articles found: {len(articles)}\n"
                f"• Articles published: {published_count}\n"
                f"• Duration: {duration:.1f} seconds\n"
                f"• Total processed: {self.database.get_processed_count()}"
            )
            
            await self.publisher.send_status_message(completion_msg)
            
            return {
                "success": True,
                "articles_found": len(articles),
                "published": published_count,
                "duration": duration
            }
            
        except Exception as e:
            logger.error(f"Error in scraping cycle: {e}")
            error_msg = f"❌ *Scraping Error*\n\nError: {str(e)}"
            await self.publisher.send_status_message(error_msg)
            return {"success": False, "error": str(e)}
    
    async def run_once(self):
        """Run the scraper once"""
        result = await self.run_scraping_cycle()
        
        if result["success"]:
            logger.info(f"✅ Cycle completed successfully: {result['published']} articles published")
        else:
            logger.error(f"❌ Cycle failed: {result.get('error', 'Unknown error')}")
        
        await self.publisher.close()
    
    async def run_scheduled(self, schedule_hours: int = 1):
        """Run the main and Twitter cycles on schedule"""
        logger.info(f"🕐 Starting scheduled scraper (every {schedule_hours} hours)")
        schedule.every(schedule_hours).hours.do(lambda: asyncio.create_task(self.run_scraping_cycle()))
        schedule.every(1).hours.do(lambda: asyncio.create_task(self.run_twitter_cycle()))  # Changed from 15 minutes to 1 hour
        while True:
            schedule.run_pending()
            await asyncio.sleep(10)

    async def process_tweets(self):
        fetcher = TwitterFetcher()
        publisher = self.publisher
        db = self.database
        try:
            tweets = await fetcher.fetch_new_tweets()
            if not tweets:
                logger.info("No new tweets found (might be due to rate limiting or no new content)")
                return 0
            logger.info(f"Found {len(tweets)} new tweets to publish")
            sent_count = 0
            for tweet in tweets:
                # Always save tweet ID to prevent duplicates, regardless of send success
                tweet_id = tweet.get("post_id", tweet.get("id"))
                
                # For new format, we don't need to pass username separately
                success = await publisher.send_tweet(tweet)
                if success:
                    sent_count += 1
                    logger.info(f"Successfully sent tweet: {tweet_id}")
                else:
                    logger.error(f"Failed to send tweet: {tweet_id}")
                
                # Always update last tweet ID to prevent duplicates
                db.set_last_tweet_id(X_USER_ID, tweet_id)
                await asyncio.sleep(1)
            logger.info(f"Sent {sent_count}/{len(tweets)} tweets successfully")
            return sent_count
        except Exception as e:
            logger.error(f"Error processing tweets: {e}")
            return 0
    
    async def check_api_status(self):
        """Check X API status and rate limits"""
        fetcher = TwitterFetcher()
        try:
            headers = {"Authorization": f"Bearer {fetcher.bearer_token}"}
            async with httpx.AsyncClient(timeout=10) as client:
                # Test basic API access
                resp = await client.get("https://api.twitter.com/2/users/me", headers=headers)
                
                if resp.status_code == 200:
                    logger.info("✅ X API connection successful")
                    data = resp.json()
                    logger.info(f"Connected as: {data.get('data', {}).get('username', 'Unknown')}")
                elif resp.status_code == 429:
                    retry_after = resp.headers.get('x-rate-limit-reset', 'Unknown')
                    logger.error(f"❌ Rate limit exceeded. Reset at: {retry_after}")
                elif resp.status_code == 401:
                    logger.error("❌ Invalid Bearer Token")
                else:
                    logger.error(f"❌ API Error: {resp.status_code} - {resp.text}")
                    
        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
    
    async def test_news_classifier(self):
        """Test classifier on real news articles"""
        print("🧠 Testing classifier on real news articles...")
        print("=" * 60)
        
        # Try to get articles from sources
        articles = self.scraper.scrape_all_sources(limit_per_source=5)
        
        # If no articles found, use sample articles
        if not articles:
            print("⚠️  No articles found from sources, using sample articles")
            articles = [
                {
                    'title': 'OpenAI Launches GPT-5 with Revolutionary Multimodal Capabilities',
                    'content': 'OpenAI has announced the release of GPT-5, featuring groundbreaking multimodal capabilities that can process text, images, audio, and video simultaneously. The new model represents a significant advancement in artificial intelligence technology.',
                    'source': 'Sample Tech News',
                    'url': 'https://example.com/gpt5-launch'
                },
                {
                    'title': 'Google DeepMind Publishes Research on Quantum AI Breakthrough',
                    'content': 'Researchers at Google DeepMind have published a groundbreaking study demonstrating how quantum computing can accelerate machine learning algorithms. The research shows promising results for solving complex optimization problems.',
                    'source': 'Sample AI Research',
                    'url': 'https://example.com/deepmind-quantum'
                },
                {
                    'title': 'Meta CEO Mark Zuckerberg Announces $50 Billion AI Investment',
                    'content': 'Meta CEO Mark Zuckerberg revealed plans to invest $50 billion in artificial intelligence research and development over the next five years. The investment will focus on developing next-generation AI models and infrastructure.',
                    'source': 'Sample Business News',
                    'url': 'https://example.com/meta-investment'
                },
                {
                    'title': 'Microsoft Releases Major Update to Azure AI Services',
                    'content': 'Microsoft has rolled out a comprehensive update to its Azure AI services, introducing new machine learning tools and enhanced natural language processing capabilities. The update includes improved integration with existing Microsoft products.',
                    'source': 'Sample Tech Updates',
                    'url': 'https://example.com/azure-update'
                },
                {
                    'title': 'Stanford Researchers Develop New AI Model for Drug Discovery',
                    'content': 'A team of researchers at Stanford University has developed an innovative AI model that can predict drug interactions and accelerate the drug discovery process. The model has shown promising results in preliminary tests.',
                    'source': 'Sample Research News',
                    'url': 'https://example.com/stanford-drug-ai'
                }
            ]
        
        classifier = ContentClassifier()
        
        # Test on first 5 articles
        test_articles = articles[:5]
        
        for i, article in enumerate(test_articles, 1):
            print(f"\n📰 Article {i}:")
            print(f"Title: {article['title'][:80]}...")
            print(f"Source: {article['source']}")
            
            # Classify based on title + first part of content
            text_to_classify = f"{article['title']} {article['content'][:200]}"
            category, confidence = classifier.classify_content(text_to_classify)
            
            print(f"🏷️  Category: {category}")
            print(f"📊 Confidence: {confidence:.3f}")
            print("-" * 40)
        
        print(f"\n✅ Tested classifier on {len(test_articles)} articles")
    
    async def test_summarizer(self):
        """Test summarization on a sample article"""
        print("📝 Testing summarization on sample article...")
        print("=" * 60)
        
        # Sample article for testing
        sample_article = {
            'title': 'Artificial Intelligence Transforms Healthcare Industry with Revolutionary Diagnostic Tools',
            'content': '''Artificial intelligence is revolutionizing the healthcare industry through the development of sophisticated diagnostic tools that can detect diseases earlier and more accurately than traditional methods. Machine learning algorithms are being trained on vast datasets of medical images, patient records, and clinical data to identify patterns that human doctors might miss.

Recent breakthroughs in AI-powered medical imaging have shown remarkable results in detecting cancer, heart disease, and neurological conditions. For example, Google's DeepMind has developed an AI system that can diagnose over 50 eye diseases with 94% accuracy, matching the performance of world-leading experts. Similarly, researchers at Stanford University have created a deep learning model that can identify skin cancer from photographs with the same accuracy as dermatologists.

The integration of AI in healthcare extends beyond diagnosis to treatment planning and drug discovery. AI systems can analyze patient data to recommend personalized treatment plans, predict treatment outcomes, and identify potential drug interactions. Pharmaceutical companies are using machine learning to accelerate the drug discovery process, reducing the time and cost required to bring new medications to market.

However, the adoption of AI in healthcare faces several challenges, including regulatory approval, data privacy concerns, and the need for extensive validation. Medical professionals also need training to effectively use these new tools, and healthcare systems must invest in the necessary infrastructure to support AI implementation.

Despite these challenges, the potential benefits of AI in healthcare are enormous. Early detection of diseases can save lives and reduce treatment costs, while personalized medicine can improve patient outcomes and reduce adverse reactions. As AI technology continues to advance, we can expect to see even more innovative applications in healthcare, potentially transforming how we prevent, diagnose, and treat diseases.

The future of healthcare will likely be characterized by the seamless integration of human expertise and artificial intelligence, creating a more efficient, accurate, and accessible healthcare system for patients worldwide.''',
            'source': 'VentureBeat AI'
        }
        
        print(f"📰 Original Article:")
        print(f"Title: {sample_article['title']}")
        print(f"Content length: {len(sample_article['content'])} characters")
        print(f"Source: {sample_article['source']}")
        
        # Test summarization
        print(f"\n🔄 Summarizing article...")
        summary = self.summarizer.summarize_article(
            sample_article['title'], 
            sample_article['content']
        )
        
        print(f"\n📝 Summary ({len(summary)} characters):")
        print("=" * 60)
        print(summary)
        print("=" * 60)
        
        # Test should_summarize method
        should_summarize_news = self.summarizer.should_summarize("VentureBeat AI")
        should_summarize_twitter = self.summarizer.should_summarize("Twitter")
        
        print(f"\n🔍 Summarization Rules:")
        print(f"News sources (VentureBeat AI): {should_summarize_news}")
        print(f"Twitter/X sources: {should_summarize_twitter}")
        
        print(f"\n✅ Summarization test completed")
    
    async def debug_tweets(self, username: str = None):
        """Debug tweets - reset ID and fetch fresh tweets to analyze media"""
        target_user = username or "TwitterDev"
        print(f"🐛 Debug: Fetching fresh tweets from @{target_user} for media analysis...")
        print("=" * 60)
        
        # For custom usernames, we'd need to get user ID first
        # For now, we'll use TwitterDev ID but note the limitation
        user_id = X_USER_ID  # This is TwitterDev's ID
        
        if username and username.lower() != "twitterdev":
            print(f"⚠️  Note: Currently only supports TwitterDev. Username '{username}' will be ignored.")
            print("To support other accounts, we'd need to implement user lookup by username.")
        
        # Clear last tweet ID to get fresh tweets
        self.database.clear_last_tweet_id(user_id)
        print("🔄 Cleared last tweet ID")
        
        # Fetch tweets
        fetcher = TwitterFetcher()
        tweets = await fetcher.fetch_new_tweets(max_results=30)  # Keep 30 for X as requested
        
        if not tweets:
            print("❌ No tweets found")
            return
        
        print(f"📱 Found {len(tweets)} tweets")
        
        # Analyze each tweet for media
        for i, tweet in enumerate(tweets[:3], 1):  # Analyze first 3
            print(f"\n🐦 Tweet {i}:")
            print(f"ID: {tweet['post_id']}")
            print(f"Author: {tweet['author_name']} (@{tweet['author_username']})")
            print(f"Text: {tweet['post_text'][:100]}...")
            print(f"URL: {tweet['post_url']}")
            print(f"Media URLs: {tweet['media_urls']}")
            print(f"Media count: {len(tweet['media_urls'])}")
            
            if tweet['media_urls']:
                print("📸 Media found:")
                for j, media_url in enumerate(tweet['media_urls'], 1):
                    print(f"  {j}. {media_url}")
            else:
                print("❌ No media in this tweet")
            
            print("-" * 40)
        
        # Export to JSON for detailed analysis
        import json
        with open('debug_tweets.json', 'w', encoding='utf-8') as f:
            json.dump(tweets, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Exported {len(tweets)} tweets to debug_tweets.json")
        print("✅ Debug complete")

async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI News Scraper and Telegram Publisher")
    parser.add_argument(
        "--once", 
        action="store_true", 
        help="Run once and exit"
    )
    parser.add_argument(
        "--schedule", 
        type=int, 
        default=1, 
        help="Run on schedule every N hours (default: 1)"
    )
    parser.add_argument(
        "--post-tweets",
        action="store_true",
        help="Post new tweets to Telegram now and exit"
    )
    parser.add_argument(
        "--export-tweets",
        type=str,
        help="Export tweets to JSON file (e.g., --export-tweets tweets.json)"
    )
    parser.add_argument(
        "--test-classifier",
        type=str,
        help="Test neural network classifier with sample text"
    )
    parser.add_argument("--check-api-status", action="store_true", help="Check X API connection and rate limits")
    parser.add_argument("--test-news-classifier", action="store_true", help="Test classifier on 5 real news articles")
    parser.add_argument("--send-test-news", action="store_true", help="Send 5 test news articles to Telegram")
    parser.add_argument("--test-summarizer", action="store_true", help="Test summarization on a sample article")
    parser.add_argument("--debug-tweets", action="store_true", help="Reset tweet ID and fetch fresh tweets for media debugging")
    parser.add_argument("--test-media-account", type=str, help="Test media from specific Twitter account (provide username)")
    args = parser.parse_args()
    
    app = AINewsScraperApp()
    
    try:
        if args.post_tweets:
            await app.process_tweets()
        elif args.export_tweets:
            # Export tweets to JSON file
            fetcher = TwitterFetcher()
            tweets = await fetcher.fetch_new_tweets()
            if tweets:
                with open(args.export_tweets, 'w', encoding='utf-8') as f:
                    json.dump(tweets, f, ensure_ascii=False, indent=2)
                logger.info(f"Exported {len(tweets)} tweets to {args.export_tweets}")
            else:
                logger.info("No tweets found to export")
        elif args.test_classifier:
            # Test neural network classifier
            classifier = ContentClassifier()
            category, confidence = classifier.classify_content(args.test_classifier)
            print(f"\nТекст: {args.test_classifier}")
            print(f"Категория: {category}")
            print(f"Уверенность: {confidence:.3f}")
            
            # Show all categories
            print("\nДоступные категории:")
            categories = classifier.get_categories_info()
            for cat, keywords in categories.items():
                print(f"  {cat}: {', '.join(keywords[:3])}...")
        elif args.check_api_status:
            await app.check_api_status()
        elif args.test_news_classifier:
            await app.test_news_classifier()
        elif args.test_summarizer:
            await app.test_summarizer()
        elif args.debug_tweets:
            await app.debug_tweets()
        elif args.test_media_account:
            await app.debug_tweets(username=args.test_media_account)
        elif args.send_test_news:
            # Send 5 sample news articles to Telegram with classification
            sample_articles = [
                {
                    'title': 'OpenAI Launches GPT-5 with Revolutionary Multimodal Capabilities',
                    'content': 'OpenAI has announced the release of GPT-5, featuring groundbreaking multimodal capabilities that can process text, images, audio, and video simultaneously. The new model represents a significant advancement in artificial intelligence technology.',
                    'source': 'Sample Tech News',
                    'url': 'https://example.com/gpt5-launch'
                },
                {
                    'title': 'Google DeepMind Publishes Research on Quantum AI Breakthrough',
                    'content': 'Researchers at Google DeepMind have published a groundbreaking study demonstrating how quantum computing can accelerate machine learning algorithms. The research shows promising results for solving complex optimization problems.',
                    'source': 'Sample AI Research',
                    'url': 'https://example.com/deepmind-quantum'
                },
                {
                    'title': 'Meta CEO Mark Zuckerberg Announces $50 Billion AI Investment',
                    'content': 'Meta CEO Mark Zuckerberg revealed plans to invest $50 billion in artificial intelligence research and development over the next five years. The investment will focus on developing next-generation AI models and infrastructure.',
                    'source': 'Sample Business News',
                    'url': 'https://example.com/meta-investment'
                },
                {
                    'title': 'Microsoft Releases Major Update to Azure AI Services',
                    'content': 'Microsoft has rolled out a comprehensive update to its Azure AI services, introducing new machine learning tools and enhanced natural language processing capabilities. The update includes improved integration with existing Microsoft products.',
                    'source': 'Sample Tech Updates',
                    'url': 'https://example.com/azure-update'
                },
                {
                    'title': 'Stanford Researchers Develop New AI Model for Drug Discovery',
                    'content': 'A team of researchers at Stanford University has developed an innovative AI model that can predict drug interactions and accelerate the drug discovery process. The model has shown promising results in preliminary tests.',
                    'source': 'Sample Research News',
                    'url': 'https://example.com/stanford-drug-ai'
                }
            ]
            
            # Add classification to each article
            classifier = ContentClassifier()
            for article in sample_articles:
                text_to_classify = f"{article['title']} {article['content'][:200]}"
                category, confidence = classifier.classify_content(text_to_classify)
                article['classification'] = category
            
            # Send articles to Telegram
            sent_count = await app.publisher.send_articles_batch(sample_articles)
            logger.info(f"✅ Sent {sent_count}/5 sample news articles to Telegram.")
        elif args.once:
            await app.run_once()
        else:
            await app.run_scheduled(args.schedule)
    except KeyboardInterrupt:
        logger.info("🛑 Scraper stopped by user")
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
    finally:
        await app.publisher.close()

if __name__ == "__main__":
    asyncio.run(main()) 