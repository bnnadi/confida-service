"""
Integration tests for scoring conversion logic.

Tests the conversion between legacy and enhanced scoring formats.
"""
import pytest
from unittest.mock import AsyncMock, patch
from app.routers.scoring import _convert_to_multi_agent_analysis
from app.utils.scoring_utils import (
    create_enhanced_rubric_from_legacy_scores,
    parse_enhanced_rubric_from_ai_response
)


class TestScoreConversion:
    """Tests for score conversion in analysis conversion."""
    
    @pytest.mark.integration
    def test_convert_legacy_scores_to_100_point(self):
        """Test converting legacy 0-10 scores to 100-point scale."""
        result = {
            "score": {
                "clarity": 8.0,
                "confidence": 7.5
            },
            "analysis": "Test analysis",
            "suggestions": ["Suggestion 1", "Suggestion 2"]
        }
        
        analysis = _convert_to_multi_agent_analysis(result)
        
        # Verify scores are on 0-100 scale
        assert 0.0 <= analysis.content_agent.score <= 100.0
        assert 0.0 <= analysis.delivery_agent.score <= 100.0
        assert 0.0 <= analysis.technical_agent.score <= 100.0
        assert 0.0 <= analysis.overall_score <= 100.0
        
        # Verify conversion: 8.0 * 10 = 80.0
        assert analysis.content_agent.score == 80.0
        # Verify conversion: 7.5 * 10 = 75.0
        assert analysis.delivery_agent.score == 75.0
    
    @pytest.mark.integration
    def test_convert_with_enhanced_rubric(self):
        """Test conversion when AI service returns enhanced rubric."""
        result = {
            "score": {
                "clarity": 8.0,
                "confidence": 7.5
            },
            "analysis": "Test analysis",
            "suggestions": [],
            "enhanced_rubric": {
                "verbal_communication": {
                    "articulation": {"score": 4.0, "feedback": "Clear", "examples": []},
                    "content_relevance": {"score": 4.5, "feedback": "Relevant", "examples": []},
                    "structure": {"score": 3.5, "feedback": "Organized", "examples": []},
                    "vocabulary": {"score": 4.0, "feedback": "Good", "examples": []},
                    "delivery_confidence": {"score": 4.5, "feedback": "Confident", "examples": []},
                    "category_score": 20.5,
                    "category_feedback": "Strong verbal communication"
                },
                "interview_readiness": {
                    "preparedness": {"score": 4.0, "feedback": "Prepared", "examples": []},
                    "example_quality": {"score": 3.5, "feedback": "Good examples", "examples": []},
                    "problem_solving": {"score": 4.0, "feedback": "Strong", "examples": []},
                    "responsiveness": {"score": 3.5, "feedback": "Responsive", "examples": []},
                    "category_score": 15.0,
                    "category_feedback": "Well prepared"
                },
                "non_verbal_communication": {
                    "eye_contact": {"score": 3.0, "feedback": "Good", "examples": []},
                    "body_language": {"score": 3.0, "feedback": "Positive", "examples": []},
                    "vocal_variety": {"score": 3.5, "feedback": "Varied", "examples": []},
                    "pacing": {"score": 3.0, "feedback": "Appropriate", "examples": []},
                    "engagement": {"score": 3.5, "feedback": "Engaged", "examples": []},
                    "category_score": 16.0,
                    "category_feedback": "Good non-verbal cues"
                },
                "adaptability_engagement": {
                    "adaptability": {"score": 3.5, "feedback": "Adaptable", "examples": []},
                    "enthusiasm": {"score": 4.0, "feedback": "Enthusiastic", "examples": []},
                    "active_listening": {"score": 3.5, "feedback": "Attentive", "examples": []},
                    "category_score": 11.0,
                    "category_feedback": "Engaged and adaptable"
                },
                "overall_feedback": "Strong overall performance",
                "top_strengths": ["Clear communication"],
                "improvement_areas": ["Could improve pacing"]
            }
        }
        
        analysis = _convert_to_multi_agent_analysis(result)
        
        # Verify enhanced rubric is present
        assert analysis.enhanced_rubric is not None
        assert analysis.enhanced_rubric.total_score > 0
        assert analysis.enhanced_rubric.total_score <= 100.0
        assert analysis.grade_tier is not None
    
    @pytest.mark.integration
    def test_convert_without_enhanced_rubric_fallback(self):
        """Test conversion falls back to legacy scores when enhanced rubric not present."""
        result = {
            "score": {
                "clarity": 6.0,
                "confidence": 7.0
            },
            "analysis": "Test analysis",
            "suggestions": ["Suggestion 1"]
        }
        
        analysis = _convert_to_multi_agent_analysis(result)
        
        # Should create enhanced rubric from legacy scores
        assert analysis.enhanced_rubric is not None
        assert analysis.enhanced_rubric.total_score > 0
        assert analysis.grade_tier is not None
        
        # Verify all categories are present
        assert analysis.enhanced_rubric.verbal_communication is not None
        assert analysis.enhanced_rubric.interview_readiness is not None
        assert analysis.enhanced_rubric.non_verbal_communication is not None
        assert analysis.enhanced_rubric.adaptability_engagement is not None
    
    @pytest.mark.integration
    def test_convert_zero_scores(self):
        """Test conversion with zero scores."""
        result = {
            "score": {
                "clarity": 0.0,
                "confidence": 0.0
            },
            "analysis": "Poor answer",
            "suggestions": []
        }
        
        analysis = _convert_to_multi_agent_analysis(result)
        
        assert analysis.overall_score >= 0.0
        assert analysis.grade_tier.value == "At Risk"  # Should be At Risk for low scores


