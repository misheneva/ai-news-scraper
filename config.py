"""
Configuration file for AI News Scraper and Telegram Publisher
"""

import os
from typing import List, Dict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Telegram Configuration
TELEGRAM_BOT_TOKEN = "7542441675:AAHp4-AhVVydGsuSutxwJKVEp6EpJkQ-brk"
TELEGRAM_CHAT_ID = -1002717964198

# Database Configuration
DATABASE_PATH = "news_articles.db"

# Scraping Configuration
REQUEST_DELAY = 2  # Delay between requests in seconds
REQUEST_TIMEOUT = 30  # Timeout for HTTP requests
MAX_RETRIES = 3  # Maximum number of retries for failed requests
MAX_ARTICLE_AGE_DAYS = 14  # Maximum age of articles in days (2 weeks)

# User Agent for requests
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# News Sources Configuration
NEWS_SOURCES = {
    "venturebeat": {
        "name": "VentureBeat AI",
        "url": "https://venturebeat.com/category/ai/",
        "article_links_selector": "article a",
        "title_selector": "h1.entry-title, h1",
        "content_selector": ".entry-content p, .post-content p, .article-content p",
        "date_selector": "time, .entry-date, .post-date, .published-date",
        "base_url": "https://venturebeat.com"
    },
    "scmp": {
        "name": "SCMP Tech",
        "url": "https://www.scmp.com/tech",
        "article_links_selector": "a[href*='/article/']",
        "title_selector": "h1, .article__headline",
        "content_selector": "article p",
        "date_selector": "time, .published-date, .article__date, .date",
        "base_url": "https://www.scmp.com"
    },
    "artificialintelligence_news": {
        "name": "AI News",
        "url": "https://artificialintelligence-news.com/",
        "article_links_selector": "a[href*='/news/']",
        "title_selector": "h1.entry-title, h1",
        "content_selector": ".entry-content p, .post-content p",
        "date_selector": "time, .entry-date, .post-date, .published-date",
        "base_url": "https://artificialintelligence-news.com"
    },
    "theverge_ai": {
        "name": "The Verge AI",
        "url": "https://www.theverge.com/ai-artificial-intelligence",
        "article_links_selector": "a[data-analytics-link='article']",
        "title_selector": "h1, .c-page-title",
        "content_selector": ".c-entry-content p, .e-content p",
        "date_selector": "time, .c-byline__item, .published-date",
        "base_url": "https://www.theverge.com"
    },
    "epoch_ai_data": {
        "name": "Epoch AI - Data Insights",
        "url": "https://epoch.ai/data-insights",
        "article_links_selector": "a[href*='/data-insights/']",
        "title_selector": "h1, .post-title, .entry-title",
        "content_selector": ".post-content p, .entry-content p, .content p",
        "date_selector": "time, .post-date, .published-date, .date",
        "base_url": "https://epoch.ai"
    },
    "epoch_ai_blog": {
        "name": "Epoch AI - Blog",
        "url": "https://epoch.ai/blog",
        "article_links_selector": "a[href*='/blog/']",
        "title_selector": "h1, .post-title, .entry-title",
        "content_selector": ".post-content p, .entry-content p, .content p",
        "date_selector": "time, .post-date, .published-date, .date",
        "base_url": "https://epoch.ai"
    },
    "epoch_ai_gradient": {
        "name": "Epoch AI - Gradient Updates",
        "url": "https://epoch.ai/gradient-updates",
        "article_links_selector": "a[href*='/gradient-updates/']",
        "title_selector": "h1, .post-title, .entry-title",
        "content_selector": ".post-content p, .entry-content p, .content p",
        "date_selector": "time, .post-date, .published-date, .date",
        "base_url": "https://epoch.ai"
    },
    "metr_research": {
        "name": "METR Research",
        "url": "https://metr.org/research/",
        "article_links_selector": "a[href*='/research/']",
        "title_selector": "h1, .post-title, .entry-title",
        "content_selector": ".post-content p, .entry-content p, .content p",
        "date_selector": "time, .post-date, .published-date, .date",
        "base_url": "https://metr.org"
    },
    "techxplore": {
        "name": "TechXplore Latest News",
        "url": "https://techxplore.com/latest-news/",
        "article_links_selector": "a[href*='/news/']",
        "title_selector": "h1, .news-article-title",
        "content_selector": ".news-article-content p, .article-content p",
        "date_selector": "time, .news-date, .published-date, .date",
        "base_url": "https://techxplore.com"
    },
    "forbes_innovation": {
        "name": "Forbes Innovation",
        "url": "https://www.forbes.com/innovation/",
        "article_links_selector": "a[href*='/innovation/']",
        "title_selector": "h1, .headline",
        "content_selector": ".article-body p, .entry-content p",
        "date_selector": "time, .published-date, .date, .timestamp",
        "base_url": "https://www.forbes.com"
    },
    "forbes_ai": {
        "name": "Forbes AI",
        "url": "https://www.forbes.com/ai/",
        "article_links_selector": "a[href*='/ai/']",
        "title_selector": "h1, .headline",
        "content_selector": ".article-body p, .entry-content p",
        "date_selector": "time, .published-date, .date, .timestamp",
        "base_url": "https://www.forbes.com"
    },
    "sakana_ai": {
        "name": "Sakana AI Blog",
        "url": "https://sakana.ai/blog/",
        "article_links_selector": "a[href*='/blog/']",
        "title_selector": "h1, .post-title, .entry-title",
        "content_selector": ".post-content p, .entry-content p, .content p",
        "date_selector": "time, .post-date, .published-date, .date",
        "base_url": "https://sakana.ai"
    },
    "interesting_engineering": {
        "name": "Interesting Engineering - Innovation",
        "url": "https://interestingengineering.com/innovation",
        "article_links_selector": "a[href*='/innovation/']",
        "title_selector": "h1, .article-title",
        "content_selector": "article p",
        "date_selector": "time, .article-date, .published-date, .date",
        "base_url": "https://interestingengineering.com"
    }
}

# Telegram Message Format
MESSAGE_TEMPLATE = """*{title}*

{content}

Source: {source_name} | [Read Full Article]({url})"""

# Logging Configuration
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# X (Twitter) API Configuration
X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN")
X_USER_ID = "2244994945"  # TwitterDev
X_USERNAME = "TwitterDev"  # For link formatting
X_API_ENDPOINT = f"https://api.twitter.com/2/users/{X_USER_ID}/tweets" 