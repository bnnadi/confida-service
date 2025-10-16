"""
Content Analysis Agent

This agent specializes in analyzing the content relevance, completeness, and structure
of interview answers.
"""
import re
from typing import Dict, Any, List
from app.models.scoring_models import ContentAnalysis
from app.utils.prompt_templates import PromptTemplates
from app.services.unified_ai_service import UnifiedAIService
from app.services.agents.base_agent import BaseAgent
from app.utils.logger import get_logger

logger = get_logger(__name__)

class ContentAnalysisAgent(BaseAgent):
    """Agent for analyzing content relevance and completeness."""
    
    def __init__(self):
        super().__init__("Content Analysis Agent")
        self.ai_service = UnifiedAIService()
    
    async def analyze(
        self, 
        response: str, 
        question: str, 
        job_description: str, 
        role: str = ""
    ) -> ContentAnalysis:
        """
        Analyze content relevance, completeness, and structure.
        
        Args:
            response: The candidate's answer
            question: The interview question
            job_description: Job description for context
            role: Job role for specialized analysis
            
        Returns:
            ContentAnalysis with detailed content evaluation
        """
        try:
            logger.info(f"Content agent analyzing response for role: {role}")
            
            # Generate content analysis prompt
            prompt = self._create_content_analysis_prompt(response, question, job_description, role)
            
            # Get AI analysis
            ai_response = await self.ai_service.analyze_answer(
                job_description=job_description,
                answer=response,
                question=question,
                role=role
            )
            
            # Parse AI response
            analysis_data = self._parse_ai_response(ai_response)
            
            # Calculate content score
            score = self._calculate_content_score(response, question, analysis_data)
            
            # Generate feedback
            feedback = self._generate_content_feedback(analysis_data, score)
            
            # Create recommendations
            recommendations = self._generate_recommendations(analysis_data, score)
            
            return ContentAnalysis(
                score=score,
                feedback=feedback,
                confidence=analysis_data.get("confidence", 0.8),
                details=analysis_data,
                recommendations=recommendations,
                content_metrics={
                    "relevance_score": analysis_data.get("relevance_score", 0),
                    "completeness_score": analysis_data.get("completeness_score", 0),
                    "structure_score": analysis_data.get("structure_score", 0),
                    "keyword_coverage": analysis_data.get("keyword_coverage", 0),
                    "example_quality": analysis_data.get("example_quality", 0)
                }
            )
            
        except Exception as e:
            logger.error(f"Error in content analysis: {e}")
            return self._create_fallback_analysis(response, question)
    
    def _create_content_analysis_prompt(
        self, 
        response: str, 
        question: str, 
        job_description: str, 
        role: str
    ) -> str:
        """Create specialized prompt for content analysis."""
        return f"""
        Analyze the content quality of this interview answer for a {role} position.

        Question: {question}
        Job Description: {job_description}
        Candidate's Answer: {response}

        Evaluate the following aspects and provide scores (1-10) and detailed feedback:

        1. RELEVANCE: How well does the answer address the specific question asked?
        2. COMPLETENESS: Does the answer cover all important aspects of the question?
        3. STRUCTURE: Is the answer well-organized and easy to follow?
        4. KEYWORD COVERAGE: Does the answer include relevant technical terms and concepts?
        5. EXAMPLE QUALITY: Are the examples specific, relevant, and well-explained?

        Provide your analysis in this JSON format:
        {{
            "relevance_score": <score 1-10>,
            "completeness_score": <score 1-10>,
            "structure_score": <score 1-10>,
            "keyword_coverage": <score 1-10>,
            "example_quality": <score 1-10>,
            "confidence": <confidence 0.0-1.0>,
            "strengths": ["strength1", "strength2"],
            "weaknesses": ["weakness1", "weakness2"],
            "missing_elements": ["element1", "element2"],
            "improvement_suggestions": ["suggestion1", "suggestion2"]
        }}
        """
    
    def _get_content_system_prompt(self) -> str:
        """Get system prompt for content analysis."""
        return """
        You are a content analysis expert specializing in evaluating interview answers.
        Focus on content relevance, completeness, structure, and quality of examples.
        Be objective, constructive, and provide actionable feedback.
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
            "relevance_score": 7,
            "completeness_score": 7,
            "structure_score": 7,
            "keyword_coverage": 7,
            "example_quality": 7,
            "confidence": 0.6,
            "strengths": ["Answer provided"],
            "weaknesses": ["Analysis parsing failed"],
            "missing_elements": [],
            "improvement_suggestions": ["Provide more detailed analysis"]
        }
    
    def _calculate_content_score(self, response: str, question: str, analysis_data: Dict[str, Any]) -> float:
        """Calculate overall content score."""
        # Weighted average of content metrics
        weights = {
            "relevance_score": 0.3,
            "completeness_score": 0.25,
            "structure_score": 0.2,
            "keyword_coverage": 0.15,
            "example_quality": 0.1
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
    
    def _generate_content_feedback(self, analysis_data: Dict[str, Any], score: float) -> str:
        """Generate comprehensive content feedback."""
        feedback_parts = []
        
        # Overall assessment
        if score >= 8.0:
            feedback_parts.append("Excellent content quality with strong relevance and completeness.")
        elif score >= 6.0:
            feedback_parts.append("Good content quality with room for improvement in some areas.")
        else:
            feedback_parts.append("Content needs significant improvement in relevance and structure.")
        
        # Specific strengths
        strengths = analysis_data.get("strengths", [])
        if strengths:
            feedback_parts.append(f"Strengths: {', '.join(strengths[:3])}")
        
        # Key weaknesses
        weaknesses = analysis_data.get("weaknesses", [])
        if weaknesses:
            feedback_parts.append(f"Areas to improve: {', '.join(weaknesses[:2])}")
        
        return " ".join(feedback_parts)
    
    def _generate_recommendations(self, analysis_data: Dict[str, Any], score: float) -> List[str]:
        """Generate specific recommendations for improvement."""
        recommendations = []
        
        # Add AI-generated suggestions
        suggestions = analysis_data.get("improvement_suggestions", [])
        recommendations.extend(suggestions[:3])
        
        # Add score-based recommendations
        if score < 6.0:
            recommendations.append("Focus on directly addressing the question asked")
            recommendations.append("Provide more specific examples and details")
        elif score < 8.0:
            recommendations.append("Enhance the structure and organization of your answer")
            recommendations.append("Include more relevant technical terms and concepts")
        
        return recommendations[:5]  # Limit to top 5 recommendations
    
    def _create_fallback_analysis(self, response: str, question: str) -> ContentAnalysis:
        """Create fallback analysis when content analysis fails."""
        # Simple heuristic-based analysis
        response_length = len(response)
        question_length = len(question)
        
        # Basic scoring based on response length and structure
        length_score = min(10, max(1, response_length / 50))
        structure_score = 7 if response_length > 100 else 5
        
        overall_score = (length_score + structure_score) / 2
        
        return ContentAnalysis(
            score=round(overall_score, 2),
            feedback="Basic content analysis - detailed analysis temporarily unavailable",
            confidence=0.5,
            details={"fallback": True, "response_length": response_length},
            recommendations=["Detailed content analysis temporarily unavailable"],
            content_metrics={
                "relevance_score": overall_score,
                "completeness_score": overall_score,
                "structure_score": structure_score,
                "keyword_coverage": overall_score,
                "example_quality": overall_score
            }
        )
    
    async def _run_health_test(self):
        """Run content agent specific health test."""
        return await self.analyze(
            response="This is a test response",
            question="Test question",
            job_description="Test job description",
            role="test"
        )
