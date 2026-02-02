from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

class PersonaType(Enum):
    GENAI_NEWS = "genai_news"
    PRODUCT_IDEAS = "product_ideas"

class SourceType(Enum):
    HACKERNEWS = "hackernews"
    REDDIT = "reddit"
    RSS = "rss"
    PRODUCT_HUNT = "product_hunt"
    INDIE_HACKERS = "indie_hackers"

@dataclass
class IngestedItem:
    """Raw item from content sources"""
    id: str
    title: str
    description: str
    url: str
    source_type: SourceType
    source_id: str  # Original ID from source
    timestamp: datetime
    engagement_score: Optional[float] = None
    full_text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    # New fields for engagement metrics
    like_count: Optional[int] = None
    dislike_count: Optional[int] = None
    comment_count: Optional[int] = None

@dataclass
class EvaluationResult:
    """LLM evaluation output"""
    item_id: str
    persona: PersonaType
    relevance_score: float
    decision: bool  # Include in digest
    reasoning: str
    extracted_data: Dict[str, Any]  # Persona-specific fields
    # New fields
    tags: List[str] = None  # Content tags
    star_rating: str = None  # Star representation
    
@dataclass
class DigestItem:
    """Processed item ready for digest"""
    original_item: IngestedItem
    evaluation: EvaluationResult
    summary: str
    cluster_id: Optional[str] = None