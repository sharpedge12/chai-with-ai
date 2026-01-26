import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.services.database import db
from src.models.schemas import SourceType, PersonaType
import json

def view_all_data():
    print("🗄️  Complete Database Contents")
    print("=" * 60)
    
    try:
        with db.get_connection() as conn:
            
            # 1. INGESTED ITEMS
            print("\n📥 INGESTED ITEMS")
            print("-" * 40)
            
            cursor = conn.execute("""
                SELECT COUNT(*) as total,
                       source_type,
                       MIN(timestamp) as oldest,
                       MAX(timestamp) as newest
                FROM ingested_items 
                GROUP BY source_type
                ORDER BY total DESC
            """)
            
            print("📊 Summary by source:")
            for row in cursor.fetchall():
                print(f"  {row['source_type']}: {row['total']} items ({row['oldest']} to {row['newest']})")
            
            # Show all items
            cursor = conn.execute("""
                SELECT id, title, description, url, source_type, timestamp, engagement_score
                FROM ingested_items 
                ORDER BY timestamp DESC
            """)
            
            items = cursor.fetchall()
            print(f"\n📋 All {len(items)} items:")
            
            for i, item in enumerate(items, 1):
                print(f"\n{i}. [{item['source_type']}] {item['title']}")
                print(f"   ID: {item['id']}")
                print(f"   URL: {item['url']}")
                print(f"   Description: {item['description'][:100]}...")
                print(f"   Timestamp: {item['timestamp']}")
                print(f"   Engagement: {item['engagement_score']}")
            
            # 2. EVALUATIONS
            print(f"\n\n🤖 EVALUATIONS")
            print("-" * 40)
            
            cursor = conn.execute("""
                SELECT COUNT(*) as total,
                       persona,
                       AVG(relevance_score) as avg_score,
                       SUM(CASE WHEN decision = 1 THEN 1 ELSE 0 END) as approved
                FROM evaluations 
                GROUP BY persona
            """)
            
            print("📊 Summary by persona:")
            for row in cursor.fetchall():
                approval_rate = (row['approved'] / row['total']) * 100 if row['total'] > 0 else 0
                print(f"  {row['persona']}: {row['total']} evaluations, {row['approved']} approved ({approval_rate:.1f}%)")
                print(f"    Average score: {row['avg_score']:.3f}")
            
            # Show all evaluations with item details
            cursor = conn.execute("""
                SELECT e.*, i.title, i.source_type
                FROM evaluations e
                JOIN ingested_items i ON e.item_id = i.id
                ORDER BY e.created_at DESC
            """)
            
            evaluations = cursor.fetchall()
            print(f"\n📋 All {len(evaluations)} evaluations:")
            
            for i, eval in enumerate(evaluations, 1):
                status = "✅ APPROVED" if eval['decision'] else "❌ REJECTED"
                print(f"\n{i}. {status} [{eval['persona']}] Score: {eval['relevance_score']:.2f}")
                print(f"   Item: {eval['title']}")
                print(f"   Source: {eval['source_type']}")
                print(f"   Reasoning: {eval['reasoning'][:100]}...")
                
                # Show extracted data if available
                if eval['extracted_data']:
                    try:
                        extracted = json.loads(eval['extracted_data'])
                        print(f"   Topic: {extracted.get('topic', 'N/A')}")
                        print(f"   Target: {extracted.get('target_audience', 'N/A')}")
                    except:
                        pass
                
                print(f"   Evaluated: {eval['created_at']}")
            
            # 3. APPROVED ITEMS READY FOR DIGEST
            print(f"\n\n✅ APPROVED ITEMS (Ready for Digest)")
            print("-" * 40)
            
            cursor = conn.execute("""
                SELECT i.title, i.url, i.source_type, e.persona, e.relevance_score, e.reasoning
                FROM evaluations e
                JOIN ingested_items i ON e.item_id = i.id
                WHERE e.decision = 1
                ORDER BY e.persona, e.relevance_score DESC
            """)
            
            approved = cursor.fetchall()
            
            if approved:
                current_persona = None
                for item in approved:
                    if item['persona'] != current_persona:
                        current_persona = item['persona']
                        print(f"\n🎯 {current_persona.upper()}:")
                    
                    print(f"  • {item['title']} (Score: {item['relevance_score']:.2f})")
                    print(f"    Source: {item['source_type']} | URL: {item['url']}")
                    print(f"    Reasoning: {item['reasoning'][:80]}...")
                    print()
            else:
                print("❌ No approved items found")
            
            # 4. DATABASE STATISTICS
            print(f"\n📊 DATABASE STATISTICS")
            print("-" * 40)
            
            # Total counts
            cursor = conn.execute("SELECT COUNT(*) FROM ingested_items")
            total_items = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM evaluations")
            total_evaluations = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM evaluations WHERE decision = 1")
            total_approved = cursor.fetchone()[0]
            
            print(f"📥 Total items ingested: {total_items}")
            print(f"🤖 Total evaluations: {total_evaluations}")
            print(f"✅ Total approved: {total_approved}")
            
            if total_evaluations > 0:
                approval_rate = (total_approved / total_evaluations) * 100
                print(f"📈 Overall approval rate: {approval_rate:.1f}%")
            
            # Score distribution
            cursor = conn.execute("""
                SELECT 
                    CASE 
                        WHEN relevance_score < 0.3 THEN 'Low (0.0-0.3)'
                        WHEN relevance_score < 0.6 THEN 'Medium (0.3-0.6)'
                        WHEN relevance_score < 0.8 THEN 'High (0.6-0.8)'
                        ELSE 'Very High (0.8+)'
                    END as score_range,
                    COUNT(*) as count
                FROM evaluations
                GROUP BY score_range
                ORDER BY MIN(relevance_score)
            """)
            
            print(f"\n📊 Score distribution:")
            for row in cursor.fetchall():
                print(f"  {row['score_range']}: {row['count']} evaluations")
                
    except Exception as e:
        print(f"❌ Error viewing database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    view_all_data()