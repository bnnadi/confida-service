#!/usr/bin/env python3
"""
Question Bank Migration and Data Seeding Script

This script migrates existing question data to the new question bank structure
and provides comprehensive data seeding capabilities for the global question bank.
"""

import os
import sys
import json
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text, select, update, delete
from sqlalchemy.exc import IntegrityError

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.database.models import (
    User, InterviewSession, Question, SessionQuestion, Answer,
    UserPerformance, AnalyticsEvent, AgentConfiguration
)
from app.database.connection import get_db
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

class QuestionBankMigrator:
    """Handles migration of existing questions to the new question bank structure."""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.migration_stats = {
            "questions_migrated": 0,
            "sessions_updated": 0,
            "duplicates_skipped": 0,
            "errors": 0
        }
    
    def migrate_existing_questions(self) -> Dict[str, Any]:
        """Migrate existing session-bound questions to the global question bank."""
        logger.info("🔄 Starting migration of existing questions to question bank...")
        
        try:
            # Get all existing questions that are still bound to sessions
            existing_questions = self.db_session.execute(
                select(Question).where(Question.session_id.isnot(None))
            ).scalars().all()
            
            logger.info(f"Found {len(existing_questions)} existing questions to migrate")
            
            for question in existing_questions:
                try:
                    # Check if question already exists in global bank
                    existing_global_question = self.db_session.execute(
                        select(Question).where(
                            Question.question_text == question.question_text,
                            Question.session_id.is_(None)
                        )
                    ).scalar_one_or_none()
                    
                    if existing_global_question:
                        # Question already exists in global bank, create session-question link
                        self._create_session_question_link(question.session_id, existing_global_question.id, question.question_order)
                        self.migration_stats["duplicates_skipped"] += 1
                        logger.debug(f"Skipped duplicate question: {question.question_text[:50]}...")
                    else:
                        # Migrate question to global bank
                        self._migrate_question_to_global_bank(question)
                        self.migration_stats["questions_migrated"] += 1
                        logger.debug(f"Migrated question: {question.question_text[:50]}...")
                    
                except Exception as e:
                    logger.error(f"Error migrating question {question.id}: {e}")
                    self.migration_stats["errors"] += 1
            
            # Update session statistics
            self._update_session_statistics()
            
            logger.info("✅ Question migration completed successfully!")
            return self.migration_stats
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            raise
    
    def _migrate_question_to_global_bank(self, question: Question) -> Question:
        """Migrate a single question to the global question bank."""
        # Create new global question
        global_question = Question(
            id=uuid.uuid4(),
            question_text=question.question_text,
            question_metadata=self._extract_question_metadata(question),
            difficulty_level=question.difficulty_level or "medium",
            category=question.category or "general",
            subcategory=self._determine_subcategory(question.question_text, question.category),
            compatible_roles=self._extract_compatible_roles(question),
            required_skills=self._extract_required_skills(question.question_text),
            industry_tags=self._extract_industry_tags(question),
            usage_count=1,  # Start with 1 usage
            average_score=self._calculate_average_score(question),
            success_rate=self._calculate_success_rate(question),
            ai_service_used="migrated",
            generation_prompt_hash=self._generate_prompt_hash(question.question_text),
            created_at=question.created_at,
            updated_at=datetime.utcnow()
        )
        
        self.db_session.add(global_question)
        self.db_session.flush()  # Get the ID without committing
        
        # Create session-question link
        self._create_session_question_link(question.session_id, global_question.id, question.question_order)
        
        # Delete the old session-bound question
        self.db_session.delete(question)
        
        return global_question
    
    def _create_session_question_link(self, session_id: uuid.UUID, question_id: uuid.UUID, question_order: int):
        """Create a link between a session and a question in the global bank."""
        session_question = SessionQuestion(
            id=uuid.uuid4(),
            session_id=session_id,
            question_id=question_id,
            question_order=question_order,
            session_specific_context=None,
            created_at=datetime.utcnow()
        )
        
        self.db_session.add(session_question)
    
    def _extract_question_metadata(self, question: Question) -> Dict[str, Any]:
        """Extract metadata from an existing question."""
        metadata = {
            "migrated_from_session": str(question.session_id),
            "original_question_id": str(question.id),
            "migration_timestamp": datetime.utcnow().isoformat(),
            "source": "migration"
        }
        
        # Add any existing metadata
        if hasattr(question, 'question_metadata') and question.question_metadata:
            metadata.update(question.question_metadata)
        
        return metadata
    
    def _determine_subcategory(self, question_text: str, category: str) -> Optional[str]:
        """Determine subcategory based on question text and category."""
        text_lower = question_text.lower()
        
        if category == "Technical":
            if any(keyword in text_lower for keyword in ["python", "django", "flask"]):
                return "python"
            elif any(keyword in text_lower for keyword in ["javascript", "react", "node"]):
                return "javascript"
            elif any(keyword in text_lower for keyword in ["java", "spring"]):
                return "java"
            elif any(keyword in text_lower for keyword in ["database", "sql"]):
                return "database"
            elif any(keyword in text_lower for keyword in ["algorithm", "data structure"]):
                return "algorithms"
            elif any(keyword in text_lower for keyword in ["design", "architecture"]):
                return "system_design"
        
        elif category == "Behavioral":
            if any(keyword in text_lower for keyword in ["leadership", "team", "manage"]):
                return "leadership"
            elif any(keyword in text_lower for keyword in ["conflict", "challenge", "difficult"]):
                return "conflict_resolution"
            elif any(keyword in text_lower for keyword in ["learn", "improve", "growth"]):
                return "learning_agility"
        
        return None
    
    def _extract_compatible_roles(self, question: Question) -> List[str]:
        """Extract compatible roles from question context."""
        # Get the session role
        session = self.db_session.get(InterviewSession, question.session_id)
        if session:
            return [session.role.lower()]
        return []
    
    def _extract_required_skills(self, question_text: str) -> List[str]:
        """Extract required skills from question text."""
        text_lower = question_text.lower()
        skills = []
        
        skill_mapping = {
            "python": ["python", "django", "flask"],
            "javascript": ["javascript", "js", "react", "node"],
            "java": ["java", "spring"],
            "sql": ["sql", "database"],
            "aws": ["aws", "cloud"],
            "docker": ["docker", "container"],
            "kubernetes": ["kubernetes", "k8s"],
            "git": ["git", "version control"],
            "api": ["api", "rest", "graphql"],
            "testing": ["test", "testing", "tdd"],
            "agile": ["agile", "scrum", "sprint"],
            "leadership": ["lead", "manage", "team"],
            "communication": ["communicate", "present", "explain"]
        }
        
        for skill, keywords in skill_mapping.items():
            if any(keyword in text_lower for keyword in keywords):
                skills.append(skill)
        
        return skills[:10]  # Limit to 10 skills
    
    def _extract_industry_tags(self, question: Question) -> List[str]:
        """Extract industry tags from question context."""
        session = self.db_session.get(InterviewSession, question.session_id)
        if not session:
            return []
        
        job_desc_lower = session.job_description.lower()
        tags = []
        
        industry_mapping = {
            "technology": ["tech", "software", "it", "computer"],
            "finance": ["finance", "banking", "fintech", "financial"],
            "healthcare": ["healthcare", "medical", "health", "pharma"],
            "ecommerce": ["ecommerce", "retail", "shopping", "marketplace"],
            "education": ["education", "learning", "edtech", "school"],
            "gaming": ["gaming", "game", "entertainment"],
            "automotive": ["automotive", "car", "vehicle", "transportation"]
        }
        
        for industry, keywords in industry_mapping.items():
            if any(keyword in job_desc_lower for keyword in keywords):
                tags.append(industry)
        
        return tags[:5]  # Limit to 5 tags
    
    def _calculate_average_score(self, question: Question) -> Optional[float]:
        """Calculate average score from question answers."""
        answers = self.db_session.execute(
            select(Answer).where(Answer.question_id == question.id)
        ).scalars().all()
        
        if not answers:
            return None
        
        total_score = 0
        valid_scores = 0
        
        for answer in answers:
            if answer.score and isinstance(answer.score, dict):
                overall_score = answer.score.get('overall')
                if overall_score is not None:
                    total_score += overall_score
                    valid_scores += 1
        
        return total_score / valid_scores if valid_scores > 0 else None
    
    def _calculate_success_rate(self, question: Question) -> Optional[float]:
        """Calculate success rate from question answers."""
        answers = self.db_session.execute(
            select(Answer).where(Answer.question_id == question.id)
        ).scalars().all()
        
        if not answers:
            return None
        
        successful_answers = 0
        for answer in answers:
            if answer.score and isinstance(answer.score, dict):
                overall_score = answer.score.get('overall', 0)
                if overall_score >= 7.0:  # Consider 7+ as successful
                    successful_answers += 1
        
        return successful_answers / len(answers) if answers else None
    
    def _generate_prompt_hash(self, question_text: str) -> str:
        """Generate a hash for the question text."""
        return hashlib.sha256(question_text.encode()).hexdigest()[:16]
    
    def _update_session_statistics(self):
        """Update session statistics after migration."""
        sessions = self.db_session.execute(select(InterviewSession)).scalars().all()
        
        for session in sessions:
            # Count questions linked to this session
            question_count = self.db_session.execute(
                select(SessionQuestion).where(SessionQuestion.session_id == session.id)
            ).scalars().all()
            
            session.total_questions = len(question_count)
            self.migration_stats["sessions_updated"] += 1
        
        self.db_session.commit()

