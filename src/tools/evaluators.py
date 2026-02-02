from typing import Dict, Any
from src.models.schemas import IngestedItem, EvaluationResult, PersonaType
from src.services.llm_client import llm
import re

class GenAINewsEvaluator:
    """Evaluates content for GenAI News persona"""
    
    SYSTEM_PROMPT = """You are an expert AI researcher and engineer evaluating content for a technical newsletter.

TAGS TO USE (select 1-3 most relevant):
- "llm" - Large Language Models, GPT, Claude, etc.
- "computer-vision" - Image processing, object detection, etc.
- "ml-ops" - Model deployment, monitoring, infrastructure
- "research" - Academic papers, new techniques
- "tools" - Developer tools, frameworks, libraries
- "tutorial" - How-to guides, educational content
- "industry" - Company news, funding, acquisitions
- "open-source" - Open source projects and releases
- "hardware" - AI chips, GPUs, specialized hardware
- "ethics" - AI safety, bias, responsible AI

HIGH RELEVANCE (0.7-1.0): New models, technical tutorials, architecture papers, performance benchmarks, deployment guides, novel techniques
MEDIUM RELEVANCE (0.4-0.6): Industry news with technical implications, tool announcements, research summaries  
LOW RELEVANCE (0.0-0.3): General AI hype, non-technical discussions, basic introductions, opinion pieces

Be precise with scoring - avoid round numbers like 0.2, 0.6, 0.7. Use specific scores like 0.23, 0.67, 0.84.

IMPORTANT: You MUST always provide at least 1 tag. Never leave tags empty."""
    
    def evaluate(self, item: IngestedItem) -> EvaluationResult:
        """Evaluate an item for GenAI News relevance"""
        
        print(f"    🔍 Evaluating for GenAI News...")
        
        # Enhanced prompt with mandatory tags
        prompt = f"""Analyze this content for a technical GenAI/LLM newsletter:

TITLE: {item.title}
DESCRIPTION: {item.description[:400]}
SOURCE: {item.source_type.value}

ENGAGEMENT: {item.engagement_score or 'N/A'}

Evaluate based on:
1. Technical depth - Does it explain HOW things work?
2. Actionability - Can practitioners apply this knowledge?
3. Novelty - Is this new information or techniques?
4. Relevance - Is it specifically about AI/ML/LLM?

MANDATORY: Select 1-3 most relevant tags from: llm, computer-vision, ml-ops, research, tools, tutorial, industry, open-source, hardware, ethics

Provide a precise score (avoid 0.2, 0.6, 0.7 - be more specific like 0.34, 0.78, etc.)

CRITICAL: You MUST include at least one tag. Look at the title and description to determine the most appropriate category.

Examples:
- If about ChatGPT/GPT/Claude → use "llm"
- If about code/development → use "tools" 
- If about research papers → use "research"
- If about tutorials/guides → use "tutorial"
- If about company news → use "industry"

Respond with ONLY a valid JSON object:
{{"relevance_score": 0.XX, "topic": "specific topic", "why_it_matters": "detailed explanation", "target_audience": "developer/architect/manager/researcher", "decision": true/false, "reasoning": "detailed reasoning for the score", "tags": ["tag1", "tag2"]}}"""
        
        try:
            print(f"    📤 Sending to LLM...")
            result = llm.generate_json(prompt=prompt, system_prompt=self.SYSTEM_PROMPT)
            score = result["relevance_score"]
            
            # Convert score to stars
            star_rating = self._score_to_stars(score)
            
            # Ensure tags are provided - add fallback logic
            tags = result.get("tags", [])
            if not tags or len(tags) == 0:
                print(f"    ⚠️  No tags provided by LLM, assigning fallback tag...")
                tags = self._assign_fallback_tags(item)
            
            print(f"    📥 LLM response: score={score}, stars={star_rating}, tags={tags}, decision={result['decision']}")
            
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
                star_rating=star_rating,
                tags=tags,
                extracted_data={
                    "topic": result["topic"],
                    "why_it_matters": f'"{result["why_it_matters"]}"',  # Add quotes
                    "target_audience": result["target_audience"]
                }
            )
            
            return evaluation
            
        except Exception as e:
            print(f"    ❌ Evaluation failed: {str(e)}")
            fallback_tags = self._assign_fallback_tags(item)
            return EvaluationResult(
                item_id=item.id,
                persona=PersonaType.GENAI_NEWS,
                relevance_score=0.0,
                decision=False,
                reasoning=f"Evaluation failed: {str(e)}",
                star_rating="⭐",
                tags=fallback_tags,
                extracted_data={}
            )
    
    def _assign_fallback_tags(self, item: IngestedItem) -> list:
        """Assign fallback tags based on title and description keywords"""
        title_desc = (item.title + " " + (
item.description or "")).lower()
        
        # Keyword-based tag assignment
        if any(word in title_desc for word in ["gpt", "llm", "language model", "chatgpt", "claude", "gemini"]):
            return ["llm"]
        elif any(word in title_desc for word in ["vision", "image", "computer vision", "opencv", "detection"]):
            return ["computer-vision"]
        elif any(word in title_desc for word in ["deployment", "mlops", "kubernetes", "docker", "production"]):
            return ["ml-ops"]
        elif any(word in title_desc for word in ["research", "paper", "arxiv", "study", "experiment"]):
            return ["research"]
        elif any(word in title_desc for word in ["tool", "framework", "library", "api", "sdk"]):
            return ["tools"]
        elif any(word in title_desc for word in ["tutorial", "guide", "how to", "learn", "course"]):
            return ["tutorial"]
        elif any(word in title_desc for word in ["company", "startup", "funding", "acquisition", "business"]):
            return ["industry"]
        elif any(word in title_desc for word in ["open source", "github", "repository", "open-source"]):
            return ["open-source"]
        elif any(word in title_desc for word in ["gpu", "chip", "hardware", "nvidia", "amd"]):
            return ["hardware"]
        elif any(word in title_desc for word in ["ethics", "bias", "safety", "responsible", "fairness"]):
            return ["ethics"]
        else:
            # Default fallback based on source
            if item.source_type.value == "hackernews":
                return ["industry"]
            elif item.source_type.value == "reddit":
                return ["tools"]
            else:
                return ["research"]
    
    def _score_to_stars(self, score: float) -> str:
        """Convert numerical score to star rating"""
        if score >= 0.9:
            return "⭐⭐⭐⭐⭐"
        elif score >= 0.7:
            return "⭐⭐⭐⭐"
        elif score >= 0.5:
            return "⭐⭐⭐"
        elif score >= 0.3:
            return "⭐⭐"
        else:
            return "⭐"

