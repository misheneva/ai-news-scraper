# AI News Scraper and Telegram Publisher

An automated Python system that scrapes AI news articles from multiple sources and publishes them to a Telegram channel. Built with BeautifulSoup for web scraping and aiogram for Telegram integration.

## 🚀 Features

- **Multi-source scraping**: Collects news from Reuters, Tech in Asia, and SCMP
- **Deduplication**: Prevents duplicate articles using SQLite database
- **Telegram integration**: Publishes formatted articles to your channel
- **Scheduling**: Runs automatically on configurable intervals
- **Error handling**: Robust error handling and logging
- **Rate limiting**: Respects website rate limits and robots.txt

## 📋 Requirements

- Python 3.8+
- Telegram Bot Token
- Telegram Channel ID

## 🛠️ Installation

1. **Clone or download the project files**

2. **Install dependencies**:
```bash
pip3 install -r requirements.txt
```

3. **Configure your settings**:
   - Edit `config.py` to update your Telegram bot token and chat ID
   - Adjust scraping parameters as needed

## 📁 Project Structure

```
Parser/
├── main.py                 # Main application entry point
├── config.py              # Configuration settings
├── database.py            # SQLite database operations
├── scraper.py             # Web scraping logic
├── telegram_publisher.py  # Telegram publishing
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── ai_news_scraper.log   # Application logs (created automatically)
└── news_articles.db      # SQLite database (created automatically)
```

## 🚀 Usage

### Quick Start

Run the scraper once to test:
```bash
python3 main.py --once
```

### Scheduled Operation

Run the scraper every hour (default):
```bash
python3 main.py
```

Run every 2 hours:
```bash
python3 main.py --schedule 2
```

### Command Line Options

- `--once`: Run once and exit
- `--schedule N`: Run every N hours (default: 1)

## 📰 News Sources

The system scrapes AI news from:

1. **Reuters AI Section**: https://www.reuters.com/technology/artificial-intelligence/
2. **Tech in Asia AI Category**: https://www.techinasia.com/category/artificial-intelligence
3. **SCMP Tech Section**: https://www.scmp.com/tech

## 📊 Telegram Message Format

Articles are published in this format:

```
*Article Title*

Article content (truncated if too long)...

Source: Source Name | [Read Full Article](URL)
```

## ⚙️ Configuration

Edit `config.py` to customize:

- **Telegram settings**: Bot token and chat ID
- **Scraping parameters**: Delays, timeouts, retries
- **Message format**: Customize how articles appear
- **Source selectors**: CSS selectors for each website

## 🔧 Customization

### Adding New Sources

1. Add source configuration to `NEWS_SOURCES` in `config.py`:
```python
"new_source": {
    "name": "New Source Name",
    "url": "https://example.com/ai-news",
    "article_links_selector": "a[href*='/article/']",
    "title_selector": "h1",
    "content_selector": ".article-content p",
    "base_url": "https://example.com"
}
```

2. Update the `_is_valid_article_url` method in `scraper.py` if needed.

### Modifying Message Format

Edit the `MESSAGE_TEMPLATE` in `config.py` to change how articles appear in Telegram.

## 📈 Monitoring

The system provides comprehensive logging:

- **Console output**: Real-time status updates
- **Log file**: `ai_news_scraper.log` for detailed logs
- **Telegram status**: Summary messages sent to your channel

## 🛡️ Best Practices

- **Rate limiting**: Built-in delays prevent overwhelming websites
- **Error handling**: Graceful handling of network issues
- **Deduplication**: Prevents spam and duplicate content
- **Logging**: Comprehensive logging for debugging

## 🔍 Troubleshooting

### Common Issues

1. **"chat not found" error**:
   - Ensure the bot is added to the channel as an admin
   - Verify the chat ID is correct (use `-100` prefix for channels)

2. **No articles found**:
   - Check website selectors in `config.py`
   - Verify websites are accessible
   - Check logs for specific errors

3. **Telegram API errors**:
   - Verify bot token is correct
   - Check bot permissions in the channel

### Debug Mode

Enable debug logging by changing `LOG_LEVEL = "DEBUG"` in `config.py`.

## 📝 Logs

The system creates detailed logs in `ai_news_scraper.log`:

- Scraping progress
- Article processing
- Telegram publishing status
- Error details

## 🔄 Database

The SQLite database (`news_articles.db`) stores:

- Processed article URLs
- Article titles and sources
- Processing timestamps

## 📋 Dependencies

- `aiogram`: Telegram Bot API
- `requests`: HTTP requests
- `beautifulsoup4`: HTML parsing
- `lxml`: XML/HTML parser
- `schedule`: Task scheduling
- `sqlite3`: Database (built-in)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is open source and available under the MIT License.

## ⚠️ Disclaimer

This tool is for educational and personal use. Please respect website terms of service and robots.txt files. The authors are not responsible for any misuse of this software. 