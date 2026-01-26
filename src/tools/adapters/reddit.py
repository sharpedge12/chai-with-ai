import httpx
import re
from datetime import datetime
from typing import List, Optional
from src.tools.adapters.base import BaseAdapter
from src.models.schemas import IngestedItem, SourceType
from src.services.config import config

class RedditAdapter(BaseAdapter):
    """Adapter for Reddit API with improved content extraction"""
    
    BASE_URL = "https://www.reddit.com"
    SUBREDDITS = [
        "MachineLearning",
        "LocalLLaMA", 
        "artificial",
        "OpenAI",
        "ChatGPT",
        "compsci",
        "programming",
        "deeplearning"
    ]
    
    def __init__(self):
        super().__init__(SourceType.REDDIT)
        self.client = httpx.Client(timeout=30.0)
        self.headers = {
            'User-Agent': config.REDDIT_USER_AGENT
        }
    
    def fetch_items(self, hours: int = 24) -> List[IngestedItem]:
        """Fetch hot posts from relevant subreddits"""
        items = []
        
        for subreddit in self.SUBREDDITS:
            try:
                subreddit_items = self._fetch_subreddit(subreddit, hours)
                items.extend(subreddit_items)
            except Exception as e:
                print(f"    ❌ Error fetching r/{subreddit}: {e}")
                continue
        
        return items
    
    def _fetch_subreddit(self, subreddit: str, hours: int) -> List[IngestedItem]:
        """Fetch posts from a specific subreddit with improved content extraction"""
        
        try:
            url = f"{self.BASE_URL}/r/{subreddit}/hot.json?limit=25"
            response = self.client.get(url, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            posts = data['data']['children']
            
            items = []
            for post_data in posts:
                post = post_data['data']
                
                # Skip pinned posts, ads, and deleted posts
                if post.get('stickied') or post.get('is_sponsored') or post.get('removed_by_category'):
                    continue
                
                timestamp = datetime.fromtimestamp(post.get('created_utc', 0))
                if not self._is_recent(timestamp, hours):
                    continue
                
                # Get full description with better handling
                description = self._get_full_description(post)
                
                # Skip posts with no meaningful content
                if not description or len(description.strip()) < 20:
                    continue
                
                # Ensure full URL with domain
                url = self._ensure_full_url(post.get('url', ''), post.get('permalink', ''))
                
                # Skip image-only posts unless they have good descriptions
                if any(url.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif']) and len(description) < 50:
                    continue
                
                # Generate a unique ID for this item
                post_id = post.get('id', '')
                item_id = self._generate_item_id(post_id)
                
                item = IngestedItem(
                    id=item_id,  # Include the ID parameter
                    title=self._clean_title(post.get('title', '')),
                    description=description,
                    url=url,
                    source_type=self.source_type,
                    source_id=post_id,
                    timestamp=timestamp,
                    engagement_score=float(post.get('score', 0)),
                    metadata={
                        'subreddit': subreddit,
                        'comments': post.get('num_comments', 0),
                        'author': post.get('author', ''),
                        'upvote_ratio': post.get('upvote_ratio', 0),
                        'post_type': self._get_post_type(post)
                    }
                )
                items.append(item)
            
            return items
            
        except Exception as e:
            print(f"    ❌ Error fetching r/{subreddit}: {e}")
            return []
    
    def _ensure_full_url(self, url: str, permalink: str) -> str:
        """Ensure URL has full domain"""
        # If URL is empty, use permalink
        if not url:
            return f"{self.BASE_URL}{permalink}"
        
        # If URL is already a full URL, return it
        if url.startswith(('http://', 'https://')):
            return url
        
        # If URL is a relative Reddit URL (starts with /r/)
        if url.startswith('/r/'):
            return f"{self.BASE_URL}{url}"
        
        # If URL is a relative permalink
        if permalink:
            return f"{self.BASE_URL}{permalink}"
        
        # Default fallback
        return url
    
    # Rest of the methods remain the same...
    
    def _get_full_description(self, post: dict) -> str:
        """Get full description with better handling"""
        description = ""
        
        # Try selftext first (full text posts)
        if post.get('selftext') and post['selftext'].strip():
            description = post['selftext']
        
        # If no selftext, try to construct from other fields
        elif post.get('url') and post.get('domain'):
            # For link posts, use title + domain info
            domain = post.get('domain', '')
            if domain and domain not in ['self.' + post.get('subreddit', ''), 'i.redd.it']:
                description = f"Link to {domain}"
                
                # Add preview text if available
                if post.get('preview', {}).get('enabled'):
                    preview_text = self._extract_preview_text(post)
                    if preview_text:
                        description += f": {preview_text}"
        
        # For gallery posts, add gallery info
        elif post.get('is_gallery'):
            gallery_count = len(post.get('gallery_data', {}).get('items', []))
            description = f"Gallery with {gallery_count} images"
            if post.get('title'):
                description += f" - {post['title']}"
        
        # Clean and format the description
        if description:
            description = self._clean_description(description)
            
            # Ensure we don't cut off mid-sentence
            if len(description) > 400:
                description = self._truncate_at_sentence(description, 400)
        
        return description or "Content available at source link"
    
    def _extract_preview_text(self, post: dict) -> str:
        """Extract preview text from post data"""
        try:
            preview = post.get('preview', {})
            if preview.get('enabled') and 'reddit_video_preview' not in preview:
                # Try to get text from preview
                images = preview.get('images', [
])
                if images and 'variants' in images[1]:
                    # This is usually an image preview, skip
                    return ""
                
                # Look for text content in other preview fields
                return ""
        except:
            return ""
    
    def _clean_description(self, text: str) -> str:
        """Clean description text with improved handling"""
        if not text:
            return ""
        
        # Remove Reddit markdown formatting
        cleaned = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # Links
        cleaned = re.sub(r'\*\*([^*]+)\*\*', r'\1', cleaned)      # Bold
        cleaned = re.sub(r'\*([^*]+)\*', r'\1', cleaned)          # Italic
        cleaned = re.sub(r'~~([^~]+)~~', r'\1', cleaned)          # Strikethrough
        cleaned = re.sub(r'`([^`]+)`', r'\1', cleaned)            # Code
        cleaned = re.sub(r'^#+\s*', '', cleaned, flags=re.MULTILINE)  # Headers
        cleaned = re.sub(r'^\s*[-*+]\s*', '', cleaned, flags=re.MULTILINE)  # Lists
        cleaned = re.sub(r'^\s*\d+\.\s*', '', cleaned, flags=re.MULTILINE)  # Numbered lists
        
        # Remove excessive whitespace and newlines
        cleaned = re.sub(r'\n\s*\n', '\n', cleaned)  # Multiple newlines
        cleaned = re.sub(r'\s+', ' ', cleaned)       # Multiple spaces
        cleaned = cleaned.strip()
        
        # Remove common Reddit artifacts
        cleaned = re.sub(r'Edit\s*:\s*', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'Update\s*:\s*', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'TLDR\s*:\s*', 'Summary: ', cleaned, flags=re.IGNORECASE)
        
        return cleaned
    
    def _truncate_at_sentence(self, text: str, max_length: int) -> str:
        """Truncate text at sentence boundary"""
        if len(text) <= max_length:
            return text
        
        truncated = text[:max_length]
        
        # Find last sentence ending
        last_period = truncated.rfind('.')
        last_exclamation = truncated.rfind('!')
        last_question = truncated.rfind('?')
        
        last_sentence_end = max(last_period, last_exclamation, last_question)
        
        if last_sentence_end > max_length - 100:  # If we found a good break point
            return text[:last_sentence_end + 1]
        else:
            # Find last space instead
            last_space = truncated.rfind(' ')
            if last_space > max_length - 50:
                return text[:last_space] + "..."
            else:
                return truncated + "..."
    
    def _clean_title(self, title: str) -> str:
        """Clean post title"""
        if not title:
            return "Untitled Post"
        
        # Remove common Reddit title prefixes
        cleaned = re.sub(r'^\[([^\]]+)\]\s*', '', title)  # Remove [tags]
        cleaned = re.sub(r'^(TIFU|TIL|LPT|PSA|AMA|IAMA):\s*', '', cleaned, flags=re.IGNORECASE)
        
        # Clean up formatting
        cleaned = re.sub(r'\s+', ' ', cleaned.strip())
        
        return cleaned[:200]  # Limit title length
    
    def _get_post_type(self, post: dict) -> str:
        """Determine the type of Reddit post"""
        if post.get('is_self'):
            return 'text'
        elif post.get('is_video'):
            return 'video'
        elif post.get('is_gallery'):
            return 'gallery'
        elif any(post.get('url', '').endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif']):
            return 'image'
        else:
            return 'link'