class ProductIdeasEvaluator:
    """Evaluates content for Product Ideas persona"""
    
    SYSTEM_PROMPT = """You are a product strategist evaluating startup ideas and product launches.

TAGS TO USE (select 1-3 most relevant):
- "saas" - Software as a Service products
- "mobile-app" - Mobile applications
- "web-app" - Web applications and platforms
- "ai-tool" - AI-powered tools and services
- "productivity" - Productivity and workflow tools
- "developer-tool" - Tools for developers
- "startup" - New company launches
- "funding" - Investment and funding news
- "marketplace" - Platform and marketplace businesses
- "automation" - Process automation tools
- "analytics" - Data and analytics platforms
- "social" - Social media and community platforms

SCORING GUIDELINES (be precise, avoid round numbers):
- 0.85-1.0: Revolutionary products, major launches, breakthrough solutions
- 0.75-0.84: Strong product concepts, solid technical implementations
- 0.65-0.74: Interesting ideas, moderate innovation potential
- 0.55-0.64: Basic concepts, limited novelty but some merit
- 0.45-0.54: Weak ideas, minimal innovation
- 0.0-0.44: Not relevant, no product potential

Use specific decimals like 0.73, 0.81, 0.59 - avoid 0.60, 0.70, 0.80

IMPORTANT: You MUST always provide at least 1 tag. Never leave tags empty."""
    
    def evaluate(self, item: IngestedItem) -> EvaluationResult:
        """Evaluate an item for Product Ideas relevance"""
        
        print(f"    🔍 Evaluating for Product Ideas...")
        
        # Enhanced prompt with mandatory tags
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
5. Reusability - Can others learn
 from this?

MANDATORY: Select 1-3 most relevant tags from: saas, mobile-app, web-app, ai-tool, productivity, developer-tool, startup, funding, marketplace, automation, analytics, social

Provide a precise score between 0.0-1.0 (avoid round numbers like 0.6, 0.7).
Focus on actual product launches, MVPs, tools, or innovative business approaches.

CRITICAL: You MUST include at least one tag. Look at the title and description to determine the most appropriate category.

Examples:
- If about new software/platform → use "saas" or "web-app"
- If about mobile apps → use "mobile-app"
- If about AI products → use "ai-tool"
- If about developer tools → use "developer-tool"
- If about new companies → use "startup"
- If about investment → use "funding"

