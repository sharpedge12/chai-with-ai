import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.services.database import db

def check_content_quality():
    print("🔍 Analyzing Your Actual Content Quality")
    print("=" * 50)
    
    recent_items = db.get_recent_items(hours=24)
    
    print(f"📊 Total items: {len(recent_items)}")
    print("\n📋 Sample of your actual content:")
    
    for i, item in enumerate(recent_items[:10], 1):
        print(f"\n{i}. {item.title}")
        print(f"   Description: {item.description[:150]}...")
        print(f"   Source: {item.source_type.value}")
        print(f"   Engagement: {item.engagement_score}")
        
        # Predict what this should score
        title_lower = item.title.lower()
        desc_lower = item.description.lower() if item.description else ""
        
        technical_keywords = ['model', 'architecture', 'training', 'api', 'framework', 'algorithm', 'neural', 'transformer', 'deployment', 'benchmark']
        ai_keywords = ['ai', 'ml', 'llm', 'gpt', 'neural', 'machine learning', 'artificial intelligence']
        
        has_technical = any(keyword in title_lower + desc_lower for keyword in technical_keywords)
        has_ai = any(keyword in title_lower + desc_lower for keyword in ai_keywords)
        
        predicted_score = "High (0.7+)" if has_technical and has_ai else "Medium (0.4-0.6)" if has_ai else "Low (0.1-0.3)"
        print(f"   Predicted: {predicted_score}")

if __name__ == "__main__":
    check_content_quality()