class TestLegacyToEnhancedConversion:
    """Tests for converting legacy scores to enhanced rubric."""
    
    @pytest.mark.integration
    def test_create_rubric_from_high_scores(self):
        """Test creating rubric from high legacy scores."""
        rubric = create_enhanced_rubric_from_legacy_scores(
            clarity=9.0,
            confidence=8.5,
            analysis="Excellent answer",
            suggestions=["Keep it up"]
        )
        
        assert rubric.total_score > 70.0  # Should be high
        assert rubric.grade_tier.value in ["Excellent", "Strong"]
        assert rubric.verbal_communication.category_score > 0
        assert rubric.interview_readiness.category_score > 0
    
    @pytest.mark.integration
    def test_create_rubric_from_low_scores(self):
        """Test creating rubric from low legacy scores."""
        rubric = create_enhanced_rubric_from_legacy_scores(
            clarity=3.0,
            confidence=2.5,
            analysis="Needs improvement",
            suggestions=["Work on clarity", "Improve confidence"]
        )
        
        assert rubric.total_score < 50.0  # Should be low
        assert rubric.grade_tier.value in ["Average", "At Risk"]
    
    @pytest.mark.integration
    def test_create_rubric_category_limits(self):
        """Test that category scores respect their limits."""
        rubric = create_enhanced_rubric_from_legacy_scores(
            clarity=10.0,
            confidence=10.0,
            analysis="Perfect",
            suggestions=[]
        )
        
        # Verify category score limits
        assert rubric.verbal_communication.category_score <= 40.0
        assert rubric.interview_readiness.category_score <= 20.0
        assert rubric.non_verbal_communication.category_score <= 25.0
        assert rubric.adaptability_engagement.category_score <= 15.0
        
        # Total should be sum of categories
        expected_total = (
            rubric.verbal_communication.category_score +
            rubric.interview_readiness.category_score +
            rubric.non_verbal_communication.category_score +
            rubric.adaptability_engagement.category_score
        )
        assert abs(rubric.total_score - expected_total) < 0.1


class TestEnhancedRubricParsing:
    """Tests for parsing enhanced rubric from AI response."""
    
    @pytest.mark.integration
    def test_parse_rubric_from_response(self):
        """Test parsing enhanced rubric from AI service response."""
        response = {
            "enhanced_rubric": {
                "verbal_communication": {
                    "articulation": {"score": 4.0, "feedback": "Clear", "examples": []},
                    "content_relevance": {"score": 4.0, "feedback": "Relevant", "examples": []},
                    "structure": {"score": 4.0, "feedback": "Organized", "examples": []},
                    "vocabulary": {"score": 4.0, "feedback": "Good", "examples": []},
                    "delivery_confidence": {"score": 4.0, "feedback": "Confident", "examples": []},
                    "category_score": 20.0,
                    "category_feedback": "Strong"
                },
                "interview_readiness": {
                    "preparedness": {"score": 3.0, "feedback": "Prepared", "examples": []},
                    "example_quality": {"score": 3.0, "feedback": "Good", "examples": []},
                    "problem_solving": {"score": 3.0, "feedback": "Strong", "examples": []},
                    "responsiveness": {"score": 3.0, "feedback": "Responsive", "examples": []},
                    "category_score": 12.0,
                    "category_feedback": "Well prepared"
                },
                "non_verbal_communication": {
                    "eye_contact": {"score": 3.0, "feedback": "Good", "examples": []},
                    "body_language": {"score": 3.0, "feedback": "Positive", "examples": []},
                    "vocal_variety": {"score": 3.0, "feedback": "Varied", "examples": []},
                    "pacing": {"score": 3.0, "feedback": "Appropriate", "examples": []},
                    "engagement": {"score": 3.0, "feedback": "Engaged", "examples": []},
                    "category_score": 15.0,
                    "category_feedback": "Good"
                },
                "adaptability_engagement": {
                    "adaptability": {"score": 3.0, "feedback": "Adaptable", "examples": []},
                    "enthusiasm": {"score": 3.0, "feedback": "Enthusiastic", "examples": []},
                    "active_listening": {"score": 3.0, "feedback": "Attentive", "examples": []},
                    "category_score": 9.0,
                    "category_feedback": "Engaged"
                },
                "overall_feedback": "Overall assessment",
                "top_strengths": ["Strength 1"],
                "improvement_areas": ["Area 1"]
            }
        }
        
        rubric = parse_enhanced_rubric_from_ai_response(response)
        
        assert rubric is not None
        assert rubric.total_score == 56.0  # 20 + 12 + 15 + 9
        assert rubric.grade_tier.value == "Average"
        assert len(rubric.top_strengths) == 1
        assert len(rubric.improvement_areas) == 1
    
    @pytest.mark.integration
    def test_parse_rubric_missing_data(self):
        """Test parsing when some data is missing."""
        response = {
            "enhanced_rubric": {
                "verbal_communication": {
                    # Missing some fields - should use defaults
                    "articulation": {"score": 4.0},
                    "category_score": 20.0,
                    "category_feedback": "Test"
                }
            }
        }
        
        # Should handle gracefully - may return None if data is incomplete
        rubric = parse_enhanced_rubric_from_ai_response(response)
        # May return None if required fields are missing
        assert rubric is None or hasattr(rubric, 'total_score')

