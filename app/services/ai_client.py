"""
AI Service Client for Backend Integration
This file should be copied to the main backend service for integration
"""

import asyncio
from app.utils.logger import get_logger
from typing import Dict, Any, Optional, List
import httpx
import os
from datetime import datetime

logger = get_logger(__name__)


class AIServiceClient:
    """
    Client for communicating with the AI Service microservice
    """
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv("AI_SERVICE_URL", "http://localhost:8001")
        self.timeout = float(os.getenv("AI_SERVICE_TIMEOUT", "30.0"))
        self.retry_attempts = int(os.getenv("AI_SERVICE_RETRY_ATTEMPTS", "3"))
        
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
    
    async def score_interview(
        self,
        transcript: str,
        session_id: str,
        user_id: Optional[str] = None,
        video_analysis: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Score an interview using AI service
        
        Args:
            transcript: Interview transcript
            session_id: Session identifier
            user_id: Optional user identifier
            video_analysis: Optional video analysis data
            
        Returns:
            Dict containing scoring results
        """
        try:
            logger.info(f"Scoring interview for session: {session_id}")
            
            payload = {
                "transcript": transcript,
                "session_id": session_id,
                "user_id": user_id,
                "video_analysis": video_analysis
            }
            
            response = await self.client.post(
                f"{self.base_url}/score",
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Interview scored successfully for session: {session_id}")
                return result
            else:
                logger.error(f"Scoring failed: {response.status_code}")
                raise Exception(f"Scoring failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Failed to score interview: {e}")
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
                raise Exception(f"Transcription failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Failed to transcribe audio: {e}")
            raise
    
    async def analyze_video(
        self,
        video_file_path: str,
        session_id: str,
        analysis_type: str = "full"
    ) -> Dict[str, Any]:
        """
        Analyze video for body language using AI service
        
        Args:
            video_file_path: Path to video file
            session_id: Session identifier
            analysis_type: Type of analysis
            
        Returns:
            Dict containing analysis results
        """
        try:
            logger.info(f"Analyzing video for session: {session_id}")
            
            with open(video_file_path, 'rb') as f:
                files = {'video_file': f}
                data = {
                    'session_id': session_id,
                    'analysis_type': analysis_type
                }
                
                response = await self.client.post(
                    f"{self.base_url}/analyze",
                    files=files,
                    data=data
                )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Video analyzed successfully for session: {session_id}")
                return result
            else:
                logger.error(f"Video analysis failed: {response.status_code}")
                raise Exception(f"Video analysis failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Failed to analyze video: {e}")
            raise
    
    async def quick_score(
        self,
        transcript: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Get quick score without detailed breakdown
        
        Args:
            transcript: Interview transcript
            session_id: Session identifier
            
        Returns:
            Dict containing quick score
        """
        try:
            logger.info(f"Getting quick score for session: {session_id}")
            
            payload = {
                "transcript": transcript,
                "session_id": session_id
            }
            
            response = await self.client.post(
                f"{self.base_url}/score/quick",
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Quick score obtained for session: {session_id}")
                return result
            else:
                logger.error(f"Quick scoring failed: {response.status_code}")
                raise Exception(f"Quick scoring failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Failed to get quick score: {e}")
            raise
    
    async def analyze_eye_contact(
        self,
        video_file_path: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Analyze eye contact in video
        
        Args:
            video_file_path: Path to video file
            session_id: Session identifier
            
        Returns:
            Dict containing eye contact analysis
        """
        try:
            logger.info(f"Analyzing eye contact for session: {session_id}")
            
            with open(video_file_path, 'rb') as f:
                files = {'video_file': f}
                data = {'session_id': session_id}
                
                response = await self.client.post(
                    f"{self.base_url}/analyze/eye-contact",
                    files=files,
                    data=data
                )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Eye contact analyzed for session: {session_id}")
                return result
            else:
                logger.error(f"Eye contact analysis failed: {response.status_code}")
                raise Exception(f"Eye contact analysis failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Failed to analyze eye contact: {e}")
            raise
    
    async def analyze_posture(
        self,
        video_file_path: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Analyze posture in video
        
        Args:
            video_file_path: Path to video file
            session_id: Session identifier
            
        Returns:
            Dict containing posture analysis
        """
        try:
            logger.info(f"Analyzing posture for session: {session_id}")
            
            with open(video_file_path, 'rb') as f:
                files = {'video_file': f}
                data = {'session_id': session_id}
                
                response = await self.client.post(
                    f"{self.base_url}/analyze/posture",
                    files=files,
                    data=data
                )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Posture analyzed for session: {session_id}")
                return result
            else:
                logger.error(f"Posture analysis failed: {response.status_code}")
                raise Exception(f"Posture analysis failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Failed to analyze posture: {e}")
            raise
    
    async def get_scoring_rubric(self) -> Dict[str, Any]:
        """
        Get the current scoring rubric
        
        Returns:
            Dict containing scoring rubric information
        """
        try:
            response = await self.client.get(f"{self.base_url}/score/rubric")
            
            if response.status_code == 200:
                result = response.json()
                logger.info("Scoring rubric retrieved successfully")
                return result
            else:
                logger.error(f"Failed to get scoring rubric: {response.status_code}")
                raise Exception(f"Failed to get scoring rubric: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Failed to get scoring rubric: {e}")
            raise
    
    async def get_analysis_capabilities(self) -> Dict[str, Any]:
        """
        Get available analysis capabilities
        
        Returns:
            Dict containing analysis capabilities
        """
        try:
            response = await self.client.get(f"{self.base_url}/analyze/capabilities")
            
            if response.status_code == 200:
                result = response.json()
                logger.info("Analysis capabilities retrieved successfully")
                return result
            else:
                logger.error(f"Failed to get analysis capabilities: {response.status_code}")
                raise Exception(f"Failed to get analysis capabilities: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Failed to get analysis capabilities: {e}")
            raise
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
        logger.info("AI Service client closed")
    
    def __del__(self):
        """Cleanup on deletion"""
        if hasattr(self, 'client'):
            asyncio.create_task(self.close())


# Convenience functions for easy integration
async def score_interview(
    transcript: str,
    session_id: str,
    user_id: Optional[str] = None,
    video_analysis: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Convenience function to score an interview
    
    Args:
        transcript: Interview transcript
        session_id: Session identifier
        user_id: Optional user identifier
        video_analysis: Optional video analysis data
        
    Returns:
        Dict containing scoring results
    """
    client = AIServiceClient()
    try:
        return await client.score_interview(transcript, session_id, user_id, video_analysis)
    finally:
        await client.close()


async def transcribe_audio(
    audio_file_path: str,
    session_id: str,
    language: str = "en"
) -> Dict[str, Any]:
    """
    Convenience function to transcribe audio
    
    Args:
        audio_file_path: Path to audio file
        session_id: Session identifier
        language: Language code
        
    Returns:
        Dict containing transcription results
    """
    client = AIServiceClient()
    try:
        return await client.transcribe_audio(audio_file_path, session_id, language)
    finally:
        await client.close()


async def analyze_video(
    video_file_path: str,
    session_id: str,
    analysis_type: str = "full"
) -> Dict[str, Any]:
    """
    Convenience function to analyze video
    
    Args:
        video_file_path: Path to video file
        session_id: Session identifier
        analysis_type: Type of analysis
        
    Returns:
        Dict containing analysis results
    """
    client = AIServiceClient()
    try:
        return await client.analyze_video(video_file_path, session_id, analysis_type)
    finally:
        await client.close()
