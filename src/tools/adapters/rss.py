import feedparser
import requests
from datetime import datetime, timedelta
from typing import List
from src.tools.adapters.base import BaseAdapter
from src.models.schemas import IngestedItem, SourceType

class RSSAdapter(BaseAdapter):
    """Adapter for RSS feeds with technical AI sources"""
    
    # Working feed URLs that successfully return content
    FEEDS = [
        "https://huggingface.co/blog/feed.xml",
        "https://blog.google/technology/ai/rss/",
        "https://openai.com/news/rss.xml",
        "https://blog.langchain.dev/rss/",
        "https://towardsdatascience.com/feed",
    ]
    
    def __init__(self):
        super().__init__(SourceType.RSS)
    
    def _is_recent(self, timestamp: datetime, hours: int) -> bool:
        """Check if timestamp is within the specified hours"""
        cutoff = datetime.now() - timedelta(hours=hours)


        return timestamp >= cutoff
    
    def fetch_items(self, hours: int = 24) -> List[IngestedItem]:
        """Fetch items from RSS feeds"""
        items = []
        
        for feed_url in self.FEEDS:
            try:
                print(f"    Trying feed: {feed_url}")
                feed_items = self._fetch_feed(feed_url, hours)
                items.extend(feed_items)
                print(f"    ✅ Got {len(feed_items)} items")
            except Exception as e:
                print(f"    ❌ Error: {e}")
                continue
        
        return items
    
    def _fetch_feed(self, feed_url: str, hours: int) -> List[IngestedItem]:
        """Fetch items from a single RSS feed"""
        try:
            # Use requests with timeout instead of direct feedparser.parse
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; AI-Digest-Bot/1.0)"
            }
            
            try:
                response = requests.get(feed_url, headers=headers, timeout=15)
                response.raise_for_status()
                feed = feedparser.parse(response.content)
            except requests.exceptions.RequestException as e:
                print(f"    Request error for {feed_url}: {e}")
                return []
            
            # Check if feed was successfully parsed
            if hasattr(feed, 'bozo') and feed.bozo:
                print(f"    Warning: Feed {feed_url} has format issues: {feed.bozo_exception}")
            
            if not hasattr(feed, 'entries') or not feed.entries:
                print(f"    No entries found in {feed_url}")
                return []
            
            items = []
            for entry in feed.entries[:10]:  # Process up to 10 entries per feed
                try:
                    # Parse timestamp
                    timestamp = datetime.now()
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        timestamp = datetime(*entry.published_parsed[:6])
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        timestamp = datetime(*entry.updated_parsed[:6])
                    
                    # Check if recent
                    if not self._is_recent(timestamp, hours):
                        continue
                    
                    # Clean description
                    import re
                    description = entry.get('summary', entry.get('description', ''))[:400]
                    description = re.sub(r'<[^>]+>', '', description)
                    
                    # Get link
                    link = entry.get('link', entry.get('href', None))
                    if not link:
                        continue
                    
                    # Generate a unique ID for the item
                    source_id = entry.get('id', link)
                    
                    # Create the item with both id and source_id parameters
                    item = IngestedItem(
                        id=source_id,  # Add the required id parameter
                        title=entry.get('title', 'No Title'),
                        description=description,
                        url=link,
                        source_type=self.source_type,
                        source_id=source_id,
                        timestamp=timestamp,
                        metadata={'feed_url': feed_url}
                    )
                    
                    items.append(item)
                    
                except Exception as e:
                    print(f"    Error processing entry: {e}")
                    continue
            
            return items
            
        except Exception as e:
            print(f"    Unexpected error in _fetch_feed: {e}")
            return []