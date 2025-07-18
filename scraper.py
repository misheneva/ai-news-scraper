"""
AI News Scraper Module
Handles web scraping of AI news articles from multiple sources
"""

import requests
import time
import logging
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
from config import (
    REQUEST_DELAY, REQUEST_TIMEOUT, MAX_RETRIES, 
    USER_AGENT, NEWS_SOURCES, X_BEARER_TOKEN, X_API_ENDPOINT, X_USER_ID,
    MAX_ARTICLE_AGE_DAYS
)
import httpx
from tenacity import retry, stop_after_attempt, wait_fixed
from database import NewsDatabase
from classifier import ContentClassifier

logger = logging.getLogger(__name__)

class NewsScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.max_age = timedelta(days=MAX_ARTICLE_AGE_DAYS)
    
    def _parse_date(self, date_text: str) -> Optional[datetime]:
        """Parse date from various formats"""
        if not date_text:
            return None
        
        # Clean up the date text
        date_text = date_text.strip()
        
        # Common date formats to try
        date_formats = [
            '%Y-%m-%d',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%B %d, %Y',
            '%b %d, %Y',
            '%d %B %Y',
            '%d %b %Y',
            '%m/%d/%Y',
            '%d/%m/%Y',
            '%Y/%m/%d',
            '%d-%m-%Y',
            '%m-%d-%Y',
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_text, fmt)
            except ValueError:
                continue
        
        # Try to extract date with regex patterns
        patterns = [
            r'(\d{4}-\d{2}-\d{2})',
            r'(\d{1,2}/\d{1,2}/\d{4})',
            r'(\w+ \d{1,2}, \d{4})',
            r'(\d{1,2} \w+ \d{4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, date_text)
            if match:
                try:
                    date_str = match.group(1)
                    for fmt in date_formats:
                        try:
                            return datetime.strptime(date_str, fmt)
                        except ValueError:
                            continue
                except:
                    continue
        
        logger.warning(f"Could not parse date: {date_text}")
        return None

    def _extract_date_from_url(self, url: str) -> Optional[datetime]:
        """Try to extract date from URL"""
        # Common URL date patterns
        url_patterns = [
            r'/(\d{4})/(\d{2})/(\d{2})/',  # /2023/06/08/
            r'/(\d{4})-(\d{2})-(\d{2})/',  # /2023-06-08/
            r'/(\d{4})(\d{2})(\d{2})/',    # /20230608/
            r'-(\d{4})-(\d{2})-(\d{2})',   # -2023-06-08
            r'(\d{4})-(\d{2})-(\d{2})',    # 2023-06-08
        ]
        
        for pattern in url_patterns:
            match = re.search(pattern, url)
            if match:
                try:
                    if len(match.groups()) == 3:
                        year, month, day = match.groups()
                        return datetime(int(year), int(month), int(day))
                except (ValueError, IndexError):
                    continue
        
        return None

    def _extract_date_from_text(self, text: str) -> Optional[datetime]:
        """Try to extract date from article text"""
        # Look for date patterns in text
        text_patterns = [
            r'\b(\w+ \d{1,2}, \d{4})\b',  # Jun 08, 2023
            r'\b(\d{1,2} \w+ \d{4})\b',   # 08 Jun 2023
            r'\b(\d{4}-\d{2}-\d{2})\b',   # 2023-06-08
        ]
        
        for pattern in text_patterns:
            matches = re.findall(pattern, text)
            if matches:
                # Try to parse the first match
                for match in matches:
                    parsed_date = self._parse_date(match)
                    if parsed_date:
                        # Only return dates that seem reasonable (not too far in the future)
                        if parsed_date <= datetime.now() + timedelta(days=30):
                            return parsed_date
        
        return None
    
    def _is_article_recent(self, article_date: Optional[datetime]) -> bool:
        """Check if article is within the maximum age limit"""
        if not article_date:
            # If we can't determine the date, be more conservative
            logger.warning("No article date found, assuming article is NOT recent to avoid old articles")
            return False
        
        age = datetime.now() - article_date
        is_recent = age <= self.max_age
        
        if not is_recent:
            logger.info(f"Article is too old: {age.days} days (max: {MAX_ARTICLE_AGE_DAYS} days)")
        else:
            logger.info(f"Article is recent: {age.days} days old")
        
        return is_recent
    
    def get_page_content(self, url: str) -> Optional[str]:
        """Fetch page content with retry logic"""
        for attempt in range(MAX_RETRIES):
            try:
                logger.info(f"Fetching page: {url} (attempt {attempt + 1})")
                response = self.session.get(url, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                return response.text
            except requests.RequestException as e:
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(REQUEST_DELAY * (attempt + 1))
                else:
                    logger.error(f"Failed to fetch {url} after {MAX_RETRIES} attempts")
                    return None
    
    def extract_article_links(self, source_key: str, html_content: str) -> List[str]:
        """Extract article links from a source page"""
        source_config = NEWS_SOURCES[source_key]
        soup = BeautifulSoup(html_content, 'lxml')
        links = []
        
        try:
            # Find all article links
            article_elements = soup.select(source_config['article_links_selector'])
            
            for element in article_elements:
                href = element.get('href')
                if href:
                    # Convert relative URLs to absolute URLs
                    full_url = urljoin(source_config['base_url'], href)
                    
                    # Filter out non-article URLs
                    if self._is_valid_article_url(full_url, source_key):
                        links.append(full_url)
            
            logger.info(f"Found {len(links)} article links from {source_config['name']}")
            return list(set(links))  # Remove duplicates
            
        except Exception as e:
            logger.error(f"Error extracting links from {source_config['name']}: {e}")
            return []
    
    def _is_valid_article_url(self, url: str, source_key: str) -> bool:
        """Check if URL is a valid article URL"""
        parsed = urlparse(url)
        
        # Basic validation
        if not parsed.scheme or not parsed.netloc:
            return False
        
        # Source-specific validation
        if source_key == "venturebeat":
            return "/ai/" in url or "/category/ai/" in url or "/programming-development/" in url
        elif source_key == "scmp":
            return "/tech/" in url and "/article/" in url
        elif source_key == "artificialintelligence_news":
            return "/news/" in url
        elif source_key == "theverge_ai":
            return "/ai-artificial-intelligence/" in url or "/artificial-intelligence/" in url
        elif source_key == "epoch_ai_data":
            return "/data-insights/" in url
        elif source_key == "epoch_ai_blog":
            return "/blog/" in url
        elif source_key == "epoch_ai_gradient":
            return "/gradient-updates/" in url
        elif source_key == "metr_research":
            return "/research/" in url
        elif source_key == "techxplore":
            return "/news/" in url
        elif source_key == "forbes_innovation":
            return "/innovation/" in url
        elif source_key == "forbes_ai":
            return "/ai/" in url
        elif source_key == "sakana_ai":
            return "/blog/" in url
        elif source_key == "interesting_engineering":
            return "/innovation/" in url
        
        return True
    
    def extract_article_content(self, source_key: str, html_content: str, url: str = None) -> Tuple[Optional[str], Optional[str], Optional[datetime]]:
        """Extract title, content, and date from an article page"""
        source_config = NEWS_SOURCES[source_key]
        soup = BeautifulSoup(html_content, 'lxml')
        
        # Extract title
        title = None
        title_element = soup.select_one(source_config['title_selector'])
        if title_element:
            title = title_element.get_text(strip=True)
        
        # Extract content
        content = None
        content_elements = soup.select(source_config['content_selector'])
        if content_elements:
            # Combine all paragraphs
            paragraphs = []
            for element in content_elements:
                text = element.get_text(strip=True)
                if text and len(text) > 50:  # Filter out short text (likely ads)
                    paragraphs.append(text)
            
            if paragraphs:
                content = '\n\n'.join(paragraphs)
        
        # Extract date - try multiple methods
        article_date = None
        
        # Method 1: Try standard date selectors
        date_element = soup.select_one(source_config['date_selector'])
        if date_element:
            # Try to get date from datetime attribute first
            date_text = date_element.get('datetime') or date_element.get('content') or date_element.get_text(strip=True)
            article_date = self._parse_date(date_text)
        
        # Method 2: If no date found, try to extract from URL
        if not article_date and url:
            article_date = self._extract_date_from_url(url)
        
        # Method 3: If still no date, try to extract from article text
        if not article_date and content:
            article_date = self._extract_date_from_text(content)
        
        # Method 4: If still no date, try to extract from title
        if not article_date and title:
            article_date = self._extract_date_from_text(title)
        
        return title, content, article_date
    
    def scrape_source(self, source_key: str, limit: int = 10) -> List[Dict]:
        """Scrape articles from a specific source"""
        source_config = NEWS_SOURCES[source_key]
        articles = []
        
        logger.info(f"Starting to scrape {source_config['name']}")
        
        # Get main page content
        html_content = self.get_page_content(source_config['url'])
        if not html_content:
            logger.error(f"Failed to get content from {source_config['name']}")
            return articles
        
        # Extract article links
        article_links = self.extract_article_links(source_key, html_content)
        
        # Process each article
        for link in article_links[:limit]:  # Limit articles per source
            logger.info(f"Processing article: {link}")
            
            # Get article page content
            article_html = self.get_page_content(link)
            if not article_html:
                continue
            
            # Extract article content
            title, content, article_date = self.extract_article_content(source_key, article_html, link)
            
            if title and content:
                # Check if article is recent enough
                if not self._is_article_recent(article_date):
                    logger.info(f"Skipping old article: {title} (date: {article_date})")
                    continue
                
                articles.append({
                    'url': link,
                    'title': title,
                    'content': content,
                    'source': source_config['name'],
                    'source_key': source_key,
                    'date': article_date
                })
                logger.info(f"Successfully extracted article: {title}")
            
            # Respect rate limits
            time.sleep(REQUEST_DELAY)
        
        logger.info(f"Completed scraping {source_config['name']}: {len(articles)} articles found")
        return articles
    
    def scrape_all_sources(self, limit_per_source: int = 10) -> List[Dict]:
        """Scrape articles from all configured sources"""
        all_articles = []
        
        for source_key in NEWS_SOURCES.keys():
            try:
                articles = self.scrape_source(source_key, limit_per_source)
                all_articles.extend(articles)
                
                # Delay between sources
                time.sleep(REQUEST_DELAY * 2)
                
            except Exception as e:
                logger.error(f"Error scraping {source_key}: {e}")
                continue
        
        logger.info(f"Total articles scraped: {len(all_articles)}")
        return all_articles

class TwitterFetcher:
    def __init__(self, user_id: str = X_USER_ID, bearer_token: str = X_BEARER_TOKEN):
        self.user_id = user_id
        self.bearer_token = bearer_token
        self.api_endpoint = X_API_ENDPOINT
        self.db = NewsDatabase()
        self.classifier = ContentClassifier()

    def classify_tweet(self, text: str) -> str:
        """Classify tweet content using neural network"""
        category, confidence = self.classifier.classify_content(text)
        logger.info(f"Tweet classified as: {category} (confidence: {confidence:.3f})")
        return category

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
    async def fetch_new_tweets(self, max_results: int = 30) -> list:
        last_tweet_id = self.db.get_last_tweet_id(self.user_id)
        headers = {"Authorization": f"Bearer {self.bearer_token}"}
        
        # Request more fields including author info and media
        # Add tweet.fields to get full text (not truncated)
        params = {
            "max_results": str(max_results),
            "tweet.fields": "author_id,created_at,text,entities,public_metrics,referenced_tweets",
            "expansions": "author_id,attachments.media_keys,referenced_tweets.id",
            "user.fields": "name,username",
            "media.fields": "url,preview_image_url,type"
        }
        
        if last_tweet_id:
            params["since_id"] = last_tweet_id
            
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(self.api_endpoint, headers=headers, params=params)
                
                # Handle rate limiting (429 error)
                if resp.status_code == 429:
                    retry_after = resp.headers.get('x-rate-limit-reset', '3600')
                    logger.error(f"Rate limit exceeded (429). Next reset in {retry_after} seconds")
                    logger.info("Suggestion: Consider upgrading X API plan or increasing request intervals")
                    return []
                
                # Handle other HTTP errors
                if resp.status_code == 401:
                    logger.error("Unauthorized (401). Check your Bearer Token")
                    return []
                elif resp.status_code == 403:
                    logger.error("Forbidden (403). Check API permissions")
                    return []
                elif resp.status_code >= 400:
                    logger.error(f"API Error {resp.status_code}: {resp.text}")
                    return []
                
                resp.raise_for_status()
                data = resp.json()
                
                # Debug: Log the raw response structure
                logger.info(f"API Response keys: {list(data.keys())}")
                if "includes" in data:
                    logger.info(f"Includes keys: {list(data['includes'].keys())}")
                    if "media" in data["includes"]:
                        logger.info(f"Found {len(data['includes']['media'])} media items")
                
                tweets = data.get("data", [])
                if not tweets:
                    logger.info("No new tweets found")
                    return []
                
                users = {user["id"]: user for user in data.get("includes", {}).get("users", [])}
                media = {m["media_key"]: m for m in data.get("includes", {}).get("media", [])}
                # Get referenced tweets for full text extraction
                referenced_tweets = {t["id"]: t for t in data.get("includes", {}).get("tweets", [])}
                
                logger.info(f"Processing {len(tweets)} tweets with {len(media)} media items available")
                
                # Transform tweets to required format
                formatted_tweets = []
                for tweet in tweets:
                    author = users.get(tweet.get("author_id", ""), {})
                    media_urls = []
                    
                    # Debug: Log tweet structure
                    logger.debug(f"Tweet {tweet['id']} has keys: {list(tweet.keys())}")
                    
                    # Extract media URLs
                    if "attachments" in tweet and "media_keys" in tweet["attachments"]:
                        logger.info(f"Tweet {tweet['id']} has {len(tweet['attachments']['media_keys'])} media attachments")
                        for media_key in tweet["attachments"]["media_keys"]:
                            if media_key in media:
                                media_item = media[media_key]
                                logger.info(f"Media item {media_key}: type={media_item.get('type')}, keys={list(media_item.keys())}")
                                
                                if media_item.get("type") == "photo":
                                    photo_url = media_item.get("url", "")
                                    if photo_url:
                                        media_urls.append(photo_url)
                                        logger.info(f"Added photo URL: {photo_url}")
                                elif media_item.get("type") == "video":
                                    # Try different video URL fields
                                    video_url = media_item.get("url") or media_item.get("preview_image_url", "")
                                    if video_url:
                                        media_urls.append(video_url)
                                        logger.info(f"Added video URL: {video_url}")
                                elif media_item.get("type") == "animated_gif":
                                    gif_url = media_item.get("url") or media_item.get("preview_image_url", "")
                                    if gif_url:
                                        media_urls.append(gif_url)
                                        logger.info(f"Added GIF URL: {gif_url}")
                            else:
                                logger.warning(f"Media key {media_key} not found in media includes")
                    else:
                        logger.debug(f"Tweet {tweet['id']} has no media attachments")
                    
                    # Get full text - handle retweets with comments that might be truncated
                    full_text = tweet["text"]
                    
                    # Log text length for debugging
                    logger.debug(f"Tweet {tweet['id']} text length: {len(full_text)} characters")
                    
                    # Check if this is a retweet with comments and text might be truncated
                    if "referenced_tweets" in tweet:
                        for ref_tweet in tweet["referenced_tweets"]:
                            if ref_tweet.get("type") == "retweeted":
                                # For retweets with comments, try to get the full text
                                # If the text ends with "…" it's likely truncated
                                if full_text.endswith("…") or full_text.endswith("..."):
                                    # Try to get the referenced tweet for full context
                                    referenced_tweet = referenced_tweets.get(ref_tweet["id"])
                                    if referenced_tweet:
                                        # Combine the retweet comment with the original tweet
                                        # Extract the comment part (before "RT @username:")
                                        rt_marker = "RT @"
                                        if rt_marker in full_text:
                                            comment_part = full_text.split(rt_marker)[0].strip()
                                            if comment_part:
                                                full_text = f"{comment_part} RT @{referenced_tweet.get('author_id', 'unknown')}: {referenced_tweet.get('text', '')}"
                                            else:
                                                full_text = f"RT @{referenced_tweet.get('author_id', 'unknown')}: {referenced_tweet.get('text', '')}"
                                        else:
                                            # If no RT marker, just use the referenced tweet text
                                            full_text = referenced_tweet.get("text", full_text)
                                        
                                        logger.debug(f"Retweet with truncated text reconstructed: {len(full_text)} chars")
                                    else:
                                        logger.debug(f"Referenced tweet {ref_tweet['id']} not found in includes")
                                else:
                                    logger.debug(f"Retweet with comments detected, text not truncated: {len(full_text)} chars")
                                break
                    
                    formatted_tweet = {
                        "post_id": tweet["id"],
                        "author_username": author.get("username", ""),
                        "author_name": author.get("name", ""),
                        "post_text": full_text,
                        "post_url": f"https://x.com/{author.get('username', '')}/status/{tweet['id']}",
                        "media_urls": media_urls,
                        "classification": self.classify_tweet(full_text)
                    }
                    formatted_tweets.append(formatted_tweet)
                
                # Sort from oldest to newest
                formatted_tweets = sorted(formatted_tweets, key=lambda t: int(t["post_id"]))
                logger.info(f"Successfully fetched {len(formatted_tweets)} new tweets")
                return formatted_tweets
                
        except httpx.ConnectTimeout:
            logger.error("Connection timeout to X API. Check your internet connection or VPN")
            return []
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.error("Rate limit exceeded. Try again later or upgrade API plan")
            else:
                logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching tweets: {e}")
            return [] 