#!/usr/bin/env python3
"""
Question Database Seeder for Phase 2: Gradual Database Enhancement

This script seeds the question database with high-quality interview questions
to reduce AI service calls and optimize costs.
"""

import sys
import os
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from app.database.connection import SessionLocal
from app.database.question_database_models import QuestionTemplate, Base
from app.database.connection import engine
from app.utils.logger import get_logger

logger = get_logger(__name__)

class QuestionDatabaseSeeder:
    """Seeder for populating the question database with high-quality questions."""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.questions_seeded = 0
        self.categories_seeded = 0
    
    def seed_question_database(self):
        """Seed the question database with comprehensive question sets."""
        try:
            logger.info("Starting question database seeding...")
            
            # Create tables if they don't exist
            Base.metadata.create_all(bind=engine)
            
            # Seed different categories of questions
            self._seed_technical_questions()
            self._seed_behavioral_questions()
            self._seed_system_design_questions()
            self._seed_leadership_questions()
            self._seed_data_science_questions()
            self._seed_devops_questions()
            self._seed_product_management_questions()
            
            # Commit all changes
            self.db_session.commit()
            
            logger.info(f"✅ Seeding complete! Added {self.questions_seeded} questions across {self.categories_seeded} categories")
            
        except Exception as e:
            logger.error(f"Error seeding question database: {e}")
            self.db_session.rollback()
            raise
    
    def _seed_technical_questions(self):
        """Seed technical interview questions."""
        technical_questions = [
            {
                "question_text": "Explain the difference between a stack and a queue. When would you use each?",
                "question_type": "technical",
                "difficulty_level": "easy",
                "target_roles": ["software_engineer", "backend_engineer", "full_stack_engineer"],
                "seniority_levels": ["junior", "mid"],
                "required_skills": ["data_structures", "algorithms"],
                "technical_domains": ["backend", "algorithms"],
                "complexity_keywords": ["data_structures", "algorithms"],
                "quality_score": 0.9
            },
            {
                "question_text": "How would you implement a thread-safe singleton pattern in Python?",
                "question_type": "technical",
                "difficulty_level": "medium",
                "target_roles": ["software_engineer", "backend_engineer", "python_developer"],
                "seniority_levels": ["mid", "senior"],
                "required_skills": ["python", "design_patterns", "concurrency"],
                "technical_domains": ["backend", "python"],
                "complexity_keywords": ["threading", "singleton", "concurrency"],
                "quality_score": 0.85
            },
            {
                "question_text": "Explain the CAP theorem and its implications for distributed systems design.",
                "question_type": "technical",
                "difficulty_level": "hard",
                "target_roles": ["software_engineer", "backend_engineer", "system_architect"],
                "seniority_levels": ["senior", "lead", "principal"],
                "required_skills": ["distributed_systems", "system_design", "databases"],
                "technical_domains": ["backend", "distributed_systems"],
                "complexity_keywords": ["distributed_systems", "consistency", "availability"],
                "quality_score": 0.95
            },
            {
                "question_text": "How would you optimize a slow database query? Walk me through your debugging process.",
                "question_type": "technical",
                "difficulty_level": "medium",
                "target_roles": ["software_engineer", "backend_engineer", "database_engineer"],
                "seniority_levels": ["mid", "senior"],
                "required_skills": ["sql", "database_optimization", "performance"],
                "technical_domains": ["backend", "databases"],
                "complexity_keywords": ["optimization", "performance", "sql"],
                "quality_score": 0.88
            },
            {
                "question_text": "Explain the difference between REST and GraphQL. When would you choose one over the other?",
                "question_type": "technical",
                "difficulty_level": "medium",
                "target_roles": ["software_engineer", "backend_engineer", "api_developer"],
                "seniority_levels": ["mid", "senior"],
                "required_skills": ["rest", "graphql", "api_design"],
                "technical_domains": ["backend", "api"],
                "complexity_keywords": ["api", "rest", "graphql"],
                "quality_score": 0.87
            }
        ]
        
        self._add_questions(technical_questions, "Technical Questions")
    
    def _seed_behavioral_questions(self):
        """Seed behavioral interview questions."""
        behavioral_questions = [
            {
                "question_text": "Tell me about a time when you had to work with a difficult team member. How did you handle it?",
                "question_type": "behavioral",
                "difficulty_level": "medium",
                "target_roles": ["software_engineer", "team_lead", "manager"],
                "seniority_levels": ["mid", "senior", "lead"],
                "required_skills": ["communication", "teamwork", "conflict_resolution"],
                "technical_domains": ["soft_skills"],
                "complexity_keywords": ["teamwork", "communication"],
                "quality_score": 0.9
            },
            {
                "question_text": "Describe a situation where you had to learn a new technology quickly. How did you approach it?",
                "question_type": "behavioral",
                "difficulty_level": "easy",
                "target_roles": ["software_engineer", "developer"],
                "seniority_levels": ["junior", "mid", "senior"],
                "required_skills": ["learning", "adaptability", "problem_solving"],
                "technical_domains": ["soft_skills"],
                "complexity_keywords": ["learning", "adaptability"],
                "quality_score": 0.85
            },
            {
                "question_text": "Give me an example of a project where you had to balance multiple competing priorities. How did you manage it?",
                "question_type": "behavioral",
                "difficulty_level": "medium",
                "target_roles": ["software_engineer", "project_manager", "team_lead"],
                "seniority_levels": ["mid", "senior", "lead"],
                "required_skills": ["project_management", "prioritization", "time_management"],
                "technical_domains": ["soft_skills"],
                "complexity_keywords": ["prioritization", "project_management"],
                "quality_score": 0.88
            }
        ]
        
        self._add_questions(behavioral_questions, "Behavioral Questions")
    
    def _seed_system_design_questions(self):
        """Seed system design interview questions."""
        system_design_questions = [
            {
                "question_text": "Design a URL shortener like bit.ly. What are the key components and how would you scale it?",
                "question_type": "system_design",
                "difficulty_level": "hard",
                "target_roles": ["software_engineer", "system_architect", "backend_engineer"],
                "seniority_levels": ["senior", "lead", "principal"],
                "required_skills": ["system_design", "scalability", "databases"],
                "technical_domains": ["system_design", "backend"],
                "complexity_keywords": ["scalability", "system_design", "microservices"],
                "quality_score": 0.95
            },
            {
                "question_text": "How would you design a chat application like WhatsApp? Consider real-time messaging and scalability.",
                "question_type": "system_design",
                "difficulty_level": "hard",
                "target_roles": ["software_engineer", "system_architect", "backend_engineer"],
                "seniority_levels": ["senior", "lead", "principal"],
                "required_skills": ["system_design", "real_time", "websockets"],
                "technical_domains": ["system_design", "real_time"],
                "complexity_keywords": ["real_time", "websockets", "scalability"],
                "quality_score": 0.92
            },
            {
                "question_text": "Design a distributed cache system. How would you ensure consistency and handle failures?",
                "question_type": "system_design",
                "difficulty_level": "hard",
                "target_roles": ["software_engineer", "system_architect", "backend_engineer"],
                "seniority_levels": ["senior", "lead", "principal"],
                "required_skills": ["distributed_systems", "caching", "consistency"],
                "technical_domains": ["system_design", "distributed_systems"],
                "complexity_keywords": ["distributed_systems", "caching", "consistency"],
                "quality_score": 0.93
            }
        ]
        
        self._add_questions(system_design_questions, "System Design Questions")
    
    def _seed_leadership_questions(self):
        """Seed leadership and management questions."""
        leadership_questions = [
            {
                "question_text": "How would you handle a situation where your team disagrees with a technical decision you've made?",
                "question_type": "leadership",
                "difficulty_level": "medium",
                "target_roles": ["team_lead", "engineering_manager", "tech_lead"],
                "seniority_levels": ["senior", "lead", "principal"],
                "required_skills": ["leadership", "communication", "decision_making"],
                "technical_domains": ["leadership"],
                "complexity_keywords": ["leadership", "team_management"],
                "quality_score": 0.9
            },
            {
                "question_text": "Describe your approach to mentoring junior developers. What strategies have worked best?",
                "question_type": "leadership",
                "difficulty_level": "medium",
                "target_roles": ["senior_engineer", "team_lead", "engineering_manager"],
                "seniority_levels": ["senior", "lead", "principal"],
                "required_skills": ["mentoring", "leadership", "communication"],
                "technical_domains": ["leadership"],
                "complexity_keywords": ["mentoring", "leadership"],
                "quality_score": 0.87
            },
            {
                "question_text": "How do you balance technical debt with feature development in your team?",
                "question_type": "leadership",
                "difficulty_level": "hard",
                "target_roles": ["tech_lead", "engineering_manager", "cto"],
                "seniority_levels": ["lead", "principal", "staff"],
                "required_skills": ["technical_debt", "project_management", "leadership"],
                "technical_domains": ["leadership", "project_management"],
                "complexity_keywords": ["technical_debt", "project_management"],
                "quality_score": 0.92
            }
        ]
        
        self._add_questions(leadership_questions, "Leadership Questions")
    
    def _seed_data_science_questions(self):
        """Seed data science and ML questions."""
        data_science_questions = [
            {
                "question_text": "Explain the bias-variance tradeoff in machine learning. How do you address each?",
                "question_type": "technical",
                "difficulty_level": "medium",
                "target_roles": ["data_scientist", "ml_engineer", "data_engineer"],
                "seniority_levels": ["mid", "senior"],
                "required_skills": ["machine_learning", "statistics", "modeling"],
                "technical_domains": ["data_science", "machine_learning"],
                "complexity_keywords": ["machine_learning", "bias", "variance"],
                "quality_score": 0.9
            },
            {
                "question_text": "How would you handle missing data in a dataset? What are the different approaches?",
                "question_type": "technical",
                "difficulty_level": "medium",
                "target_roles": ["data_scientist", "data_engineer", "analyst"],
                "seniority_levels": ["junior", "mid", "senior"],
                "required_skills": ["data_preprocessing", "statistics", "pandas"],
                "technical_domains": ["data_science", "data_engineering"],
                "complexity_keywords": ["data_preprocessing", "missing_data"],
                "quality_score": 0.85
            },
            {
                "question_text": "Design an A/B testing framework for a recommendation system. What metrics would you track?",
                "question_type": "system_design",
                "difficulty_level": "hard",
                "target_roles": ["data_scientist", "ml_engineer", "product_analyst"],
                "seniority_levels": ["senior", "lead"],
                "required_skills": ["ab_testing", "recommendation_systems", "statistics"],
                "technical_domains": ["data_science", "recommendation_systems"],
                "complexity_keywords": ["ab_testing", "recommendation_systems"],
                "quality_score": 0.93
            }
        ]
        
        self._add_questions(data_science_questions, "Data Science Questions")
    
    def _seed_devops_questions(self):
        """Seed DevOps and infrastructure questions."""
        devops_questions = [
            {
                "question_text": "Explain the difference between Docker and Kubernetes. When would you use each?",
                "question_type": "technical",
                "difficulty_level": "medium",
                "target_roles": ["devops_engineer", "site_reliability_engineer", "platform_engineer"],
                "seniority_levels": ["mid", "senior"],
                "required_skills": ["docker", "kubernetes", "containerization"],
                "technical_domains": ["devops", "infrastructure"],
                "complexity_keywords": ["docker", "kubernetes", "containerization"],
                "quality_score": 0.88
            },
            {
                "question_text": "How would you implement a CI/CD pipeline for a microservices architecture?",
                "question_type": "technical",
                "difficulty_level": "hard",
                "target_roles": ["devops_engineer", "platform_engineer", "site_reliability_engineer"],
                "seniority_levels": ["senior", "lead"],
                "required_skills": ["cicd", "microservices", "automation"],
                "technical_domains": ["devops", "microservices"],
                "complexity_keywords": ["cicd", "microservices", "automation"],
                "quality_score": 0.92
            },
            {
                "question_text": "Describe your approach to monitoring and alerting in a production environment.",
                "question_type": "technical",
                "difficulty_level": "medium",
                "target_roles": ["devops_engineer", "site_reliability_engineer", "platform_engineer"],
                "seniority_levels": ["mid", "senior"],
                "required_skills": ["monitoring", "alerting", "observability"],
                "technical_domains": ["devops", "monitoring"],
                "complexity_keywords": ["monitoring", "alerting", "observability"],
                "quality_score": 0.87
            }
        ]
        
        self._add_questions(devops_questions, "DevOps Questions")
    
    def _seed_product_management_questions(self):
        """Seed product management questions."""
        product_questions = [
            {
                "question_text": "How would you prioritize features for a new product launch? What framework would you use?",
                "question_type": "product",
                "difficulty_level": "medium",
                "target_roles": ["product_manager", "product_owner", "product_analyst"],
                "seniority_levels": ["mid", "senior"],
                "required_skills": ["product_management", "prioritization", "strategy"],
                "technical_domains": ["product_management"],
                "complexity_keywords": ["prioritization", "product_strategy"],
                "quality_score": 0.9
            },
            {
                "question_text": "Describe how you would measure the success of a new feature. What metrics would you track?",
                "question_type": "product",
                "difficulty_level": "medium",
                "target_roles": ["product_manager", "product_analyst", "growth_manager"],
                "seniority_levels": ["mid", "senior"],
                "required_skills": ["analytics", "metrics", "product_management"],
                "technical_domains": ["product_management", "analytics"],
                "complexity_keywords": ["metrics", "analytics", "success_measurement"],
                "quality_score": 0.88
            },
            {
                "question_text": "How would you handle conflicting requirements from different stakeholders?",
                "question_type": "behavioral",
                "difficulty_level": "medium",
                "target_roles": ["product_manager", "product_owner", "project_manager"],
                "seniority_levels": ["mid", "senior"],
                "required_skills": ["stakeholder_management", "communication", "negotiation"],
                "technical_domains": ["product_management"],
                "complexity_keywords": ["stakeholder_management", "negotiation"],
                "quality_score": 0.87
            }
        ]
        
        self._add_questions(product_questions, "Product Management Questions")
    
    def _add_questions(self, questions: List[Dict[str, Any]], category_name: str):
        """Add questions to the database."""
        try:
            for question_data in questions:
                # Check if question already exists
                existing = self.db_session.query(QuestionTemplate).filter(
                    QuestionTemplate.question_text == question_data["question_text"]
                ).first()
                
                if existing:
                    logger.debug(f"Question already exists: {question_data['question_text'][:50]}...")
                    continue
                
                # Create new question template
                question = QuestionTemplate(
                    question_text=question_data["question_text"],
                    question_type=question_data["question_type"],
                    difficulty_level=question_data["difficulty_level"],
                    target_roles=question_data.get("target_roles", []),
                    seniority_levels=question_data.get("seniority_levels", []),
                    industries=question_data.get("industries", []),
                    required_skills=question_data.get("required_skills", []),
                    technical_domains=question_data.get("technical_domains", []),
                    complexity_keywords=question_data.get("complexity_keywords", []),
                    quality_score=question_data.get("quality_score", 0.8),
                    source="human_curated"
                )
                
                self.db_session.add(question)
                self.questions_seeded += 1
            
            self.categories_seeded += 1
            logger.info(f"✅ Added {len(questions)} {category_name}")
            
        except Exception as e:
            logger.error(f"Error adding {category_name}: {e}")
            raise

def main():
    """Main function to run the seeder."""
    try:
        # Get database session
        db_session = SessionLocal()
        
        # Create seeder and run
        seeder = QuestionDatabaseSeeder(db_session)
        seeder.seed_question_database()
        
        print("🎉 Question database seeding completed successfully!")
        print(f"📊 Total questions added: {seeder.questions_seeded}")
        print(f"📁 Categories seeded: {seeder.categories_seeded}")
        
    except Exception as e:
        logger.error(f"Seeding failed: {e}")
        print(f"❌ Seeding failed: {e}")
        sys.exit(1)
    finally:
        if 'db_session' in locals():
            db_session.close()

if __name__ == "__main__":
    main()
