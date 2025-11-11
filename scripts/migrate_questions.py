#!/usr/bin/env python3
"""
Question Bank Data Migration Script

This script migrates any existing session-bound questions to the global question bank structure.
Since the schema migration (7b15fd9db179) already removed session_id from questions table,
this script handles edge cases and ensures data integrity.

Note: This script is safe to run multiple times - it will skip already migrated questions.
"""

import os
import sys
import json
import uuid
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from sqlalchemy import create_engine, select, text, func
from sqlalchemy.exc import IntegrityError

from app.database.models import (
    Question, SessionQuestion, InterviewSession, Answer
)
from app.services.database_service import get_db
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

class QuestionDataMigration:
    """Handles migration of existing questions to the global question bank."""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.migration_stats = {
            "questions_migrated": 0,
            "sessions_updated": 0,
            "duplicates_skipped": 0,
            "errors": 0,
            "orphaned_questions_found": 0
        }
    
    def migrate_existing_questions(self) -> Dict[str, Any]:
        """
        Migrate existing questions to the global question bank.
        
        Since the schema migration already happened, this script:
        1. Checks for any orphaned questions (questions without session_questions links)
        2. Ensures all questions have proper metadata
        3. Validates data integrity
        """
        logger.info("🔄 Starting question bank data migration...")
        
        try:
            # Check current state
            total_questions = self.db_session.execute(
                select(func.count(Question.id))
            ).scalar()
            
            total_session_questions = self.db_session.execute(
                select(func.count(SessionQuestion.id))
            ).scalar()
            
            logger.info(f"📊 Current state:")
            logger.info(f"  - Total questions in bank: {total_questions}")
            logger.info(f"  - Total session-question links: {total_session_questions}")
            
            # Check for questions without proper metadata
            from sqlalchemy import or_
            questions_without_metadata = self.db_session.execute(
                select(Question).where(
                    or_(
                        Question.question_metadata == {},
                        Question.question_metadata.is_(None)
                    )
                )
            ).scalars().all()
            
            if questions_without_metadata:
                logger.info(f"Found {len(questions_without_metadata)} questions without metadata - updating...")
                for question in questions_without_metadata:
                    self._update_question_metadata(question)
                    self.migration_stats["questions_migrated"] += 1
            
            # Validate data integrity
            self._validate_data_integrity()
            
            # Update session statistics
            self._update_session_statistics()
            
            logger.info("✅ Question migration completed successfully!")
            logger.info("📊 Migration Statistics:")
            for key, value in self.migration_stats.items():
                logger.info(f"  {key}: {value}")
            
            return self.migration_stats
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            self.db_session.rollback()
            raise
    
    def _update_question_metadata(self, question: Question) -> None:
        """Update question metadata if missing."""
        if not question.question_metadata or question.question_metadata == {}:
            question.question_metadata = {
                "source": "migration",
                "migration_timestamp": datetime.utcnow().isoformat(),
                "version": "1.0"
            }
            
            # Try to infer category if missing
            if not question.category or question.category == "general":
                question.category = self._infer_category(question.question_text)
            
            # Try to infer subcategory if missing
            if not question.subcategory:
                question.subcategory = self._infer_subcategory(question.question_text, question.category)
            
            # Generate prompt hash if missing
            if not question.generation_prompt_hash:
                question.generation_prompt_hash = self._generate_prompt_hash(question.question_text)
            
            self.db_session.add(question)
    
    def _infer_category(self, question_text: str) -> str:
        """Infer category from question text."""
        text_lower = question_text.lower()
        
        if any(keyword in text_lower for keyword in ["design", "architecture", "system", "scale", "distributed"]):
            return "system_design"
        elif any(keyword in text_lower for keyword in ["tell me", "describe", "time when", "situation"]):
            return "behavioral"
        elif any(keyword in text_lower for keyword in ["lead", "manage", "team", "stakeholder"]):
            return "leadership"
        elif any(keyword in text_lower for keyword in ["python", "javascript", "java", "sql", "algorithm", "code"]):
            return "technical"
        else:
            return "general"
    
    def _infer_subcategory(self, question_text: str, category: str) -> Optional[str]:
        """Infer subcategory from question text and category."""
        text_lower = question_text.lower()
        
        if category == "technical":
            if any(keyword in text_lower for keyword in ["python", "django", "flask"]):
                return "python"
            elif any(keyword in text_lower for keyword in ["javascript", "react", "node", "js"]):
                return "javascript"
            elif any(keyword in text_lower for keyword in ["java", "spring"]):
                return "java"
            elif any(keyword in text_lower for keyword in ["sql", "database", "query"]):
                return "database"
            elif any(keyword in text_lower for keyword in ["algorithm", "data structure", "sort", "search"]):
                return "algorithms"
        
        elif category == "behavioral":
            if any(keyword in text_lower for keyword in ["conflict", "difficult", "challenge"]):
                return "conflict_resolution"
            elif any(keyword in text_lower for keyword in ["learn", "improve", "growth"]):
                return "learning_agility"
            elif any(keyword in text_lower for keyword in ["fail", "mistake", "error"]):
                return "resilience"
            elif any(keyword in text_lower for keyword in ["decision", "choose", "prioritize"]):
                return "decision_making"
        
        elif category == "system_design":
            if any(keyword in text_lower for keyword in ["url", "shortener", "bit.ly"]):
                return "web_services"
            elif any(keyword in text_lower for keyword in ["chat", "messaging", "real-time"]):
                return "real_time_systems"
            elif any(keyword in text_lower for keyword in ["cache", "distributed"]):
                return "distributed_systems"
        
        return None
    
    def _generate_prompt_hash(self, question_text: str) -> str:
        """Generate a hash for the question text."""
        return hashlib.sha256(question_text.encode()).hexdigest()[:16]
    
    def _validate_data_integrity(self) -> None:
        """Validate data integrity after migration."""
        logger.info("🔍 Validating data integrity...")
        
        # Check for questions without session links (orphaned questions)
        # These are questions that exist but aren't linked to any session
        all_questions = self.db_session.execute(select(Question)).scalars().all()
        all_session_question_ids = self.db_session.execute(
            select(SessionQuestion.question_id).distinct()
        ).scalars().all()
        
        orphaned_count = 0
        for question in all_questions:
            if question.id not in all_session_question_ids:
                orphaned_count += 1
                logger.warning(f"Found orphaned question: {question.id} - {question.question_text[:50]}...")
        
        if orphaned_count > 0:
            self.migration_stats["orphaned_questions_found"] = orphaned_count
            logger.warning(f"⚠️  Found {orphaned_count} orphaned questions (not linked to any session)")
            logger.info("   These questions are still valid in the global bank and can be used for future sessions")
        
        # Check for session_questions without valid question references
        invalid_links = self.db_session.execute(
            select(SessionQuestion).where(
                ~SessionQuestion.question_id.in_(select(Question.id))
            )
        ).scalars().all()
        
        if invalid_links:
            logger.error(f"❌ Found {len(invalid_links)} invalid session-question links!")
            for link in invalid_links:
                logger.error(f"   Session {link.session_id} references non-existent question {link.question_id}")
            raise IntegrityError("Invalid session-question links found", None, None)
        
        logger.info("✅ Data integrity validation passed")
    
    def _update_session_statistics(self) -> None:
        """Update session statistics after migration."""
        logger.info("📊 Updating session statistics...")
        
        sessions = self.db_session.execute(select(InterviewSession)).scalars().all()
        
        for session in sessions:
            # Count questions linked to this session
            question_count = self.db_session.execute(
                select(func.count(SessionQuestion.id)).where(
                    SessionQuestion.session_id == session.id
                )
            ).scalar()
            
            if session.total_questions != question_count:
                logger.debug(f"Updating session {session.id}: {session.total_questions} -> {question_count} questions")
                session.total_questions = question_count
                self.migration_stats["sessions_updated"] += 1
        
        self.db_session.commit()
        logger.info(f"✅ Updated {self.migration_stats['sessions_updated']} session statistics")

def main():
    """Main function to run migration."""
    logger.info("🚀 Starting Question Bank Data Migration...")
    
    try:
        settings = get_settings()
        engine = create_engine(settings.DATABASE_URL)
        
        with Session(engine) as db:
            migrator = QuestionDataMigration(db)
            stats = migrator.migrate_existing_questions()
            
            logger.info("🎉 Migration completed successfully!")
            return stats
        
    except Exception as e:
        logger.error(f"❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

