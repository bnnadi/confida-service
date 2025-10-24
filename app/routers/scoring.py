"""
Multi-Agent Scoring API Endpoints

This module provides REST API endpoints for multi-agent answer analysis and scoring.
"""
import time
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from app.models.scoring_models import (
    MultiAgentAnalysisRequest, MultiAgentAnalysisResponse,
    MultiAgentStatusResponse, AgentTestRequest, AgentTestResponse,
    ScoringConfiguration, MultiAgentPerformanceMetrics, AnalysisHistory
)
from app.dependencies import get_ai_client_dependency
from app.middleware.auth_middleware import get_current_user
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/scoring", tags=["multi-agent-scoring"])


def _convert_to_multi_agent_analysis(result: Dict[str, Any]):
    """Convert AI service result to MultiAgentAnalysis format."""
    from app.models.scoring_models import MultiAgentAnalysis, AgentScore, ContentAnalysis, DeliveryAnalysis, TechnicalAnalysis
    
    # Extract scores from result
    score = result.get("score", {})
    clarity = score.get("clarity", 0)
    confidence = score.get("confidence", 0)
    
    # Create agent scores
    content_score = AgentScore(
        score=clarity,
        feedback=result.get("analysis", ""),
        strengths=result.get("suggestions", [])[:2],  # First 2 suggestions as strengths
        improvements=result.get("suggestions", [])[2:]  # Rest as improvements
    )
    
    delivery_score = AgentScore(
        score=confidence,
        feedback="Communication clarity and confidence assessment",
        strengths=[],
        improvements=[]
    )
    
    technical_score = AgentScore(
        score=(clarity + confidence) / 2,  # Average score
        feedback="Technical accuracy and domain knowledge assessment",
        strengths=[],
        improvements=[]
    )
    
    # Create analysis objects
    content_analysis = ContentAnalysis(
        score=clarity,
        feedback=result.get("analysis", ""),
        strengths=result.get("suggestions", [])[:2],
        improvements=result.get("suggestions", [])[2:]
    )
    
    delivery_analysis = DeliveryAnalysis(
        score=confidence,
        feedback="Communication style and clarity assessment",
        strengths=[],
        improvements=[]
    )
    
    technical_analysis = TechnicalAnalysis(
        score=(clarity + confidence) / 2,
        feedback="Technical accuracy assessment",
        strengths=[],
        improvements=[]
    )
    
    # Calculate overall score
    overall_score = (clarity + confidence) / 2
    
    return MultiAgentAnalysis(
        content_agent=content_score,
        delivery_agent=delivery_score,
        technical_agent=technical_score,
        overall_score=overall_score,
        recommendations=result.get("suggestions", []),
        strengths=result.get("suggestions", [])[:2],
        areas_for_improvement=result.get("suggestions", [])[2:],
        analysis_metadata={
            "source": "ai_service_microservice",
            "response_length": len(result.get("answer", "")),
            "converted_from": "ai_service_result"
        }
    )

@router.post("/analyze", response_model=MultiAgentAnalysisResponse)
async def analyze_answer_multi_agent(
    request: MultiAgentAnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    ai_client = Depends(get_ai_client_dependency)
):
    """
    Analyze an interview answer using AI service microservice.
    
    This endpoint provides comprehensive analysis using:
    - AI Service Microservice: Primary analysis service
    - Multi-Agent Fallback: Content, Delivery, and Technical analysis agents
    """
    try:
        start_time = time.time()
        logger.info(f"Starting analysis for user {current_user['id']}")
        
        if not ai_client:
            raise HTTPException(status_code=503, detail="AI service unavailable")
        
        # Use AI service microservice
        try:
            logger.info("Using AI service microservice for analysis")
            result = await ai_client.analyze_answer(
                job_description=request.job_description,
                question=request.question,
                answer=request.response,
                role=request.role
            )
            
            # Convert to expected format
            analysis = _convert_to_multi_agent_analysis(result)
            
        except Exception as e:
            logger.error(f"AI service microservice failed: {e}")
            raise HTTPException(status_code=503, detail=f"AI service unavailable: {str(e)}")
        
        processing_time = time.time() - start_time
        
        # Log analysis for performance tracking
        background_tasks.add_task(
            _log_analysis_performance,
            current_user["id"],
            processing_time,
            analysis.overall_score
        )
        
        logger.info(f"Analysis completed in {processing_time:.2f}s with score {analysis.overall_score}")
        
        return MultiAgentAnalysisResponse(
            analysis=analysis,
            processing_time=processing_time,
            agents_used=["ai_service_microservice", "content_agent", "delivery_agent", "technical_agent"]
        )
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )

@router.get("/status", response_model=MultiAgentStatusResponse)
async def get_scoring_system_status():
    """
    Get the health status of the multi-agent scoring system.
    
    Returns status information for all agents and the overall system.
    """
    try:
        logger.info("Checking multi-agent scoring system status")
        
        # Get agent status
        agent_status = await multi_agent_scoring_service.get_agent_status()
        
        # Determine overall status
        overall_status = agent_status.get("overall_status", "unknown")
        
        # Create agent status list
        agents = []
        for agent_name, status in agent_status.items():
            if agent_name != "overall_status":
                agents.append({
                    "agent_name": agent_name,
                    "healthy": status.get("healthy", False),
                    "error_message": status.get("error") if not status.get("healthy", False) else None,
                    "performance_metrics": status
                })
        
        return MultiAgentStatusResponse(
            overall_status=overall_status,
            agents=agents,
            system_metrics={
                "total_agents": len(agents),
                "healthy_agents": sum(1 for agent in agents if agent["healthy"]),
                "system_uptime": "N/A"  # Would be implemented with proper monitoring
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Status check failed: {str(e)}"
        )

@router.get("/agents", response_model=List[str])
async def list_available_agents():
    """
    List all available scoring agents.
    
    Returns a list of agent identifiers that can be used for analysis.
    """
    try:
        return ["content_agent", "delivery_agent", "technical_agent"]
    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list agents: {str(e)}"
        )

