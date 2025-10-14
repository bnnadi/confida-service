"""
Async Database Monitor Service.

This service provides monitoring and health checks for the async database connection pool,
including connection statistics, performance metrics, and health status.
"""
import asyncio
import time
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncEngine
from app.database.async_connection import async_db_manager
from app.utils.logger import get_logger
from datetime import datetime, timedelta

logger = get_logger(__name__)

class AsyncDatabaseMonitor:
    """Monitor for async database connection pool health and performance."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.monitoring_enabled = True
        self.monitoring_interval = 30  # seconds
        self.performance_history = []
        self.max_history_size = 100
    
    async def start_monitoring(self) -> None:
        """Start the monitoring task."""
        if not self.monitoring_enabled:
            return
        
        self.logger.info("Starting async database monitoring...")
        
        while self.monitoring_enabled:
            try:
                await self._collect_metrics()
                await asyncio.sleep(self.monitoring_interval)
            except Exception as e:
                self.logger.error(f"Error in database monitoring: {e}")
                await asyncio.sleep(self.monitoring_interval)
    
    async def stop_monitoring(self) -> None:
        """Stop the monitoring task."""
        self.monitoring_enabled = False
        self.logger.info("Stopped async database monitoring")
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status of the async database."""
        try:
            if not async_db_manager.engine:
                return {
                    "status": "unhealthy",
                    "error": "Database engine not initialized",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Test database connectivity
            connectivity_status = await self._test_connectivity()
            
            # Get connection pool statistics
            pool_stats = await self._get_pool_statistics()
            
            # Get performance metrics
            performance_metrics = await self._get_performance_metrics()
            
            # Determine overall health
            overall_status = "healthy"
            if not connectivity_status["connected"]:
                overall_status = "unhealthy"
            elif pool_stats["pool_size"] >= pool_stats["max_overflow"] * 0.9:
                overall_status = "degraded"
            
            return {
                "status": overall_status,
                "connectivity": connectivity_status,
                "pool_statistics": pool_stats,
                "performance_metrics": performance_metrics,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting health status: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_connection_pool_status(self) -> Dict[str, Any]:
        """Get detailed connection pool status."""
        try:
            if not async_db_manager.engine:
                return {"error": "Database engine not initialized"}
            
            pool = async_db_manager.engine.pool
            
            return {
                "pool_size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "invalid": pool.invalid(),
                "max_overflow": pool._max_overflow,
                "pool_timeout": pool._timeout,
                "pool_recycle": pool._recycle,
                "pool_pre_ping": pool._pre_ping,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting connection pool status: {e}")
            return {"error": str(e)}
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the database."""
        try:
            if not self.performance_history:
                return {"message": "No performance data available yet"}
            
            # Calculate averages from recent history
            recent_history = self.performance_history[-10:]  # Last 10 measurements
            
            avg_response_time = sum(m["response_time"] for m in recent_history) / len(recent_history)
            avg_connections = sum(m["active_connections"] for m in recent_history) / len(recent_history)
            avg_queries_per_second = sum(m["queries_per_second"] for m in recent_history) / len(recent_history)
            
            return {
                "average_response_time_ms": round(avg_response_time * 1000, 2),
                "average_active_connections": round(avg_connections, 2),
                "average_queries_per_second": round(avg_queries_per_second, 2),
                "total_measurements": len(self.performance_history),
                "last_measurement": self.performance_history[-1]["timestamp"] if self.performance_history else None,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting performance metrics: {e}")
            return {"error": str(e)}
    
    async def _collect_metrics(self) -> None:
        """Collect performance metrics."""
        try:
            start_time = time.time()
            
            # Test a simple query
            async with async_db_manager.engine.begin() as conn:
                await conn.execute("SELECT 1")
            
            response_time = time.time() - start_time
            
            # Get connection pool stats
            pool_stats = await self._get_pool_statistics()
            
            # Calculate queries per second (simplified)
            queries_per_second = 1 / response_time if response_time > 0 else 0
            
            # Store metrics
            metrics = {
                "timestamp": datetime.utcnow().isoformat(),
                "response_time": response_time,
                "active_connections": pool_stats["checked_out"],
                "queries_per_second": queries_per_second,
                "pool_size": pool_stats["pool_size"],
                "overflow": pool_stats["overflow"]
            }
            
            self.performance_history.append(metrics)
            
            # Keep history size manageable
            if len(self.performance_history) > self.max_history_size:
                self.performance_history = self.performance_history[-self.max_history_size:]
            
            # Log performance issues
            if response_time > 1.0:  # More than 1 second
                self.logger.warning(f"Slow database response: {response_time:.2f}s")
            
            if pool_stats["checked_out"] >= pool_stats["pool_size"] * 0.8:
                self.logger.warning(f"High connection pool usage: {pool_stats['checked_out']}/{pool_stats['pool_size']}")
                
        except Exception as e:
            self.logger.error(f"Error collecting metrics: {e}")
    
    async def _test_connectivity(self) -> Dict[str, Any]:
        """Test database connectivity."""
        try:
            start_time = time.time()
            
            async with async_db_manager.engine.begin() as conn:
                result = await conn.execute("SELECT 1 as test")
                test_value = result.scalar()
            
            response_time = time.time() - start_time
            
            return {
                "connected": True,
                "response_time_ms": round(response_time * 1000, 2),
                "test_value": test_value,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Database connectivity test failed: {e}")
            return {
                "connected": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _get_pool_statistics(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        try:
            if not async_db_manager.engine:
                return {"error": "Database engine not initialized"}
            
            pool = async_db_manager.engine.pool
            
            return {
                "pool_size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "invalid": pool.invalid(),
                "max_overflow": pool._max_overflow,
                "pool_timeout": pool._timeout,
                "pool_recycle": pool._recycle
            }
            
        except Exception as e:
            self.logger.error(f"Error getting pool statistics: {e}")
            return {"error": str(e)}
    
    async def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        try:
            if not self.performance_history:
                return {"message": "No performance data available yet"}
            
            latest = self.performance_history[-1]
            
            return {
                "latest_response_time_ms": round(latest["response_time"] * 1000, 2),
                "latest_active_connections": latest["active_connections"],
                "latest_queries_per_second": round(latest["queries_per_second"], 2),
                "measurement_count": len(self.performance_history),
                "last_measurement": latest["timestamp"]
            }
            
        except Exception as e:
            self.logger.error(f"Error getting performance metrics: {e}")
            return {"error": str(e)}
    
    async def reset_metrics(self) -> None:
        """Reset performance metrics history."""
        self.performance_history = []
        self.logger.info("Reset performance metrics history")
    
    async def get_health_summary(self) -> Dict[str, Any]:
        """Get a summary of database health for quick status checks."""
        try:
            health_status = await self.get_health_status()
            pool_status = await self.get_connection_pool_status()
            
            return {
                "overall_status": health_status["status"],
                "connected": health_status["connectivity"]["connected"],
                "active_connections": pool_status.get("checked_out", 0),
                "pool_size": pool_status.get("pool_size", 0),
                "response_time_ms": health_status["connectivity"].get("response_time_ms", 0),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting health summary: {e}")
            return {
                "overall_status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

# Global monitor instance
async_db_monitor = AsyncDatabaseMonitor()
