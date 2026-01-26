import sys
import os
from datetime import datetime
from pathlib import Path
from src.services.telegram_delivery import telegram_delivery

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Now import with absolute paths
from src.services.config import config
from src.services.database import db
from src.services.llm_client import llm
from src.tools.adapters.hackernews import HackerNewsAdapter
from src.tools.adapters.reddit import RedditAdapter
from src.tools.adapters.rss import RSSAdapter
from src.tools.evaluators import genai_evaluator, product_evaluator
from src.models.schemas import PersonaType
from src.workflows.digest_builder import digest_builder  # Add this import

# Rest of your functions remain the same...

def test_setup():
    """Test basic setup and connections"""
    print("🔧 Testing AI Digest System Setup...")
    
    # Test database
    print("📊 Testing database connection...")
    try:
        db.init_database()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False
    
    # Test LLM
    print("🤖 Testing LLM connection...")
    try:
        if llm.test_connection():
            print("✅ LLM connection successful")
        else:
            print("❌ LLM connection failed - make sure Ollama is running")
            print("   Run: ollama serve")
            print("   Then: ollama pull llama3:8b-instruct-q4_K_M")
            return False
    except Exception as e:
        print(f"❌ LLM error: {e}")
        return False
    
    return True

def fetch_content():
    """Fetch content from all sources"""
    print("📥 Fetching content from sources...")
    
    adapters = [
        HackerNewsAdapter(),
        RedditAdapter(),
        RSSAdapter()
    ]
    
    total_items = 0
    new_items = 0
    
    for adapter in adapters:
        print(f"  Fetching from {adapter.source_type.value}...")
        try:
            items = adapter.fetch_items(hours=config.CONTENT_HOURS_LOOKBACK)
            print(f"    Found {len(items)} items")
            
            for item in items:
                total_items += 1
                if db.save_ingested_item(item):
                    new_items += 1
                    
        except Exception as e:
            print(f"    ❌ Error: {e}")
    
    print(f"📊 Total items: {total_items}, New items: {new_items}")
    return new_items

def evaluate_content(limit: int = None, force: bool = False):
    """Evaluate content with LLM"""
    print("🤖 Evaluating content...")
    
    if force:
        print("  🔄 Force mode: Will re-evaluate existing items")
    
    # Get recent items
    recent_items = db.get_recent_items(hours=config.CONTENT_HOURS_LOOKBACK)
    
    # Limit items for testing
    if limit:
        recent_items = recent_items[:limit]
        print(f"  Limited to {limit} items for testing")
    
    print(f"  Found {len(recent_items)} recent items to evaluate")
    
    evaluated_count = 0
    skipped_count = 0
    start_time = datetime.now()

    
    for i, item in enumerate(recent_items, 1):
        try:
            print(f"  Processing {i}/{len(recent_items)}: {item.title[:50]}...")
            
            # Evaluate for GenAI News if enabled
            if config.PERSONA_GENAI_NEWS_ENABLED:
                existing = db.get_evaluation(item.id, PersonaType.GENAI_NEWS)
                
                if existing and not force:
                    print(f"    ⏭️  GenAI evaluation already exists (score: {existing.relevance_score:.2f})")
                    skipped_count += 1
                else:
                    print(f"    🔄 Starting GenAI evaluation...")
                    evaluation = genai_evaluator.evaluate(item)
                    
                    if force and existing:
                        # Delete existing evaluation first
                        with db.get_connection() as conn:
                            conn.execute("DELETE FROM evaluations WHERE item_id = ? AND persona = ?", 
                                       (item.id, PersonaType.GENAI_NEWS.value))
                    
                    if db.save_evaluation(evaluation):
                        evaluated_count += 1
                        print(f"    ✅ GenAI: {'Relevant' if evaluation.decision else 'Not relevant'} (score: {evaluation.relevance_score:.2f})")
                    else:
                        print(f"    ❌ Failed to save GenAI evaluation")
            
            # Evaluate for Product Ideas if enabled
            if config.PERSONA_PRODUCT_IDEAS_ENABLED:
                existing = db.get_evaluation(item.id, PersonaType.PRODUCT_IDEAS)
                
                if existing and not force:
                    print(f"    ⏭️  Product evaluation already exists (score: {existing.relevance_score:.2f})")
                    skipped_count += 1
                else:
                    print(f"    🔄 Starting Product evaluation...")
                    evaluation = product_evaluator.evaluate(item)
                    
                    if force and existing:
                        # Delete existing evaluation first
                        with db.get_connection() as conn:
                            conn.execute("DELETE FROM evaluations WHERE item_id = ? AND persona = ?", 
                                       (item.id, PersonaType.PRODUCT_IDEAS.value))
                    
                    if db.save_evaluation(evaluation):
                        evaluated_count += 1
                        print(f"    ✅ Product: {'Relevant' if evaluation.decision else 'Not relevant'} (score: {evaluation.relevance_score:.2f})")
                    else:
                        print(f"    ❌ Failed to save Product evaluation")
                        
        except Exception as e:
            print(f"    ❌ Evaluation error: {e}")
    
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"📊 Evaluated {evaluated_count} new items, skipped {skipped_count} existing items")
    print(f"⏱️  Total time: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")

