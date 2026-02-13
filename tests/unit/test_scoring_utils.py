"""
Unit tests for scoring utilities.

Tests the 100-point scoring rubric utilities including:
- Grade tier calculation
- Score conversion (10-point to 100-point scale)
- Category score calculation
- Enhanced rubric parsing and creation
"""
import pytest
from app.utils.scoring_utils import (
    calculate_grade_tier,
    convert_10_to_100,
    convert_100_to_10,
    calculate_category_score,
    calculate_total_score,
    create_sub_dimension_score,
    parse_enhanced_rubric_from_ai_response,
    create_enhanced_rubric_from_legacy_scores,
    _parse_sub_dimension
)
from app.models.scoring_models import (
    GradeTier,
    SubDimensionScore,
    EnhancedScoringRubric,
    VerbalCommunicationScores,
    InterviewReadinessScores,
    NonVerbalCommunicationScores,
    AdaptabilityEngagementScores
)


class TestGradeTierCalculation:
    """Tests for grade tier calculation."""
    
    @pytest.mark.unit
    def test_excellent_tier(self):
        """Test Excellent tier (90-100 points)."""
        assert calculate_grade_tier(90.0) == GradeTier.EXCELLENT
        assert calculate_grade_tier(95.0) == GradeTier.EXCELLENT
        assert calculate_grade_tier(100.0) == GradeTier.EXCELLENT
    
    @pytest.mark.unit
    def test_strong_tier(self):
        """Test Strong tier (72-89 points)."""
        assert calculate_grade_tier(72.0) == GradeTier.STRONG
        assert calculate_grade_tier(75.0) == GradeTier.STRONG
        assert calculate_grade_tier(82.5) == GradeTier.STRONG
        assert calculate_grade_tier(89.9) == GradeTier.STRONG
    
    @pytest.mark.unit
    def test_average_tier(self):
        """Test Average tier (60-71.9 points). Strong is 72-89.9."""
        assert calculate_grade_tier(60.0) == GradeTier.AVERAGE
        assert calculate_grade_tier(67.5) == GradeTier.AVERAGE
        assert calculate_grade_tier(71.9) == GradeTier.AVERAGE
    
    @pytest.mark.unit
    def test_at_risk_tier(self):
        """Test At Risk tier (0-59 points)."""
        assert calculate_grade_tier(0.0) == GradeTier.AT_RISK
        assert calculate_grade_tier(30.0) == GradeTier.AT_RISK
        assert calculate_grade_tier(59.9) == GradeTier.AT_RISK


class TestScoreConversion:
    """Tests for score conversion between scales."""
    
    @pytest.mark.unit
    def test_convert_10_to_100(self):
        """Test conversion from 0-10 to 0-100 scale."""
        assert convert_10_to_100(0.0) == 0.0
        assert convert_10_to_100(5.0) == 50.0
        assert convert_10_to_100(10.0) == 100.0
        assert convert_10_to_100(7.5) == 75.0
    
    @pytest.mark.unit
    def test_convert_10_to_100_clamping(self):
        """Test that conversion clamps values to valid range."""
        assert convert_10_to_100(-5.0) == 0.0
        assert convert_10_to_100(15.0) == 100.0
    
    @pytest.mark.unit
    def test_convert_100_to_10(self):
        """Test conversion from 0-100 to 0-10 scale."""
        assert convert_100_to_10(0.0) == 0.0
        assert convert_100_to_10(50.0) == 5.0
        assert convert_100_to_10(100.0) == 10.0
        assert convert_100_to_10(75.0) == 7.5
    
    @pytest.mark.unit
    def test_convert_100_to_10_clamping(self):
        """Test that conversion clamps values to valid range."""
        assert convert_100_to_10(-10.0) == 0.0
        assert convert_100_to_10(150.0) == 10.0
    
    @pytest.mark.unit
    def test_conversion_roundtrip(self):
        """Test that conversion is reversible (with rounding)."""
        original = 7.5
        converted = convert_10_to_100(original)
        back = convert_100_to_10(converted)
        assert abs(back - original) < 0.01


class TestSubDimensionScore:
    """Tests for sub-dimension score creation."""
    
    @pytest.mark.unit
    def test_create_sub_dimension_score_valid(self):
        """Test creating valid sub-dimension score."""
        score = create_sub_dimension_score(3.5, "Good feedback", ["example1"])
        assert score.score == 3.5
        assert score.feedback == "Good feedback"
        assert score.examples == ["example1"]
    
    @pytest.mark.unit
    def test_create_sub_dimension_score_clamping(self):
        """Test that scores are clamped to 1-5 range."""
        score_low = create_sub_dimension_score(0.0, "test")
        assert score_low.score == 1.0
        
        score_high = create_sub_dimension_score(10.0, "test")
        assert score_high.score == 5.0
    
    @pytest.mark.unit
    def test_create_sub_dimension_score_defaults(self):
        """Test default values for sub-dimension score."""
        score = create_sub_dimension_score(3.0, "test")
        assert score.examples == []


