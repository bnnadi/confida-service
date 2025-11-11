#!/usr/bin/env python3
"""
Question Bank Seeding Script

This script seeds the global question bank with comprehensive, diverse questions
from the sample_questions.json file and additional curated questions.

The script is safe to run multiple times - it will skip questions that already exist.
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
from sqlalchemy import create_engine, select, func

from app.database.models import Question
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

class QuestionBankSeeder:
    """Handles seeding of the question bank with comprehensive question data."""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.seeding_stats = {
            "questions_created": 0,
            "questions_skipped": 0,
            "categories_created": 0,
            "errors": 0
        }
        # Track existing categories in memory to avoid querying after each addition
        self._existing_categories = set()
        self._load_existing_categories()
    
    def seed_question_bank(self, use_sample_file: bool = True) -> Dict[str, Any]:
        """
        Seed the question bank with comprehensive question data.
        
        Args:
            use_sample_file: If True, load questions from data/sample_questions.json
        """
        logger.info("🌱 Starting question bank seeding...")
        
        try:
            # Load questions from sample file if available
            if use_sample_file:
                sample_file = project_root / "data" / "sample_questions.json"
                if sample_file.exists():
                    logger.info(f"📂 Loading questions from {sample_file}")
                    with open(sample_file, 'r') as f:
                        sample_data = json.load(f)
                    self._seed_from_sample_data(sample_data)
                else:
                    logger.warning(f"⚠️  Sample questions file not found: {sample_file}")
                    logger.info("   Proceeding with built-in questions only")
            
            # Seed additional comprehensive questions
            self._seed_additional_questions()
            
            # Commit all changes
            self.db_session.commit()
            
            logger.info("✅ Question bank seeding completed successfully!")
            logger.info("📊 Seeding Statistics:")
            for key, value in self.seeding_stats.items():
                logger.info(f"  {key}: {value}")
            
            # Show final statistics
            total_questions = self.db_session.execute(
                select(func.count(Question.id))
            ).scalar()
            
            categories = self.db_session.execute(
                select(Question.category, func.count(Question.id))
                .group_by(Question.category)
            ).all()
            
            logger.info(f"📈 Total questions in question bank: {total_questions}")
            logger.info("📊 Question distribution by category:")
            for category, count in categories:
                logger.info(f"  {category}: {count}")
            
            return self.seeding_stats
            
        except Exception as e:
            logger.error(f"❌ Seeding failed: {e}")
            self.db_session.rollback()
            raise
    
    def _seed_from_sample_data(self, sample_data: Dict[str, Any]) -> None:
        """Seed questions from sample_questions.json file."""
        logger.info("📥 Processing sample questions data...")
        
        # Process technical questions
        if "technical_questions" in sample_data:
            for tech_category, questions in sample_data["technical_questions"].items():
                logger.info(f"  Processing {tech_category} questions...")
                for q_data in questions:
                    self._create_question(
                        question_text=q_data["question"],
                        category="technical",
                        subcategory=tech_category,
                        difficulty_level=q_data.get("difficulty", "medium"),
                        required_skills=q_data.get("skills", []),
                        compatible_roles=self._get_compatible_roles_for_tech(tech_category),
                        industry_tags=q_data.get("tags", [])
                    )
        
        # Process behavioral questions
        if "behavioral_questions" in sample_data:
            logger.info("  Processing behavioral questions...")
            for q_data in sample_data["behavioral_questions"]:
                self._create_question(
                    question_text=q_data["question"],
                    category=q_data.get("category", "behavioral"),
                    subcategory=q_data.get("subcategory", "general"),
                    difficulty_level=q_data.get("difficulty", "medium"),
                    required_skills=q_data.get("skills", []),
                    compatible_roles=["all"],  # Behavioral questions apply to all roles
                    industry_tags=q_data.get("tags", [])
                )
        
        # Process system design questions
        if "system_design_questions" in sample_data:
            logger.info("  Processing system design questions...")
            for q_data in sample_data["system_design_questions"]:
                self._create_question(
                    question_text=q_data["question"],
                    category=q_data.get("category", "system_design"),
                    subcategory=q_data.get("subcategory", "system_design"),
                    difficulty_level=q_data.get("difficulty", "hard"),
                    required_skills=q_data.get("skills", []),
                    compatible_roles=["senior_developer", "architect", "tech_lead", "principal_engineer"],
                    industry_tags=q_data.get("tags", [])
                )
        
        # Process leadership questions
        if "leadership_questions" in sample_data:
            logger.info("  Processing leadership questions...")
            for q_data in sample_data["leadership_questions"]:
                self._create_question(
                    question_text=q_data["question"],
                    category=q_data.get("category", "leadership"),
                    subcategory=q_data.get("subcategory", "general"),
                    difficulty_level=q_data.get("difficulty", "medium"),
                    required_skills=q_data.get("skills", []),
                    compatible_roles=["engineering_manager", "tech_lead", "product_manager", "director"],
                    industry_tags=q_data.get("tags", [])
                )
        
        # Process industry-specific questions
        if "industry_specific_questions" in sample_data:
            logger.info("  Processing industry-specific questions...")
            for industry, questions in sample_data["industry_specific_questions"].items():
                for q_data in questions:
                    self._create_question(
                        question_text=q_data["question"],
                        category=q_data.get("category", "industry_specific"),
                        subcategory=q_data.get("subcategory", industry),
                        difficulty_level=q_data.get("difficulty", "hard"),
                        required_skills=q_data.get("skills", []),
                        compatible_roles=["software_engineer", "architect", "tech_lead"],
                        industry_tags=[industry] + q_data.get("tags", [])
                    )
    
    def _seed_additional_questions(self) -> None:
        """Seed additional comprehensive questions not in sample file."""
        logger.info("📝 Adding additional comprehensive questions...")
        
        additional_questions = [
            # Technical - General
            {
                "question_text": "Explain the difference between REST and GraphQL APIs. When would you use each?",
                "category": "technical",
                "subcategory": "api_design",
                "difficulty_level": "medium",
                "required_skills": ["api_design", "web_development", "rest", "graphql"],
                "compatible_roles": ["backend_developer", "fullstack_developer", "api_developer"],
                "industry_tags": ["tech", "saas", "ecommerce"]
            },
            {
                "question_text": "What is the difference between microservices and monolithic architecture? What are the trade-offs?",
                "category": "technical",
                "subcategory": "architecture",
                "difficulty_level": "medium",
                "required_skills": ["architecture", "microservices", "system_design"],
                "compatible_roles": ["backend_developer", "architect", "tech_lead"],
                "industry_tags": ["tech", "saas"]
            },
            # Behavioral - General
            {
                "question_text": "Tell me about a time you had to work with a difficult team member. How did you handle the situation?",
                "category": "behavioral",
                "subcategory": "teamwork",
                "difficulty_level": "medium",
                "required_skills": ["communication", "teamwork", "conflict_resolution"],
                "compatible_roles": ["all"],
                "industry_tags": ["all"]
            },
            {
                "question_text": "Describe a situation where you had to learn a new technology quickly. How did you approach it?",
                "category": "behavioral",
                "subcategory": "learning_agility",
                "difficulty_level": "easy",
                "required_skills": ["learning", "adaptability", "problem_solving"],
                "compatible_roles": ["all"],
                "industry_tags": ["all"]
            },
            # System Design
            {
                "question_text": "How would you design a URL shortener like bit.ly?",
                "category": "system_design",
                "subcategory": "scalability",
                "difficulty_level": "hard",
                "required_skills": ["system_design", "scalability", "databases"],
                "compatible_roles": ["senior_developer", "architect", "tech_lead"],
                "industry_tags": ["tech", "saas"]
            },
            {
                "question_text": "Design a distributed caching system. What challenges would you face?",
                "category": "system_design",
                "subcategory": "distributed_systems",
                "difficulty_level": "hard",
                "required_skills": ["system_design", "caching", "distributed_systems", "consistency"],
                "compatible_roles": ["senior_developer", "architect", "tech_lead"],
                "industry_tags": ["tech", "saas"]
            }
        ]
        
        for q_data in additional_questions:
            self._create_question(**q_data)
    
    def _get_compatible_roles_for_tech(self, tech_category: str) -> List[str]:
        """Get compatible roles for a technical category."""
        role_mapping = {
            "python": ["python_developer", "backend_developer", "data_scientist", "fullstack_developer"],
            "javascript": ["javascript_developer", "frontend_developer", "fullstack_developer", "node_developer"],
            "java": ["java_developer", "backend_developer", "enterprise_developer"],
            "database": ["backend_developer", "database_engineer", "data_engineer", "fullstack_developer"],
            "algorithms": ["software_engineer", "backend_developer", "fullstack_developer", "data_scientist"]
        }
        return role_mapping.get(tech_category, ["software_engineer", "backend_developer"])
    
    def _create_question(
        self,
        question_text: str,
        category: str,
        subcategory: Optional[str] = None,
        difficulty_level: str = "medium",
        required_skills: List[str] = None,
        compatible_roles: List[str] = None,
        industry_tags: List[str] = None
    ) -> Optional[Question]:
        """Create a question in the global question bank."""
        try:
            # Check if question already exists (by text)
            existing_question = self.db_session.execute(
                select(Question).where(Question.question_text == question_text)
            ).scalar_one_or_none()
            
            if existing_question:
                logger.debug(f"Question already exists: {question_text[:50]}...")
                self.seeding_stats["questions_skipped"] += 1
                return existing_question
            
            # Create new question
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
            
            # Track categories BEFORE adding to session
            # Check if this is a new category (not in existing categories and not already tracked)
            is_new_category = category not in self._existing_categories
            if is_new_category:
                self._existing_categories.add(category)
                self.seeding_stats["categories_created"] += 1
            
            self.db_session.add(question)
            self.seeding_stats["questions_created"] += 1
            
            return question
            
        except Exception as e:
            logger.error(f"Error creating question: {e}")
            logger.error(f"  Question text: {question_text[:100]}...")
            self.seeding_stats["errors"] += 1
            return None
    
    def _load_existing_categories(self) -> None:
        """Load existing categories from database into memory."""
        try:
            existing_categories = self.db_session.execute(
                select(Question.category).distinct()
            ).scalars().all()
            self._existing_categories = set(existing_categories)
            logger.debug(f"Loaded {len(self._existing_categories)} existing categories: {self._existing_categories}")
        except Exception as e:
            logger.warning(f"Could not load existing categories: {e}")
            self._existing_categories = set()
    
    def _generate_prompt_hash(self, question_text: str) -> str:
        """Generate a hash for the question text."""
        return hashlib.sha256(question_text.encode()).hexdigest()[:16]

def main():
    """Main function to run seeding."""
    logger.info("🚀 Starting Question Bank Seeding...")
    
    try:
        settings = get_settings()
        engine = create_engine(settings.DATABASE_URL)
        
        with Session(engine) as db:
            seeder = QuestionBankSeeder(db)
            stats = seeder.seed_question_bank(use_sample_file=True)
            
            logger.info("🎉 Seeding completed successfully!")
            return stats
        
    except Exception as e:
        logger.error(f"❌ Error during seeding: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

