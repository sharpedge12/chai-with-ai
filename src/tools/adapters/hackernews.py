import httpx
from datetime import datetime
from typing import List, Optional
from src.tools.adapters.base import BaseAdapter
from src.models.schemas import IngestedItem, SourceType

class HackerNewsAdapter(BaseAdapter):
    """Adapter for Hacker News API"""
    
    BASE_URL = "https://hacker-news.firebaseio.com/v0"
    
    def __init__(self):
        super().__init__(SourceType.HACKERNEWS)
        self.client = httpx.Client(timeout=30.0)
    
    def fetch_items(self, hours: int = 24) -> List[IngestedItem]:
        """Fetch top stories from Hacker News"""
        try:
            # Get top story IDs
            response = self.client.get(f"{self.BASE_URL}/topstories.json")
            response.raise_for_status()
            story_ids = response.json()[:100]  # Top 100 stories
            
            items = []
            for story_id in story_ids:
                item = self._fetch_story(story_id)
                if item and self._is_recent(item.timestamp, hours):
                    items.append(item)
                    
                # Limit to prevent rate limiting
                if len(items) >= 50:
                    break
            
            return items
            
        except Exception as e:
            print(f"Error fetching Hacker News: {e}")
            return []
    
    def _fetch_story(self, story_id: int) -> Optional[IngestedItem]:
        """Fetch individual story details"""
        try:
            response = self.client.get(f"{self.BASE_URL}/item/{story_id}.json")
            response.raise_for_status()
            data = response.json()
            
            if not data or data.get('type') != 'story':
                return None
            
            # Skip stories without URLs (Ask HN, etc.)
            if not data.get('url'):
                return None
            
            # Generate a unique ID for this item
            item_id = self._generate_item_id(str(story_id))
            
            return IngestedItem(
                id=item_id,
                title=data.get('title', ''),
                description=data.get('text', '')[:500] if data.get('text') else '',
                url=data.get('url', ''),
                source_type=self.source_type,
                source_id=str(story_id),
                timestamp=datetime.fromtimestamp(data.get('time', 0)),
                engagement_score=float(data.get('score', 0)),
                # Add engagement metrics
                like_count=data.get('score', 0),  # HN uses score as upvotes
                comment_count=data.get('descendants', 0),
                metadata={
                    'comments': data.get('descendants', 0),
                    'author': data.get('by', '')
                }
            )
            
        except Exception as e:
            print(f"Error fetching story {story_id}: {e}")
            return None