def show_status():
    """Show database status and recent items"""
    print("📊 Database Status")
    print("=" * 30)
    
    # Get recent items
    recent_items = db.get_recent_items(hours=24)
    print(f"📥 Recent items (24h): {len(recent_items)}")
    
    # Group by source
    by_source = {}
    for item in recent_items:
        source = item.source_type.value
        by_source[source] = by_source.get(source, 0) + 1
    
    for source, count in by_source.items():
        print(f"  {source}: {count} items")
    
    # Show evaluation counts
    eval_counts = db.count_evaluations()
    if eval_counts:
        print(f"\n🤖 Evaluations:")
        for persona, count in eval_counts.items():
            print(f"  {persona}: {count} evaluations")
    else:
        print(f"\n🤖 No evaluations found")
    
    # Show sample items
    print(f"\n📋 Sample Items:")
    for item in recent_items[:3]:
        print(f"  • {item.title[:60]}...")
        print(f"    Source: {item.source_type.value} | Score: {item.engagement_score}")
        
        # Show evaluations for this item
        genai_eval = db.get_evaluation(item.id, PersonaType.GENAI_NEWS)
        product_eval = db.get_evaluation(item.id, PersonaType.PRODUCT_IDEAS)
        
        if genai_eval:
            print(f"    GenAI: {'✅' if genai_eval.decision else '❌'} ({genai_eval.relevance_score:.2f})")
        if product_eval:
            print(f"    Product: {'✅' if product_eval.decision else '❌'} ({product_eval.relevance_score:.2f})")
        print()

def generate_digests():
    """Generate and save digests"""
    print("📝 Generating digests...")
    
    try:
        results = digest_builder.build_all_digests()
        
        total_items = sum(digest.get('count', 0) for digest in results.values())
        
        if total_items > 0:
            print(f"✅ Generated digests with {total_items} total items!")
            print(f"📁 Check the 'output' folder for your digest files")
        else:
            print("⚠️  No approved items found. Try evaluating more content first.")
            print("💡 Suggestion: Run 'python -m src.cli.main evaluate 20' to evaluate more items")
    
    except Exception as e:
        print(f"❌ Error generating digests: {e}")
        import traceback
        traceback.print_exc()

def test_telegram():
    """Test Telegram delivery"""
    print("📱 Testing Telegram delivery...")
    
    if not telegram_delivery.is_configured():
        print("❌ Telegram delivery not configured")
        print("💡 Update your .env file with TELEGRAM_ENABLED=true and valid credentials")
        return
    
    test_message = "🤖 *AI Digest System Test*\n\nThis is a test message from your AI Digest System. If you're seeing this, Telegram delivery is working correctly!"
    
    success = telegram_delivery.send_message(test_message)
    
    if success:
        print("✅ Test message sent successfully!")
        print("📱 Check your Telegram for the test message")
    else:
        print("❌ Failed to send test message")
        print("💡 Check your credentials and internet connection")


def main():
    """Main CLI entry point"""
    print("🚀 AI-Powered Intelligence Digest System")
    print("=" * 50)
    
    if len(sys.argv) < 2:
        print("Usage: python -m src.cli.main <command> [options]")
        print("Commands:")
        print("  test     - Test system setup")
        print("  fetch    - Fetch content from sources")
        print("  evaluate [N] [--force] - Evaluate content")
        print("  digest   - Generate digest files")
        print("  status   - Show database status")
        print("  clear    - Clear all data from database")
        print("  telegram - Test Telegram delivery")
        print("  run      - Full pipeline (fetch + evaluate + digest)")
        return
    
    command = sys.argv[1]
    
    # Add this case


    
    if command == "test":
        if test_setup():
            print("🎉 All tests passed!")
        else:
            print("💥 Setup issues detected")
    
    elif command == "fetch":
        fetch_content()
    elif command == "telegram":
        test_telegram()
    
    elif command == "evaluate":
        # Parse arguments
        limit = None
        force = False
        
        for arg in sys.argv[2:]:
            if arg == "--force":
                force = True
            else:
                try:
                    limit = int(arg)
                except ValueError:
                    print(f"Invalid argument: {arg}")
                    return
        
        evaluate_content(limit, force)
    
    elif command == "digest":
        generate_digests()
    
    elif command == "status":
        show_status()
    
    elif command == "run":
        print("🔄 Running full pipeline...")
        if test_setup():
            fetch_content()
            evaluate_content(limit=30)
            generate_digests()
            print("✅ Complete pipeline finished!")
        else:
            print("❌ Setup test failed, aborting pipeline")
    
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()