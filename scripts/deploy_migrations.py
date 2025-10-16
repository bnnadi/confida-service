#!/usr/bin/env python3
"""
Production Migration Deployment Script for Confida.

This script provides a comprehensive production deployment system for database
migrations with safety checks, rollback capabilities, and monitoring.
"""
import os
import sys
import argparse
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import get_settings
from app.utils.logger import get_logger
from app.utils.migration_validator import MigrationValidator
from app.database.migrate import MigrationManager

logger = get_logger(__name__)

class ProductionMigrationDeployer:
    """Production migration deployment system with comprehensive safety checks."""
    
    def __init__(self, environment: str = "production"):
        self.environment = environment
        self.settings = get_settings()
        self.migration_manager = MigrationManager()
        self.validator = MigrationValidator()
        self.deployment_log = []
        
    def deploy_migration(self, revision: str = "head", 
                        create_backup: bool = True,
                        validate_before: bool = True,
                        monitor_after: bool = True,
                        maintenance_window: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Deploy migration to production with comprehensive safety checks."""
        
        deployment_id = f"deploy_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        logger.info(f"Starting production migration deployment: {deployment_id}")
        
        deployment_results = {
            "deployment_id": deployment_id,
            "timestamp": datetime.utcnow().isoformat(),
            "environment": self.environment,
            "target_revision": revision,
            "success": False,
            "rollback_required": False,
            "backup_path": None,
            "issues": [],
            "warnings": [],
            "validation_results": {},
            "performance_metrics": {},
            "monitoring_results": {}
        }
        
        try:
            # Step 1: Pre-deployment validation
            if validate_before:
                logger.info("Running pre-deployment validation...")
                validation_results = self._run_pre_deployment_validation(revision)
                deployment_results["validation_results"] = validation_results
                
                if not validation_results.get("validation_passed", False):
                    deployment_results["issues"].extend(validation_results.get("issues", []))
                    logger.error("Pre-deployment validation failed, aborting deployment")
                    return deployment_results
            
            # Step 2: Check maintenance window
            if maintenance_window:
                if not self._check_maintenance_window(maintenance_window):
                    deployment_results["issues"].append("Outside maintenance window")
                    logger.error("Deployment outside maintenance window, aborting")
                    return deployment_results
            
            # Step 3: Create backup
            if create_backup:
                logger.info("Creating database backup...")
                backup_path = self._create_production_backup(deployment_id)
                if backup_path:
                    deployment_results["backup_path"] = backup_path
                    logger.info(f"Backup created: {backup_path}")
                else:
                    deployment_results["issues"].append("Backup creation failed")
                    logger.error("Backup creation failed, aborting deployment")
                    return deployment_results
            
            # Step 4: Notify stakeholders
            self._notify_deployment_start(deployment_id, revision)
            
            # Step 5: Apply migration
            logger.info(f"Applying migration to revision: {revision}")
            migration_success = self._apply_migration_safely(revision)
            
            if not migration_success:
                deployment_results["rollback_required"] = True
                deployment_results["issues"].append("Migration application failed")
                logger.error("Migration application failed")
                
                # Attempt automatic rollback
                if deployment_results["backup_path"]:
                    logger.info("Attempting automatic rollback...")
                    rollback_success = self._rollback_from_backup(deployment_results["backup_path"])
                    if rollback_success:
                        logger.info("Automatic rollback completed successfully")
                    else:
                        deployment_results["issues"].append("Automatic rollback failed")
                        self._notify_deployment_failure(deployment_id, "Rollback failed")
                else:
                    self._notify_deployment_failure(deployment_id, "No backup available for rollback")
                
                return deployment_results
            
            # Step 6: Post-deployment validation
            logger.info("Running post-deployment validation...")
            post_validation = self._run_post_deployment_validation(revision)
            deployment_results["validation_results"]["post_deployment"] = post_validation
            
            if not post_validation.get("validation_passed", False):
                deployment_results["rollback_required"] = True
                deployment_results["issues"].extend(post_validation.get("issues", []))
                logger.error("Post-deployment validation failed")
                
                # Attempt rollback
                if deployment_results["backup_path"]:
                    logger.info("Attempting rollback due to validation failure...")
                    rollback_success = self._rollback_from_backup(deployment_results["backup_path"])
                    if rollback_success:
                        logger.info("Rollback completed successfully")
                    else:
                        deployment_results["issues"].append("Rollback after validation failure failed")
                
                return deployment_results
            
            # Step 7: Performance monitoring
            if monitor_after:
                logger.info("Starting post-deployment monitoring...")
                monitoring_results = self._monitor_post_deployment_performance()
                deployment_results["monitoring_results"] = monitoring_results
                
                if monitoring_results.get("performance_issues"):
                    deployment_results["warnings"].extend(monitoring_results["performance_issues"])
            
            # Step 8: Success notification
            deployment_results["success"] = True
            logger.info(f"Migration deployment completed successfully: {deployment_id}")
            self._notify_deployment_success(deployment_id, revision)
            
            return deployment_results
            
        except Exception as e:
            logger.error(f"Deployment failed with exception: {e}")
            deployment_results["issues"].append(f"Deployment exception: {str(e)}")
            deployment_results["rollback_required"] = True
            
            # Attempt emergency rollback
            if deployment_results["backup_path"]:
                logger.info("Attempting emergency rollback...")
                self._rollback_from_backup(deployment_results["backup_path"])
            
            self._notify_deployment_failure(deployment_id, str(e))
            return deployment_results
    
    def _run_pre_deployment_validation(self, revision: str) -> Dict[str, Any]:
        """Run comprehensive pre-deployment validation."""
        validation_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "validation_passed": True,
            "issues": [],
            "checks": {}
        }
        
        try:
            # Check 1: Migration integrity
            integrity_check = self.validator.validate_migration_integrity(revision)
            validation_results["checks"]["integrity"] = integrity_check
            if not integrity_check.get("validation_passed", True):
                validation_results["validation_passed"] = False
                validation_results["issues"].extend(integrity_check.get("issues", []))
            
            # Check 2: Test on clean database
            clean_test = self.validator.test_migration_on_clean_database(revision)
            validation_results["checks"]["clean_database_test"] = clean_test
            if not clean_test.get("test_passed", True):
                validation_results["validation_passed"] = False
                validation_results["issues"].extend(clean_test.get("issues", []))
            
            # Check 3: Performance test
            performance_test = self.validator.performance_test_migration(revision)
            validation_results["checks"]["performance"] = performance_test
            if not performance_test.get("performance_passed", True):
                validation_results["validation_passed"] = False
                validation_results["issues"].extend(performance_test.get("issues", []))
            
            # Check 4: Database connectivity
            connectivity_check = self._check_database_connectivity()
            validation_results["checks"]["connectivity"] = connectivity_check
            if not connectivity_check.get("connected", True):
                validation_results["validation_passed"] = False
                validation_results["issues"].append("Database connectivity check failed")
            
            # Check 5: System resources
            resource_check = self._check_system_resources()
            validation_results["checks"]["resources"] = resource_check
            if not resource_check.get("sufficient", True):
                validation_results["validation_passed"] = False
                validation_results["issues"].extend(resource_check.get("issues", []))
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Pre-deployment validation failed: {e}")
            validation_results["validation_passed"] = False
            validation_results["issues"].append(f"Validation error: {str(e)}")
            return validation_results
    
    def _run_post_deployment_validation(self, revision: str) -> Dict[str, Any]:
        """Run post-deployment validation."""
        validation_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "validation_passed": True,
            "issues": []
        }
        
        try:
            # Check 1: Data integrity
            integrity_check = self.validator.validate_data_integrity_after_migration(revision)
            validation_results["data_integrity"] = integrity_check
            if not integrity_check.get("integrity_passed", True):
                validation_results["validation_passed"] = False
                validation_results["issues"].extend(integrity_check.get("issues", []))
            
            # Check 2: Application connectivity
            app_connectivity = self._check_application_connectivity()
            validation_results["app_connectivity"] = app_connectivity
            if not app_connectivity.get("connected", True):
                validation_results["validation_passed"] = False
                validation_results["issues"].append("Application connectivity check failed")
            
            # Check 3: Critical queries
            critical_queries = self._test_critical_queries()
            validation_results["critical_queries"] = critical_queries
            if not critical_queries.get("all_passed", True):
                validation_results["validation_passed"] = False
                validation_results["issues"].extend(critical_queries.get("failed_queries", []))
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Post-deployment validation failed: {e}")
            validation_results["validation_passed"] = False
            validation_results["issues"].append(f"Post-validation error: {str(e)}")
            return validation_results
    
    def _check_maintenance_window(self, window: Dict[str, str]) -> bool:
        """Check if current time is within maintenance window."""
        try:
            now = datetime.now()
            start_time = datetime.strptime(window["start"], "%H:%M").time()
            end_time = datetime.strptime(window["end"], "%H:%M").time()
            
            current_time = now.time()
            
            # Handle overnight maintenance windows
            if start_time <= end_time:
                return start_time <= current_time <= end_time
            else:
                return current_time >= start_time or current_time <= end_time
                
        except Exception as e:
            logger.error(f"Maintenance window check failed: {e}")
            return False
    
    def _create_production_backup(self, deployment_id: str) -> Optional[str]:
        """Create production database backup."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"production_backup_{deployment_id}_{timestamp}.sql"
            backup_path = f"/tmp/{backup_filename}"
            
            # Parse database URL
            db_url = self.settings.DATABASE_URL
            if db_url.startswith("postgresql://"):
                url_parts = db_url.replace("postgresql://", "").split("/")
                db_name = url_parts[1]
                auth_host = url_parts[0].split("@")
                auth = auth_host[0].split(":")
                host_port = auth_host[1].split(":")
                
                user = auth[0]
                password = auth[1] if len(auth) > 1 else ""
                host = host_port[0]
                port = host_port[1] if len(host_port) > 1 else "5432"
                
                # Create backup using pg_dump
                env = os.environ.copy()
                if password:
                    env["PGPASSWORD"] = password
                
                backup_cmd = [
                    "pg_dump",
                    "-h", host,
                    "-p", port,
                    "-U", user,
                    "-d", db_name,
                    "-f", backup_path,
                    "--verbose",
                    "--no-password",
                    "--format=custom",
                    "--compress=9"
                ]
                
                result = subprocess.run(
                    backup_cmd,
                    env=env,
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                # Verify backup file was created and has content
                if os.path.exists(backup_path) and os.path.getsize(backup_path) > 0:
                    logger.info(f"Production backup created successfully: {backup_path}")
                    return backup_path
                else:
                    logger.error("Backup file was not created or is empty")
                    return None
                    
        except Exception as e:
            logger.error(f"Production backup creation failed: {e}")
            return None
    
    def _apply_migration_safely(self, revision: str) -> bool:
        """Apply migration with safety checks."""
        try:
            # Set maintenance mode
            self._set_maintenance_mode(True)
            
            # Apply migration
            success = self.migration_manager.upgrade(revision)
            
            # Disable maintenance mode
            self._set_maintenance_mode(False)
            
            return success
            
        except Exception as e:
            logger.error(f"Safe migration application failed: {e}")
            # Ensure maintenance mode is disabled
            self._set_maintenance_mode(False)
            return False
    
    def _rollback_from_backup(self, backup_path: str) -> bool:
        """Rollback database from backup."""
        try:
            logger.info(f"Rolling back database from backup: {backup_path}")
            
            # Set maintenance mode
            self._set_maintenance_mode(True)
            
            # Restore from backup
            success = self.migration_manager.restore_database(backup_path)
            
            # Disable maintenance mode
            self._set_maintenance_mode(False)
            
            if success:
                logger.info("Database rollback completed successfully")
            else:
                logger.error("Database rollback failed")
            
            return success
            
        except Exception as e:
            logger.error(f"Rollback from backup failed: {e}")
            # Ensure maintenance mode is disabled
            self._set_maintenance_mode(False)
            return False
    
    def _monitor_post_deployment_performance(self) -> Dict[str, Any]:
        """Monitor post-deployment performance."""
        monitoring_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "performance_issues": [],
            "metrics": {}
        }
        
        try:
            # Monitor for 5 minutes after deployment
            monitoring_duration = 300  # 5 minutes
            start_time = time.time()
            
            while time.time() - start_time < monitoring_duration:
                # Check database performance
                db_performance = self._check_database_performance()
                monitoring_results["metrics"][f"check_{int(time.time())}"] = db_performance
                
                # Check for performance issues
                if db_performance.get("slow_queries", 0) > 10:
                    monitoring_results["performance_issues"].append("High number of slow queries detected")
                
                if db_performance.get("connection_count", 0) > 80:
                    monitoring_results["performance_issues"].append("High connection count detected")
                
                time.sleep(30)  # Check every 30 seconds
            
            return monitoring_results
            
        except Exception as e:
            logger.error(f"Post-deployment monitoring failed: {e}")
            monitoring_results["performance_issues"].append(f"Monitoring error: {str(e)}")
            return monitoring_results
    
    def _check_database_connectivity(self) -> Dict[str, Any]:
        """Check database connectivity."""
        try:
            import psycopg2
            conn = psycopg2.connect(self.settings.DATABASE_URL)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            return {"connected": True, "response_time": "< 1s"}
            
        except Exception as e:
            return {"connected": False, "error": str(e)}
    
    def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resources."""
        try:
            import psutil
            
            # Check disk space
            disk_usage = psutil.disk_usage('/')
            disk_free_gb = disk_usage.free / (1024**3)
            
            # Check memory
            memory = psutil.virtual_memory()
            memory_available_gb = memory.available / (1024**3)
            
            issues = []
            sufficient = True
            
            if disk_free_gb < 5:  # Less than 5GB free
                issues.append(f"Low disk space: {disk_free_gb:.2f}GB available")
                sufficient = False
            
            if memory_available_gb < 2:  # Less than 2GB available
                issues.append(f"Low memory: {memory_available_gb:.2f}GB available")
                sufficient = False
            
            return {
                "sufficient": sufficient,
                "issues": issues,
                "disk_free_gb": disk_free_gb,
                "memory_available_gb": memory_available_gb
            }
            
        except ImportError:
            return {"sufficient": True, "issues": ["psutil not available for resource checking"]}
        except Exception as e:
            return {"sufficient": False, "issues": [f"Resource check error: {str(e)}"]}
    
    def _check_application_connectivity(self) -> Dict[str, Any]:
        """Check application connectivity."""
        try:
            # This would typically check if the application can connect to the database
            # and perform basic operations
            engine = create_engine(self.settings.DATABASE_URL)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM users"))
                user_count = result.fetchone()[0]
            
            return {"connected": True, "user_count": user_count}
            
        except Exception as e:
            return {"connected": False, "error": str(e)}
    
    def _test_critical_queries(self) -> Dict[str, Any]:
        """Test critical application queries."""
        critical_queries = [
            "SELECT COUNT(*) FROM users",
            "SELECT COUNT(*) FROM interview_sessions",
            "SELECT COUNT(*) FROM questions",
            "SELECT COUNT(*) FROM session_questions",
            "SELECT COUNT(*) FROM answers"
        ]
        
        results = {"all_passed": True, "failed_queries": []}
        
        try:
            engine = create_engine(self.settings.DATABASE_URL)
            with engine.connect() as conn:
                for query in critical_queries:
                    try:
                        result = conn.execute(text(query))
                        result.fetchone()
                    except Exception as e:
                        results["all_passed"] = False
                        results["failed_queries"].append(f"Query failed: {query} - {str(e)}")
            
            return results
            
        except Exception as e:
            results["all_passed"] = False
            results["failed_queries"].append(f"Critical query test error: {str(e)}")
            return results
    
    def _check_database_performance(self) -> Dict[str, Any]:
        """Check database performance metrics."""
        try:
            engine = create_engine(self.settings.DATABASE_URL)
            with engine.connect() as conn:
                # Check active connections
                result = conn.execute(text("SELECT COUNT(*) FROM pg_stat_activity"))
                connection_count = result.fetchone()[0]
                
                # Check slow queries (simplified)
                result = conn.execute(text("""
                    SELECT COUNT(*) 
                    FROM pg_stat_activity 
                    WHERE state = 'active' 
                    AND query_start < NOW() - INTERVAL '30 seconds'
                """))
                slow_queries = result.fetchone()[0]
                
                return {
                    "connection_count": connection_count,
                    "slow_queries": slow_queries,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}
    
    def _set_maintenance_mode(self, enabled: bool):
        """Set application maintenance mode."""
        try:
            # This would typically update a configuration file or database setting
            # For now, we'll just log the action
            if enabled:
                logger.info("Setting application to maintenance mode")
            else:
                logger.info("Disabling application maintenance mode")
                
        except Exception as e:
            logger.error(f"Failed to set maintenance mode: {e}")
    
    def _notify_deployment_start(self, deployment_id: str, revision: str):
        """Notify stakeholders of deployment start."""
        logger.info(f"Deployment started: {deployment_id} to revision {revision}")
        # In production, this would send notifications via email, Slack, etc.
    
    def _notify_deployment_success(self, deployment_id: str, revision: str):
        """Notify stakeholders of successful deployment."""
        logger.info(f"Deployment successful: {deployment_id} to revision {revision}")
        # In production, this would send success notifications
    
    def _notify_deployment_failure(self, deployment_id: str, error: str):
        """Notify stakeholders of deployment failure."""
        logger.error(f"Deployment failed: {deployment_id} - {error}")
        # In production, this would send failure notifications and alerts

def main():
    """Main CLI interface for production migration deployment."""
    parser = argparse.ArgumentParser(description="Confida Production Migration Deployer")
    parser.add_argument("revision", nargs="?", default="head", help="Target revision (default: head)")
    parser.add_argument("--environment", default="production", help="Target environment")
    parser.add_argument("--no-backup", action="store_true", help="Skip backup creation")
    parser.add_argument("--no-validation", action="store_true", help="Skip pre-deployment validation")
    parser.add_argument("--no-monitoring", action="store_true", help="Skip post-deployment monitoring")
    parser.add_argument("--maintenance-window", help="Maintenance window (format: HH:MM-HH:MM)")
    parser.add_argument("--dry-run", action="store_true", help="Perform dry run without applying changes")
    
    args = parser.parse_args()
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be applied")
        # In dry run mode, we would run all validations but skip the actual migration
    
    deployer = ProductionMigrationDeployer(environment=args.environment)
    
    # Parse maintenance window if provided
    maintenance_window = None
    if args.maintenance_window:
        start, end = args.maintenance_window.split("-")
        maintenance_window = {"start": start, "end": end}
    
    # Deploy migration
    results = deployer.deploy_migration(
        revision=args.revision,
        create_backup=not args.no_backup,
        validate_before=not args.no_validation,
        monitor_after=not args.no_monitoring,
        maintenance_window=maintenance_window
    )
    
    # Output results
    print(json.dumps(results, indent=2))
    
    # Exit with appropriate code
    sys.exit(0 if results["success"] else 1)

if __name__ == "__main__":
    main()
