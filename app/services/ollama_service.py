import os
import json
import requests
import time
from typing import List, Dict, Any
from app.models.schemas import ParseJDResponse, AnalyzeAnswerResponse, Score
from app.utils.prompt_templates import PromptTemplates
from app.utils.response_parsers import ResponseParsers
from app.utils.logger import get_logger
from app.exceptions import ServiceUnavailableError

logger = get_logger(__name__)

class OllamaService:
    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "llama2")  # or "mistral", "codellama", etc.
        self.api_url = f"{self.base_url}/api/generate"
    
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
                response = requests.post(
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
        """Generate role-specific interview questions using Ollama."""
        
        prompt = PromptTemplates.get_question_generation_prompt(role, job_description)
        
        try:
            response = self._call_ollama(prompt, PromptTemplates.QUESTION_GENERATION_SYSTEM)
            questions = ResponseParsers.parse_questions_from_response(response)
            
            # Ensure we have some questions
            if not questions:
                questions = self._get_fallback_questions(role)
            
            return ParseJDResponse(questions=questions)
            
        except Exception as e:
            logger.error(f"Error generating questions with Ollama: {e}")
            return self._get_fallback_questions(role)
    
    def analyze_answer(self, job_description: str, question: str, answer: str) -> AnalyzeAnswerResponse:
        """Analyze candidate's answer using Ollama."""
        
        prompt = PromptTemplates.get_analysis_prompt(job_description, question, answer)
        
        try:
            response = self._call_ollama(prompt, PromptTemplates.ANALYSIS_SYSTEM)
            return ResponseParsers.parse_analysis_response(response)
                
        except Exception as e:
            logger.error(f"Error analyzing answer with Ollama: {e}")
            return self._get_fallback_analysis()
    
    def _get_fallback_questions(self, role: str) -> ParseJDResponse:
        """Fallback questions if Ollama fails."""
        return ParseJDResponse(questions=[
            f"Tell me about your experience with {role}",
            "Describe a challenging project you've worked on",
            "How do you handle tight deadlines?",
            "What's your approach to problem-solving?",
            "How do you stay updated with industry trends?",
            "Tell me about a time you had to learn a new technology quickly",
            "How do you handle conflicting priorities?",
            "What's your experience with code review?",
            "How do you ensure code quality?",
            "Describe a situation where you had to mentor junior developers"
        ])
    
    def _get_fallback_analysis(self) -> AnalyzeAnswerResponse:
        """Fallback analysis if Ollama fails."""
        return AnalyzeAnswerResponse(
            score=Score(clarity=5, confidence=5),
            missingKeywords=["specific examples", "metrics", "technical details"],
            improvements=[
                "Provide more specific examples",
                "Include quantifiable results",
                "Add more technical details",
                "Demonstrate problem-solving approach"
            ],
            idealAnswer="Please provide a more detailed answer with specific examples, measurable outcomes, and technical depth."
        )
    
    def list_available_models(self) -> List[str]:
        """List available Ollama models."""
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            return [model["name"] for model in data.get("models", [])]
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return []
    
    def pull_model(self, model_name: str) -> bool:
        """Pull a model to Ollama."""
        try:
            response = requests.post(f"{self.base_url}/api/pull", json={"name": model_name})
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Error pulling model {model_name}: {e}")
            return False 