"""
Generic Analytics Aggregation Framework for InterviewIQ.

This module provides a unified framework for aggregating analytics data,
eliminating repetitive aggregation logic across different metric types.
"""
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from app.database.models import UserPerformance, AnalyticsEvent, InterviewSession
from app.utils.logger import get_logger

logger = get_logger(__name__)

class AggregationType(Enum):
    COUNT = "count"
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    PERCENTILE = "percentile"

class TimeGranularity(Enum):
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"

@dataclass
class AggregationConfig:
    """Configuration for aggregation operations."""
    entity_type: str
    entity_id_field: str
    metrics: List[str]
    aggregation_types: List[AggregationType]
    time_granularity: Optional[TimeGranularity] = None
    date_range_days: int = 30
    filters: Optional[Dict[str, Any]] = None

@dataclass
class AggregationResult:
    """Result of aggregation operation."""
    entity_type: str
    entity_id: str
    metrics: Dict[str, Any]
    time_range: Dict[str, datetime]
    aggregation_config: AggregationConfig
    execution_time_ms: int

class MetricAggregator:
    """Generic metric aggregator for different entity types."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.aggregation_functions = {
            AggregationType.COUNT: self._aggregate_count,
            AggregationType.SUM: self._aggregate_sum,
            AggregationType.AVG: self._aggregate_avg,
            AggregationType.MIN: self._aggregate_min,
            AggregationType.MAX: self._aggregate_max,
            AggregationType.PERCENTILE: self._aggregate_percentile
        }
    
    def aggregate(self, config: AggregationConfig, entity_id: str, 
                 start_date: Optional[datetime] = None, 
                 end_date: Optional[datetime] = None) -> AggregationResult:
        """Execute aggregation based on configuration."""
        start_time = datetime.utcnow()
        
        # Set default date range if not provided
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=config.date_range_days)
        
        logger.info(f"Aggregating {config.entity_type} metrics for entity {entity_id}")
        
        # Get base query for the entity type
        base_query = self._get_base_query(config.entity_type, entity_id, start_date, end_date)
        
        # Apply filters
        if config.filters:
            base_query = self._apply_filters(base_query, config.filters)
        
        # Execute aggregations
        metrics = {}
        for metric in config.metrics:
            for agg_type in config.aggregation_types:
                key = f"{metric}_{agg_type.value}"
                metrics[key] = self._execute_aggregation(base_query, metric, agg_type)
        
        execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return AggregationResult(
            entity_type=config.entity_type,
            entity_id=entity_id,
            metrics=metrics,
            time_range={"start": start_date, "end": end_date},
            aggregation_config=config,
            execution_time_ms=execution_time
        )
    
    def _get_base_query(self, entity_type: str, entity_id: str, 
                       start_date: datetime, end_date: datetime):
        """Get base query for the entity type."""
        query_mapping = {
            "user_performance": self.db.query(UserPerformance).filter(
                and_(
                    UserPerformance.user_id == entity_id,
                    UserPerformance.created_at >= start_date,
                    UserPerformance.created_at <= end_date
                )
            ),
            "analytics_events": self.db.query(AnalyticsEvent).filter(
                and_(
                    AnalyticsEvent.user_id == entity_id,
                    AnalyticsEvent.timestamp >= start_date,
                    AnalyticsEvent.timestamp <= end_date
                )
            ),
            "interview_sessions": self.db.query(InterviewSession).filter(
                and_(
                    InterviewSession.user_id == entity_id,
                    InterviewSession.created_at >= start_date,
                    InterviewSession.created_at <= end_date
                )
            )
        }
        
        return query_mapping.get(entity_type, self.db.query())
    
    def _apply_filters(self, query, filters: Dict[str, Any]):
        """Apply additional filters to the query."""
        for field, value in filters.items():
            if hasattr(query.column_descriptions[0]['entity'], field):
                query = query.filter(getattr(query.column_descriptions[0]['entity'], field) == value)
        return query
    
    def _execute_aggregation(self, query, metric: str, agg_type: AggregationType):
        """Execute specific aggregation type."""
        aggregator = self.aggregation_functions.get(agg_type)
        if not aggregator:
            logger.warning(f"Unknown aggregation type: {agg_type}")
            return None
        
        try:
            return aggregator(query, metric)
        except Exception as e:
            logger.error(f"Aggregation failed for {metric} with {agg_type}: {e}")
            return None
    
    def _aggregate_count(self, query, metric: str) -> int:
        """Count aggregation."""
        return query.count()
    
    def _aggregate_sum(self, query, metric: str) -> float:
        """Sum aggregation."""
        if hasattr(query.column_descriptions[0]['entity'], metric):
            return query.with_entities(func.sum(getattr(query.column_descriptions[0]['entity'], metric))).scalar() or 0
        return 0
    
    def _aggregate_avg(self, query, metric: str) -> float:
        """Average aggregation."""
        if hasattr(query.column_descriptions[0]['entity'], metric):
            return query.with_entities(func.avg(getattr(query.column_descriptions[0]['entity'], metric))).scalar() or 0
        return 0
    
    def _aggregate_min(self, query, metric: str) -> float:
        """Minimum aggregation."""
        if hasattr(query.column_descriptions[0]['entity'], metric):
            return query.with_entities(func.min(getattr(query.column_descriptions[0]['entity'], metric))).scalar() or 0
        return 0
    
    def _aggregate_max(self, query, metric: str) -> float:
        """Maximum aggregation."""
        if hasattr(query.column_descriptions[0]['entity'], metric):
            return query.with_entities(func.max(getattr(query.column_descriptions[0]['entity'], metric))).scalar() or 0
        return 0
    
    def _aggregate_percentile(self, query, metric: str, percentile: float = 0.5) -> float:
        """Percentile aggregation."""
        if hasattr(query.column_descriptions[0]['entity'], metric):
            # Simple percentile calculation (can be enhanced with proper percentile functions)
            values = query.with_entities(getattr(query.column_descriptions[0]['entity'], metric)).all()
            if values:
                sorted_values = sorted([v[0] for v in values if v[0] is not None])
                index = int(len(sorted_values) * percentile)
                return sorted_values[min(index, len(sorted_values) - 1)]
        return 0

class SimplifiedAnalyticsService:
    """Simplified analytics service using generic aggregation framework."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.aggregator = MetricAggregator(db_session)
    
    def get_user_performance_metrics(self, user_id: str, date_range_days: int = 30) -> Dict[str, Any]:
        """Get user performance metrics using generic aggregation."""
        config = AggregationConfig(
            entity_type="user_performance",
            entity_id_field="user_id",
            metrics=["score", "completion_time", "accuracy"],
            aggregation_types=[AggregationType.COUNT, AggregationType.AVG, AggregationType.MAX],
            date_range_days=date_range_days
        )
        
        result = self.aggregator.aggregate(config, user_id)
        return {
            "user_id": user_id,
            "metrics": result.metrics,
            "time_range": result.time_range,
            "execution_time_ms": result.execution_time_ms
        }
    
    def get_session_analytics(self, session_id: str, date_range_days: int = 30) -> Dict[str, Any]:
        """Get session analytics using generic aggregation."""
        config = AggregationConfig(
            entity_type="interview_sessions",
            entity_id_field="session_id",
            metrics=["duration", "questions_answered", "score"],
            aggregation_types=[AggregationType.COUNT, AggregationType.SUM, AggregationType.AVG],
            date_range_days=date_range_days
        )
        
        result = self.aggregator.aggregate(config, session_id)
        return {
            "session_id": session_id,
            "metrics": result.metrics,
            "time_range": result.time_range,
            "execution_time_ms": result.execution_time_ms
        }
    
    def get_question_analytics(self, question_id: str, date_range_days: int = 30) -> Dict[str, Any]:
        """Get question analytics using generic aggregation."""
        config = AggregationConfig(
            entity_type="analytics_events",
            entity_id_field="question_id",
            metrics=["response_time", "accuracy", "difficulty_rating"],
            aggregation_types=[AggregationType.COUNT, AggregationType.AVG, AggregationType.PERCENTILE],
            date_range_days=date_range_days
        )
        
        result = self.aggregator.aggregate(config, question_id)
        return {
            "question_id": question_id,
            "metrics": result.metrics,
            "time_range": result.time_range,
            "execution_time_ms": result.execution_time_ms
        }
    
    def get_custom_analytics(self, entity_type: str, entity_id: str, 
                           metrics: List[str], aggregation_types: List[AggregationType],
                           date_range_days: int = 30, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get custom analytics using flexible configuration."""
        config = AggregationConfig(
            entity_type=entity_type,
            entity_id_field="id",
            metrics=metrics,
            aggregation_types=aggregation_types,
            date_range_days=date_range_days,
            filters=filters
        )
        
        result = self.aggregator.aggregate(config, entity_id)
        return {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "metrics": result.metrics,
            "time_range": result.time_range,
            "execution_time_ms": result.execution_time_ms
        }
