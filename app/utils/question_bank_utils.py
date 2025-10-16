"""
Question Bank Utilities

Shared utilities for question bank operations to eliminate duplication
between question_bank_validator.py and question_bank_cli.py
"""
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.database.models import Question, SessionQuestion
from app.utils.logger import get_logger

logger = get_logger(__name__)


class QuestionBankUtils:
    """Shared utilities for question bank operations."""
    
    @staticmethod
    def find_duplicate_questions(db: Session) -> List[Tuple[str, int]]:
        """
        Find duplicate questions in the database.
        
        Returns:
            List of tuples (question_text, count) for duplicate questions
        """
        try:
            duplicates = db.execute(
                select(Question.question_text, func.count(Question.id))
                .group_by(Question.question_text)
                .having(func.count(Question.id) > 1)
            ).fetchall()
            
            return [(question_text, count) for question_text, count in duplicates]
            
        except Exception as e:
            logger.error(f"Error finding duplicate questions: {e}")
            return []
    
    @staticmethod
    def get_duplicate_question_instances(db: Session, question_text: str) -> List[Question]:
        """
        Get all instances of a duplicate question, ordered by creation date.
        
        Args:
            db: Database session
            question_text: The duplicate question text
            
        Returns:
            List of Question instances ordered by created_at
        """
        try:
            return db.execute(
                select(Question).where(Question.question_text == question_text)
                .order_by(Question.created_at)
            ).scalars().all()
            
        except Exception as e:
            logger.error(f"Error getting duplicate question instances: {e}")
            return []
    
    @staticmethod
    def is_question_linked_to_sessions(db: Session, question_id: int) -> bool:
        """
        Check if a question is linked to any sessions.
        
        Args:
            db: Database session
            question_id: The question ID to check
            
        Returns:
            True if question is linked to sessions, False otherwise
        """
        try:
            session_links = db.execute(
                select(SessionQuestion).where(SessionQuestion.question_id == question_id)
            ).scalars().all()
            
            return len(session_links) > 0
            
        except Exception as e:
            logger.error(f"Error checking question session links: {e}")
            return True  # Assume linked to be safe
    
    @staticmethod
    def remove_duplicate_questions(db: Session, dry_run: bool = True) -> Dict[str, int]:
        """
        Remove duplicate questions, keeping the oldest instance.
        
        Args:
            db: Database session
            dry_run: If True, only log what would be done
            
        Returns:
            Dictionary with cleanup statistics
        """
        stats = {
            "duplicates_found": 0,
            "questions_removed": 0,
            "questions_skipped": 0,
            "errors": 0
        }
        
        try:
            # Find all duplicate questions
            duplicates = QuestionBankUtils.find_duplicate_questions(db)
            stats["duplicates_found"] = len(duplicates)
            
            if dry_run:
                logger.info(f"DRY RUN - Found {len(duplicates)} duplicate question groups")
                for question_text, count in duplicates:
                    logger.info(f"  '{question_text[:50]}...' appears {count} times")
                return stats
            
            # Process each duplicate group
            for question_text, count in duplicates:
                question_instances = QuestionBankUtils.get_duplicate_question_instances(db, question_text)
                
                # Keep the first one, remove the rest
                for question in question_instances[1:]:
                    try:
                        # Check if question is linked to any sessions
                        if QuestionBankUtils.is_question_linked_to_sessions(db, question.id):
                            logger.warning(f"Question {question.id} is linked to sessions, skipping removal")
                            stats["questions_skipped"] += 1
                            continue
                        
                        # Remove the duplicate question
                        db.delete(question)
                        stats["questions_removed"] += 1
                        
                    except Exception as e:
                        logger.error(f"Error removing duplicate question {question.id}: {e}")
                        stats["errors"] += 1
            
            # Commit changes if not dry run
            if not dry_run:
                db.commit()
                logger.info(f"✅ Cleanup completed. Removed {stats['questions_removed']} duplicate questions")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error in duplicate question cleanup: {e}")
            stats["errors"] += 1
            if not dry_run:
                db.rollback()
            return stats
    
    @staticmethod
    def fix_invalid_difficulty_levels(db: Session, dry_run: bool = True) -> Dict[str, int]:
        """
        Fix questions with invalid difficulty levels.
        
        Args:
            db: Database session
            dry_run: If True, only log what would be done
            
        Returns:
            Dictionary with fix statistics
        """
        stats = {
            "questions_updated": 0,
            "errors": 0
        }
        
        try:
            # Find questions with invalid difficulty levels
            valid_difficulties = ['easy', 'medium', 'hard']
            questions_with_invalid_difficulty = db.execute(
                select(Question).where(
                    Question.difficulty_level.notin_(valid_difficulties)
                )
            ).scalars().all()
            
            if dry_run:
                logger.info(f"DRY RUN - Found {len(questions_with_invalid_difficulty)} questions with invalid difficulty")
                return stats
            
            # Fix invalid difficulty levels
            for question in questions_with_invalid_difficulty:
                try:
                    question.difficulty_level = "medium"  # Default to medium
                    stats["questions_updated"] += 1
                except Exception as e:
                    logger.error(f"Error fixing difficulty for question {question.id}: {e}")
                    stats["errors"] += 1
            
            # Commit changes if not dry run
            if not dry_run:
                db.commit()
                logger.info(f"✅ Fixed {stats['questions_updated']} questions with invalid difficulty levels")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error fixing invalid difficulty levels: {e}")
            stats["errors"] += 1
            if not dry_run:
                db.rollback()
            return stats
    
    @staticmethod
    def get_question_bank_statistics(db: Session) -> Dict[str, Any]:
        """
        Get comprehensive question bank statistics.
        
        Args:
            db: Database session
            
        Returns:
            Dictionary with question bank statistics
        """
        try:
            # Total questions
            total_questions = db.execute(select(func.count(Question.id))).scalar()
            
            # Questions by difficulty
            difficulty_stats = db.execute(
                select(Question.difficulty_level, func.count(Question.id))
                .group_by(Question.difficulty_level)
            ).fetchall()
            
            # Questions by category
            category_stats = db.execute(
                select(Question.category, func.count(Question.id))
                .group_by(Question.category)
            ).fetchall()
            
            # Duplicate questions
            duplicates = QuestionBankUtils.find_duplicate_questions(db)
            
            # Questions linked to sessions
            linked_questions = db.execute(
                select(func.count(func.distinct(SessionQuestion.question_id)))
            ).scalar()
            
            return {
                "total_questions": total_questions,
                "difficulty_distribution": dict(difficulty_stats),
                "category_distribution": dict(category_stats),
                "duplicate_groups": len(duplicates),
                "total_duplicates": sum(count - 1 for _, count in duplicates),
                "linked_questions": linked_questions,
                "unlinked_questions": total_questions - linked_questions
            }
            
        except Exception as e:
            logger.error(f"Error getting question bank statistics: {e}")
            return {
                "total_questions": 0,
                "difficulty_distribution": {},
                "category_distribution": {},
                "duplicate_groups": 0,
                "total_duplicates": 0,
                "linked_questions": 0,
                "unlinked_questions": 0,
                "error": str(e)
            }
