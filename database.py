"""
Database module for storing processed article URLs
"""

import sqlite3
import logging
from typing import List, Optional
from config import DATABASE_PATH

logger = logging.getLogger(__name__)

class NewsDatabase:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create table for processed articles
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS processed_articles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        url TEXT UNIQUE NOT NULL,
                        title TEXT,
                        source TEXT NOT NULL,
                        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create index for faster URL lookups
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_url ON processed_articles(url)
                ''')
                
                # Create table for storing last tweet id per user
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS twitter_state (
                        user_id TEXT PRIMARY KEY,
                        last_tweet_id TEXT
                    )
                ''')
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def is_article_processed(self, url: str) -> bool:
        """Check if an article URL has been processed before"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM processed_articles WHERE url = ?", (url,))
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking if article is processed: {e}")
            return False
    
    def mark_article_processed(self, url: str, title: str, source: str):
        """Mark an article as processed"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO processed_articles (url, title, source) VALUES (?, ?, ?)",
                    (url, title, source)
                )
                conn.commit()
                logger.info(f"Marked article as processed: {url}")
        except sqlite3.IntegrityError:
            logger.warning(f"Article already exists in database: {url}")
        except Exception as e:
            logger.error(f"Error marking article as processed: {e}")
    
    def get_processed_count(self, source: Optional[str] = None) -> int:
        """Get count of processed articles, optionally filtered by source"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if source:
                    cursor.execute("SELECT COUNT(*) FROM processed_articles WHERE source = ?", (source,))
                else:
                    cursor.execute("SELECT COUNT(*) FROM processed_articles")
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error getting processed count: {e}")
            return 0
    
    def get_recent_articles(self, limit: int = 10) -> List[tuple]:
        """Get recent processed articles"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT url, title, source, processed_at FROM processed_articles ORDER BY processed_at DESC LIMIT ?",
                    (limit,)
                )
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting recent articles: {e}")
            return []
    
    def get_last_tweet_id(self, user_id: str) -> Optional[str]:
        """Get the last processed tweet ID for a Twitter user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT last_tweet_id FROM twitter_state WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.error(f"Error getting last tweet id: {e}")
            return None

    def set_last_tweet_id(self, user_id: str, tweet_id: str):
        """Set the last processed tweet ID for a Twitter user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO twitter_state (user_id, last_tweet_id) VALUES (?, ?) "
                    "ON CONFLICT(user_id) DO UPDATE SET last_tweet_id=excluded.last_tweet_id",
                    (user_id, tweet_id)
                )
                conn.commit()
                logger.info(f"Set last tweet id for user {user_id}: {tweet_id}")
        except Exception as e:
            logger.error(f"Error setting last tweet id: {e}")
    
    def clear_last_tweet_id(self, user_id: str):
        """Clear the last processed tweet ID for a Twitter user (for testing)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM twitter_state WHERE user_id = ?", (user_id,))
                conn.commit()
                logger.info(f"Cleared last tweet id for user {user_id}")
        except Exception as e:
            logger.error(f"Error clearing last tweet id: {e}") 