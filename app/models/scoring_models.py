"""
Multi-Agent Scoring Models

This module defines Pydantic models for multi-agent analysis and scoring.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class AgentScore(BaseModel):
    """Score and feedback from an individual agent."""
    score: float = Field(..., ge=0.0, le=10.0, description="Agent score from 0-10")
    feedback: str = Field(..., description="Detailed feedback from the agent")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Agent confidence in the analysis")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional agent-specific details")

class ScoringWeights(BaseModel):
    """Weights for combining different agent scores."""
    content_weight: float = Field(default=0.4, ge=0.0, le=1.0, description="Weight for content analysis")
    delivery_weight: float = Field(default=0.3, ge=0.0, le=1.0, description="Weight for delivery analysis")
    technical_weight: float = Field(default=0.3, ge=0.0, le=1.0, description="Weight for technical analysis")
    
    def __post_init__(self):
        """Ensure weights sum to 1.0."""
        total = self.content_weight + self.delivery_weight + self.technical_weight
        if total > 0:
            self.content_weight /= total
            self.delivery_weight /= total
            self.technical_weight /= total

class ContentAnalysis(BaseModel):
    """Content analysis results from the content agent."""
    score: float = Field(..., ge=0.0, le=10.0, description="Overall content score")
    feedback: str = Field(..., description="Content analysis feedback")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Analysis confidence")
    details: Dict[str, Any] = Field(default_factory=dict, description="Detailed analysis data")
    recommendations: List[str] = Field(default_factory=list, description="Content improvement recommendations")
    content_metrics: Dict[str, float] = Field(default_factory=dict, description="Individual content metrics")

class DeliveryAnalysis(BaseModel):
    """Delivery analysis results from the delivery agent."""
    score: float = Field(..., ge=0.0, le=10.0, description="Overall delivery score")
    feedback: str = Field(..., description="Delivery analysis feedback")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Analysis confidence")
    details: Dict[str, Any] = Field(default_factory=dict, description="Detailed analysis data")
    recommendations: List[str] = Field(default_factory=list, description="Delivery improvement recommendations")
    delivery_metrics: Dict[str, float] = Field(default_factory=dict, description="Individual delivery metrics")

class TechnicalAnalysis(BaseModel):
    """Technical analysis results from the technical agent."""
    score: float = Field(..., ge=0.0, le=10.0, description="Overall technical score")
    feedback: str = Field(..., description="Technical analysis feedback")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Analysis confidence")
    details: Dict[str, Any] = Field(default_factory=dict, description="Detailed analysis data")
    recommendations: List[str] = Field(default_factory=list, description="Technical improvement recommendations")
    technical_metrics: Dict[str, float] = Field(default_factory=dict, description="Individual technical metrics")

class MultiAgentAnalysis(BaseModel):
    """Comprehensive multi-agent analysis results."""
    content_agent: AgentScore = Field(..., description="Content analysis results")
    delivery_agent: AgentScore = Field(..., description="Delivery analysis results")
    technical_agent: AgentScore = Field(..., description="Technical analysis results")
    overall_score: float = Field(..., ge=0.0, le=10.0, description="Weighted overall score")
    recommendations: List[str] = Field(default_factory=list, description="Comprehensive recommendations")
    strengths: List[str] = Field(default_factory=list, description="Identified strengths")
    areas_for_improvement: List[str] = Field(default_factory=list, description="Areas needing improvement")
    analysis_metadata: Dict[str, Any] = Field(default_factory=dict, description="Analysis metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Analysis timestamp")

class MultiAgentAnalysisRequest(BaseModel):
    """Request model for multi-agent analysis."""
    response: str = Field(..., min_length=1, max_length=10000, description="The candidate's answer")
    question: str = Field(..., min_length=1, max_length=2000, description="The interview question")
    job_description: str = Field(..., min_length=1, max_length=5000, description="Job description for context")
    role: str = Field(default="", max_length=200, description="Job role for specialized analysis")
    weights: Optional[ScoringWeights] = Field(default=None, description="Custom scoring weights")

class MultiAgentAnalysisResponse(BaseModel):
    """Response model for multi-agent analysis."""
    analysis: MultiAgentAnalysis = Field(..., description="Complete multi-agent analysis")
    processing_time: float = Field(..., ge=0.0, description="Analysis processing time in seconds")
    agents_used: List[str] = Field(..., description="List of agents that participated in analysis")

class AgentStatus(BaseModel):
    """Status information for an individual agent."""
    agent_name: str = Field(..., description="Name of the agent")
    healthy: bool = Field(..., description="Whether the agent is healthy")
    last_check: datetime = Field(default_factory=datetime.utcnow, description="Last health check timestamp")
    error_message: Optional[str] = Field(default=None, description="Error message if unhealthy")
    performance_metrics: Dict[str, Any] = Field(default_factory=dict, description="Agent performance metrics")

class MultiAgentStatusResponse(BaseModel):
    """Response model for multi-agent system status."""
    overall_status: str = Field(..., description="Overall system status: healthy, degraded, or unhealthy")
    agents: List[AgentStatus] = Field(..., description="Status of individual agents")
    system_metrics: Dict[str, Any] = Field(default_factory=dict, description="System-wide metrics")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last status update")

class AgentTestRequest(BaseModel):
    """Request model for testing individual agents."""
    agent_id: str = Field(..., description="ID of the agent to test")
    test_data: Dict[str, Any] = Field(default_factory=dict, description="Test data for the agent")

class AgentTestResponse(BaseModel):
    """Response model for agent testing."""
    agent_id: str = Field(..., description="ID of the tested agent")
    test_passed: bool = Field(..., description="Whether the test passed")
    test_results: Dict[str, Any] = Field(default_factory=dict, description="Detailed test results")
    error_message: Optional[str] = Field(default=None, description="Error message if test failed")
    test_duration: float = Field(..., ge=0.0, description="Test duration in seconds")

class ScoringConfiguration(BaseModel):
    """Configuration for multi-agent scoring system."""
    default_weights: ScoringWeights = Field(default_factory=ScoringWeights, description="Default scoring weights")
    enable_parallel_processing: bool = Field(default=True, description="Whether to process agents in parallel")
    timeout_seconds: int = Field(default=30, ge=1, le=300, description="Timeout for agent analysis")
    fallback_enabled: bool = Field(default=True, description="Whether to use fallback analysis on failure")
    cache_enabled: bool = Field(default=False, description="Whether to cache analysis results")

class AnalysisHistory(BaseModel):
    """Historical analysis data for tracking and improvement."""
    analysis_id: str = Field(..., description="Unique analysis identifier")
    user_id: str = Field(..., description="User who submitted the answer")
    question_id: str = Field(..., description="Question that was answered")
    analysis: MultiAgentAnalysis = Field(..., description="The analysis results")
    user_feedback: Optional[Dict[str, Any]] = Field(default=None, description="User feedback on the analysis")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Analysis timestamp")

class MultiAgentPerformanceMetrics(BaseModel):
    """Performance metrics for the multi-agent system."""
    total_analyses: int = Field(default=0, ge=0, description="Total number of analyses performed")
    average_processing_time: float = Field(default=0.0, ge=0.0, description="Average processing time in seconds")
    success_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Success rate of analyses")
    agent_performance: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Performance metrics per agent")
    error_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Error rate of analyses")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last metrics update")
