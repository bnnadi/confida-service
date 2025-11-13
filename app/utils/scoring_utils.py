"""
Scoring Utilities for 100-Point Rubric System

This module provides utility functions for calculating scores,
converting between formats, and determining grade tiers.
"""
from typing import Dict, Any, Optional
from app.models.scoring_models import (
    GradeTier, EnhancedScoringRubric, SubDimensionScore,
    VerbalCommunicationScores, InterviewReadinessScores,
    NonVerbalCommunicationScores, AdaptabilityEngagementScores
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


def calculate_grade_tier(total_score: float) -> GradeTier:
    """
    Calculate grade tier based on total score.
    
    Args:
        total_score: Total score out of 100
        
    Returns:
        GradeTier enum value
    """
    if total_score >= 90:
        return GradeTier.EXCELLENT
    elif total_score >= 75:
        return GradeTier.STRONG
    elif total_score >= 60:
        return GradeTier.AVERAGE
    else:
        return GradeTier.AT_RISK


def convert_10_to_100(score_10: float) -> float:
    """
    Convert a score from 0-10 scale to 0-100 scale.
    
    Args:
        score_10: Score on 0-10 scale
        
    Returns:
        Score on 0-100 scale
    """
    return min(max(score_10 * 10, 0.0), 100.0)


def convert_100_to_10(score_100: float) -> float:
    """
    Convert a score from 0-100 scale to 0-10 scale (for backward compatibility).
    
    Args:
        score_100: Score on 0-100 scale
        
    Returns:
        Score on 0-10 scale
    """
    return min(max(score_100 / 10, 0.0), 10.0)


def calculate_category_score(sub_dimensions: Dict[str, SubDimensionScore]) -> float:
    """
    Calculate total category score from sub-dimension scores.
    Each sub-dimension is worth 5 points (1-5 scale).
    
    Args:
        sub_dimensions: Dictionary of sub-dimension name to SubDimensionScore
        
    Returns:
        Total category score (sum of all sub-dimension scores)
    """
    total = 0.0
    for sub_dim in sub_dimensions.values():
        total += sub_dim.score
    return min(max(total, 0.0), len(sub_dimensions) * 5.0)


def calculate_total_score(rubric: EnhancedScoringRubric) -> float:
    """
    Calculate total score from all categories.
    
    Args:
        rubric: EnhancedScoringRubric instance
        
    Returns:
        Total score out of 100
    """
    total = (
        rubric.verbal_communication.category_score +
        rubric.interview_readiness.category_score +
        rubric.non_verbal_communication.category_score +
        rubric.adaptability_engagement.category_score
    )
    return min(max(total, 0.0), 100.0)


def create_sub_dimension_score(
    score: float,
    feedback: str,
    examples: Optional[list] = None
) -> SubDimensionScore:
    """
    Create a SubDimensionScore with validation.
    
    Args:
        score: Score from 1-5
        feedback: Feedback text
        examples: Optional list of examples
        
    Returns:
        SubDimensionScore instance
    """
    # Clamp score to valid range
    score = min(max(score, 1.0), 5.0)
    
    return SubDimensionScore(
        score=score,
        feedback=feedback,
        examples=examples or []
    )


def _parse_sub_dimension(data: Dict[str, Any], field_name: str, default_score: float = 3.0) -> SubDimensionScore:
    """Helper to parse a single sub-dimension from data."""
    field_data = data.get(field_name, {})
    return create_sub_dimension_score(
        field_data.get("score", default_score),
        field_data.get("feedback", ""),
        field_data.get("examples", [])
    )


def parse_enhanced_rubric_from_ai_response(
    ai_response: Dict[str, Any]
) -> Optional[EnhancedScoringRubric]:
    """
    Parse enhanced scoring rubric from AI service response.
    
    This function attempts to extract the 100-point rubric structure
    from the AI service response. If the response doesn't contain
    the enhanced format, it returns None.
    
    Args:
        ai_response: Response dictionary from AI service
        
    Returns:
        EnhancedScoringRubric if found, None otherwise
    """
    try:
        # Check if response contains enhanced_rubric field
        rubric_data = ai_response.get("enhanced_rubric") or ai_response.get("rubric")
        
        if not rubric_data:
            return None
        
        # Define field mappings for each category
        VERBAL_FIELDS = ["articulation", "content_relevance", "structure", "vocabulary", "delivery_confidence"]
        READINESS_FIELDS = ["preparedness", "example_quality", "problem_solving", "responsiveness"]
        NON_VERBAL_FIELDS = ["eye_contact", "body_language", "vocal_variety", "pacing", "engagement"]
        ADAPTABILITY_FIELDS = ["adaptability", "enthusiasm", "active_listening"]
        
        # Parse verbal communication
        verbal_data = rubric_data.get("verbal_communication", {})
        verbal_sub_dims = {field: _parse_sub_dimension(verbal_data, field) for field in VERBAL_FIELDS}
        verbal_scores = VerbalCommunicationScores(
            **verbal_sub_dims,
            category_score=verbal_data.get("category_score", sum(sd.score for sd in verbal_sub_dims.values())),
            category_feedback=verbal_data.get("category_feedback", "")
        )
        
        # Parse interview readiness
        readiness_data = rubric_data.get("interview_readiness", {})
        readiness_sub_dims = {field: _parse_sub_dimension(readiness_data, field) for field in READINESS_FIELDS}
        readiness_scores = InterviewReadinessScores(
            **readiness_sub_dims,
            category_score=readiness_data.get("category_score", sum(sd.score for sd in readiness_sub_dims.values())),
            category_feedback=readiness_data.get("category_feedback", "")
        )
        
        # Parse non-verbal communication
        non_verbal_data = rubric_data.get("non_verbal_communication", {})
        non_verbal_sub_dims = {field: _parse_sub_dimension(non_verbal_data, field) for field in NON_VERBAL_FIELDS}
        non_verbal_scores = NonVerbalCommunicationScores(
            **non_verbal_sub_dims,
            category_score=non_verbal_data.get("category_score", sum(sd.score for sd in non_verbal_sub_dims.values())),
            category_feedback=non_verbal_data.get("category_feedback", "")
        )
        
        # Parse adaptability & engagement
        adaptability_data = rubric_data.get("adaptability_engagement", {})
        adaptability_sub_dims = {field: _parse_sub_dimension(adaptability_data, field) for field in ADAPTABILITY_FIELDS}
        adaptability_scores = AdaptabilityEngagementScores(
            **adaptability_sub_dims,
            category_score=adaptability_data.get("category_score", sum(sd.score for sd in adaptability_sub_dims.values())),
            category_feedback=adaptability_data.get("category_feedback", "")
        )
        
        # Calculate total score directly
        total_score = min(max(
            verbal_scores.category_score +
            readiness_scores.category_score +
            non_verbal_scores.category_score +
            adaptability_scores.category_score,
            0.0
        ), 100.0)
        
        # Create rubric
        return EnhancedScoringRubric(
            verbal_communication=verbal_scores,
            interview_readiness=readiness_scores,
            non_verbal_communication=non_verbal_scores,
            adaptability_engagement=adaptability_scores,
            total_score=total_score,
            grade_tier=calculate_grade_tier(total_score),
            overall_feedback=rubric_data.get("overall_feedback", ""),
            top_strengths=rubric_data.get("top_strengths", []),
            improvement_areas=rubric_data.get("improvement_areas", [])
        )
        
    except Exception as e:
        logger.error(f"Failed to parse enhanced rubric from AI response: {e}")
        return None


def create_enhanced_rubric_from_legacy_scores(
    clarity: float,
    confidence: float,
    analysis: str = "",
    suggestions: list = None
) -> EnhancedScoringRubric:
    """
    Create an enhanced rubric from legacy clarity/confidence scores.
    This is a fallback function for backward compatibility.
    
    Args:
        clarity: Clarity score (0-10 scale)
        confidence: Confidence score (0-10 scale)
        analysis: Analysis text
        suggestions: List of suggestions
        
    Returns:
        EnhancedScoringRubric with estimated scores
    """
    # Convert to 1-5 scale for sub-dimensions
    clarity_5 = (clarity / 10.0) * 5.0 if clarity > 0 else 3.0
    confidence_5 = (confidence / 10.0) * 5.0 if confidence > 0 else 3.0
    avg_score = (clarity_5 + confidence_5) / 2.0
    
    # Define mappings: (field_name, score_value, feedback)
    verbal_mappings = [
        ("articulation", clarity_5, "Based on clarity assessment"),
        ("content_relevance", clarity_5, "Based on content analysis"),
        ("structure", avg_score, "Based on overall structure"),
        ("vocabulary", clarity_5, "Based on word choice"),
        ("delivery_confidence", confidence_5, "Based on confidence assessment"),
    ]
    
    readiness_mappings = [
        ("preparedness", avg_score, "Based on overall preparation"),
        ("example_quality", clarity_5, "Based on example quality"),
        ("problem_solving", avg_score, "Based on problem-solving approach"),
        ("responsiveness", confidence_5, "Based on responsiveness"),
    ]
    
    non_verbal_mappings = [
        ("eye_contact", avg_score, "Estimated from delivery"),
        ("body_language", avg_score, "Estimated from delivery"),
        ("vocal_variety", confidence_5, "Based on vocal confidence"),
        ("pacing", avg_score, "Based on overall pacing"),
        ("engagement", confidence_5, "Based on engagement level"),
    ]
    
    adaptability_mappings = [
        ("adaptability", avg_score, "Based on adaptability"),
        ("enthusiasm", confidence_5, "Based on enthusiasm"),
        ("active_listening", avg_score, "Based on active listening"),
    ]
    
    # Create sub-dimensions and calculate category scores in one pass
    verbal_sub_dims = {
        field: create_sub_dimension_score(score, feedback)
        for field, score, feedback in verbal_mappings
    }
    verbal_scores = VerbalCommunicationScores(
        **verbal_sub_dims,
        category_score=sum(sd.score for sd in verbal_sub_dims.values()),
        category_feedback=analysis or "Verbal communication assessment"
    )
    
    readiness_sub_dims = {
        field: create_sub_dimension_score(score, feedback)
        for field, score, feedback in readiness_mappings
    }
    readiness_scores = InterviewReadinessScores(
        **readiness_sub_dims,
        category_score=sum(sd.score for sd in readiness_sub_dims.values()),
        category_feedback="Interview readiness assessment"
    )
    
    non_verbal_sub_dims = {
        field: create_sub_dimension_score(score, feedback)
        for field, score, feedback in non_verbal_mappings
    }
    non_verbal_scores = NonVerbalCommunicationScores(
        **non_verbal_sub_dims,
        category_score=sum(sd.score for sd in non_verbal_sub_dims.values()),
        category_feedback="Non-verbal communication assessment (estimated)"
    )
    
    adaptability_sub_dims = {
        field: create_sub_dimension_score(score, feedback)
        for field, score, feedback in adaptability_mappings
    }
    adaptability_scores = AdaptabilityEngagementScores(
        **adaptability_sub_dims,
        category_score=sum(sd.score for sd in adaptability_sub_dims.values()),
        category_feedback="Adaptability & engagement assessment"
    )
    
    # Calculate total directly
    total_score = min(max(
        verbal_scores.category_score +
        readiness_scores.category_score +
        non_verbal_scores.category_score +
        adaptability_scores.category_score,
        0.0
    ), 100.0)
    
    return EnhancedScoringRubric(
        verbal_communication=verbal_scores,
        interview_readiness=readiness_scores,
        non_verbal_communication=non_verbal_scores,
        adaptability_engagement=adaptability_scores,
        total_score=total_score,
        grade_tier=calculate_grade_tier(total_score),
        overall_feedback=analysis or "Comprehensive interview assessment",
        top_strengths=(suggestions or [])[:3] if suggestions else [],
        improvement_areas=(suggestions or [])[3:6] if suggestions and len(suggestions) > 3 else []
    )