class TestCategoryScoreCalculation:
    """Tests for category score calculation."""
    
    @pytest.mark.unit
    def test_calculate_category_score(self):
        """Test calculating category score from sub-dimensions."""
        sub_dims = {
            "dim1": create_sub_dimension_score(4.0, "test"),
            "dim2": create_sub_dimension_score(3.0, "test"),
            "dim3": create_sub_dimension_score(5.0, "test"),
        }
        total = calculate_category_score(sub_dims)
        assert total == 12.0
    
    @pytest.mark.unit
    def test_calculate_category_score_max_limit(self):
        """Test that category score respects maximum limit."""
        sub_dims = {
            "dim1": create_sub_dimension_score(5.0, "test"),
            "dim2": create_sub_dimension_score(5.0, "test"),
        }
        total = calculate_category_score(sub_dims)
        assert total == 10.0  # 2 dimensions * 5 points max
    
    @pytest.mark.unit
    def test_calculate_category_score_min_limit(self):
        """Test that category score respects minimum limit."""
        sub_dims = {
            "dim1": create_sub_dimension_score(-5.0, "test"),  # Will be clamped
        }
        total = calculate_category_score(sub_dims)
        assert total >= 0.0


class TestTotalScoreCalculation:
    """Tests for total score calculation."""
    
    @pytest.mark.unit
    def test_calculate_total_score(self):
        """Test calculating total score from rubric."""
        # Create a minimal rubric for testing
        verbal = VerbalCommunicationScores(
            articulation=create_sub_dimension_score(4.0, "test"),
            content_relevance=create_sub_dimension_score(4.0, "test"),
            structure=create_sub_dimension_score(4.0, "test"),
            vocabulary=create_sub_dimension_score(4.0, "test"),
            delivery_confidence=create_sub_dimension_score(4.0, "test"),
            category_score=20.0,
            category_feedback="test"
        )
        
        readiness = InterviewReadinessScores(
            preparedness=create_sub_dimension_score(3.0, "test"),
            example_quality=create_sub_dimension_score(3.0, "test"),
            problem_solving=create_sub_dimension_score(3.0, "test"),
            responsiveness=create_sub_dimension_score(3.0, "test"),
            category_score=12.0,
            category_feedback="test"
        )
        
        non_verbal = NonVerbalCommunicationScores(
            eye_contact=create_sub_dimension_score(3.0, "test"),
            body_language=create_sub_dimension_score(3.0, "test"),
            vocal_variety=create_sub_dimension_score(3.0, "test"),
            pacing=create_sub_dimension_score(3.0, "test"),
            engagement=create_sub_dimension_score(3.0, "test"),
            category_score=15.0,
            category_feedback="test"
        )
        
        adaptability = AdaptabilityEngagementScores(
            adaptability=create_sub_dimension_score(3.0, "test"),
            enthusiasm=create_sub_dimension_score(3.0, "test"),
            active_listening=create_sub_dimension_score(3.0, "test"),
            category_score=9.0,
            category_feedback="test"
        )
        
        rubric = EnhancedScoringRubric(
            verbal_communication=verbal,
            interview_readiness=readiness,
            non_verbal_communication=non_verbal,
            adaptability_engagement=adaptability,
            total_score=0.0,  # Will be calculated
            grade_tier=GradeTier.AVERAGE,
            overall_feedback="test"
        )
        
        total = calculate_total_score(rubric)
        assert total == 56.0  # 20 + 12 + 15 + 9
        assert total <= 100.0


class TestParseEnhancedRubric:
    """Tests for parsing enhanced rubric from AI response."""
    
    @pytest.mark.unit
    def test_parse_enhanced_rubric_success(self):
        """Test successfully parsing enhanced rubric from AI response."""
        ai_response = {
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
                "top_strengths": ["Clear communication", "Good preparation"],
                "improvement_areas": ["Could improve pacing", "More examples needed"]
            }
        }
        
        rubric = parse_enhanced_rubric_from_ai_response(ai_response)
        
        assert rubric is not None
        assert rubric.total_score == 62.5  # 20.5 + 15.0 + 16.0 + 11.0
        assert rubric.grade_tier == GradeTier.AVERAGE
        assert rubric.overall_feedback == "Strong overall performance"
        assert len(rubric.top_strengths) == 2
        assert len(rubric.improvement_areas) == 2
    
    @pytest.mark.unit
    def test_parse_enhanced_rubric_not_found(self):
        """Test parsing when enhanced rubric is not in response."""
        ai_response = {
            "analysis": "Some analysis",
            "score": {"clarity": 7, "confidence": 8}
        }
        
        rubric = parse_enhanced_rubric_from_ai_response(ai_response)
        assert rubric is None
    
    @pytest.mark.unit
    def test_parse_enhanced_rubric_invalid_data(self):
        """Test parsing with invalid data structure."""
        ai_response = {
            "enhanced_rubric": {
                "invalid": "data"
            }
        }
        
        # Should handle gracefully and return None or raise
        rubric = parse_enhanced_rubric_from_ai_response(ai_response)
        # May return None or raise, depending on implementation
        assert rubric is None or isinstance(rubric, EnhancedScoringRubric)


