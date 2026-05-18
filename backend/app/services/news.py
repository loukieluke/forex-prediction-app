from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import logging

import feedparser
import requests

from app.config import settings

logger = logging.getLogger(__name__)


def fetch_newsapi_headlines(query: str = "forex EUR USD", page_size: int = 20) -> list[dict]:
    if not settings.news_api_key or settings.news_api_key == "replace_me":
        return []
    try:
        response = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": query,
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": page_size,
                "apiKey": settings.news_api_key,
            },
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        return [
            {
                "source": article.get("source", {}).get("name", "newsapi"),
                "title": article.get("title", "").strip(),
                "url": article.get("url", ""),
                "published_at": datetime.fromisoformat(article["publishedAt"].replace("Z", "+00:00")),
            }
            for article in payload.get("articles", [])
            if article.get("title")
        ]
    except requests.RequestException:
        logger.warning("NewsAPI request failed; continuing with other news sources", exc_info=True)
        return []


def fetch_rss_headlines(url: str = "https://www.forexfactory.com/rss") -> list[dict]:
    feed = feedparser.parse(url)
    if getattr(feed, "bozo", False):
        logger.warning("RSS parsing warning for %s", url)
    results = []
    for entry in feed.entries[:30]:
        raw_date = entry.get("published") or entry.get("updated")
        published_at = datetime.now(timezone.utc)
        if raw_date:
            published_at = parsedate_to_datetime(raw_date).astimezone(timezone.utc)
        results.append(
            {
                "source": "forexfactory-rss",
                "title": entry.get("title", "").strip(),
                "url": entry.get("link", ""),
                "published_at": published_at,
            }
        )
    return [item for item in results if item["title"]]


def fetch_news() -> list[dict]:
    headlines = []
    if settings.use_rss_news:
        headlines.extend(fetch_rss_headlines())
    headlines.extend(fetch_newsapi_headlines())
    return headlines
