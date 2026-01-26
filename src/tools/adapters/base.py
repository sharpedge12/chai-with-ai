from abc import ABC, abstractmethod
from typing import List
from datetime import datetime, timedelta
from src.models.schemas import IngestedItem, SourceType
import re

class BaseAdapter(ABC):
    """Base class for content source adapters"""
    
    def __init__(self, source_type: SourceType):
        self.source_type = source_type
    
    @abstractmethod
    def fetch_items(self, hours: int = 24) -> List[IngestedItem]:
        """Fetch items from the last N hours"""
        pass
    
    def _generate_item_id(self, source_id: str) -> str:
        """Generate unique item ID"""
        return f"{self.source_type.value}_{source_id}"
    
    def _is_recent(self, timestamp: datetime, hours: int) -> bool:
        """Check if timestamp is within the last N hours"""
        cutoff = datetime.now() - timedelta(hours=hours)
        return timestamp > cutoff
    
    def _clean_text(self, text: str, max_length: int = 500) -> str:
        """Clean and truncate text with better handling"""
        if not text:
            return "Content not available"
        
        # Remove extra whitespace and newlines
        cleaned = re.sub(r'\s+', ' ', text.strip())
        
        # Remove markdown links but keep the text
        cleaned = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', cleaned)
        
        # Remove HTML tags
        cleaned = re.sub(r'<[^>]+>', '', cleaned)
        
        # Remove Reddit formatting
        cleaned = re.sub(r'\
*\*([^*]+)\*\*', r'\1', cleaned)  # Bold
        cleaned = re.sub(r'\*([^*]+)\*', r'\1', cleaned)      # Italic
        
        # Ensure minimum content length
        if len(cleaned) < 50:
            cleaned += " [Content summary not available - see full article for details]"
        
        # Truncate if too long, but try to end at sentence boundary
        if len(cleaned) > max_length:
            truncated = cleaned[:max_length]
            last_period = truncated.rfind('.')
            last_space = truncated.rfind(' ')
            
            if last_period > max_length - 100:  # If period is near the end
                cleaned = truncated[:last_period + 1]
            elif last_space > max_length - 50:   # If space is reasonably close
                cleaned = truncated[:last_space] + "..."
            else:
                cleaned = truncated + "..."
        
        return cleaned