"""
Migration Validation Utilities

This module provides utilities for validating question bank migrations
and ensuring data integrity.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, func, text, and_, or_
from sqlalchemy.exc import SQLAlchemyError

from app.database.models import Question, SessionQuestion, InterviewSession, Answer
from app.utils.logger import get_logger

logger = get_logger(__name__)

class MigrationValidator:
    """Validates question bank migration and data integrity."""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.validation_results = {
            "total_questions": 0,
            "total_sessions": 0,
            "total_session_questions": 0,
            "data_integrity_check": {},
            "performance_impact": {},
            "rollback_required": False,
            "issues": [],
            "warnings": []
        }
    
    def validate_migration(self) -> Dict[str, Any]:
        """
        Validate the migration was successful.
        
        Returns:
            Dictionary with validation results
        """
        logger.info("🔍 Starting migration validation...")
        
        try:
            # Count basic statistics
            self._count_statistics()
            
            # Check data integrity
            self._check_data_integrity()
            
            # Measure performance impact
            self._measure_performance_impact()
            
            # Determine if rollback is required
            self._determine_rollback_requirement()
            
            logger.info("✅ Migration validation completed")
            return self.validation_results
            
        except Exception as e:
            logger.error(f"❌ Validation failed: {e}")
            self.validation_results["rollback_required"] = True
            self.validation_results["issues"].append(f"Validation error: {str(e)}")
            raise
    
    def _count_statistics(self) -> None:
        """Count basic statistics about the question bank."""
        logger.info("📊 Counting statistics...")
        
        # Count questions
        self.validation_results["total_questions"] = self.db_session.execute(
            select(func.count(Question.id))
        ).scalar()
        
        # Count sessions
        self.validation_results["total_sessions"] = self.db_session.execute(
            select(func.count(InterviewSession.id))
        ).scalar()
        
        # Count session-question links
        self.validation_results["total_session_questions"] = self.db_session.execute(
            select(func.count(SessionQuestion.id))
        ).scalar()
        
        logger.info(f"  Total questions: {self.validation_results['total_questions']}")
        logger.info(f"  Total sessions: {self.validation_results['total_sessions']}")
        logger.info(f"  Total session-question links: {self.validation_results['total_session_questions']}")
    
    def _check_data_integrity(self) -> None:
        """Check for data integrity issues after migration."""
        logger.info("🔍 Checking data integrity...")
        
        integrity_results = {
            "failed": False,
            "issues": [],
            "warnings": []
        }
        
        # Check for orphaned questions (questions not linked to any session)
        orphaned_questions = self._find_orphaned_questions()
        if orphaned_questions:
            integrity_results["warnings"].append(
                f"Found {len(orphaned_questions)} orphaned questions (not linked to any session)"
            )
            logger.warning(f"⚠️  Found {len(orphaned_questions)} orphaned questions")
            # Note: Orphaned questions are not necessarily a problem - they can be used for future sessions
        
        # Check for invalid session-question links
        invalid_links = self._find_invalid_session_question_links()
        if invalid_links:
            integrity_results["failed"] = True
            integrity_results["issues"].append(
                f"Found {len(invalid_links)} invalid session-question links"
            )
            logger.error(f"❌ Found {len(invalid_links)} invalid session-question links!")
            for link in invalid_links[:5]:  # Show first 5
                logger.error(f"   Session {link.session_id} references non-existent question {link.question_id}")
        
        # Check for questions without required fields
        incomplete_questions = self._find_incomplete_questions()
        if incomplete_questions:
            integrity_results["warnings"].append(
                f"Found {len(incomplete_questions)} questions with missing required fields"
            )
            logger.warning(f"⚠️  Found {len(incomplete_questions)} incomplete questions")
        
        # Check for duplicate questions
        duplicate_questions = self._find_duplicate_questions()
        if duplicate_questions:
            integrity_results["warnings"].append(
                f"Found {len(duplicate_questions)} potential duplicate questions"
            )
            logger.warning(f"⚠️  Found {len(duplicate_questions)} potential duplicates")
        
        # Check for questions without metadata
        questions_without_metadata = self._find_questions_without_metadata()
        if questions_without_metadata:
            integrity_results["warnings"].append(
                f"Found {len(questions_without_metadata)} questions without metadata"
            )
            logger.warning(f"⚠️  Found {len(questions_without_metadata)} questions without metadata")
        
        self.validation_results["data_integrity_check"] = integrity_results
        self.validation_results["issues"].extend(integrity_results["issues"])
        self.validation_results["warnings"].extend(integrity_results["warnings"])
    
    def _find_orphaned_questions(self) -> List[Question]:
        """Find questions that are not linked to any session."""
        all_questions = self.db_session.execute(select(Question)).scalars().all()
        linked_question_ids = self.db_session.execute(
            select(SessionQuestion.question_id).distinct()
        ).scalars().all()
        
        orphaned = [q for q in all_questions if q.id not in linked_question_ids]
        return orphaned
    
    def _find_invalid_session_question_links(self) -> List[SessionQuestion]:
        """Find session-question links that reference non-existent questions."""
        all_question_ids = self.db_session.execute(
            select(Question.id)
        ).scalars().all()
        
        invalid_links = self.db_session.execute(
            select(SessionQuestion).where(
                ~SessionQuestion.question_id.in_(all_question_ids)
            )
        ).scalars().all()
        
        return invalid_links
    
    def _find_incomplete_questions(self) -> List[Question]:
        """Find questions with missing required fields."""
        incomplete = self.db_session.execute(
            select(Question).where(
                or_(
                    Question.question_text.is_(None),
                    Question.category.is_(None),
                    Question.difficulty_level.is_(None)
                )
            )
        ).scalars().all()
        
        return incomplete
    
    def _find_duplicate_questions(self) -> List[Question]:
        """Find potential duplicate questions (same text)."""
        # Find questions with duplicate text
        duplicates = self.db_session.execute(
            select(Question.question_text, func.count(Question.id))
            .group_by(Question.question_text)
            .having(func.count(Question.id) > 1)
        ).all()
        
        duplicate_questions = []
        for question_text, count in duplicates:
            questions = self.db_session.execute(
                select(Question).where(Question.question_text == question_text)
            ).scalars().all()
            duplicate_questions.extend(questions)
        
        return duplicate_questions
    
    def _find_questions_without_metadata(self) -> List[Question]:
        """Find questions without metadata."""
        questions = self.db_session.execute(
            select(Question).where(
                or_(
                    Question.question_metadata.is_(None),
                    Question.question_metadata == {}
                )
            )
        ).scalars().all()
        
        return questions
    
    def _measure_performance_impact(self) -> None:
        """Measure performance impact of migration."""
        logger.info("⚡ Measuring performance impact...")
        
        performance_results = {
            "average_query_time": None,
            "index_usage": {},
            "query_count": 0
        }
        
        try:
            # Test query performance
            start_time = datetime.now()
            
            # Test basic question query
            questions = self.db_session.execute(
                select(Question).limit(100)
            ).scalars().all()
            
            query_time = (datetime.now() - start_time).total_seconds() * 1000  # milliseconds
            performance_results["average_query_time"] = query_time
            performance_results["query_count"] = len(questions)
            
            logger.info(f"  Average query time: {query_time:.2f}ms")
            logger.info(f"  Queried {len(questions)} questions")
            
        except Exception as e:
            logger.warning(f"⚠️  Could not measure performance: {e}")
            performance_results["error"] = str(e)
        
        self.validation_results["performance_impact"] = performance_results
    
    def _determine_rollback_requirement(self) -> None:
        """Determine if rollback is required based on validation results."""
        integrity_check = self.validation_results.get("data_integrity_check", {})
        
        # Rollback required if there are critical issues
        if integrity_check.get("failed", False):
            self.validation_results["rollback_required"] = True
            logger.error("❌ Rollback required due to critical data integrity issues")
        elif len(self.validation_results.get("issues", [])) > 0:
            self.validation_results["rollback_required"] = True
            logger.warning("⚠️  Rollback recommended due to issues found")
        else:
            self.validation_results["rollback_required"] = False
            logger.info("✅ No rollback required - migration successful")
    
    def generate_validation_report(self) -> str:
        """Generate a human-readable validation report."""
        report = []
        report.append("=" * 60)
        report.append("QUESTION BANK MIGRATION VALIDATION REPORT")
        report.append("=" * 60)
        report.append(f"Generated: {datetime.utcnow().isoformat()}")
        report.append("")
        
        # Statistics
        report.append("📊 STATISTICS")
        report.append("-" * 60)
        report.append(f"Total Questions: {self.validation_results['total_questions']}")
        report.append(f"Total Sessions: {self.validation_results['total_sessions']}")
        report.append(f"Total Session-Question Links: {self.validation_results['total_session_questions']}")
        report.append("")
        
        # Data Integrity
        report.append("🔍 DATA INTEGRITY")
        report.append("-" * 60)
        integrity = self.validation_results.get("data_integrity_check", {})
        if integrity.get("failed", False):
            report.append("Status: ❌ FAILED")
        else:
            report.append("Status: ✅ PASSED")
        
        if integrity.get("issues"):
            report.append("\nIssues:")
            for issue in integrity["issues"]:
                report.append(f"  ❌ {issue}")
        
        if integrity.get("warnings"):
            report.append("\nWarnings:")
            for warning in integrity["warnings"]:
                report.append(f"  ⚠️  {warning}")
        report.append("")
        
        # Performance
        report.append("⚡ PERFORMANCE")
        report.append("-" * 60)
        performance = self.validation_results.get("performance_impact", {})
        if performance.get("average_query_time"):
            report.append(f"Average Query Time: {performance['average_query_time']:.2f}ms")
        report.append("")
        
        # Rollback Recommendation
        report.append("🔄 ROLLBACK RECOMMENDATION")
        report.append("-" * 60)
        if self.validation_results.get("rollback_required", False):
            report.append("Status: ⚠️  ROLLBACK RECOMMENDED")
            report.append("\nReasons:")
            for issue in self.validation_results.get("issues", []):
                report.append(f"  - {issue}")
        else:
            report.append("Status: ✅ NO ROLLBACK REQUIRED")
        report.append("")
        
        report.append("=" * 60)
        
        return "\n".join(report)
