"""
Unit tests for scoring models.

Tests the Pydantic models for the 100-point scoring rubric system.
"""
import pytest
from datetime import datetime
from app.models.scoring_models import (
    GradeTier,
    SubDimensionScore,
    VerbalCommunicationScores,
    InterviewReadinessScores,
    NonVerbalCommunicationScores,
    AdaptabilityEngagementScores,
    EnhancedScoringRubric,
    AgentScore,
    MultiAgentAnalysis,
    ScoringWeights
)


class TestGradeTier:
    """Tests for GradeTier enum."""
    
    @pytest.mark.unit
    def test_grade_tier_values(self):
        """Test that grade tier has correct string values."""
        assert GradeTier.EXCELLENT.value == "Excellent"
        assert GradeTier.STRONG.value == "Strong"
        assert GradeTier.AVERAGE.value == "Average"
        assert GradeTier.AT_RISK.value == "At Risk"


class TestSubDimensionScore:
    """Tests for SubDimensionScore model."""
    
    @pytest.mark.unit
    def test_create_sub_dimension_score_valid(self):
        """Test creating valid sub-dimension score."""
        score = SubDimensionScore(
            score=4.0,
            feedback="Good performance",
            examples=["example1", "example2"]
        )
        assert score.score == 4.0
        assert score.feedback == "Good performance"
        assert score.examples == ["example1", "example2"]
    
    @pytest.mark.unit
    def test_sub_dimension_score_validation(self):
        """Test that score validation works correctly."""
        # Valid range
        score = SubDimensionScore(score=3.0, feedback="test")
        assert 1.0 <= score.score <= 5.0
        
        # Should raise validation error for out of range
        with pytest.raises(Exception):  # Pydantic validation error
            SubDimensionScore(score=10.0, feedback="test")
        
        with pytest.raises(Exception):
            SubDimensionScore(score=0.0, feedback="test")
    
    @pytest.mark.unit
    def test_sub_dimension_score_defaults(self):
        """Test default values for sub-dimension score."""
        score = SubDimensionScore(score=3.0, feedback="test")
        assert score.examples == []


class TestVerbalCommunicationScores:
    """Tests for VerbalCommunicationScores model."""
    
    @pytest.mark.unit
    def test_create_verbal_communication_scores(self):
        """Test creating verbal communication scores."""
        sub_dim = SubDimensionScore(score=4.0, feedback="test")
        
        scores = VerbalCommunicationScores(
            articulation=sub_dim,
            content_relevance=sub_dim,
            structure=sub_dim,
            vocabulary=sub_dim,
            delivery_confidence=sub_dim,
            category_score=20.0,
            category_feedback="Good verbal communication"
        )
        
        assert scores.category_score == 20.0
        assert scores.category_feedback == "Good verbal communication"
        assert scores.articulation.score == 4.0
    
    @pytest.mark.unit
    def test_verbal_communication_score_validation(self):
        """Test that category score validation works."""
        sub_dim = SubDimensionScore(score=3.0, feedback="test")
        
        # Valid score
        scores = VerbalCommunicationScores(
            articulation=sub_dim,
            content_relevance=sub_dim,
            structure=sub_dim,
            vocabulary=sub_dim,
            delivery_confidence=sub_dim,
            category_score=20.0,
            category_feedback="test"
        )
        assert 0.0 <= scores.category_score <= 40.0
        
        # Should raise validation error for out of range
        with pytest.raises(Exception):
            VerbalCommunicationScores(
                articulation=sub_dim,
                content_relevance=sub_dim,
                structure=sub_dim,
                vocabulary=sub_dim,
                delivery_confidence=sub_dim,
                category_score=50.0,  # Exceeds max of 40
                category_feedback="test"
            )


class TestInterviewReadinessScores:
    """Tests for InterviewReadinessScores model."""
    
    @pytest.mark.unit
    def test_create_interview_readiness_scores(self):
        """Test creating interview readiness scores."""
        sub_dim = SubDimensionScore(score=3.5, feedback="test")
        
        scores = InterviewReadinessScores(
            preparedness=sub_dim,
            example_quality=sub_dim,
            problem_solving=sub_dim,
            responsiveness=sub_dim,
            category_score=14.0,
            category_feedback="Well prepared"
        )
        
        assert scores.category_score == 14.0
        assert scores.category_score <= 20.0  # Max for this category


class TestNonVerbalCommunicationScores:
    """Tests for NonVerbalCommunicationScores model."""
    
    @pytest.mark.unit
    def test_create_non_verbal_scores(self):
        """Test creating non-verbal communication scores."""
        sub_dim = SubDimensionScore(score=3.0, feedback="test")
        
        scores = NonVerbalCommunicationScores(
            eye_contact=sub_dim,
            body_language=sub_dim,
            vocal_variety=sub_dim,
            pacing=sub_dim,
            engagement=sub_dim,
            category_score=15.0,
            category_feedback="Good non-verbal cues"
        )
        
        assert scores.category_score == 15.0
        assert scores.category_score <= 25.0  # Max for this category


class TestAdaptabilityEngagementScores:
    """Tests for AdaptabilityEngagementScores model."""
    
    @pytest.mark.unit
    def test_create_adaptability_scores(self):
        """Test creating adaptability & engagement scores."""
        sub_dim = SubDimensionScore(score=4.0, feedback="test")
        
        scores = AdaptabilityEngagementScores(
            adaptability=sub_dim,
            enthusiasm=sub_dim,
            active_listening=sub_dim,
            category_score=12.0,
            category_feedback="Engaged and adaptable"
        )
        
        assert scores.category_score == 12.0
        assert scores.category_score <= 15.0  # Max for this category


