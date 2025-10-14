"""
Migration Validation and Testing Utilities for InterviewIQ.

This module provides comprehensive validation and testing capabilities
for database migrations to ensure data integrity and system stability.
"""
import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

class MigrationValidator:
    """Comprehensive migration validation and testing system."""
    
    def __init__(self):
        self.settings = get_settings()
        self.project_root = Path(__file__).parent.parent.parent
        self.migration_dir = self.project_root / "app" / "database" / "migrations"
        
    def validate_migration_integrity(self, revision: str = "head") -> Dict[str, Any]:
        """Validate migration chain integrity and consistency."""
        logger.info(f"Validating migration integrity for revision: {revision}")
        
        validation_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "target_revision": revision,
            "validation_passed": True,
            "issues": [],
            "warnings": [],
            "checks_performed": []
        }
        
        try:
            # Check 1: Validate migration files exist and are properly formatted
            file_validation = self._validate_migration_files()
            validation_results["checks_performed"].append("migration_files")
            if not file_validation["valid"]:
                validation_results["validation_passed"] = False
                validation_results["issues"].extend(file_validation["issues"])
            
            # Check 2: Validate migration chain consistency
            chain_validation = self._validate_migration_chain()
            validation_results["checks_performed"].append("migration_chain")
            if not chain_validation["valid"]:
                validation_results["validation_passed"] = False
                validation_results["issues"].extend(chain_validation["issues"])
            
            # Check 3: Validate SQL syntax in migration files
            sql_validation = self._validate_migration_sql()
            validation_results["checks_performed"].append("sql_syntax")
            if not sql_validation["valid"]:
                validation_results["validation_passed"] = False
                validation_results["issues"].extend(sql_validation["issues"])
            
            # Check 4: Validate database connectivity
            connectivity_validation = self._validate_database_connectivity()
            validation_results["checks_performed"].append("database_connectivity")
            if not connectivity_validation["valid"]:
                validation_results["validation_passed"] = False
                validation_results["issues"].extend(connectivity_validation["issues"])
            
            # Check 5: Validate migration dependencies
            dependency_validation = self._validate_migration_dependencies()
            validation_results["checks_performed"].append("migration_dependencies")
            if not dependency_validation["valid"]:
                validation_results["validation_passed"] = False
                validation_results["issues"].extend(dependency_validation["issues"])
            
            logger.info(f"Migration integrity validation completed. Passed: {validation_results['validation_passed']}")
            return validation_results
            
        except Exception as e:
            logger.error(f"Migration integrity validation failed: {e}")
            validation_results["validation_passed"] = False
            validation_results["issues"].append(f"Validation error: {str(e)}")
            return validation_results
    
    def test_migration_on_clean_database(self, revision: str = "head") -> Dict[str, Any]:
        """Test migration on a clean test database."""
        logger.info(f"Testing migration on clean database for revision: {revision}")
        
        test_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "target_revision": revision,
            "test_passed": True,
            "issues": [],
            "test_database": None,
            "cleanup_required": False
        }
        
        test_db_name = None
        try:
            # Create temporary test database
            test_db_name = self._create_test_database()
            test_results["test_database"] = test_db_name
            test_results["cleanup_required"] = True
            
            # Run migration on test database
            migration_success = self._run_migration_on_database(test_db_name, revision)
            if not migration_success:
                test_results["test_passed"] = False
                test_results["issues"].append("Migration failed on test database")
                return test_results
            
            # Validate schema after migration
            schema_validation = self._validate_schema_on_database(test_db_name)
            if not schema_validation["valid"]:
                test_results["test_passed"] = False
                test_results["issues"].extend(schema_validation["issues"])
            
            # Test rollback functionality
            rollback_success = self._test_rollback_on_database(test_db_name)
            if not rollback_success:
                test_results["test_passed"] = False
                test_results["issues"].append("Rollback test failed")
            
            logger.info(f"Clean database migration test completed. Passed: {test_results['test_passed']}")
            return test_results
            
        except Exception as e:
            logger.error(f"Clean database migration test failed: {e}")
            test_results["test_passed"] = False
            test_results["issues"].append(f"Test error: {str(e)}")
            return test_results
            
        finally:
            # Cleanup test database
            if test_db_name and test_results["cleanup_required"]:
                self._cleanup_test_database(test_db_name)
    
    def validate_data_integrity_after_migration(self, revision: str = "head") -> Dict[str, Any]:
        """Validate data integrity after migration."""
        logger.info(f"Validating data integrity after migration to revision: {revision}")
        
        integrity_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "target_revision": revision,
            "integrity_passed": True,
            "issues": [],
            "data_checks": []
        }
        
        try:
            # Check 1: Validate foreign key constraints
            fk_validation = self._validate_foreign_key_constraints()
            integrity_results["data_checks"].append("foreign_key_constraints")
            if not fk_validation["valid"]:
                integrity_results["integrity_passed"] = False
                integrity_results["issues"].extend(fk_validation["issues"])
            
            # Check 2: Validate data consistency
            consistency_validation = self._validate_data_consistency()
            integrity_results["data_checks"].append("data_consistency")
            if not consistency_validation["valid"]:
                integrity_results["integrity_passed"] = False
                integrity_results["issues"].extend(consistency_validation["issues"])
            
            # Check 3: Validate index integrity
            index_validation = self._validate_index_integrity()
            integrity_results["data_checks"].append("index_integrity")
            if not index_validation["valid"]:
                integrity_results["integrity_passed"] = False
                integrity_results["issues"].extend(index_validation["issues"])
            
            # Check 4: Validate table structures
            table_validation = self._validate_table_structures()
            integrity_results["data_checks"].append("table_structures")
            if not table_validation["valid"]:
                integrity_results["integrity_passed"] = False
                integrity_results["issues"].extend(table_validation["issues"])
            
            logger.info(f"Data integrity validation completed. Passed: {integrity_results['integrity_passed']}")
            return integrity_results
            
        except Exception as e:
            logger.error(f"Data integrity validation failed: {e}")
            integrity_results["integrity_passed"] = False
            integrity_results["issues"].append(f"Integrity check error: {str(e)}")
            return integrity_results
    
    def performance_test_migration(self, revision: str = "head") -> Dict[str, Any]:
        """Test migration performance and impact."""
        logger.info(f"Performance testing migration to revision: {revision}")
        
        performance_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "target_revision": revision,
            "performance_passed": True,
            "issues": [],
            "metrics": {
                "migration_duration": None,
                "database_size_before": None,
                "database_size_after": None,
                "index_rebuild_time": None,
                "table_lock_duration": None
            }
        }
        
        try:
            # Measure database size before migration
            size_before = self._get_database_size()
            performance_results["metrics"]["database_size_before"] = size_before
            
            # Measure migration duration
            start_time = datetime.utcnow()
            migration_success = self._run_migration_with_timing(revision)
            end_time = datetime.utcnow()
            
            migration_duration = (end_time - start_time).total_seconds()
            performance_results["metrics"]["migration_duration"] = migration_duration
            
            if not migration_success:
                performance_results["performance_passed"] = False
                performance_results["issues"].append("Migration failed during performance test")
                return performance_results
            
            # Measure database size after migration
            size_after = self._get_database_size()
            performance_results["metrics"]["database_size_after"] = size_after
            
            # Check for performance regressions
            if migration_duration > 300:  # 5 minutes threshold
                performance_results["issues"].append(f"Migration took too long: {migration_duration}s")
            
            size_increase = size_after - size_before
            if size_increase > size_before * 0.5:  # 50% size increase threshold
                performance_results["issues"].append(f"Significant database size increase: {size_increase} bytes")
            
            logger.info(f"Performance test completed. Duration: {migration_duration}s")
            return performance_results
            
        except Exception as e:
            logger.error(f"Performance test failed: {e}")
            performance_results["performance_passed"] = False
            performance_results["issues"].append(f"Performance test error: {str(e)}")
            return performance_results
    
    def _validate_migration_files(self) -> Dict[str, Any]:
        """Validate migration files exist and are properly formatted."""
        validation = {"valid": True, "issues": []}
        
        try:
            versions_dir = self.migration_dir / "versions"
            if not versions_dir.exists():
                validation["valid"] = False
                validation["issues"].append("Migration versions directory does not exist")
                return validation
            
            migration_files = list(versions_dir.glob("*.py"))
            if not migration_files:
                validation["valid"] = False
                validation["issues"].append("No migration files found")
                return validation
            
            # Check each migration file for basic structure
            for file_path in migration_files:
                with open(file_path, 'r') as f:
                    content = f.read()
                    
                # Check for required elements
                if "def upgrade()" not in content:
                    validation["valid"] = False
                    validation["issues"].append(f"Missing upgrade() function in {file_path.name}")
                
                if "def downgrade()" not in content:
                    validation["valid"] = False
                    validation["issues"].append(f"Missing downgrade() function in {file_path.name}")
                
                if "revision" not in content:
                    validation["valid"] = False
                    validation["issues"].append(f"Missing revision ID in {file_path.name}")
            
            return validation
            
        except Exception as e:
            validation["valid"] = False
            validation["issues"].append(f"File validation error: {str(e)}")
            return validation
    
    def _validate_migration_chain(self) -> Dict[str, Any]:
        """Validate migration chain consistency."""
        validation = {"valid": True, "issues": []}
        
        try:
            # Run alembic check command
            result = subprocess.run(
                ["alembic", "check"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                validation["valid"] = False
                validation["issues"].append(f"Migration chain check failed: {result.stderr}")
            
            return validation
            
        except Exception as e:
            validation["valid"] = False
            validation["issues"].append(f"Chain validation error: {str(e)}")
            return validation
    
    def _validate_migration_sql(self) -> Dict[str, Any]:
        """Validate SQL syntax in migration files."""
        validation = {"valid": True, "issues": []}
        
        try:
            # This is a simplified validation - in production, you might want to use
            # a proper SQL parser or connect to a test database
            versions_dir = self.migration_dir / "versions"
            migration_files = list(versions_dir.glob("*.py"))
            
            for file_path in migration_files:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # Basic SQL syntax checks
                if "op.execute(" in content:
                    # Check for common SQL issues
                    if "DROP TABLE" in content and "CASCADE" not in content:
                        validation["issues"].append(f"Potential unsafe DROP TABLE in {file_path.name}")
                
                if "ALTER TABLE" in content and "ADD CONSTRAINT" in content:
                    # Check for constraint naming
                    if "CONSTRAINT" in content and "FOREIGN KEY" in content:
                        if not any(name in content for name in ["fk_", "constraint_"]):
                            validation["issues"].append(f"Unnamed constraint in {file_path.name}")
            
            return validation
            
        except Exception as e:
            validation["valid"] = False
            validation["issues"].append(f"SQL validation error: {str(e)}")
            return validation
    
    def _validate_database_connectivity(self) -> Dict[str, Any]:
        """Validate database connectivity."""
        validation = {"valid": True, "issues": []}
        
        try:
            # Test database connection
            engine = create_engine(self.settings.DATABASE_URL)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            
            return validation
            
        except Exception as e:
            validation["valid"] = False
            validation["issues"].append(f"Database connectivity error: {str(e)}")
            return validation
    
    def _validate_migration_dependencies(self) -> Dict[str, Any]:
        """Validate migration dependencies."""
        validation = {"valid": True, "issues": []}
        
        try:
            # Check for circular dependencies and missing dependencies
            versions_dir = self.migration_dir / "versions"
            migration_files = list(versions_dir.glob("*.py"))
            
            dependencies = {}
            for file_path in migration_files:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # Extract revision and down_revision
                lines = content.split('\n')
                revision = None
                down_revision = None
                
                for line in lines:
                    if line.startswith('revision'):
                        revision = line.split('=')[1].strip().strip("'\"")
                    elif line.startswith('down_revision'):
                        down_revision = line.split('=')[1].strip().strip("'\"")
                
                if revision:
                    dependencies[revision] = down_revision
            
            # Check for circular dependencies
            for rev, down_rev in dependencies.items():
                if down_rev and down_rev in dependencies:
                    if dependencies[down_rev] == rev:
                        validation["valid"] = False
                        validation["issues"].append(f"Circular dependency detected: {rev} <-> {down_rev}")
            
            return validation
            
        except Exception as e:
            validation["valid"] = False
            validation["issues"].append(f"Dependency validation error: {str(e)}")
            return validation
    
    def _create_test_database(self) -> str:
        """Create a temporary test database."""
        test_db_name = f"test_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Parse database URL to get connection details
        db_url = self.settings.DATABASE_URL
        if db_url.startswith("postgresql://"):
            # Extract connection details
            url_parts = db_url.replace("postgresql://", "").split("/")
            db_name = url_parts[1]
            auth_host = url_parts[0].split("@")
            auth = auth_host[0].split(":")
            host_port = auth_host[1].split(":")
            
            user = auth[0]
            password = auth[1] if len(auth) > 1 else ""
            host = host_port[0]
            port = host_port[1] if len(host_port) > 1 else "5432"
            
            # Connect to postgres database to create test database
            conn = psycopg2.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database="postgres"
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            
            cursor = conn.cursor()
            cursor.execute(f"CREATE DATABASE {test_db_name}")
            cursor.close()
            conn.close()
            
            return test_db_name
        
        raise Exception("Unsupported database type for test database creation")
    
    def _run_migration_on_database(self, db_name: str, revision: str) -> bool:
        """Run migration on specified database."""
        try:
            # Create temporary alembic.ini for test database
            test_db_url = self.settings.DATABASE_URL.replace(
                self.settings.DATABASE_URL.split("/")[-1], db_name
            )
            
            # Run migration
            env = os.environ.copy()
            env["DATABASE_URL"] = test_db_url
            
            result = subprocess.run(
                ["alembic", "upgrade", revision],
                cwd=self.project_root,
                env=env,
                capture_output=True,
                text=True,
                check=False
            )
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Failed to run migration on test database: {e}")
            return False
    
    def _validate_schema_on_database(self, db_name: str) -> Dict[str, Any]:
        """Validate schema on test database."""
        validation = {"valid": True, "issues": []}
        
        try:
            test_db_url = self.settings.DATABASE_URL.replace(
                self.settings.DATABASE_URL.split("/")[-1], db_name
            )
            
            engine = create_engine(test_db_url)
            with engine.connect() as conn:
                # Check if all expected tables exist
                result = conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """))
                tables = [row[0] for row in result.fetchall()]
                
                expected_tables = ["users", "interview_sessions", "questions", "session_questions", "answers"]
                for table in expected_tables:
                    if table not in tables:
                        validation["valid"] = False
                        validation["issues"].append(f"Missing table: {table}")
            
            return validation
            
        except Exception as e:
            validation["valid"] = False
            validation["issues"].append(f"Schema validation error: {str(e)}")
            return validation
    
    def _test_rollback_on_database(self, db_name: str) -> bool:
        """Test rollback functionality on test database."""
        try:
            test_db_url = self.settings.DATABASE_URL.replace(
                self.settings.DATABASE_URL.split("/")[-1], db_name
            )
            
            env = os.environ.copy()
            env["DATABASE_URL"] = test_db_url
            
            # Try to rollback one step
            result = subprocess.run(
                ["alembic", "downgrade", "-1"],
                cwd=self.project_root,
                env=env,
                capture_output=True,
                text=True,
                check=False
            )
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Rollback test failed: {e}")
            return False
    
    def _cleanup_test_database(self, db_name: str):
        """Clean up test database."""
        try:
            # Parse database URL to get connection details
            db_url = self.settings.DATABASE_URL
            if db_url.startswith("postgresql://"):
                url_parts = db_url.replace("postgresql://", "").split("/")
                auth_host = url_parts[0].split("@")
                auth = auth_host[0].split(":")
                host_port = auth_host[1].split(":")
                
                user = auth[0]
                password = auth[1] if len(auth) > 1 else ""
                host = host_port[0]
                port = host_port[1] if len(host_port) > 1 else "5432"
                
                # Connect to postgres database to drop test database
                conn = psycopg2.connect(
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    database="postgres"
                )
                conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
                
                cursor = conn.cursor()
                cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")
                cursor.close()
                conn.close()
                
                logger.info(f"Test database {db_name} cleaned up successfully")
                
        except Exception as e:
            logger.error(f"Failed to cleanup test database {db_name}: {e}")
    
    def _validate_foreign_key_constraints(self) -> Dict[str, Any]:
        """Validate foreign key constraints."""
        validation = {"valid": True, "issues": []}
        
        try:
            engine = create_engine(self.settings.DATABASE_URL)
            with engine.connect() as conn:
                # Check for orphaned records
                result = conn.execute(text("""
                    SELECT 
                        tc.table_name, 
                        kcu.column_name, 
                        ccu.table_name AS foreign_table_name,
                        ccu.column_name AS foreign_column_name 
                    FROM 
                        information_schema.table_constraints AS tc 
                        JOIN information_schema.key_column_usage AS kcu
                          ON tc.constraint_name = kcu.constraint_name
                        JOIN information_schema.constraint_column_usage AS ccu
                          ON ccu.constraint_name = tc.constraint_name
                    WHERE constraint_type = 'FOREIGN KEY'
                """))
                
                fk_constraints = result.fetchall()
                
                for constraint in fk_constraints:
                    table_name, column_name, foreign_table, foreign_column = constraint
                    
                    # Check for orphaned records
                    orphan_check = conn.execute(text(f"""
                        SELECT COUNT(*) 
                        FROM {table_name} t1 
                        LEFT JOIN {foreign_table} t2 ON t1.{column_name} = t2.{foreign_column}
                        WHERE t1.{column_name} IS NOT NULL AND t2.{foreign_column} IS NULL
                    """))
                    
                    orphan_count = orphan_check.fetchone()[0]
                    if orphan_count > 0:
                        validation["valid"] = False
                        validation["issues"].append(f"Found {orphan_count} orphaned records in {table_name}.{column_name}")
            
            return validation
            
        except Exception as e:
            validation["valid"] = False
            validation["issues"].append(f"Foreign key validation error: {str(e)}")
            return validation
    
    def _validate_data_consistency(self) -> Dict[str, Any]:
        """Validate data consistency."""
        validation = {"valid": True, "issues": []}
        
        try:
            engine = create_engine(self.settings.DATABASE_URL)
            with engine.connect() as conn:
                # Check for data consistency issues
                # Example: Check if session questions reference valid questions
                result = conn.execute(text("""
                    SELECT COUNT(*) 
                    FROM session_questions sq 
                    LEFT JOIN questions q ON sq.question_id = q.id 
                    WHERE q.id IS NULL
                """))
                
                invalid_references = result.fetchone()[0]
                if invalid_references > 0:
                    validation["valid"] = False
                    validation["issues"].append(f"Found {invalid_references} invalid question references in session_questions")
            
            return validation
            
        except Exception as e:
            validation["valid"] = False
            validation["issues"].append(f"Data consistency validation error: {str(e)}")
            return validation
    
    def _validate_index_integrity(self) -> Dict[str, Any]:
        """Validate index integrity."""
        validation = {"valid": True, "issues": []}
        
        try:
            engine = create_engine(self.settings.DATABASE_URL)
            with engine.connect() as conn:
                # Check for missing indexes on foreign keys
                result = conn.execute(text("""
                    SELECT 
                        tc.table_name, 
                        kcu.column_name
                    FROM 
                        information_schema.table_constraints AS tc 
                        JOIN information_schema.key_column_usage AS kcu
                          ON tc.constraint_name = kcu.constraint_name
                    WHERE constraint_type = 'FOREIGN KEY'
                """))
                
                fk_columns = result.fetchall()
                
                for table_name, column_name in fk_columns:
                    # Check if index exists on foreign key column
                    index_check = conn.execute(text(f"""
                        SELECT COUNT(*) 
                        FROM pg_indexes 
                        WHERE tablename = '{table_name}' 
                        AND indexdef LIKE '%{column_name}%'
                    """))
                    
                    index_count = index_check.fetchone()[0]
                    if index_count == 0:
                        validation["issues"].append(f"Missing index on foreign key {table_name}.{column_name}")
            
            return validation
            
        except Exception as e:
            validation["valid"] = False
            validation["issues"].append(f"Index validation error: {str(e)}")
            return validation
    
    def _validate_table_structures(self) -> Dict[str, Any]:
        """Validate table structures."""
        validation = {"valid": True, "issues": []}
        
        try:
            engine = create_engine(self.settings.DATABASE_URL)
            with engine.connect() as conn:
                # Check for required tables and columns
                expected_structure = {
                    "users": ["id", "email", "name", "password_hash"],
                    "interview_sessions": ["id", "user_id", "role", "status"],
                    "questions": ["id", "question_text", "category", "difficulty_level"],
                    "session_questions": ["id", "session_id", "question_id", "question_order"],
                    "answers": ["id", "question_id", "answer_text"]
                }
                
                for table_name, expected_columns in expected_structure.items():
                    # Check if table exists
                    table_check = conn.execute(text(f"""
                        SELECT COUNT(*) 
                        FROM information_schema.tables 
                        WHERE table_name = '{table_name}' AND table_schema = 'public'
                    """))
                    
                    if table_check.fetchone()[0] == 0:
                        validation["valid"] = False
                        validation["issues"].append(f"Missing table: {table_name}")
                        continue
                    
                    # Check if required columns exist
                    for column_name in expected_columns:
                        column_check = conn.execute(text(f"""
                            SELECT COUNT(*) 
                            FROM information_schema.columns 
                            WHERE table_name = '{table_name}' 
                            AND column_name = '{column_name}' 
                            AND table_schema = 'public'
                        """))
                        
                        if column_check.fetchone()[0] == 0:
                            validation["valid"] = False
                            validation["issues"].append(f"Missing column: {table_name}.{column_name}")
            
            return validation
            
        except Exception as e:
            validation["valid"] = False
            validation["issues"].append(f"Table structure validation error: {str(e)}")
            return validation
    
    def _get_database_size(self) -> int:
        """Get current database size in bytes."""
        try:
            engine = create_engine(self.settings.DATABASE_URL)
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT pg_database_size(current_database())
                """))
                return result.fetchone()[0]
        except Exception as e:
            logger.error(f"Failed to get database size: {e}")
            return 0
    
    def _run_migration_with_timing(self, revision: str) -> bool:
        """Run migration with timing measurement."""
        try:
            start_time = datetime.utcnow()
            result = subprocess.run(
                ["alembic", "upgrade", revision],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=False
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Migration with timing failed: {e}")
            return False
