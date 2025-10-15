"""
Delivery Analysis Agent

This agent specializes in analyzing communication style, clarity, confidence,
and delivery aspects of interview answers.
"""
import re
from typing import Dict, Any, List
from app.models.scoring_models import DeliveryAnalysis
from app.utils.prompt_templates import PromptTemplates
from app.services.ai_service import AIService
from app.services.agents.base_agent import BaseAgent
from app.utils.logger import get_logger

logger = get_logger(__name__)

class DeliveryAnalysisAgent(BaseAgent):
    """Agent for analyzing communication and delivery quality."""
    
    def __init__(self):
        super().__init__("Delivery Analysis Agent")
        self.ai_service = AIService()
    
    async def analyze(
        self, 
        response: str, 
        question: str, 
        job_description: str
    ) -> DeliveryAnalysis:
        """
        Analyze communication style, clarity, and delivery.
        
        Args:
            response: The candidate's answer
            question: The interview question
            job_description: Job description for context
            
        Returns:
            DeliveryAnalysis with detailed delivery evaluation
        """
        try:
            logger.info("Delivery agent analyzing communication and delivery")
            
            # Generate delivery analysis prompt
            prompt = self._create_delivery_analysis_prompt(response, question, job_description)
            
            # Get AI analysis
            ai_response = await self.ai_service.analyze_with_ai(
                prompt=prompt,
                system_prompt=self._get_delivery_system_prompt()
            )
            
            # Parse AI response
            analysis_data = self._parse_ai_response(ai_response)
            
            # Calculate delivery score
            score = self._calculate_delivery_score(response, analysis_data)
            
            # Generate feedback
            feedback = self._generate_delivery_feedback(analysis_data, score)
            
            # Create recommendations
            recommendations = self._generate_recommendations(analysis_data, score)
            
            return DeliveryAnalysis(
                score=score,
                feedback=feedback,
                confidence=analysis_data.get("confidence", 0.8),
                details=analysis_data,
                recommendations=recommendations,
                delivery_metrics={
                    "clarity_score": analysis_data.get("clarity_score", 0),
                    "confidence_score": analysis_data.get("confidence_score", 0),
                    "structure_score": analysis_data.get("structure_score", 0),
                    "conciseness_score": analysis_data.get("conciseness_score", 0),
                    "professional_tone_score": analysis_data.get("professional_tone_score", 0)
                }
            )
            
        except Exception as e:
            logger.error(f"Error in delivery analysis: {e}")
            return self._create_fallback_analysis(response, question)
    
    def _create_delivery_analysis_prompt(
        self, 
        response: str, 
        question: str, 
        job_description: str
    ) -> str:
        """Create specialized prompt for delivery analysis."""
        return f"""
        Analyze the communication and delivery quality of this interview answer.

        Question: {question}
        Job Description: {job_description}
        Candidate's Answer: {response}

        Evaluate the following delivery aspects and provide scores (1-10) and detailed feedback:

        1. CLARITY: Is the answer clear, well-articulated, and easy to understand?
        2. CONFIDENCE: Does the candidate sound confident and assured in their response?
        3. STRUCTURE: Is the answer well-organized with logical flow and transitions?
        4. CONCISENESS: Is the answer appropriately detailed without being too verbose or too brief?
        5. PROFESSIONAL TONE: Does the answer maintain a professional and appropriate tone?

        Provide your analysis in this JSON format:
        {{
            "clarity_score": <score 1-10>,
            "confidence_score": <score 1-10>,
            "structure_score": <score 1-10>,
            "conciseness_score": <score 1-10>,
            "professional_tone_score": <score 1-10>,
            "confidence": <confidence 0.0-1.0>,
            "communication_strengths": ["strength1", "strength2"],
            "communication_weaknesses": ["weakness1", "weakness2"],
            "tone_analysis": "professional/casual/uncertain/etc",
            "improvement_suggestions": ["suggestion1", "suggestion2"]
        }}
        """
    
    def _get_delivery_system_prompt(self) -> str:
        """Get system prompt for delivery analysis."""
        return """
        You are a communication analysis expert specializing in evaluating interview answer delivery.
        Focus on clarity, confidence, structure, conciseness, and professional tone.
        Be objective and provide constructive feedback for improvement.
        """
    
    def _parse_ai_response(self, ai_response: str) -> Dict[str, Any]:
        """Parse AI response into structured data."""
        try:
            import json
            # Try to extract JSON from the response
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                # Fallback parsing
                return self._fallback_parse(ai_response)
        except Exception as e:
            logger.warning(f"Failed to parse AI response: {e}")
            return self._fallback_parse(ai_response)
    
    def _fallback_parse(self, response: str) -> Dict[str, Any]:
        """Fallback parsing when JSON parsing fails."""
        return {
            "clarity_score": 7,
            "confidence_score": 7,
            "structure_score": 7,
            "conciseness_score": 7,
            "professional_tone_score": 7,
            "confidence": 0.6,
            "communication_strengths": ["Response provided"],
            "communication_weaknesses": ["Analysis parsing failed"],
            "tone_analysis": "neutral",
            "improvement_suggestions": ["Provide more detailed analysis"]
        }
    
    def _calculate_delivery_score(self, response: str, analysis_data: Dict[str, Any]) -> float:
        """Calculate overall delivery score."""
        # Weighted average of delivery metrics
        weights = {
            "clarity_score": 0.3,
            "confidence_score": 0.25,
            "structure_score": 0.2,
            "conciseness_score": 0.15,
            "professional_tone_score": 0.1
        }
        
        total_score = 0
        total_weight = 0
        
        for metric, weight in weights.items():
            if metric in analysis_data:
                total_score += analysis_data[metric] * weight
                total_weight += weight
        
        # Normalize to 0-10 scale
        if total_weight > 0:
            return round(total_score / total_weight, 2)
        else:
            return 7.0  # Default score
    
    def _generate_delivery_feedback(self, analysis_data: Dict[str, Any], score: float) -> str:
        """Generate comprehensive delivery feedback."""
        feedback_parts = []
        
        # Overall assessment
        if score >= 8.0:
            feedback_parts.append("Excellent communication with clear, confident delivery.")
        elif score >= 6.0:
            feedback_parts.append("Good communication with some areas for improvement.")
        else:
            feedback_parts.append("Communication needs improvement in clarity and confidence.")
        
        # Communication strengths
        strengths = analysis_data.get("communication_strengths", [])
        if strengths:
            feedback_parts.append(f"Communication strengths: {', '.join(strengths[:2])}")
        
        # Key weaknesses
        weaknesses = analysis_data.get("communication_weaknesses", [])
        if weaknesses:
            feedback_parts.append(f"Areas to improve: {', '.join(weaknesses[:2])}")
        
        # Tone analysis
        tone = analysis_data.get("tone_analysis", "neutral")
        if tone != "professional":
            feedback_parts.append(f"Consider adjusting tone to be more {tone}")
        
        return " ".join(feedback_parts)
    
    def _generate_recommendations(self, analysis_data: Dict[str, Any], score: float) -> List[str]:
        """Generate specific recommendations for delivery improvement."""
        recommendations = []
        
        # Add AI-generated suggestions
        suggestions = analysis_data.get("improvement_suggestions", [])
        recommendations.extend(suggestions[:3])
        
        # Add score-based recommendations
        if score < 6.0:
            recommendations.append("Practice speaking more clearly and confidently")
            recommendations.append("Structure your answers with clear beginning, middle, and end")
        elif score < 8.0:
            recommendations.append("Work on being more concise while maintaining detail")
            recommendations.append("Practice maintaining professional tone throughout")
        
        # Specific metric-based recommendations
        if analysis_data.get("clarity_score", 0) < 6:
            recommendations.append("Focus on clear, simple language and avoid jargon")
        if analysis_data.get("confidence_score", 0) < 6:
            recommendations.append("Practice confident delivery and avoid hedging language")
        if analysis_data.get("structure_score", 0) < 6:
            recommendations.append("Use clear transitions and logical flow in your answers")
        
        return recommendations[:5]  # Limit to top 5 recommendations
    
    def _create_fallback_analysis(self, response: str, question: str) -> DeliveryAnalysis:
        """Create fallback analysis when delivery analysis fails."""
        # Simple heuristic-based analysis
        response_length = len(response)
        
        # Basic scoring based on response characteristics
        length_score = min(10, max(1, response_length / 50))
        structure_score = 7 if response_length > 100 else 5
        
        # Check for basic structure indicators
        has_sentences = len(response.split('.')) > 1
        has_paragraphs = len(response.split('\n')) > 1
        
        structure_bonus = 1 if has_sentences else 0
        structure_bonus += 1 if has_paragraphs else 0
        
        overall_score = (length_score + structure_score + structure_bonus) / 3
        
        return DeliveryAnalysis(
            score=round(overall_score, 2),
            feedback="Basic delivery analysis - detailed analysis temporarily unavailable",
            confidence=0.5,
            details={"fallback": True, "response_length": response_length},
            recommendations=["Detailed delivery analysis temporarily unavailable"],
            delivery_metrics={
                "clarity_score": overall_score,
                "confidence_score": overall_score,
                "structure_score": structure_score + structure_bonus,
                "conciseness_score": overall_score,
                "professional_tone_score": overall_score
            }
        )
    
    async def _run_health_test(self):
        """Run delivery agent specific health test."""
        return await self.analyze(
            response="This is a test response for delivery analysis",
            question="Test question",
            job_description="Test job description"
        )