class TestEnhancedScoringRubric:
    """Tests for EnhancedScoringRubric model."""
    
    @pytest.mark.unit
    def test_create_enhanced_rubric(self):
        """Test creating enhanced scoring rubric."""
        sub_dim = SubDimensionScore(score=3.0, feedback="test")
        
        verbal = VerbalCommunicationScores(
            articulation=sub_dim,
            content_relevance=sub_dim,
            structure=sub_dim,
            vocabulary=sub_dim,
            delivery_confidence=sub_dim,
            category_score=15.0,
            category_feedback="test"
        )
        
        readiness = InterviewReadinessScores(
            preparedness=sub_dim,
            example_quality=sub_dim,
            problem_solving=sub_dim,
            responsiveness=sub_dim,
            category_score=12.0,
            category_feedback="test"
        )
        
        non_verbal = NonVerbalCommunicationScores(
            eye_contact=sub_dim,
            body_language=sub_dim,
            vocal_variety=sub_dim,
            pacing=sub_dim,
            engagement=sub_dim,
            category_score=15.0,
            category_feedback="test"
        )
        
        adaptability = AdaptabilityEngagementScores(
            adaptability=sub_dim,
            enthusiasm=sub_dim,
            active_listening=sub_dim,
            category_score=9.0,
            category_feedback="test"
        )
        
        rubric = EnhancedScoringRubric(
            verbal_communication=verbal,
            interview_readiness=readiness,
            non_verbal_communication=non_verbal,
            adaptability_engagement=adaptability,
            total_score=51.0,
            grade_tier=GradeTier.AVERAGE,
            overall_feedback="Overall assessment",
            top_strengths=["Strength 1", "Strength 2"],
            improvement_areas=["Area 1"]
        )
        
        assert rubric.total_score == 51.0
        assert rubric.grade_tier == GradeTier.AVERAGE
        assert len(rubric.top_strengths) == 2
        assert len(rubric.improvement_areas) == 1
        assert isinstance(rubric.created_at, datetime)
    
    @pytest.mark.unit
    def test_enhanced_rubric_total_score_validation(self):
        """Test that total score validation works."""
        sub_dim = SubDimensionScore(score=3.0, feedback="test")
        
        verbal = VerbalCommunicationScores(
            articulation=sub_dim,
            content_relevance=sub_dim,
            structure=sub_dim,
            vocabulary=sub_dim,
            delivery_confidence=sub_dim,
            category_score=40.0,
            category_feedback="test"
        )
        
        readiness = InterviewReadinessScores(
            preparedness=sub_dim,
            example_quality=sub_dim,
            problem_solving=sub_dim,
            responsiveness=sub_dim,
            category_score=20.0,
            category_feedback="test"
        )
        
        non_verbal = NonVerbalCommunicationScores(
            eye_contact=sub_dim,
            body_language=sub_dim,
            vocal_variety=sub_dim,
            pacing=sub_dim,
            engagement=sub_dim,
            category_score=25.0,
            category_feedback="test"
        )
        
        adaptability = AdaptabilityEngagementScores(
            adaptability=sub_dim,
            enthusiasm=sub_dim,
            active_listening=sub_dim,
            category_score=15.0,
            category_feedback="test"
        )
        
        # Valid total (100 points)
        rubric = EnhancedScoringRubric(
            verbal_communication=verbal,
            interview_readiness=readiness,
            non_verbal_communication=non_verbal,
            adaptability_engagement=adaptability,
            total_score=100.0,
            grade_tier=GradeTier.EXCELLENT,
            overall_feedback="Perfect score"
        )
        assert rubric.total_score == 100.0
        
        # Should raise validation error for out of range
        with pytest.raises(Exception):
            EnhancedScoringRubric(
                verbal_communication=verbal,
                interview_readiness=readiness,
                non_verbal_communication=non_verbal,
                adaptability_engagement=adaptability,
                total_score=150.0,  # Exceeds max
                grade_tier=GradeTier.EXCELLENT,
                overall_feedback="test"
            )


class TestAgentScore:
    """Tests for AgentScore model."""
    
    @pytest.mark.unit
    def test_create_agent_score(self):
        """Test creating agent score."""
        score = AgentScore(
            score=85.0,
            feedback="Good analysis",
            confidence=0.9,
            details={"source": "ai_service"}
        )
        
        assert score.score == 85.0
        assert score.feedback == "Good analysis"
        assert score.confidence == 0.9
        assert score.details == {"source": "ai_service"}
    
    @pytest.mark.unit
    def test_agent_score_validation(self):
        """Test that agent score validation works."""
        # Valid score (0-100)
        score = AgentScore(score=75.0, feedback="test", confidence=0.8)
        assert 0.0 <= score.score <= 100.0
        
        # Should raise validation error for out of range
        with pytest.raises(Exception):
            AgentScore(score=150.0, feedback="test", confidence=0.8)


class TestScoringWeights:
    """Tests for ScoringWeights model."""
    
    @pytest.mark.unit
    def test_create_scoring_weights(self):
        """Test creating scoring weights."""
        weights = ScoringWeights(
            content_weight=0.4,
            delivery_weight=0.3,
            technical_weight=0.3
        )
        
        assert weights.content_weight == 0.4
        assert weights.delivery_weight == 0.3
        assert weights.technical_weight == 0.3
    
    @pytest.mark.unit
    def test_scoring_weights_defaults(self):
        """Test default scoring weights."""
        weights = ScoringWeights()
        assert weights.content_weight == 0.4
        assert weights.delivery_weight == 0.3
        assert weights.technical_weight == 0.3