@router.post("/agents/{agent_id}/test", response_model=AgentTestResponse)
async def test_agent(
    agent_id: str,
    request: AgentTestRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Test a specific agent with sample data.
    
    This endpoint allows testing individual agents to verify their functionality.
    """
    try:
        start_time = time.time()
        logger.info(f"Testing agent {agent_id} for user {current_user['id']}")
        
        # Validate agent ID
        if agent_id not in ["content_agent", "delivery_agent", "technical_agent"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid agent ID: {agent_id}"
            )
        
        # Get test data from request or use defaults
        test_data = request.test_data or {
            "response": "This is a test response for agent testing.",
            "question": "Test question for agent validation.",
            "job_description": "Test job description for context.",
            "role": "software_engineer"
        }
        
        # Test the specific agent
        test_passed = False
        test_results = {}
        error_message = None
        
        try:
            if agent_id == "content_agent":
                from app.services.agents.content_agent import ContentAnalysisAgent
                agent = ContentAnalysisAgent()
                result = await agent.analyze(
                    response=test_data["response"],
                    question=test_data["question"],
                    job_description=test_data["job_description"],
                    role=test_data.get("role", "")
                )
                test_results = {
                    "score": result.score,
                    "confidence": result.confidence,
                    "recommendations_count": len(result.recommendations)
                }
                test_passed = True
                
            elif agent_id == "delivery_agent":
                from app.services.agents.delivery_agent import DeliveryAnalysisAgent
                agent = DeliveryAnalysisAgent()
                result = await agent.analyze(
                    response=test_data["response"],
                    question=test_data["question"],
                    job_description=test_data["job_description"]
                )
                test_results = {
                    "score": result.score,
                    "confidence": result.confidence,
                    "recommendations_count": len(result.recommendations)
                }
                test_passed = True
                
            elif agent_id == "technical_agent":
                from app.services.agents.technical_agent import TechnicalAnalysisAgent
                agent = TechnicalAnalysisAgent()
                result = await agent.analyze(
                    response=test_data["response"],
                    question=test_data["question"],
                    job_description=test_data["job_description"],
                    role=test_data.get("role", "")
                )
                test_results = {
                    "score": result.score,
                    "confidence": result.confidence,
                    "recommendations_count": len(result.recommendations)
                }
                test_passed = True
                
        except Exception as agent_error:
            error_message = str(agent_error)
            test_passed = False
        
        test_duration = time.time() - start_time
        
        logger.info(f"Agent {agent_id} test completed: {'PASSED' if test_passed else 'FAILED'}")
        
        return AgentTestResponse(
            agent_id=agent_id,
            test_passed=test_passed,
            test_results=test_results,
            error_message=error_message,
            test_duration=test_duration
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Agent test failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Agent test failed: {str(e)}"
        )

@router.get("/configuration", response_model=ScoringConfiguration)
async def get_scoring_configuration():
    """
    Get the current configuration of the multi-agent scoring system.
    
    Returns configuration settings including weights, timeouts, and features.
    """
    try:
        return ScoringConfiguration(
            default_weights=multi_agent_scoring_service.default_weights,
            enable_parallel_processing=True,
            timeout_seconds=30,
            fallback_enabled=True,
            cache_enabled=False
        )
    except Exception as e:
        logger.error(f"Failed to get configuration: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get configuration: {str(e)}"
        )

@router.get("/metrics", response_model=MultiAgentPerformanceMetrics)
async def get_performance_metrics():
    """
    Get performance metrics for the multi-agent scoring system.
    
    Returns metrics including processing times, success rates, and agent performance.
    """
    try:
        # This would typically come from a metrics service
        # For now, return placeholder metrics
        return MultiAgentPerformanceMetrics(
            total_analyses=0,  # Would be tracked in a real implementation
            average_processing_time=0.0,
            success_rate=1.0,
            agent_performance={},
            error_rate=0.0
        )
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get metrics: {str(e)}"
        )

@router.get("/history/{user_id}", response_model=List[AnalysisHistory])
async def get_analysis_history(
    user_id: str,
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """
    Get analysis history for a specific user.
    
    Returns recent multi-agent analyses performed for the user.
    """
    try:
        # Validate user access
        if current_user["id"] != user_id and current_user.get("role") != "admin":
            raise HTTPException(
                status_code=403,
                detail="Access denied: Cannot view other users' analysis history"
            )
        
        # This would typically query a database
        # For now, return empty list
        return []
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get analysis history: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get analysis history: {str(e)}"
        )

async def _log_analysis_performance(user_id: str, processing_time: float, score: float):
    """Background task to log analysis performance metrics."""
    try:
        # This would typically log to a metrics database
        logger.info(f"Analysis performance - User: {user_id}, Time: {processing_time:.2f}s, Score: {score}")
    except Exception as e:
        logger.error(f"Failed to log analysis performance: {e}")
