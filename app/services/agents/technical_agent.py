"""
Technical Analysis Agent

This agent specializes in analyzing technical accuracy, domain knowledge,
and technical depth of interview answers.
"""
import re
from typing import Dict, Any, List
from app.models.scoring_models import TechnicalAnalysis
from app.utils.prompt_templates import PromptTemplates
from app.services.ai_service import UnifiedAIService
from app.services.agents.base_agent import BaseAgent
from app.utils.logger import get_logger

logger = get_logger(__name__)

class TechnicalAnalysisAgent(BaseAgent):
    """Agent for analyzing technical accuracy and domain knowledge."""
    
    def __init__(self):
        super().__init__("Technical Analysis Agent")
        self.ai_service = UnifiedAIService()
    
    async def analyze(
        self, 
        response: str, 
        question: str, 
        job_description: str, 
        role: str = ""
    ) -> TechnicalAnalysis:
        """
        Analyze technical accuracy, domain knowledge, and technical depth.
        
        Args:
            response: The candidate's answer
            question: The interview question
            job_description: Job description for context
            role: Job role for specialized analysis
            
        Returns:
            TechnicalAnalysis with detailed technical evaluation
        """
        try:
            logger.info(f"Technical agent analyzing response for role: {role}")
            
            # Generate technical analysis prompt
            prompt = self._create_technical_analysis_prompt(response, question, job_description, role)
            
            # Get AI analysis
            ai_response = await self.ai_service.analyze_answer(
                job_description=job_description,
                answer=response,
                question=question,
                role=role
            )
            
            # Parse AI response
            analysis_data = self._parse_ai_response(ai_response)
            
            # Calculate technical score
            score = self._calculate_technical_score(response, analysis_data)
            
            # Generate feedback
            feedback = self._generate_technical_feedback(analysis_data, score)
            
            # Create recommendations
            recommendations = self._generate_recommendations(analysis_data, score)
            
            return TechnicalAnalysis(
                score=score,
                feedback=feedback,
                confidence=analysis_data.get("confidence", 0.8),
                details=analysis_data,
                recommendations=recommendations,
                technical_metrics={
                    "accuracy_score": analysis_data.get("accuracy_score", 0),
                    "depth_score": analysis_data.get("depth_score", 0),
                    "relevance_score": analysis_data.get("relevance_score", 0),
                    "terminology_score": analysis_data.get("terminology_score", 0),
                    "problem_solving_score": analysis_data.get("problem_solving_score", 0)
                }
            )
            
        except Exception as e:
            logger.error(f"Error in technical analysis: {e}")
            return self._create_fallback_analysis(response, question, role)
    
    def _create_technical_analysis_prompt(
        self, 
        response: str, 
        question: str, 
        job_description: str, 
        role: str
    ) -> str:
        """Create specialized prompt for technical analysis."""
        return f"""
        Analyze the technical accuracy and domain knowledge of this interview answer for a {role} position.

        Question: {question}
        Job Description: {job_description}
        Candidate's Answer: {response}

        Evaluate the following technical aspects and provide scores (1-10) and detailed feedback:

        1. ACCURACY: Are the technical concepts, facts, and information correct?
        2. DEPTH: Does the answer demonstrate deep understanding of the technical concepts?
        3. RELEVANCE: Are the technical details relevant to the question and role?
        4. TERMINOLOGY: Is appropriate technical terminology used correctly?
        5. PROBLEM-SOLVING: Does the answer demonstrate good technical problem-solving approach?

        Provide your analysis in this JSON format:
        {{
            "accuracy_score": <score 1-10>,
            "depth_score": <score 1-10>,
            "relevance_score": <score 1-10>,
            "terminology_score": <score 1-10>,
            "problem_solving_score": <score 1-10>,
            "confidence": <confidence 0.0-1.0>,
            "technical_strengths": ["strength1", "strength2"],
            "technical_weaknesses": ["weakness1", "weakness2"],
            "incorrect_concepts": ["concept1", "concept2"],
            "missing_concepts": ["concept1", "concept2"],
            "improvement_suggestions": ["suggestion1", "suggestion2"]
        }}
        """
    
    def _get_technical_system_prompt(self) -> str:
        """Get system prompt for technical analysis."""
        return """
        You are a technical analysis expert specializing in evaluating interview answers for technical accuracy.
        Focus on technical correctness, depth of knowledge, relevance, terminology, and problem-solving approach.
        Be objective and provide constructive feedback for technical improvement.
        """
    
    def _fallback_parse(self, response: str) -> Dict[str, Any]:
        """Technical-specific fallback parsing when JSON parsing fails."""
        return {
            "accuracy_score": 7,
            "depth_score": 7,
            "relevance_score": 7,
            "terminology_score": 7,
            "problem_solving_score": 7,
            "confidence": 0.6,
            "technical_strengths": ["Response provided"],
            "technical_weaknesses": ["Analysis parsing failed"],
            "incorrect_concepts": [],
            "missing_concepts": [],
            "improvement_suggestions": ["Provide more detailed analysis"]
        }
    
    def _calculate_technical_score(self, response: str, analysis_data: Dict[str, Any]) -> float:
        """Calculate overall technical score."""
        # Weighted average of technical metrics
        weights = {
            "accuracy_score": 0.3,
            "depth_score": 0.25,
            "relevance_score": 0.2,
            "terminology_score": 0.15,
            "problem_solving_score": 0.1
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
    
    def _generate_technical_feedback(self, analysis_data: Dict[str, Any], score: float) -> str:
        """Generate comprehensive technical feedback."""
        feedback_parts = []
        
        # Overall assessment
        if score >= 8.0:
            feedback_parts.append("Excellent technical knowledge with accurate and deep understanding.")
        elif score >= 6.0:
            feedback_parts.append("Good technical knowledge with some areas for improvement.")
        else:
            feedback_parts.append("Technical knowledge needs improvement in accuracy and depth.")
        
        # Technical strengths
        strengths = analysis_data.get("technical_strengths", [])
        if strengths:
            feedback_parts.append(f"Technical strengths: {', '.join(strengths[:2])}")
        
        # Key weaknesses
        weaknesses = analysis_data.get("technical_weaknesses", [])
        if weaknesses:
            feedback_parts.append(f"Areas to improve: {', '.join(weaknesses[:2])}")
        
        # Incorrect concepts
        incorrect = analysis_data.get("incorrect_concepts", [])
        if incorrect:
            feedback_parts.append(f"Review these concepts: {', '.join(incorrect[:2])}")
        
        # Missing concepts
        missing = analysis_data.get("missing_concepts", [])
        if missing:
            feedback_parts.append(f"Consider including: {', '.join(missing[:2])}")
        
        return " ".join(feedback_parts)
    
    def _generate_recommendations(self, analysis_data: Dict[str, Any], score: float) -> List[str]:
        """Generate specific recommendations for technical improvement."""
        recommendations = []
        
        # Add AI-generated suggestions
        suggestions = analysis_data.get("improvement_suggestions", [])
        recommendations.extend(suggestions[:3])
        
        # Add score-based recommendations
        if score < 6.0:
            recommendations.append("Review fundamental concepts and terminology")
            recommendations.append("Practice explaining technical concepts clearly")
        elif score < 8.0:
            recommendations.append("Deepen understanding of advanced concepts")
            recommendations.append("Practice technical problem-solving approaches")
        
        # Specific metric-based recommendations
        if analysis_data.get("accuracy_score", 0) < 6:
            recommendations.append("Verify technical facts and concepts before answering")
        if analysis_data.get("depth_score", 0) < 6:
            recommendations.append("Provide more detailed technical explanations")
        if analysis_data.get("terminology_score", 0) < 6:
            recommendations.append("Use appropriate technical terminology correctly")
        if analysis_data.get("problem_solving_score", 0) < 6:
            recommendations.append("Structure technical problem-solving with clear steps")
        
        return recommendations[:5]  # Limit to top 5 recommendations
    
    def _create_fallback_analysis(self, response: str, question: str, role: str) -> TechnicalAnalysis:
        """Create fallback analysis when technical analysis fails."""
        # Simple heuristic-based analysis
        response_length = len(response)
        
        # Basic scoring based on response characteristics
        length_score = min(10, max(1, response_length / 50))
        
        # Check for technical indicators
        technical_terms = self._count_technical_terms(response, role)
        technical_score = min(10, max(1, technical_terms * 2))
        
        overall_score = (length_score + technical_score) / 2
        
        return TechnicalAnalysis(
            score=round(overall_score, 2),
            feedback="Basic technical analysis - detailed analysis temporarily unavailable",
            confidence=0.5,
            details={"fallback": True, "response_length": response_length, "technical_terms": technical_terms},
            recommendations=["Detailed technical analysis temporarily unavailable"],
            technical_metrics={
                "accuracy_score": overall_score,
                "depth_score": overall_score,
                "relevance_score": overall_score,
                "terminology_score": technical_score,
                "problem_solving_score": overall_score
            }
        )
    
    def _count_technical_terms(self, response: str, role: str) -> int:
        """Count technical terms in the response based on role."""
        response_lower = response.lower()
        
        # Common technical terms by role
        technical_terms = {
            "software_engineer": ["algorithm", "data structure", "api", "database", "framework", "library", "code", "function", "class", "method"],
            "data_scientist": ["machine learning", "model", "algorithm", "data", "analysis", "statistics", "python", "r", "pandas", "numpy"],
            "product_manager": ["user story", "requirement", "feature", "roadmap", "stakeholder", "metrics", "kpi", "agile", "sprint", "backlog"],
            "default": ["technical", "system", "process", "method", "approach", "solution", "implementation", "architecture", "design", "development"]
        }
        
        terms_to_check = technical_terms.get(role.lower(), technical_terms["default"])
        count = sum(1 for term in terms_to_check if term in response_lower)
        
        return count
    
    async def _run_health_test(self):
        """Run technical agent specific health test."""
        return await self.analyze(
            response="This is a test technical response",
            question="Test technical question",
            job_description="Test job description",
            role="software_engineer"
        )
