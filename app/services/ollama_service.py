import os
import json
import requests
import time
from typing import List, Dict, Any
from app.models.schemas import ParseJDResponse, AnalyzeAnswerResponse, Score
from app.utils.prompt_templates import PromptTemplates
from app.utils.response_parser import ResponseParser
from app.utils.fallback_responses import FallbackResponses
from app.utils.http_pool import http_pool
from app.utils.logger import get_logger
from app.exceptions import ServiceUnavailableError
from app.services.smart_token_optimizer import SmartTokenOptimizer

logger = get_logger(__name__)

class OllamaService:
    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "llama2")  # or "mistral", "codellama", etc.
        self.api_url = f"{self.base_url}/api/generate"
        self.session = http_pool.get_session()
        self.token_optimizer = SmartTokenOptimizer()
    
    def _call_ollama(self, prompt: str, system_prompt: str = None, max_retries: int = 3) -> str:
        """Make a call to Ollama API with retry logic."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": float(os.getenv("OLLAMA_TEMPERATURE", "0.7")),
                "top_p": float(os.getenv("OLLAMA_TOP_P", "0.9")),
                "max_tokens": int(os.getenv("OLLAMA_MAX_TOKENS", "2000"))
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        for attempt in range(max_retries):
            try:
                response = self.session.post(
                    self.api_url, 
                    json=payload, 
                    timeout=int(os.getenv("OLLAMA_TIMEOUT", "60"))
                )
                response.raise_for_status()
                result = response.json()
                return result.get("response", "").strip()
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    logger.error(f"Error calling Ollama after {max_retries} attempts: {e}")
                    raise ServiceUnavailableError(f"Failed to communicate with Ollama after {max_retries} attempts: {str(e)}")
                logger.info(f"Attempt {attempt + 1} failed, retrying in {2 ** attempt} seconds...")
                time.sleep(2 ** attempt)  # Exponential backoff
    
    def _call_ollama_with_tokens(self, prompt: str, system_prompt: str = None, max_tokens: int = 2000, max_retries: int = 3) -> str:
        """Make a call to Ollama API with optimized token count."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": float(os.getenv("OLLAMA_TEMPERATURE", "0.7")),
                "top_p": float(os.getenv("OLLAMA_TOP_P", "0.9")),
                "num_predict": max_tokens  # Use optimized token count
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        for attempt in range(max_retries):
            try:
                response = self.session.post(
                    self.api_url, 
                    json=payload, 
                    timeout=int(os.getenv("OLLAMA_TIMEOUT", "60"))
                )
                response.raise_for_status()
                result = response.json()
                return result.get("response", "").strip()
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    logger.error(f"Error calling Ollama after {max_retries} attempts: {e}")
                    raise ServiceUnavailableError(f"Failed to communicate with Ollama after {max_retries} attempts: {str(e)}")
                logger.info(f"Attempt {attempt + 1} failed, retrying in {2 ** attempt} seconds...")
                time.sleep(2 ** attempt)  # Exponential backoff
    
    def generate_interview_questions(self, role: str, job_description: str) -> ParseJDResponse:
        """Generate role-specific interview questions using Ollama with token optimization."""
        
        # Optimize token usage
        optimization_result = self.token_optimizer.optimize_request(
            role=role,
            job_description=job_description,
            service="ollama",
            target_questions=10
        )
        
        prompt = PromptTemplates.get_question_generation_prompt(role, job_description)
        
        try:
            # Use optimized token count in the call
            response = self._call_ollama_with_tokens(
                prompt, 
                PromptTemplates.QUESTION_GENERATION_SYSTEM,
                optimization_result.optimal_tokens
            )
            parser = ResponseParser()
            questions = parser.parse_questions(response)
            
            # Ensure we have some questions
            if not questions:
                return FallbackResponses.get_fallback_questions(role)
            
            return ParseJDResponse(questions=questions)
            
        except Exception as e:
            logger.error(f"Error generating questions with Ollama: {e}")
            return FallbackResponses.get_fallback_questions(role)
    
    def analyze_answer(self, job_description: str, question: str, answer: str) -> AnalyzeAnswerResponse:
        """Analyze candidate's answer using Ollama."""
        
        prompt = PromptTemplates.get_analysis_prompt(job_description, question, answer)
        
        try:
            response = self._call_ollama(prompt, PromptTemplates.ANALYSIS_SYSTEM)
            parser = ResponseParser()
            return parser.parse_analysis(response)
                
        except Exception as e:
            logger.error(f"Error analyzing answer with Ollama: {e}")
            return FallbackResponses.get_fallback_analysis()
    
    
    def list_available_models(self) -> List[str]:
        """List available Ollama models."""
        try:
            response = self.session.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            return [model["name"] for model in data.get("models", [])]
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return []
    
    def pull_model(self, model_name: str) -> bool:
        """Pull a model to Ollama."""
        try:
            response = self.session.post(f"{self.base_url}/api/pull", json={"name": model_name})
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Error pulling model {model_name}: {e}")
            return False 