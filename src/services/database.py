import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

# Fix imports - use absolute imports
from src.models.schemas import IngestedItem, EvaluationResult, SourceType, PersonaType
from src.services.config import config

class DatabaseManager:
    """SQLite database manager for the digest system"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.DATABASE_PATH
        self.init_database()
    
    def init_database(self):
        """Create database tables if they don't exist"""
        with self.get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS ingested_items (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    url TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    engagement_score REAL,
                    full_text TEXT,
                    metadata TEXT,  -- JSON
                    like_count INTEGER,
                    dislike_count INTEGER,
                    comment_count INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(source_type, source_id)
                );
                
                CREATE TABLE IF NOT EXISTS evaluations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id TEXT NOT NULL,
                    persona TEXT NOT NULL,
                    relevance_score REAL NOT NULL,
                    decision BOOLEAN NOT NULL,
                    reasoning TEXT,
                    extracted_data TEXT,  -- JSON
                    star_rating TEXT,
                    tags TEXT,  -- JSON array
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (item_id) REFERENCES ingested_items (id),
                    UNIQUE(item_id, persona)
                );
                
                CREATE TABLE IF NOT EXISTS digests (
                    id TEXT PRIMARY KEY,
                    persona TEXT NOT NULL,
                    generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    item_count INTEGER NOT NULL,
                    content TEXT NOT NULL,  -- JSON
                    delivered BOOLEAN DEFAULT FALSE
                );
                
                CREATE TABLE IF NOT EXISTS delivery_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    digest_id TEXT NOT NULL,
                    channel
 TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    delivered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (digest_id) REFERENCES digests (id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_items_timestamp ON ingested_items(timestamp);
                CREATE INDEX IF NOT EXISTS idx_items_source ON ingested_items(source_type);
                CREATE INDEX IF NOT EXISTS idx_evaluations_persona ON evaluations(persona);
                CREATE INDEX IF NOT EXISTS idx_evaluations_decision ON evaluations(decision);
            """)
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def save_ingested_item(self, item: IngestedItem) -> bool:
        """Save an ingested item, return True if new item"""
        with self.get_connection() as conn:
            try:
                conn.execute("""
                    INSERT INTO ingested_items 
                    (id, title, description, url, source_type, source_id, 
                     timestamp, engagement_score, full_text, metadata, 
                     like_count, dislike_count, comment_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item.id, item.title, item.description, item.url,
                    item.source_type.value, item.source_id, item.timestamp,
                    item.engagement_score, item.full_text,
                    json.dumps(item.metadata) if item.metadata else None,
                    item.like_count, item.dislike_count, item.comment_count
                ))
                return True
            except sqlite3.IntegrityError:
                # Item already exists
                return False
    
    def get_recent_items(self, hours: int = 24, source_type: SourceType = None) -> List[IngestedItem]:
        """Get items from the last N hours"""
        with self.get_connection() as conn:
            query = """
                SELECT * FROM ingested_items 
                WHERE timestamp > datetime('now', '-{} hours')
            """.format(hours)
            
            params = []
            if source_type:
                query += " AND source_type = ?"
                params.append(source_type.value)
            
            query += " ORDER BY timestamp DESC"
            
            rows = conn.execute(query, params).fetchall()
            
            items = []
            for row in rows:
                items.append(IngestedItem(
                    id=row['id'],
                    title=row['title'],
                    description=row['description'],
                    url=row['url'],
                    source_type=SourceType(row['source_type']),
                    source_id=row['source_id'],
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    engagement_score=row['engagement_score'],
                    full_text=row['full_text'],
                    metadata=json.loads(row['metadata']) if row['metadata'] else None,
                    like_count=row['like_count'],
                    dislike_count=row['dislike_count'],
                    comment_count=row['comment_count']
                ))
            
            return items
    
    def save_evaluation(self, evaluation: EvaluationResult) -> bool:
        """Save an evaluation result"""
        with self.get_connection() as conn:
            try:
                conn.execute("""
                    INSERT INTO evaluations 
                    (item_id, persona, relevance_score, decision, reasoning, extracted_data, star_rating, tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    evaluation.item_id,
                    evaluation.persona.value,
                    evaluation.relevance_score,
                    evaluation.decision,
                    evaluation.reasoning,
                    json.dumps(evaluation.extracted_data),
                    evaluation.star_rating,
                    json.dumps(evaluation.tags) if evaluation.tags else None
                ))
                return True
            except sqlite3.IntegrityError:
                # Evaluation already exists
                return False
    
    def get_evaluation(self, item_id: str, persona: PersonaType) -> Optional[EvaluationResult]:
        """Get existing evaluation for an item and persona"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM evaluations 
                WHERE item_id = ? AND persona = ?
            """, (item_id, persona.value))
            
            row = cursor.fetchone()
            if row:
                return EvaluationResult(
                    item_id=row['item_id'],
                    persona=PersonaType(row['persona']),
                    relevance_score=row['relevance_score'],
                    decision=bool(row['decision']),
                    reasoning=row['reasoning'],
                    extracted_data=json.loads(row['extracted_data']) if row['extracted_data'] else {},
                    star_rating=row['star_rating'],
                    tags=json.loads(row['tags']) if row['tags'] else []
                )
            return None

    def count_evaluations(self) -> Dict[str, int]:
        """Count evaluations by persona"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT persona, COUNT(*) as count 
                FROM evaluations 
                GROUP BY persona
            """)
            
            counts = {}
            for row in cursor.fetchall():
                counts[row['persona']] = row['count']
            
            return counts
        
    def update_evaluation_tags(self, item_id: str, persona: PersonaType, tags: list) -> bool:
        """Update tags for existing evaluation"""
        with self.get_connection() as conn:
            try:
                conn.execute("""
                    UPDATE evaluations 
                    SET tags = ?
                    WHERE item_id = ? AND persona = ?
                """, (
                    json.dumps(tags) if tags else None,
                    item_id,
                    persona.value
                ))
                return True
            except Exception as e:
                print(f"Failed to update tags: {e}")
                return False


# Global database instance
db = DatabaseManager()