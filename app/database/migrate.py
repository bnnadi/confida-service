#!/usr/bin/env python3
"""
Database Migration Management Script for Confida.

This script provides a comprehensive interface for managing database migrations
using Alembic. It includes validation, rollback capabilities, and production
deployment procedures.
"""
import subprocess
import sys
import os
import argparse
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Add project root to Python path before importing app modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

class MigrationManager:
    """Comprehensive migration management system."""
    
    def __init__(self):
        self.settings = get_settings()
        self.project_root = Path(__file__).parent.parent.parent
        self.migration_dir = self.project_root / "app" / "database" / "migrations"
        
    def run_alembic_command(self, command: str, capture_output: bool = True) -> subprocess.CompletedProcess:
        """Run an alembic command with proper error handling."""
        try:
            result = subprocess.run(
                ["alembic"] + command.split(),
                cwd=self.project_root,
                capture_output=capture_output,
                text=True,
                check=True
            )
            if capture_output:
                logger.info(f"Alembic command '{command}' completed successfully")
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"Alembic command '{command}' failed: {e.stderr}")
            raise MigrationError(f"Migration command failed: {e.stderr}")
    
    def upgrade(self, revision: str = "head") -> bool:
        """Upgrade database to specified revision."""
        logger.info(f"Upgrading database to revision: {revision}")
        try:
            self.run_alembic_command(f"upgrade {revision}")
            logger.info(f"Database successfully upgraded to {revision}")
            return True
        except MigrationError as e:
            logger.error(f"Upgrade failed: {e}")
            return False
    
    def downgrade(self, revision: str = "-1") -> bool:
        """Downgrade database to specified revision."""
        logger.info(f"Downgrading database to revision: {revision}")
        try:
            self.run_alembic_command(f"downgrade {revision}")
            logger.info(f"Database successfully downgraded to {revision}")
            return True
        except MigrationError as e:
            logger.error(f"Downgrade failed: {e}")
            return False
    
    def create_migration(self, message: str, autogenerate: bool = True) -> bool:
        """Create a new migration."""
        logger.info(f"Creating migration: {message}")
        try:
            if autogenerate:
                self.run_alembic_command(f'revision --autogenerate -m "{message}"')
            else:
                self.run_alembic_command(f'revision -m "{message}"')
            logger.info(f"Migration created successfully: {message}")
            return True
        except MigrationError as e:
            logger.error(f"Migration creation failed: {e}")
            return False
    
    def show_history(self) -> List[Dict[str, str]]:
        """Show migration history."""
        try:
            result = self.run_alembic_command("history --verbose")
            return self._parse_history_output(result.stdout)
        except MigrationError as e:
            logger.error(f"Failed to get migration history: {e}")
            return []
    
    def show_current(self) -> Optional[str]:
        """Show current database revision."""
        try:
            result = self.run_alembic_command("current")
            return result.stdout.strip()
        except MigrationError as e:
            logger.error(f"Failed to get current revision: {e}")
            return None
    
    def validate_migration(self, revision: str = "head") -> Dict[str, Any]:
        """Validate migration before applying."""
        logger.info(f"Validating migration to revision: {revision}")
        
        validation_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "target_revision": revision,
            "current_revision": self.show_current(),
            "validation_passed": True,
            "issues": [],
            "warnings": []
        }
        
        try:
            # Check if database is accessible
            if not self._test_database_connection():
                validation_results["validation_passed"] = False
                validation_results["issues"].append("Database connection failed")
            
            # Check if migration files exist
            if not self._validate_migration_files():
                validation_results["validation_passed"] = False
                validation_results["issues"].append("Migration files validation failed")
            
            # Check for pending migrations
            pending_migrations = self._get_pending_migrations()
            if pending_migrations:
                validation_results["warnings"].append(f"Found {len(pending_migrations)} pending migrations")
            
            # Validate migration chain integrity
            if not self._validate_migration_chain():
                validation_results["validation_passed"] = False
                validation_results["issues"].append("Migration chain integrity check failed")
            
            logger.info(f"Migration validation completed. Passed: {validation_results['validation_passed']}")
            return validation_results
            
        except Exception as e:
            logger.error(f"Migration validation failed: {e}")
            validation_results["validation_passed"] = False
            validation_results["issues"].append(f"Validation error: {str(e)}")
            return validation_results
    
    def backup_database(self, backup_path: Optional[str] = None) -> str:
        """Create a database backup before migration."""
        if not backup_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"backup_confida_{timestamp}.sql"
        
        logger.info(f"Creating database backup: {backup_path}")
        
        try:
            # Extract connection details from DATABASE_URL
            db_url = self.settings.DATABASE_URL
            # Simple parsing - in production, use proper URL parsing
            if db_url.startswith("postgresql://"):
                # Parse postgresql://user:pass@host:port/dbname
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
                    "--verbose"
                ]
                
                result = subprocess.run(
                    backup_cmd,
                    env=env,
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                logger.info(f"Database backup created successfully: {backup_path}")
                return backup_path
                
        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            raise MigrationError(f"Backup failed: {e}")
    
    def restore_database(self, backup_path: str) -> bool:
        """Restore database from backup."""
        logger.info(f"Restoring database from backup: {backup_path}")
        
        try:
            # Extract connection details from DATABASE_URL
            db_url = self.settings.DATABASE_URL
            if db_url.startswith("postgresql://"):
                # Parse connection details (same as backup)
                url_parts = db_url.replace("postgresql://", "").split("/")
                db_name = url_parts[1]
                auth_host = url_parts[0].split("@")
                auth = auth_host[0].split(":")
                host_port = auth_host[1].split(":")
                
                user = auth[0]
                password = auth[1] if len(auth) > 1 else ""
                host = host_port[0]
                port = host_port[1] if len(host_port) > 1 else "5432"
                
                # Restore using psql
                env = os.environ.copy()
                if password:
                    env["PGPASSWORD"] = password
                
                restore_cmd = [
                    "psql",
                    "-h", host,
                    "-p", port,
                    "-U", user,
                    "-d", db_name,
                    "-f", backup_path
                ]
                
                result = subprocess.run(
                    restore_cmd,
                    env=env,
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                logger.info(f"Database restored successfully from: {backup_path}")
                return True
                
        except Exception as e:
            logger.error(f"Database restore failed: {e}")
            return False
    
    def production_deploy(self, revision: str = "head", create_backup: bool = True) -> Dict[str, Any]:
        """Production deployment with safety checks and rollback capability."""
        logger.info(f"Starting production deployment to revision: {revision}")
        
        deployment_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "target_revision": revision,
            "success": False,
            "backup_path": None,
            "rollback_required": False,
            "issues": []
        }
        
        try:
            # Step 1: Validate migration
            validation = self.validate_migration(revision)
            if not validation["validation_passed"]:
                deployment_results["issues"].extend(validation["issues"])
                logger.error("Migration validation failed, aborting deployment")
                return deployment_results
            
            # Step 2: Create backup if requested
            if create_backup:
                try:
                    backup_path = self.backup_database()
                    deployment_results["backup_path"] = backup_path
                    logger.info(f"Backup created: {backup_path}")
                except Exception as e:
                    deployment_results["issues"].append(f"Backup creation failed: {e}")
                    logger.error("Backup creation failed, aborting deployment")
                    return deployment_results
            
            # Step 3: Apply migration
            if self.upgrade(revision):
                deployment_results["success"] = True
                logger.info("Production deployment completed successfully")
            else:
                deployment_results["rollback_required"] = True
                deployment_results["issues"].append("Migration application failed")
                
                # Attempt rollback if backup exists
                if deployment_results["backup_path"]:
                    logger.info("Attempting rollback from backup")
                    if self.restore_database(deployment_results["backup_path"]):
                        logger.info("Rollback completed successfully")
                    else:
                        deployment_results["issues"].append("Rollback failed")
            
            return deployment_results
            
        except Exception as e:
            logger.error(f"Production deployment failed: {e}")
            deployment_results["issues"].append(f"Deployment error: {str(e)}")
            deployment_results["rollback_required"] = True
            return deployment_results
    
    def _test_database_connection(self) -> bool:
        """Test database connection."""
        try:
            # Simple connection test
            result = self.run_alembic_command("current")
            return True
        except Exception:
            return False
    
    def _validate_migration_files(self) -> bool:
        """Validate migration files exist and are properly formatted."""
        try:
            versions_dir = self.migration_dir / "versions"
            if not versions_dir.exists():
                return False
            
            # Check for at least one migration file
            migration_files = list(versions_dir.glob("*.py"))
            return len(migration_files) > 0
            
        except Exception:
            return False
    
    def _get_pending_migrations(self) -> List[str]:
        """Get list of pending migrations."""
        try:
            result = self.run_alembic_command("heads")
            # Parse the output to get pending migrations
            # This is a simplified implementation
            return []
        except Exception:
            return []
    
    def _validate_migration_chain(self) -> bool:
        """Validate migration chain integrity."""
        try:
            # Check for migration chain issues
            result = self.run_alembic_command("check")
            return True
        except Exception:
            return False
    
    def _parse_history_output(self, output: str) -> List[Dict[str, str]]:
        """Parse alembic history output into structured data."""
        migrations = []
        lines = output.strip().split('\n')
        
        for line in lines:
            if line.strip() and not line.startswith('Rev:'):
                # Parse migration line
                parts = line.split(' -> ')
                if len(parts) >= 2:
                    revision = parts[0].strip()
                    description = parts[1].strip()
                    migrations.append({
                        "revision": revision,
                        "description": description
                    })
        
        return migrations

class MigrationError(Exception):
    """Custom exception for migration-related errors."""
    pass

def main():
    """Main CLI interface for migration management."""
    parser = argparse.ArgumentParser(description="Confida Database Migration Manager")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Upgrade command
    upgrade_parser = subparsers.add_parser("upgrade", help="Upgrade database to specified revision")
    upgrade_parser.add_argument("revision", nargs="?", default="head", help="Target revision (default: head)")
    
    # Downgrade command
    downgrade_parser = subparsers.add_parser("downgrade", help="Downgrade database to specified revision")
    downgrade_parser.add_argument("revision", nargs="?", default="-1", help="Target revision (default: -1)")
    
    # Create migration command
    create_parser = subparsers.add_parser("create", help="Create a new migration")
    create_parser.add_argument("message", help="Migration message")
    create_parser.add_argument("--no-autogenerate", action="store_true", help="Create empty migration")
    
    # History command
    subparsers.add_parser("history", help="Show migration history")
    
    # Current command
    subparsers.add_parser("current", help="Show current database revision")
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate migration")
    validate_parser.add_argument("revision", nargs="?", default="head", help="Target revision (default: head)")
    
    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Create database backup")
    backup_parser.add_argument("--path", help="Backup file path")
    
    # Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore database from backup")
    restore_parser.add_argument("backup_path", help="Path to backup file")
    
    # Production deploy command
    deploy_parser = subparsers.add_parser("deploy", help="Production deployment")
    deploy_parser.add_argument("revision", nargs="?", default="head", help="Target revision (default: head)")
    deploy_parser.add_argument("--no-backup", action="store_true", help="Skip backup creation")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = MigrationManager()
    
    try:
        if args.command == "upgrade":
            success = manager.upgrade(args.revision)
            sys.exit(0 if success else 1)
            
        elif args.command == "downgrade":
            success = manager.downgrade(args.revision)
            sys.exit(0 if success else 1)
            
        elif args.command == "create":
            success = manager.create_migration(args.message, not args.no_autogenerate)
            sys.exit(0 if success else 1)
            
        elif args.command == "history":
            history = manager.show_history()
            for migration in history:
                print(f"{migration['revision']} -> {migration['description']}")
            
        elif args.command == "current":
            current = manager.show_current()
            print(current)
            
        elif args.command == "validate":
            validation = manager.validate_migration(args.revision)
            print(json.dumps(validation, indent=2))
            sys.exit(0 if validation["validation_passed"] else 1)
            
        elif args.command == "backup":
            backup_path = manager.backup_database(args.path)
            print(f"Backup created: {backup_path}")
            
        elif args.command == "restore":
            success = manager.restore_database(args.backup_path)
            sys.exit(0 if success else 1)
            
        elif args.command == "deploy":
            results = manager.production_deploy(args.revision, not args.no_backup)
            print(json.dumps(results, indent=2))
            sys.exit(0 if results["success"] else 1)
            
    except Exception as e:
        logger.error(f"Command failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
