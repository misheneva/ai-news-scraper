"""
Telegram Publisher Module
Handles sending formatted news articles to Telegram channel
"""

import asyncio
import logging
from typing import Dict, List
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, MESSAGE_TEMPLATE

logger = logging.getLogger(__name__)

class TelegramPublisher:
    def __init__(self):
        self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
        self.chat_id = TELEGRAM_CHAT_ID
    
    def _escape_markdown(self, text: str) -> str:
        """Escape markdown special characters to prevent parsing errors"""
        # List of characters that need to be escaped in Telegram Markdown
        special_chars = ['*', '_', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        
        escaped_text = text
        for char in special_chars:
            escaped_text = escaped_text.replace(char, f'\\{char}')
        
        return escaped_text
    
    async def format_message(self, article: Dict) -> str:
        """Format article data into a Telegram message"""
        try:
            # Truncate content if too long (Telegram has a 4096 character limit)
            content = article['content']
            if len(content) > 3000:
                content = content[:3000] + "...\n\n[Content truncated due to length]"
            
            # Format the message using the template
            message = MESSAGE_TEMPLATE.format(
                title=article['title'],
                content=content,
                source_name=article['source'],
                url=article['url']
            )
            
            return message
            
        except Exception as e:
            logger.error(f"Error formatting message: {e}")
            return None
    
    async def send_article(self, article: Dict) -> bool:
        """Send a single article to Telegram channel"""
        try:
            logger.info(f"Sending article to Telegram: {article['title']}")
            
            # Format the message
            message = await self.format_message(article)
            if not message:
                logger.error("Failed to format message")
                return False
            
            # Add classification if available
            classification = article.get('classification', '')
            if classification:
                message = f"{classification}\n\n{message}"
            
            # Send the message
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
            logger.info(f"Successfully sent article: {article['title']}")
            return True
            
        except TelegramBadRequest as e:
            logger.error(f"Telegram API error: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending article: {e}")
            return False
    
    async def send_articles_batch(self, articles: List[Dict]) -> int:
        """Send multiple articles to Telegram channel"""
        success_count = 0
        
        for article in articles:
            try:
                success = await self.send_article(article)
                if success:
                    success_count += 1
                
                # Add delay between messages to avoid rate limiting
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error processing article {article.get('title', 'Unknown')}: {e}")
                continue
        
        logger.info(f"Sent {success_count}/{len(articles)} articles successfully")
        return success_count
    
    async def send_status_message(self, message: str) -> bool:
        """Send a status message to the channel"""
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown'
            )
            return True
        except Exception as e:
            logger.error(f"Error sending status message: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """Test the Telegram bot connection"""
        try:
            bot_info = await self.bot.get_me()
            logger.info(f"Telegram bot connected: {bot_info.first_name} (@{bot_info.username})")
            return True
        except Exception as e:
            logger.error(f"Telegram connection test failed: {e}")
            return False
    
    async def close(self):
        """Close the bot session"""
        await self.bot.session.close()
    
    async def send_tweet(self, tweet: dict, username: str = None) -> bool:
        """Send a tweet to Telegram channel in the required format"""
        try:
            # Handle both old and new tweet formats
            if "post_id" in tweet:
                # New format
                tweet_id = tweet["post_id"]
                text = tweet["post_text"]
                author_username = tweet["author_username"]
                author_name = tweet["author_name"]
                classification = tweet["classification"]
                url = tweet["post_url"]
                media_urls = tweet.get("media_urls", [])
                
                # Create caption with structured format - classification in header
                # For X/Twitter, use full text without truncation (tweets are already limited by platform)
                # Escape markdown special characters in tweet text to prevent parsing errors
                escaped_text = self._escape_markdown(text)
                caption = f"{classification}\n\n{escaped_text}\n\n---\n\nАвтор: **{author_name}** ( @{author_username} )\n\n[🔗 Оригинал в X]({url})"
                
                # Send media if available, otherwise send as text
                if media_urls:
                    logger.info(f"Processing {len(media_urls)} media items for tweet {tweet_id}")
                    # Send first media with caption
                    media_url = media_urls[0]
                    logger.info(f"Attempting to send media: {media_url}")
                    
                    # Improved media type detection
                    media_url_lower = media_url.lower()
                    try:
                        if any(ext in media_url_lower for ext in ['.jpg', '.jpeg', '.png', '.gif', 'format=jpg', 'format=png']):
                            logger.info("Sending as photo")
                            await self.bot.send_photo(
                                chat_id=self.chat_id,
                                photo=media_url,
                                caption=caption,
                                parse_mode='Markdown'
                            )
                        elif any(ext in media_url_lower for ext in ['.mp4', '.mov', '.avi', 'format=mp4']):
                            logger.info("Sending as video")
                            await self.bot.send_video(
                                chat_id=self.chat_id,
                                video=media_url,
                                caption=caption,
                                parse_mode='Markdown'
                            )
                        else:
                            # Try as photo first (most common), fallback to text
                            logger.info("Unknown media type, trying as photo")
                            try:
                                await self.bot.send_photo(
                                    chat_id=self.chat_id,
                                    photo=media_url,
                                    caption=caption,
                                    parse_mode='Markdown'
                                )
                            except Exception as photo_error:
                                logger.warning(f"Failed to send as photo: {photo_error}, falling back to text")
                                await self.bot.send_message(
                                    chat_id=self.chat_id,
                                    text=f"{caption}\n\n📎 Media: {media_url}",
                                    parse_mode='Markdown',
                                    disable_web_page_preview=True
                                )
                    except Exception as media_error:
                        logger.error(f"Failed to send media {media_url}: {media_error}")
                        # Fallback to text with media link
                        await self.bot.send_message(
                            chat_id=self.chat_id,
                            text=f"{caption}\n\n📎 Media: {media_url}",
                            parse_mode='Markdown',
                            disable_web_page_preview=True
                        )
                else:
                    logger.info("No media found, sending as text")
                    # No media, send as text message
                    await self.bot.send_message(
                        chat_id=self.chat_id,
                        text=caption,
                        parse_mode='Markdown',
                        disable_web_page_preview=True
                    )
            else:
                # Old format (backward compatibility)
                tweet_id = tweet['id']
                text = tweet['text']
                url = f"https://twitter.com/{username}/status/{tweet_id}"
                message = f"Новый твит от @{username}:\n\n{text}\n\n{url}"
                
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=message,
                    parse_mode='Markdown',
                    disable_web_page_preview=True
                )
            
            logger.info(f"Successfully sent tweet: {tweet_id}")
            return True
        except TelegramBadRequest as e:
            logger.error(f"Telegram API error: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending tweet: {e}")
            return False 