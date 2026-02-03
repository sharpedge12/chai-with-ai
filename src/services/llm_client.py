import json
import requests
from typing import Dict, Any, Optional
from src.services.config import config

class OllamaClient:
    """Client for local Ollama LLM API using requests"""
    
    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = base_url or config.OLLAMA_BASE_URL
        self.model = model or config.OLLAMA_MODEL
        
        # Remove /v1 from base_url if present for direct Ollama API
        if self.base_url.endswith('/v1'):
            self.base_url = self.base_url[:-3]
    
    def set_model(self, model_name: str = None, use_fast: bool = True):
        """Set the model to use - either by name or by speed preference"""
        if model_name:
            self.model = model_name
            print(f"🔄 Switched to model: {self.model}")
        else:
            if use_fast:
                self.model = config.OLLAMA_MODEL_FAST
                print(f"🔄 Using fast model: {self.model}")
            else:
                self.model = config.OLLAMA_MODEL_SLOW
                print(f"🔄 Using slow but powerful model: {self.model}")
    
    def generate(self, prompt: str, system_prompt: str = None, temperature: float = 0.1, timeout: int = 120) -> str:
        """Generate text using Ollama API directly"""
        
        # Combine system and user prompts
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\nUser: {prompt}\nAssistant:"
        
        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": 500  # Limit response length
            }
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=timeout  # Use configurable timeout
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "")
            
        except requests.RequestException as e:
            raise Exception(f"LLM request failed: {e}")
        except KeyError as e:
            raise Exception(f"Unexpected LLM response format: {e}")
    
    def generate_json(self, prompt: str, system_prompt: str = None, schema: Dict[str, Any] = None, timeout: int = 120) -> Dict[str, Any]:
        """Generate structured JSON response with configurable timeout"""
        
        # More detailed prompt with scoring guidance
        json_prompt = f"""{prompt}

    Provide a detailed evaluation with a precise relevance score between 0.0 and 1.0:

    Scoring Guidelines:
    - 0.0-0.2: Completely irrelevant, no technical
 value
    - 0.3-0.4: Somewhat related but lacks depth or actionability  
    - 0.5-0.6: Moderately relevant, some technical content
    - 0.7-0.8: Highly relevant, good technical depth
    - 0.9-1.0: Exceptional content, cutting-edge and highly actionable

    Be precise with your scoring - use decimals like 0.35, 0.67, 0.83, etc.

    Respond with ONLY a valid JSON object:
    {{"relevance_score": 0.XX, "topic": "specific topic", "why_it_matters": "detailed explanation", "target_audience": "developer/architect/manager/researcher", "decision": true/false, "reasoning": "detailed reasoning for the score"}}"""
        
        response_text = self.generate(json_prompt, system_prompt, temperature=0.3, timeout=timeout)
        
        # Clean up the response
        response_text = response_text.strip()
        
        # Try to extract JSON from response
        try:
            # Look for JSON object in the response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx != -1 and end_idx != 0:
                json_str = response_text[start_idx:end_idx]
                
                # Parse JSON
                result = json.loads(json_str)
                
                # Validate required fields
                required_fields = ["relevance_score", "topic", "why_it_matters", "target_audience", "decision", "reasoning"]
                for field in required_fields:
                    if field not in result:
                        raise ValueError(f"Missing required field: {field}")
                
                # Ensure correct types
                result["relevance_score"] = float(result["relevance_score"])
                result["decision"] = bool(result["decision"])
                
                return result
            else:
                raise ValueError("No JSON object found in response")
                
        except (json.JSONDecodeError, ValueError) as e:
            raise Exception(f"Failed to parse JSON response: {e}\nResponse: {response_text}")
    
    def test_connection(self) -> bool:
        """Test if Ollama is running and model is available"""
        try:
            response = self.generate("Hello, respond with just 'OK'", temperature=0.1, timeout=30)
            return "OK" in response or len(response) > 0
        except Exception as e:
            print(f"LLM connection test failed: {e}")
            return False
    
    def list_available_models(self) -> list:
        """List all available models in Ollama"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            response.raise_for_status()
            
            result = response.json()
            models = [model['name'] for model in result.get('models', [])]
            return models
        except Exception as e:
            print(f"Failed to list models: {e}")
            return []

# Global LLM client
llm = OllamaClient()