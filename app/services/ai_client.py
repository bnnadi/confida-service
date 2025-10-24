"""
Pure AI Service Client for Backend Integration

This is a simple HTTP client that communicates with the AI service microservice.
No fallback logic - if AI service is unavailable, it returns proper errors.
"""

from app.utils.logger import get_logger
from app.config import get_settings
from typing import Dict, Any, Optional
import httpx

logger = get_logger(__name__)
settings = get_settings()


class AIServiceUnavailableError(Exception):
    """Raised when AI service microservice is unavailable"""
    pass


class AIServiceClient:
    """
    Pure HTTP client for AI Service microservice.
    
    This client only makes HTTP calls to the AI service microservice.
    No fallback logic - proper separation of concerns.
    """
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or settings.AI_SERVICE_URL
        self.timeout = settings.AI_SERVICE_TIMEOUT
        self.retry_attempts = settings.AI_SERVICE_RETRY_ATTEMPTS
        
        # HTTP client
        self.client = httpx.AsyncClient(timeout=self.timeout)
        
        logger.info(f"AI Service client initialized: {self.base_url}")
    
    async def health_check(self) -> bool:
        """
        Check if AI service is healthy
        
        Returns:
            bool: True if healthy, False otherwise
        """
        try:
            response = await self.client.get(f"{self.base_url}/health")
            if response.status_code == 200:
                logger.info("AI Service is healthy")
                return True
            else:
                logger.warning(f"AI Service health check failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"AI Service health check error: {e}")
            return False
    
    async def generate_questions(
        self,
        role: str,
        job_description: str,
        count: int = 10,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate interview questions using AI service
        
        Args:
            role: Job role/title
            job_description: Job description text
            count: Number of questions to generate
            user_context: Optional user context for personalization
            
        Returns:
            Dict containing generated questions
        """
        try:
            logger.info(f"Generating {count} questions for role: {role}")
            
            payload = {
                "role": role,
                "job_description": job_description,
                "count": count,
                "user_context": user_context or {}
            }
            
            response = await self.client.post(
                f"{self.base_url}/questions/generate",
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Questions generated successfully for role: {role}")
                return result
            else:
                logger.error(f"Question generation failed: {response.status_code}")
                raise AIServiceUnavailableError(f"Question generation failed: {response.status_code}")
                
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to AI service: {e}")
            raise AIServiceUnavailableError(f"AI service unavailable: {e}")
        except Exception as e:
            logger.error(f"Failed to generate questions: {e}")
            raise
    
    async def analyze_answer(
        self,
        job_description: str,
        question: str,
        answer: str,
        role: str = ""
    ) -> Dict[str, Any]:
        """
        Analyze interview answer using AI service
        
        Args:
            job_description: Job description for context
            question: The interview question
            answer: Candidate's answer
            role: Job role for context
            
        Returns:
            Dict containing analysis results
        """
        try:
            logger.info(f"Analyzing answer for role: {role}")
            
            payload = {
                "job_description": job_description,
                "question": question,
                "answer": answer,
                "role": role
            }
            
            response = await self.client.post(
                f"{self.base_url}/analyze/answer",
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Answer analyzed successfully for role: {role}")
                return result
            else:
                logger.error(f"Answer analysis failed: {response.status_code}")
                raise AIServiceUnavailableError(f"Answer analysis failed: {response.status_code}")
                
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to AI service: {e}")
            raise AIServiceUnavailableError(f"AI service unavailable: {e}")
        except Exception as e:
            logger.error(f"Failed to analyze answer: {e}")
            raise
    
    async def transcribe_audio(
        self,
        audio_file_path: str,
        session_id: str,
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Transcribe audio file using AI service
        
        Args:
            audio_file_path: Path to audio file
            session_id: Session identifier
            language: Language code
            
        Returns:
            Dict containing transcription results
        """
        try:
            logger.info(f"Transcribing audio for session: {session_id}")
            
            with open(audio_file_path, 'rb') as f:
                files = {'audio_file': f}
                data = {
                    'session_id': session_id,
                    'language': language
                }
                
                response = await self.client.post(
                    f"{self.base_url}/transcribe",
                    files=files,
                    data=data
                )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Audio transcribed successfully for session: {session_id}")
                return result
            else:
                logger.error(f"Transcription failed: {response.status_code}")
                raise AIServiceUnavailableError(f"Transcription failed: {response.status_code}")
                
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to AI service: {e}")
            raise AIServiceUnavailableError(f"AI service unavailable: {e}")
        except Exception as e:
            logger.error(f"Failed to transcribe audio: {e}")
            raise
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
        logger.info("AI Service client closed")