Respond with ONLY a valid JSON object:
{{"relevance_score": 0.XX, "topic": "specific topic", "why_it_matters": "detailed explanation", "target_audience": "entrepreneur/developer/investor", "decision": true/false, "reasoning": "detailed reasoning for the score", "tags": ["tag1", "tag2"]}}"""
        
        try:
            result = llm.generate_json(prompt=prompt, system_prompt=self.SYSTEM_PROMPT)
            
            # Validate score variety
            score = result["relevance_score"]
            star_rating = self._score_to_stars(score)
            
            # Ensure tags are provided - add fallback logic
            tags = result.get("tags", [])
            if not tags or len(tags) == 0:
                print(f"    ⚠️  No tags provided by LLM, assigning fallback tag...")
                tags = self._assign_fallback_tags(item)
            
            print(f"    📥 LLM response: score={score}, stars={star_rating}, tags={tags}, decision={result['decision']}")
            
            if score in [0.5, 0.6, 0.7, 0.8]:
                print(f"    ⚠️  Adjusting round score {score} to add variety")
                score += 0.03  # Add small variation
            
            return EvaluationResult(
                item_id=item.id,
                persona=PersonaType.PRODUCT_IDEAS,
                relevance_score=score,
                decision=result["decision"],
                reasoning=result["reasoning"],
                star_rating=star_rating,
                tags=tags,
                extracted_data={
                    "topic": result.get("topic", ""),
                    "why_it_matters": f'"{result.get("why_it_matters", "")}"',  # Add quotes
                    "target_audience": result.get("target_audience", ""),
                    "innovation_level": result.get("innovation_level", ""),
                    "market_potential": result.get("market_potential", "")
                }
            )
            
        except Exception as e:
            print(f"    ❌ Product evaluation failed: {str(e)}")
            fallback_tags = self._assign_fallback_tags(item)
            return EvaluationResult(
                item_id=item.id,
                persona=PersonaType.PRODUCT_IDEAS,
                relevance_score=0.0,
                decision=False,
                reasoning=f"Evaluation failed: {str(e)}",
                star_rating="⭐",
                tags=fallback_tags,
                extracted_data={}
            )
    
    def _assign_fallback_tags(self, item: IngestedItem) -> list:
        """Assign fallback tags based on title and description keywords"""
        title_desc = (item.title + " " + (item.description or "")).lower()
        
        # Keyword-based tag assignment for products
        if any(word in title_desc for word in ["saas", "software as a service", "subscription", "platform"]):
            return ["saas"]
        elif any(word in title_desc for word in ["mobile", "app", "ios", "android", "smartphone"]):
            return ["mobile-app"]
        elif any(word in title_desc for word in ["web app", "webapp", "website", "web platform"]):
            return ["web-app"]
        elif any(word in title_desc for word in ["ai tool", "ai-powered", "machine learning", "artificial intelligence"]):
            return ["ai-tool"]
        elif any(word in title_desc for word in ["productivity", "workflow", "efficiency", "organization"]):
            return ["productivity"]
        elif any(word in title_desc for word in ["developer", "coding", "programming", "api", "sdk"]):
            return ["developer-tool"]
        elif any(word in title_desc for word in ["startup", "new company", "founded", "launched"]):
            return ["startup"]
        elif any(word in title_desc for word in ["funding", "investment", "raised", "series", "venture"]):
            return ["funding"]
        elif any(word in title_desc for word in ["marketplace", "platform", "marketplace", "e-commerce"]):
            return ["marketplace"]
        elif any(word in title_desc for word in ["automation", "automate", "workflow", "process"]):
            return ["automation"]
        elif any(word in title_desc for word in ["analytics", "data", "metrics", "dashboard"]):
            return ["analytics"]
        elif any(word in title_desc for word in ["social", "community", "network", "social media"]):
            return ["social"]
        else:
            # Default fallback based on source
            if item.source_type.value == "hackernews":
                return ["startup"]
            elif item.source_type.value == "reddit":
                return ["developer-tool"]
            else:
                return ["saas"]
    
    def _score_to_stars(self, score: float) -> str:
        """Convert numerical score to star rating"""
        if score >= 0.9:
            return "⭐⭐⭐⭐⭐"
        elif score >= 0.7:
            return "⭐⭐⭐⭐"
        elif score >= 0.5:
            return "⭐⭐⭐"
        elif score >= 0.3:
            return "⭐⭐"
        else:
            return "⭐"
    
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