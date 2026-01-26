import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.services.database import db
from src.models.schemas import PersonaType

def quick_status():
    print("🔍 Quick Database Status Check")
    print("=" * 40)
    
    try:
        # Count items
        with db.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM ingested_items")
            item_count = cursor.fetchone()[0]
            print(f"📥 Total items: {item_count}")
            
            # Count evaluations
            cursor = conn.execute("SELECT COUNT(*) FROM evaluations")
            eval_count = cursor.fetchone()[0]
            print(f"🤖 Total evaluations: {eval_count}")
            
            # Count by persona
            cursor = conn.execute("SELECT persona, COUNT(*) FROM evaluations GROUP BY persona")
            for row in cursor.fetchall():
                print(f"  {row[0]}: {row[1]} evaluations")
            
            # Count approved items
            cursor = conn.execute("SELECT persona, COUNT(*) FROM evaluations WHERE decision = 1 GROUP BY persona")
            approved = cursor.fetchall()
            if approved:
                print(f"\n✅ Approved items:")
                for row in approved:
                    print(f"  {row[0]}: {row[1]} approved")
            else:
                print(f"\n⚠️  No approved items found")
                
            # Show recent evaluations
            cursor = conn.execute("""
                SELECT i.title, e.persona, e.relevance_score, e.decision 
                FROM evaluations e 
                JOIN ingested_items i ON e.item_id = i.id 
                ORDER BY e.created_at DESC 
                LIMIT 5
            """)
            
            print(f"\n📋 Recent evaluations:")
            for row in cursor.fetchall():
                status = "✅" if row[3] else "❌"
                print(f"  {status} {row[1]}: {row[0][:50]}... (score: {row[2]:.2f})")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    quick_status()