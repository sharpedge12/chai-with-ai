import json
import random
import re
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

from src.services.database import db
from src.services.config import config
from src.models.schemas import PersonaType
from src.services.telegram_delivery import telegram_delivery
from src.services.tts_service import tts_service


class DigestBuilder:
    """Builds formatted digests from evaluated content"""
    
    def __init__(self):
        self.output_dir = config.PROJECT_ROOT / "output"
        self.output_dir.mkdir(exist_ok=True)
    
    def _row_to_dict(self, row) -> Dict[str, Any]:
        """Convert SQLite Row to dictionary"""
        return {key: row[key] for key in row.keys()}
    
    def _should_include_item(self, item: Dict[str, Any]) -> bool:
        """Filter out low-quality items before including in digest"""
        
        # Skip items with very short or empty descriptions
        description = item.get('description', '')
        if not description or len(description.strip()) < 30:
            print(f"    ⚠️  Skipping '{item.get('title', '')[:50]}...' - description too short")
            return False
        
        # Skip items with placeholder descriptions
        placeholder_phrases = [
            'content not available',
            'no description available',
            'see full article for details',
            'content summary not available'
        ]
        if any(phrase in description.lower() for phrase in placeholder_phrases) and len(description) < 100:
            print(f"    ⚠️  Skipping '{item.get('title', '')[:50]}...' - placeholder content")
            return False
        
        # Skip items with very low engagement AND low scores (likely spam/low quality)
        engagement = item.get('engagement_score', 0) or 0
        score = item.get('relevance_score', 0)
        if engagement == 0 and score < 0.6:
            print(f"    ⚠️  Skipping '{item.get('title', '')[:50]}...' - low engagement + low score")
            return False
        
        # Skip items with generic/poor reasoning
        reasoning = item.get('reasoning', '').lower()
        generic_phrases = [
            'somewhat related',
            'lacks depth',
            'not directly related',
            'difficult to determine',
            'evaluation failed',
            'lacks technical depth and actionability',
            'not relevant to ai/ml practitioners'
        ]
        if any(phrase in reasoning for phrase in generic_phrases) and score < 0.7:
            print(f"    ⚠️  Skipping '{item.get('title', '')[:50]}...' - generic reasoning")
            return False
        
        # Skip duplicate or very similar titles
        title = item.get('title', '').lower()
        if len(title) < 10:
            print(f"    ⚠️  Skipping - title too short")
            return False
        
        print(f"    ✅ Including '{item.get('title', '')[:50]}...' - passed quality filter")
        return True
    
    def _ensure_source_diversity(self, items: List[Dict]) -> List[Dict]:
        """Ensure good mix of sources"""
        source_counts = {}
        diverse_items = []
        
        for item in items:
            source = item.get('source_type', 'unknown')
            current_count = source_counts.get(source, 0)
            
            # Limit items per source (max 40% from any single source)
            max_per_source = max(2, len(items) // 2)
            
            if current_count < max_per_source:
                diverse_items.append(item)
                source_counts[source] = current_count + 1
            else:
                print(f"    ⚖️  Skipping item from {source} for source diversity")
        
        return diverse_items
    
    def build_all_digests(self) -> Dict[str, Any]:
        """Build all enabled digests"""
        results = {}
        
        if config.PERSONA_GENAI_NEWS_ENABLED:
            results['genai_news'] = self.build_genai_digest()
        
        if config.PERSONA_PRODUCT_IDEAS_ENABLED:
            results['product_ideas'] = self.build_product_digest()
        
        return results
    
    def build_genai_digest(self) -> Dict[str, Any]:
        """Build GenAI News digest with enhanced features"""
        print("  📝 Building GenAI News digest...")
        
        with db.get_connection() as conn:
            cursor = conn.execute("""
                SELECT i.*, e.relevance_score, e.reasoning, e.extracted_data, e.star_rating, e.tags
                FROM ingested_items i
                JOIN evaluations e ON i.id = e.item_id
                WHERE e.persona = 'genai_news' AND e.decision = 1
                ORDER BY e.relevance_score DESC, i.engagement_score DESC
                LIMIT 30
            """)
            
            raw_items = cursor.fetchall()
        
        if not raw_items:
            print("    ⚠️  No approved GenAI items found")
            return {"items": [], "count": 0}
        
        print(f"    📊 Found {len(raw_items)} approved items, applying quality filter...")
        
        # Convert rows to dictionaries and apply quality filter
        filtered_items = []
        for row in raw_items:
            item_dict = self._row_to_dict(row)
            
            if self._should_include_item(item_dict):
                filtered_items.append(item_dict)
            
            if len(filtered_items) >= 15:
                break
        
        print(f"    ✅ After filtering: {len(filtered_items)} quality items")
        
        if not filtered_items:
            print("    ⚠️  No items passed quality filter")
            return {"items": [], "count": 0}
        
        # Build digest content with proper timestamp formatting
        current_time = datetime.now()
        formatted_time = current_time.strftime('%B %d, %Y at %I:%M %p')  # e.g., "February 02, 2026 at 05:17 PM"
        
        digest = {
            "persona": "GenAI News",
            "generated_at": formatted_time,  # Human-readable format
            "generated_timestamp": current_time.isoformat(),  # Keep ISO for programmatic use
            "count": len(filtered_items),
            "items": [],
            "summary": f'"🤖 GenAI News Digest - {len(filtered_items)} High-Quality Technical AI/ML Updates"'  # Add quotes
        }
        
        for item in filtered_items:
            try:
                extracted_data = json.loads(item['extracted_data']) if item['extracted_data'] else {}
                tags = json.loads(item['tags']) if item['tags'] else []
            except:
                extracted_data = {}
                tags = []
            
            # Ensure why_it_matters has quotes
            why_it_matters = extracted_data.get('why_it_matters', '')
            if why_it_matters and not (why_it_matters.startswith('"') and why_it_matters.endswith('"')):
                why_it_matters = f'"{why_it_matters}"'
            
            # Format description as a quote
            description = self._clean_description(item['description'])
            if description and not description.startswith('"'):
                description = f'"{description}"'
            
            digest_item = {
                "title": item['title'],
                "url": item['url'],
                "description": description,  # Now quoted
                "source": item['source_type'],
                "score": item['relevance_score'],
                "star_rating": item.get('star_rating', '⭐'),
                "tags": tags,
                "topic": extracted_data.get('topic', 'AI/ML'),
                "why_it_matters": why_it_matters,
                "target_audience": extracted_data.get('target_audience', 'developer'),
                "reasoning": item['reasoning'][:200] if item['reasoning'] else '',
                "engagement": item['engagement_score'],
                "like_count": item.get('like_count'),
                "dislike_count": item.get('dislike_count'),
                "comment_count": item.get('comment_count'),
                "timestamp": item['timestamp']
            }
            digest['items'].append(digest_item)
        
        # Save digest
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self._save_digest(digest, f"genai_news_{timestamp}")
        
        # Generate audio summary
        print("  🔊 Generating audio summary...")
        audio_path = tts_service.generate_audio_summary(digest)
        if audio_path:
            digest['audio_summary_path'] = audio_path
        
        # Deliver digest
        self.deliver_digest(digest)
        
        return digest
    
    def build_product_digest(self) -> Dict[str, Any]:
        """Build Product Ideas digest with enhanced features"""
        print("  📝 Building Product Ideas digest...")
        
        with db.get_connection() as conn:
            cursor = conn.execute("""
                SELECT i.*, e.relevance_score, e.reasoning, e.extracted_data, e.star_rating, e.tags
                FROM ingested_items i
                JOIN evaluations e ON i.id = e.item_id
                WHERE e.persona = 'product_ideas' AND e.decision = 1
                ORDER BY e.relevance_score DESC, i.engagement_score DESC
                LIMIT 30
            """)
            
            raw_items = cursor.fetchall()
        
        if not raw_items:
            print("    ⚠️  No approved Product Ideas found")
            return {"items": [], "count": 0}
        
        print(f"    📊 Found {len(raw_items)} approved items, applying quality filter...")
        
        # Convert rows to dictionaries and apply quality filter
        filtered_items = []
        for row in raw_items:
            item_dict = self._row_to_dict(row)
            
            if self._should_include_item(item_dict):
                filtered_items.append(item_dict)
            
            if len(filtered_items) >= 15:
                break
        
        print(f"    ✅ After filtering: {len(filtered_items)} quality items")
        
        if not filtered_items:
            print("    ⚠️  No items passed quality filter")
            return {"items": [], "count": 0}
        
        # Build digest content with proper timestamp formatting
        current_time = datetime.now()
        formatted_time = current_time.strftime('%B %d, %Y at %I:%M %p')
        
        digest = {
            "persona": "Product Ideas",
            "generated_at": formatted_time,  # Human-readable format
            "generated_timestamp": current_time.isoformat(),  # Keep ISO for programmatic use
            "count": len(filtered_items),
            "items": [],
            "summary": f'"💡 Product Ideas Digest - {len(filtered_items)} High-Quality Launches & Concepts"'  # Add quotes
        }
        
        for item in filtered_items:
            try:
                extracted_data = json.loads(item['extracted_data']) if item['extracted_data'] else {}
                tags = json.loads(item['tags']) if item['tags'] else []
            except:
                extracted_data = {}
                tags = []
            
            # Ensure why_it_matters has quotes
            why_it_matters = extracted_data.get('why_it_matters', '')
            if why_it_matters and not (why_it_matters.startswith('"') and why_it_matters.endswith('"')):
                why_it_matters = f'"{why_it_matters}"'
            
            # Format description as a quote
            description = self._clean_description(item['description'])
            if description and not description.startswith('"'):
                description = f'"{description}"'
            
            digest_item = {
                "title": item['title'],
                "url": item['url'],
                "description": description,  # Now quoted
                "source": item['source_type'],
                "score": item['relevance_score'],
                "star_rating": item.get('star_rating', '⭐'),
                "tags": tags,
                "topic": extracted_data.get('topic', 'Product'),
                "why_it_matters": why_it_matters,
                "target_audience": extracted_data.get('target_audience', 'entrepreneur'),
                "reasoning": item['reasoning'][:200] if item['reasoning'] else '',
                "engagement": item['engagement_score'],
                "like_count": item.get('like_count'),
                "dislike_count": item.get('dislike_count'),
                "comment_count": item.get('comment_count'),
                "timestamp": item['timestamp']
            }
            digest['items'].append(digest_item)
        
        # Save digest
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self._save_digest(digest, f"product_ideas_{timestamp}")
        
        # Generate audio summary
        print("  🔊 Generating audio summary...")
        audio_path = tts_service.generate_audio_summary(digest)
        if audio_path:
            digest['audio_summary_path'] = audio_path
        
        self.deliver_digest(digest)
        
        return digest
    
    def _clean_description(self, description: str) -> str:
        """Clean description for better display"""
        if not description:
            return "Content summary not available - see full article for details"
        
        # Remove Reddit/markdown formatting
        cleaned = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', description)
        cleaned = re.sub(r'\*\*([^*]+)\*\*', r'\1', cleaned)
        cleaned = re.sub(r'\*([^*]+)\*', r'\1', cleaned)
        cleaned = re.sub(r'\\', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned.strip())
        
        # Ensure proper length and sentence ending
        if len(cleaned) > 300:
            truncated = cleaned[:300]
            last_period = truncated.rfind('.')
            last_space = truncated.rfind(' ')
            
            if last_period > 250:
                cleaned = truncated[:last_period + 1]
            elif last_space > 280:
                cleaned = truncated[:last_space] + "..."
            else:
                cleaned = truncated + "..."
        
        return cleaned
    
    def _save_digest(self, digest: Dict[str, Any], filename: str):
        """Save digest in multiple formats"""
        
        # Save JSON
        json_path = self.output_dir / f"{filename}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(digest, f, indent=2, ensure_ascii=False)
        
        # Save Markdown
        md_path = self.output_dir / f"{filename}.md"
        markdown_content = self._convert_to_markdown(digest)
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print(f"    📄 Saved: {json_path.name}, {md_path.name}")
    
    def _convert_to_markdown(self, digest: Dict[str, Any]) -> str:
        """Convert digest to enhanced Markdown format with quote styling"""
        md = f"# {digest['summary']}\n\n"
        md += f"**Generated:** {digest['generated_at']}\n"
        md += f"**Items:** {digest['count']}\n"
        
        # Add quality metrics
        if digest['items']:
            scores = [item['score'] for item in digest['items']]
            avg_score = sum(scores) / len(scores)
            high_quality_count = len([s for s in scores if s >= 0.7])
            
            md += f"**Average Score:** {avg_score:.2f}\n"
            md += f"**High Quality Items (≥0.7):** {high_quality_count}/{len(scores)}\n"
            md += f"**Score Range:** {min(scores):.2f} - {max(scores):.2f}\n"
        
        # Add audio summary info
        if digest.get('audio_summary_path'):
            md += f"**🔊 Audio Summary:** Available\n"
        
        md += "\n---\n\n"
        
        if digest['count'] == 0:
            md += "No high-quality items found for this digest.\n"
            return md
        
        # Process items without duplication - collect unique items first
        unique_items = {}
        for item in digest['items']:
            item_id = item.get('url', item.get('title', ''))  # Use URL or title as unique identifier
            if item_id not in unique_items:
                unique_items[item_id] = item
        
        # Display all items in order without tag grouping
        item_counter = 1
        for item in unique_items.values():
            md += self._format_item_markdown(item, item_counter)
            item_counter += 1
        
        return md
    
    def _format_item_markdown(self, item: Dict[str, Any], counter: int) -> str:
        """Format individual item for markdown with quote styling"""
        title = item['title'][:80] + "..." if len(item['title']) > 80 else item['title']
        md = f"## {counter}. [{title}]({item['url']})\n\n"
        
        # Enhanced metadata with engagement
        md += f"**Rating:** {item.get('star_rating', '⭐')} | **Source:** {item['source']} | **Engagement:** {item.get('engagement', 'N/A')}"
        
        # Add engagement metrics if available
        engagement_parts = []
        if item.get('like_count') is not None:
            engagement_parts.append(f"👍 {item['like_count']}")
        if item.get('dislike_count') is not None:
            engagement_parts.append(f"👎 {item['dislike_count']}")
        if item.get('comment_count') is not None:
            engagement_parts.append(f"💬 {item['comment_count']}")
        
        if engagement_parts:
            md += f" | **Metrics:** {' | '.join(engagement_parts)}"
        
        md += "\n\n"
        
        # Tags - show without emojis, just clean text
        tags = item.get('tags', [])
        if tags:
            md += f"**Tags:** {' | '.join(tags)}\n\n"
        
        # Topic and audience
        if item.get('topic'):
            md += f"**Topic:** {item['topic']}\n"
        if item.get('target_audience'):
            md += f"**Target Audience:** {item['target_audience']}\n\n"
        
        # Description as blockquote (already has quotes, format as blockquote)
        description = item['description'].strip('"')  # Remove quotes for blockquote
        if description and "Content summary not available" not in description:
            md += f"> {description}\n\n"
        else:
            md += f"> *[View full content at source link above]*\n\n"
        
        # Why it matters as blockquote (already has quotes, format as blockquote)
        if item.get('why_it_matters'):
            why_it_matters = item['why_it_matters'].strip('"')  # Remove quotes for blockquote
            md += f"**Why it matters:**\n> {why_it_matters}\n\n"
        
        md += "---\n\n"
        return md
    
    def deliver_digest(self, digest: Dict[str, Any]) -> bool:
        """Deliver digest to configured channels"""
        delivered = False
        
        # Telegram delivery
        if config.TELEGRAM_ENABLED:
            print("  📱 Delivering to Telegram...")
            if telegram_delivery.is_configured():
                success = telegram_delivery.send_digest(digest)
                if success:
                    print("    ✅ Delivered to Telegram")
                    delivered = True
                else:
                    print("    ❌ Failed to deliver to Telegram")
            else:
                print("    ⚠️  Telegram delivery not configured")
        
        return delivered


# Global digest builder
digest_builder = DigestBuilder()