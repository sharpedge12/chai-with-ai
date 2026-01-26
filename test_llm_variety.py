import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.services.llm_client import llm

def test_scoring_variety():
    print("🔍 Testing LLM Scoring Variety")
    print("=" * 40)
    
    test_items = [
        {
            "title": "New GPT-5 Model Released with 10x Performance",
            "description": "OpenAI announces breakthrough architecture with detailed technical specifications and benchmarks",
            "expected": "High score (0.8+)"
        },
        {
            "title": "My Cat Learned to Use ChatGPT",
            "description": "Funny story about my pet using AI tools",
            "expected": "Low score (0.1-0.3)"
        },
        {
            "title": "Advanced Transformer Architecture for Code Generation",
            "description": "Research paper detailing novel attention mechanisms and implementation details for programming tasks",
            "expected": "High score (0.7+)"
        },
        {
            "title": "AI Stock Market Predictions",
            "description": "Generic article about AI in finance with no technical details",
            "expected": "Medium-low score (0.3-0.5)"
        },
        {
            "title": "Building Production LLM Systems with Kubernetes",
            "description": "Technical guide covering deployment, scaling, monitoring, and optimization of large language models in production environments",
            "expected": "High score (0.8+)"
        }
    ]
    
    for i, item in enumerate(test_items, 1):
        print(f"\n📝 Test {i}/5: {item['title'][:50]}...")
        print(f"Expected: {item['expected']}")
        
        prompt = f"""Evaluate this content for a GenAI/LLM technical newsletter:

Title: {item['title']}
Description: {item['description']}
Source: test

Is this relevant for AI/ML practitioners? Consider technical depth, actionability, and novelty.
Rate 0-1 where 0.6+ means include."""

        try:
            result = llm.generate_json(prompt=prompt, system_prompt="You are an AI expert evaluating tech content.")
            score = result.get('relevance_score', 0)
            decision = result.get('decision', False)
            reasoning = result.get('reasoning', 'No reasoning')
            
            print(f"📊 Score: {score} | Decision: {decision}")
            print(f"💭 Reasoning: {reasoning[:100]}...")
            
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_scoring_variety()