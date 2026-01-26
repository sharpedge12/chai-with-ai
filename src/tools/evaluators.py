from typing import Dict, Any
from src.models.schemas import IngestedItem, EvaluationResult, PersonaType
from src.services.llm_client import llm
import re

class GenAINewsEvaluator:
    """Evaluates content for GenAI News persona"""
    
    SYSTEM_PROMPT = """You are an expert AI researcher and engineer evaluating content for a technical newsletter.

HIGH RELEVANCE (0.7-1.0): New models, technical tutorials, architecture papers, performance benchmarks, deployment guides, novel techniques
MEDIUM RELEVANCE (0.4-0.6): Industry news with technical implications, tool announcements, research summaries  
LOW RELEVANCE (0.0-0.3): General AI hype, non-technical discussions, basic introductions, opinion pieces

Be precise with scoring - avoid round numbers like 0.2, 0.6, 0.7. Use specific scores like 0.23, 0.67, 0.84."""
    
    def evaluate(self, item: IngestedItem) -> EvaluationResult:
        """Evaluate an item for GenAI News relevance"""
        
        print(f"    🔍 Evaluating for GenAI News...")
        
        # More detailed prompt with content analysis
        prompt = f"""Analyze this content for a technical
 GenAI/LLM newsletter:

TITLE: {item.title}
DESCRIPTION: {item.description[:400]}
SOURCE: {item.source_type.value}
ENGAGEMENT: {item.engagement_score or 'N/A'}

Evaluate based on:
1. Technical depth - Does it explain HOW things work?
2. Actionability - Can practitioners apply this knowledge?
3. Novelty - Is this new information or techniques?
4. Relevance - Is it specifically about AI/ML/LLM?

Provide a precise score (avoid 0.2, 0.6, 0.7 - be more specific like 0.34, 0.78, etc.)"""
        
        try:
            print(f"    📤 Sending to LLM...")
            result = llm.generate_json(prompt=prompt, system_prompt=self.SYSTEM_PROMPT)
            score = result["relevance_score"]
            print(f"    📥 LLM response: score={score}, decision={result['decision']}")
            
            # Validate score is not a common repeated value
            common_scores = [0.2, 0.6, 0.7]
            if score in common_scores:
                print(f"    ⚠️  Warning: Common score detected ({score})")
            
            evaluation = EvaluationResult(
                item_id=item.id,
                persona=PersonaType.GENAI_NEWS,
                relevance_score=score,
                decision=result["decision"],
                reasoning=result["reasoning"],
                extracted_data={
                    "topic": result["topic"],
                    "why_it_matters": result["why_it_matters"],
                    "target_audience": result["target_audience"]
                }
            )
            
            return evaluation
            
        except Exception as e:
            print(f"    ❌ Evaluation failed: {str(e)}")
            return EvaluationResult(
                item_id=item.id,
                persona=PersonaType.GENAI_NEWS,
                relevance_score=0.0,
                decision=False,
                reasoning=f"Evaluation failed: {str(e)}",
                extracted_data={}
            )
        
class ProductIdeasEvaluator:
    """Evaluates content for Product Ideas persona"""
    
    SYSTEM_PROMPT = """You are a product strategist evaluating startup ideas and product launches.

SCORING GUIDELINES (be precise, avoid round numbers):
- 0.85-1.0: Revolutionary products, major launches, breakthrough solutions
- 0.75-0.84: Strong product concepts, solid technical implementations
- 0.65-0.74: Interesting ideas, moderate innovation potential
- 0.55-0.64: Basic concepts, limited novelty but some merit
- 0.45-0.54: Weak ideas, minimal innovation
- 0.0-0.44: Not relevant, no product potential

Use specific decimals like 0.73, 0.81, 0.59 - avoid 0.60, 0.70, 0.80"""
    
    def evaluate(self, item: IngestedItem) -> EvaluationResult:
        """Evaluate an item for Product Ideas relevance"""
        
        print(f"    🔍 Evaluating for Product Ideas...")
        
        # Enhanced prompt with better content analysis
        prompt = f"""Analyze this content for a product ideas newsletter:

TITLE: {item.title}
DESCRIPTION: {self._clean_description(item.description)}
SOURCE: {item.source_type.value}
ENGAGEMENT: {item.engagement_score or 'N/A'}

Evaluate based on:
1. Innovation Level - How novel is the approach?
2. Market Potential - Could this scale or inspire others?
3. Problem-Solution Fit - Does it solve a real problem?
4. Implementation Quality - How well executed is it?
5. Reusability - Can others learn from this?

Provide a precise score between 0.0-1.0 (avoid round numbers like 0.6, 0.7).
Focus on actual product launches, MVPs, tools, or innovative business approaches."""
        
        try:
            result = llm.generate_json(prompt=prompt, system_prompt=self.SYSTEM_PROMPT)
            
            # Validate score variety
            score = result["relevance_score"]
            if score in [0.5, 0.6, 0.7, 0.8]:
                print(f"    ⚠️  Adjusting round score {score} to add variety")
                score += 0.03  # Add small variation
            
            return EvaluationResult(
                item_id=item.id,
                persona=PersonaType.PRODUCT_IDEAS,
                relevance_score=score,
                decision=result["decision"],
                reasoning=result["reasoning"],
                extracted_data={
                    "topic": result.get("topic", ""),
                    "why_it_matters": result.get("why_it_matters", ""),
                    "target_audience": result.get("target_audience", ""),
                    "innovation_level": result.get("innovation_level", ""),
                    "market_potential": result.get("market_potential", "")
                }
            )
            
        except Exception as e:
            print(f"    ❌ Product evaluation failed: {str(e)}")
            return EvaluationResult(
                item_id=item.id,
                persona=PersonaType.PRODUCT_IDEAS,
                relevance_score=0.0,
                decision=False,
                reasoning=f"Evaluation failed: {str(e)}",
                extracted_data={}
            )
    
    def _clean_description(self, description: str) -> str:
        """Clean description for better LLM analysis"""
        if not description:
            return "No description available"
        
        # Remove Reddit/markdown formatting
        cleaned = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', description)
        cleaned = re.sub(r'\*\*([^*]+)\*\*', r'\1', cleaned)
        cleaned = re.sub(r'\\', '', cleaned)
        
        return cleaned[:400]  # Limit for LLM context
# Global evaluator instances
genai_evaluator = GenAINewsEvaluator()
product_evaluator = ProductIdeasEvaluator()