class QuestionBankSeeder:
    """Handles seeding of the question bank with comprehensive question data."""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.seeding_stats = {
            "questions_created": 0,
            "categories_created": 0,
            "roles_covered": 0,
            "errors": 0
        }
    
    def seed_comprehensive_question_bank(self) -> Dict[str, Any]:
        """Seed the question bank with comprehensive question data."""
        logger.info("🌱 Starting comprehensive question bank seeding...")
        
        try:
            # Seed questions by category and role
            self._seed_technical_questions()
            self._seed_behavioral_questions()
            self._seed_system_design_questions()
            self._seed_leadership_questions()
            self._seed_industry_specific_questions()
            
            logger.info("✅ Question bank seeding completed successfully!")
            return self.seeding_stats
            
        except Exception as e:
            logger.error(f"❌ Seeding failed: {e}")
            raise
    
    def _seed_technical_questions(self):
        """Seed technical questions for various roles and technologies."""
        logger.info("Seeding technical questions...")
        
        technical_questions = {
            "python": [
                {
                    "question": "Explain the difference between list comprehensions and generator expressions in Python.",
                    "difficulty": "medium",
                    "subcategory": "python",
                    "skills": ["python", "programming", "optimization"]
                },
                {
                    "question": "How would you implement a decorator in Python? Provide a practical example.",
                    "difficulty": "hard",
                    "subcategory": "python",
                    "skills": ["python", "decorators", "advanced_programming"]
                },
                {
                    "question": "What are Python's GIL (Global Interpreter Lock) and how does it affect multithreading?",
                    "difficulty": "hard",
                    "subcategory": "python",
                    "skills": ["python", "concurrency", "performance"]
                }
            ],
            "javascript": [
                {
                    "question": "Explain the difference between var, let, and const in JavaScript.",
                    "difficulty": "easy",
                    "subcategory": "javascript",
                    "skills": ["javascript", "programming", "scope"]
                },
                {
                    "question": "How does JavaScript's event loop work? Explain with examples.",
                    "difficulty": "hard",
                    "subcategory": "javascript",
                    "skills": ["javascript", "asynchronous", "event_loop"]
                },
                {
                    "question": "What are closures in JavaScript and how are they useful?",
                    "difficulty": "medium",
                    "subcategory": "javascript",
                    "skills": ["javascript", "closures", "programming"]
                }
            ],
            "database": [
                {
                    "question": "Explain the difference between SQL JOIN types (INNER, LEFT, RIGHT, FULL OUTER).",
                    "difficulty": "medium",
                    "subcategory": "database",
                    "skills": ["sql", "database", "joins"]
                },
                {
                    "question": "How would you optimize a slow SQL query? What tools and techniques would you use?",
                    "difficulty": "hard",
                    "subcategory": "database",
                    "skills": ["sql", "database", "optimization", "performance"]
                },
                {
                    "question": "Explain database normalization and when you might denormalize.",
                    "difficulty": "medium",
                    "subcategory": "database",
                    "skills": ["database", "normalization", "design"]
                }
            ],
            "algorithms": [
                {
                    "question": "Implement a function to find the longest common subsequence between two strings.",
                    "difficulty": "hard",
                    "subcategory": "algorithms",
                    "skills": ["algorithms", "dynamic_programming", "programming"]
                },
                {
                    "question": "Explain the time complexity of different sorting algorithms and when to use each.",
                    "difficulty": "medium",
                    "subcategory": "algorithms",
                    "skills": ["algorithms", "sorting", "complexity"]
                },
                {
                    "question": "How would you detect a cycle in a linked list?",
                    "difficulty": "medium",
                    "subcategory": "algorithms",
                    "skills": ["algorithms", "data_structures", "programming"]
                }
            ]
        }
        
        for subcategory, questions in technical_questions.items():
            for q_data in questions:
                self._create_question(
                    question_text=q_data["question"],
                    category="technical",
                    subcategory=subcategory,
                    difficulty_level=q_data["difficulty"],
                    required_skills=q_data["skills"],
                    compatible_roles=["software_engineer", "backend_developer", "full_stack_developer"]
                )
    
    def _seed_behavioral_questions(self):
        """Seed behavioral questions for various scenarios."""
        logger.info("Seeding behavioral questions...")
        
        behavioral_questions = [
            {
                "question": "Tell me about a time when you had to work with a difficult team member. How did you handle it?",
                "difficulty": "medium",
                "subcategory": "conflict_resolution",
                "skills": ["communication", "teamwork", "conflict_resolution"]
            },
            {
                "question": "Describe a situation where you had to learn a new technology quickly. How did you approach it?",
                "difficulty": "easy",
                "subcategory": "learning_agility",
                "skills": ["learning", "adaptability", "problem_solving"]
            },
            {
                "question": "Give me an example of a time when you failed at something. What did you learn from it?",
                "difficulty": "medium",
                "subcategory": "resilience",
                "skills": ["resilience", "learning", "self_awareness"]
            },
            {
                "question": "Tell me about a time when you had to make a difficult decision with limited information.",
                "difficulty": "hard",
                "subcategory": "decision_making",
                "skills": ["decision_making", "critical_thinking", "leadership"]
            }
        ]
        
        for q_data in behavioral_questions:
            self._create_question(
                question_text=q_data["question"],
                category="behavioral",
                subcategory=q_data["subcategory"],
                difficulty_level=q_data["difficulty"],
                required_skills=q_data["skills"],
                compatible_roles=["software_engineer", "product_manager", "data_scientist", "devops_engineer"]
            )
    
    def _seed_system_design_questions(self):
        """Seed system design questions for senior roles."""
        logger.info("Seeding system design questions...")
        
        system_design_questions = [
            {
                "question": "Design a URL shortener service like bit.ly. What are the key components and how would you scale it?",
                "difficulty": "hard",
                "subcategory": "system_design",
                "skills": ["system_design", "scalability", "architecture", "databases"]
            },
            {
                "question": "How would you design a chat application that supports millions of users?",
                "difficulty": "hard",
                "subcategory": "system_design",
                "skills": ["system_design", "real_time", "scalability", "websockets"]
            },
            {
                "question": "Design a distributed caching system. What challenges would you face?",
                "difficulty": "hard",
                "subcategory": "system_design",
                "skills": ["system_design", "caching", "distributed_systems", "consistency"]
            }
        ]
        
        for q_data in system_design_questions:
            self._create_question(
                question_text=q_data["question"],
                category="system_design",
                subcategory=q_data["subcategory"],
                difficulty_level=q_data["difficulty"],
                required_skills=q_data["skills"],
                compatible_roles=["senior_software_engineer", "staff_engineer", "principal_engineer", "architect"]
            )
    
    def _seed_leadership_questions(self):
        """Seed leadership questions for management roles."""
        logger.info("Seeding leadership questions...")
        
        leadership_questions = [
            {
                "question": "How do you motivate a team that's struggling with a difficult project?",
                "difficulty": "medium",
                "subcategory": "team_management",
                "skills": ["leadership", "team_management", "motivation"]
            },
            {
                "question": "Describe your approach to giving constructive feedback to team members.",
                "difficulty": "medium",
                "subcategory": "feedback",
                "skills": ["leadership", "communication", "feedback"]
            },
            {
                "question": "How do you handle conflicting priorities from different stakeholders?",
                "difficulty": "hard",
                "subcategory": "stakeholder_management",
                "skills": ["leadership", "stakeholder_management", "prioritization"]
            }
        ]
        
        for q_data in leadership_questions:
            self._create_question(
                question_text=q_data["question"],
                category="leadership",
                subcategory=q_data["subcategory"],
                difficulty_level=q_data["difficulty"],
                required_skills=q_data["skills"],
                compatible_roles=["engineering_manager", "tech_lead", "product_manager", "director"]
            )
    
    def _seed_industry_specific_questions(self):
        """Seed industry-specific questions."""
        logger.info("Seeding industry-specific questions...")
        
        industry_questions = {
            "fintech": [
                {
                    "question": "How would you ensure data security and compliance in a financial application?",
                    "difficulty": "hard",
                    "skills": ["security", "compliance", "fintech", "data_protection"]
                }
            ],
            "healthcare": [
                {
                    "question": "What considerations are important when building healthcare software?",
                    "difficulty": "hard",
                    "skills": ["healthcare", "compliance", "privacy", "regulations"]
                }
            ],
            "ecommerce": [
                {
                    "question": "How would you handle high-traffic scenarios during peak shopping seasons?",
                    "difficulty": "hard",
                    "skills": ["scalability", "ecommerce", "performance", "load_balancing"]
                }
            ]
        }
        
        for industry, questions in industry_questions.items():
            for q_data in questions:
                self._create_question(
                    question_text=q_data["question"],
                    category="industry_specific",
                    subcategory=industry,
                    difficulty_level=q_data["difficulty"],
                    required_skills=q_data["skills"],
                    industry_tags=[industry],
                    compatible_roles=["software_engineer", "architect", "tech_lead"]
                )
    
    def _create_question(self, question_text: str, category: str, subcategory: Optional[str] = None,
                        difficulty_level: str = "medium", required_skills: List[str] = None,
                        compatible_roles: List[str] = None, industry_tags: List[str] = None):
        """Create a question in the global question bank."""
        try:
            # Check if question already exists
            existing_question = self.db_session.execute(
                select(Question).where(Question.question_text == question_text)
            ).scalar_one_or_none()
            
            if existing_question:
                logger.debug(f"Question already exists: {question_text[:50]}...")
                return existing_question
            
            question = Question(
                id=uuid.uuid4(),
                question_text=question_text,
                question_metadata={
                    "source": "seeding",
                    "seeded_at": datetime.utcnow().isoformat(),
                    "version": "1.0"
                },
                difficulty_level=difficulty_level,
                category=category,
                subcategory=subcategory,
                compatible_roles=compatible_roles or [],
                required_skills=required_skills or [],
                industry_tags=industry_tags or [],
                usage_count=0,
                average_score=None,
                success_rate=None,
                ai_service_used="seeded",
                generation_prompt_hash=self._generate_prompt_hash(question_text),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            self.db_session.add(question)
            self.seeding_stats["questions_created"] += 1
            
            return question
            
        except Exception as e:
            logger.error(f"Error creating question: {e}")
            self.seeding_stats["errors"] += 1
            return None
    
    def _generate_prompt_hash(self, question_text: str) -> str:
        """Generate a hash for the question text."""
        return hashlib.sha256(question_text.encode()).hexdigest()[:16]

def main():
    """Main function to run migration and seeding."""
    logger.info("🚀 Starting Question Bank Migration and Seeding...")
    
    try:
        # Get database session
        settings = get_settings()
        engine = create_engine(settings.DATABASE_URL)
        
        with Session(engine) as db:
            # Run migration
            migrator = QuestionBankMigrator(db)
            migration_stats = migrator.migrate_existing_questions()
            
            logger.info("📊 Migration Statistics:")
            for key, value in migration_stats.items():
                logger.info(f"  {key}: {value}")
            
            # Run seeding
            seeder = QuestionBankSeeder(db)
            seeding_stats = seeder.seed_comprehensive_question_bank()
            
            logger.info("📊 Seeding Statistics:")
            for key, value in seeding_stats.items():
                logger.info(f"  {key}: {value}")
            
            # Get final question bank statistics
            total_questions = db.execute(select(Question)).scalars().all()
            logger.info(f"📈 Total questions in question bank: {len(total_questions)}")
            
            # Show question distribution by category
            categories = db.execute(
                select(Question.category, db.func.count(Question.id))
                .group_by(Question.category)
            ).fetchall()
            
            logger.info("📊 Question distribution by category:")
            for category, count in categories:
                logger.info(f"  {category}: {count}")
        
        logger.info("🎉 Question Bank Migration and Seeding completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Error during migration and seeding: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