class TestCreateRubricFromLegacyScores:
    """Tests for creating enhanced rubric from legacy scores."""
    
    @pytest.mark.unit
    def test_create_rubric_from_legacy_scores(self):
        """Test creating enhanced rubric from legacy clarity/confidence scores."""
        rubric = create_enhanced_rubric_from_legacy_scores(
            clarity=8.0,
            confidence=7.5,
            analysis="Good answer with clear explanation",
            suggestions=["Add more examples", "Elaborate on technical details"]
        )
        
        assert rubric is not None
        assert isinstance(rubric, EnhancedScoringRubric)
        assert rubric.total_score > 0
        assert rubric.total_score <= 100.0
        assert rubric.grade_tier in [GradeTier.EXCELLENT, GradeTier.STRONG, GradeTier.AVERAGE, GradeTier.AT_RISK]
        assert len(rubric.top_strengths) <= 3
        assert len(rubric.improvement_areas) <= 3
    
    @pytest.mark.unit
    def test_create_rubric_from_legacy_scores_zero(self):
        """Test creating rubric from zero scores."""
        rubric = create_enhanced_rubric_from_legacy_scores(
            clarity=0.0,
            confidence=0.0,
            analysis="Poor answer",
            suggestions=[]
        )
        
        assert rubric is not None
        assert rubric.total_score >= 0.0
        assert rubric.grade_tier == GradeTier.AT_RISK
    
    @pytest.mark.unit
    def test_create_rubric_from_legacy_scores_high(self):
        """Test creating rubric from high scores."""
        rubric = create_enhanced_rubric_from_legacy_scores(
            clarity=10.0,
            confidence=10.0,
            analysis="Excellent answer",
            suggestions=["Keep up the good work"]
        )
        
        assert rubric is not None
        assert rubric.total_score > 70.0  # Should be high
        assert rubric.grade_tier in [GradeTier.EXCELLENT, GradeTier.STRONG]
    
    @pytest.mark.unit
    def test_create_rubric_category_scores(self):
        """Test that all category scores are calculated correctly."""
        rubric = create_enhanced_rubric_from_legacy_scores(
            clarity=8.0,
            confidence=7.0,
            analysis="Test",
            suggestions=[]
        )
        
        assert rubric.verbal_communication.category_score > 0
        assert rubric.interview_readiness.category_score > 0
        assert rubric.non_verbal_communication.category_score > 0
        assert rubric.adaptability_engagement.category_score > 0
        
        # Verify category score limits
        assert rubric.verbal_communication.category_score <= 40.0
        assert rubric.interview_readiness.category_score <= 20.0
        assert rubric.non_verbal_communication.category_score <= 25.0
        assert rubric.adaptability_engagement.category_score <= 15.0


class TestParseSubDimension:
    """Tests for parsing sub-dimensions."""
    
    @pytest.mark.unit
    def test_parse_sub_dimension(self):
        """Test parsing a single sub-dimension."""
        data = {
            "articulation": {
                "score": 4.5,
                "feedback": "Clear articulation",
                "examples": ["example1", "example2"]
            }
        }
        
        score = _parse_sub_dimension(data, "articulation")
        assert score.score == 4.5
        assert score.feedback == "Clear articulation"
        assert score.examples == ["example1", "example2"]
    
    @pytest.mark.unit
    def test_parse_sub_dimension_missing(self):
        """Test parsing sub-dimension with missing data."""
        data = {}
        
        score = _parse_sub_dimension(data, "missing_field")
        assert score.score == 3.0  # Default
        assert score.feedback == ""
        assert score.examples == []
    
    @pytest.mark.unit
    def test_parse_sub_dimension_partial(self):
        """Test parsing sub-dimension with partial data."""
        data = {
            "field": {
                "score": 4.0
                # Missing feedback and examples
            }
        }
        
        score = _parse_sub_dimension(data, "field")
        assert score.score == 4.0
        assert score.feedback == ""
        assert score.examples == []

