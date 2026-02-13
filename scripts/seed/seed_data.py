#!/usr/bin/env python3
"""
Seed data script for Confida local development.
This script populates the database with demo users, sample interview sessions,
and other test data for development and testing purposes.
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from app.database.models import (
    User, InterviewSession, Question, Answer, 
    UserPerformance, AnalyticsEvent, AgentConfiguration
)
from app.services.auth_service import AuthService
from app.config import get_settings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample data
DEMO_USERS = [
    {
        "email": "demo@confida.com",
        "name": "Demo User",
        "password": "demo123456",
        "is_active": True
    },
    {
        "email": "john.doe@example.com",
        "name": "John Doe",
        "password": "password123",
        "is_active": True
    },
    {
        "email": "jane.smith@example.com",
        "name": "Jane Smith",
        "password": "password123",
        "is_active": True
    },
    {
        "email": "admin@confida.com",
        "name": "Admin User",
        "password": "admin123456",
        "is_active": True
    }
]

SAMPLE_JOB_DESCRIPTIONS = [
    {
        "role": "Senior Software Engineer",
        "description": """We are looking for a Senior Software Engineer to join our growing team. 
        The ideal candidate will have 5+ years of experience in full-stack development, 
        strong knowledge of Python, JavaScript, and cloud technologies. 
        You will be responsible for designing and implementing scalable web applications, 
        mentoring junior developers, and collaborating with cross-functional teams."""
    },
    {
        "role": "Data Scientist",
        "description": """Join our data science team to build machine learning models and 
        data pipelines. We need someone with expertise in Python, R, SQL, and experience 
        with machine learning frameworks like TensorFlow or PyTorch. 
        The role involves analyzing large datasets, building predictive models, 
        and presenting insights to stakeholders."""
    },
    {
        "role": "Product Manager",
        "description": """We're seeking a Product Manager to drive product strategy and 
        execution. The ideal candidate has 3+ years of product management experience, 
        strong analytical skills, and experience with agile methodologies. 
        You'll work closely with engineering, design, and business teams to deliver 
        products that delight our customers."""
    },
    {
        "role": "DevOps Engineer",
        "description": """Looking for a DevOps Engineer to manage our cloud infrastructure 
        and deployment pipelines. You should have experience with AWS/Azure, Docker, 
        Kubernetes, CI/CD tools, and infrastructure as code. 
        The role involves ensuring high availability, security, and scalability of our systems."""
    }
]

SAMPLE_QUESTIONS = {
    "Senior Software Engineer": [
        "Tell me about a challenging technical problem you solved recently.",
        "How do you approach code reviews and what makes a good code review?",
        "Describe your experience with microservices architecture.",
        "How do you ensure code quality and maintainability in large projects?",
        "What's your experience with cloud platforms like AWS or Azure?"
    ],
    "Data Scientist": [
        "Walk me through your process for building a machine learning model.",
        "How do you handle missing data in your datasets?",
        "Describe a time when you had to explain complex data insights to non-technical stakeholders.",
        "What's your experience with A/B testing and statistical analysis?",
        "How do you ensure your models are fair and unbiased?"
    ],
    "Product Manager": [
        "How do you prioritize features in a product roadmap?",
        "Describe a time when you had to make a difficult product decision.",
        "How do you gather and analyze user feedback?",
        "What metrics do you use to measure product success?",
        "How do you work with engineering teams to deliver products on time?"
    ],
    "DevOps Engineer": [
        "Describe your experience with containerization and orchestration.",
        "How do you ensure system security in a cloud environment?",
        "What's your approach to monitoring and alerting?",
        "How do you handle database migrations and zero-downtime deployments?",
        "Describe a time when you had to troubleshoot a production incident."
    ]
}

SAMPLE_ANSWERS = [
    "I recently worked on optimizing a database query that was taking 30 seconds to execute. I analyzed the query execution plan, identified missing indexes, and restructured the query to use proper joins. The optimization reduced the query time to under 2 seconds.",
    "In my previous role, I led the migration of our monolithic application to a microservices architecture. This involved breaking down the monolith into smaller, independent services, implementing API gateways, and ensuring proper service communication.",
    "I believe in writing clean, readable code with comprehensive tests. I use design patterns appropriately, follow SOLID principles, and ensure proper documentation. Code reviews should focus on logic, performance, security, and maintainability.",
    "I have extensive experience with AWS services including EC2, S3, RDS, Lambda, and CloudFormation. I've also worked with Azure and have certifications in both cloud platforms.",
    "For data preprocessing, I typically start by exploring the dataset to understand its structure and identify patterns in missing data. I use techniques like mean imputation, forward/backward filling, or model-based imputation depending on the data type and context."
]

def create_demo_users(db: Session) -> List[User]:
    """Create demo users with hashed passwords."""
    logger.info("Creating demo users...")
    auth_service = AuthService(db)
    created_users = []
    
    for user_data in DEMO_USERS:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == user_data["email"]).first()
        if existing_user:
            logger.info(f"User {user_data['email']} already exists, skipping...")
            created_users.append(existing_user)
            continue
        
        # Create new user
        user = User(
            email=user_data["email"],
            name=user_data["name"],
            password_hash=auth_service.get_password_hash(user_data["password"]),
            is_active=user_data["is_active"],
            created_at=datetime.utcnow(),
            last_login=datetime.utcnow() - timedelta(days=1)
        )
        
        db.add(user)
        created_users.append(user)
        logger.info(f"Created user: {user_data['email']}")
    
    db.commit()
    return created_users

def create_sample_sessions(db: Session, users: List[User]) -> List[InterviewSession]:
    """Create sample interview sessions."""
    logger.info("Creating sample interview sessions...")
    sessions = []
    
    for i, job_desc in enumerate(SAMPLE_JOB_DESCRIPTIONS):
        user = users[i % len(users)]  # Cycle through users
        
        session = InterviewSession(
            user_id=user.id,
            role=job_desc["role"],
            job_description=job_desc["description"],
            status="completed" if i < 2 else "active",
            total_questions=len(SAMPLE_QUESTIONS.get(job_desc["role"], [])),
            completed_questions=len(SAMPLE_QUESTIONS.get(job_desc["role"], [])) if i < 2 else 0,
            overall_score={
                "total_score": 85 + (i * 3),
                "clarity": 8 + (i % 2),
                "confidence": 7 + (i % 3),
                "technical_knowledge": 9 if i < 2 else 8,
                "communication": 8 + (i % 2)
            } if i < 2 else None,
            created_at=datetime.utcnow() - timedelta(days=7-i),
            updated_at=datetime.utcnow() - timedelta(days=7-i)
        )
        
        db.add(session)
        sessions.append(session)
        logger.info(f"Created session for {job_desc['role']}")
    
    db.commit()
    return sessions

def create_sample_questions(db: Session, sessions: List[InterviewSession]) -> List[Question]:
    """Create sample questions for each session."""
    logger.info("Creating sample questions...")
    questions = []
    
    for session in sessions:
        role_questions = SAMPLE_QUESTIONS.get(session.role, [])
        
        for i, question_text in enumerate(role_questions):
            question = Question(
                question_text=question_text,
                difficulty_level="medium" if i < 3 else "hard",
                category=["Technical", "Behavioral", "Situational"][i % 3],
                compatible_roles=[session.role],
                question_metadata={
                    "source": "seed_data",
                    "role": session.role,
                    "order": i + 1
                }
            )
            
            db.add(question)
            questions.append(question)
    
    db.commit()
    return questions

def create_sample_answers(db: Session, questions: List[Question], sessions: List[InterviewSession]) -> List[Answer]:
    """Create sample answers for questions in completed sessions."""
    logger.info("Creating sample answers...")
    answers = []
    
    # Create a mapping of questions to sessions based on role
    question_to_session = {}
    for question in questions:
        role = question.question_metadata.get("role")
        for session in sessions:
            if session.role == role and session.status == "completed":
                question_to_session[question.id] = session
                break
    
    for question in questions:
        # Only create answers for questions in completed sessions
        if question.id in question_to_session:
            session = question_to_session[question.id]
            answer_text = SAMPLE_ANSWERS[len(answers) % len(SAMPLE_ANSWERS)]
            
            # Create analysis result
            analysis_result = {
                "clarity_score": 8 + (len(answers) % 3),
                "confidence_score": 7 + (len(answers) % 2),
                "technical_accuracy": 8 + (len(answers) % 2),
                "communication_effectiveness": 8 + (len(answers) % 3),
                "missing_keywords": ["scalability", "performance"] if len(answers) % 2 == 0 else [],
                "improvements": [
                    "Provide more specific examples",
                    "Include metrics and quantifiable results"
                ] if len(answers) % 2 == 0 else ["Great answer overall"]
            }
            
            # Create score
            score = {
                "overall": 8 + (len(answers) % 2),
                "clarity": analysis_result["clarity_score"],
                "confidence": analysis_result["confidence_score"],
                "technical": analysis_result["technical_accuracy"],
                "communication": analysis_result["communication_effectiveness"]
            }
            
            # Create multi-agent scores
            multi_agent_scores = {
                "technical_agent": {
                    "score": analysis_result["technical_accuracy"],
                    "feedback": "Strong technical understanding demonstrated"
                },
                "communication_agent": {
                    "score": analysis_result["communication_effectiveness"],
                    "feedback": "Clear and articulate response"
                },
                "behavioral_agent": {
                    "score": 8 + (len(answers) % 2),
                    "feedback": "Shows good problem-solving approach"
                }
            }
            
            answer = Answer(
                question_id=question.id,
                answer_text=answer_text,
                analysis_result=analysis_result,
                score=score,
                multi_agent_scores=multi_agent_scores
            )
            
            db.add(answer)
            answers.append(answer)
    
    db.commit()
    return answers

def create_user_performance(db: Session, users: List[User], sessions: List[InterviewSession]):
    """Create user performance tracking data."""
    logger.info("Creating user performance data...")
    
    skill_categories = ["Technical Skills", "Communication", "Problem Solving", "Leadership"]
    
    for user in users:
        user_sessions = [s for s in sessions if s.user_id == user.id]
        
        for session in user_sessions:
            for category in skill_categories:
                performance = UserPerformance(
                    user_id=user.id,
                    session_id=session.id,
                    skill_category=category,
                    score=75 + (hash(str(user.id) + category) % 25),  # Random score 75-100
                    improvement_rate=5 + (hash(str(user.id) + category) % 10),  # Random improvement 5-15%
                    created_at=session.created_at
                )
                db.add(performance)
    
    db.commit()

def create_analytics_events(db: Session, users: List[User], sessions: List[InterviewSession]):
    """Create analytics events for tracking user interactions."""
    logger.info("Creating analytics events...")
    
    event_types = [
        "session_started", "question_answered", "session_completed",
        "login", "logout", "profile_updated", "feedback_submitted"
    ]
    
    for user in users:
        user_sessions = [s for s in sessions if s.user_id == user.id]
        
        # Login event
        login_event = AnalyticsEvent(
            user_id=user.id,
            event_type="login",
            event_data={"ip_address": "127.0.0.1", "user_agent": "Mozilla/5.0"},
            created_at=user.created_at
        )
        db.add(login_event)
        
        for session in user_sessions:
            # Session started
            session_start_event = AnalyticsEvent(
                user_id=user.id,
                event_type="session_started",
                event_data={"role": session.role, "session_id": str(session.id)},
                session_id=session.id,
                created_at=session.created_at
            )
            db.add(session_start_event)
            
            # Question answered events
            for i in range(session.completed_questions):
                answer_event = AnalyticsEvent(
                    user_id=user.id,
                    event_type="question_answered",
                    event_data={"question_number": i + 1, "session_id": str(session.id)},
                    session_id=session.id,
                    created_at=session.created_at + timedelta(minutes=i*3)
                )
                db.add(answer_event)
            
            # Session completed event
            if session.status == "completed":
                completed_event = AnalyticsEvent(
                    user_id=user.id,
                    event_type="session_completed",
                    event_data={
                        "role": session.role,
                        "session_id": str(session.id),
                        "total_questions": session.total_questions,
                        "overall_score": session.overall_score
                    },
                    session_id=session.id,
                    created_at=session.updated_at
                )
                db.add(completed_event)
    
    db.commit()

def create_agent_configurations(db: Session):
    """Create sample agent configurations."""
    logger.info("Creating agent configurations...")
    
    agent_configs = [
        {
            "agent_name": "technical_evaluator",
            "agent_type": "evaluation",
            "configuration": {
                "model": "gpt-4",
                "temperature": 0.3,
                "max_tokens": 1000,
                "evaluation_criteria": [
                    "technical_accuracy",
                    "problem_solving_approach",
                    "code_quality",
                    "architecture_understanding"
                ],
                "scoring_weights": {
                    "technical_accuracy": 0.4,
                    "problem_solving_approach": 0.3,
                    "code_quality": 0.2,
                    "architecture_understanding": 0.1
                }
            }
        },
        {
            "agent_name": "communication_analyzer",
            "agent_type": "analysis",
            "configuration": {
                "model": "gpt-3.5-turbo",
                "temperature": 0.2,
                "max_tokens": 800,
                "analysis_focus": [
                    "clarity_of_expression",
                    "confidence_level",
                    "articulation_quality",
                    "professional_tone"
                ]
            }
        },
        {
            "agent_name": "behavioral_assessor",
            "agent_type": "assessment",
            "configuration": {
                "model": "gpt-4",
                "temperature": 0.4,
                "max_tokens": 1200,
                "assessment_areas": [
                    "leadership_potential",
                    "team_collaboration",
                    "adaptability",
                    "cultural_fit"
                ]
            }
        }
    ]
    
    for config_data in agent_configs:
        # Check if agent already exists
        existing_agent = db.query(AgentConfiguration).filter(
            AgentConfiguration.agent_name == config_data["agent_name"]
        ).first()
        
        if existing_agent:
            logger.info(f"Agent {config_data['agent_name']} already exists, skipping...")
            continue
        
        agent = AgentConfiguration(
            agent_name=config_data["agent_name"],
            agent_type=config_data["agent_type"],
            configuration=config_data["configuration"],
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        db.add(agent)
        logger.info(f"Created agent configuration: {config_data['agent_name']}")
    
    db.commit()

def main():
    """Main function to seed the database."""
    logger.info("🌱 Starting database seeding...")
    
    try:
        # Get database session
        settings = get_settings()
        engine = create_engine(settings.DATABASE_URL)
        
        with Session(engine) as db:
            # Create demo users
            users = create_demo_users(db)
            logger.info(f"✅ Created {len(users)} users")
            
            # Create sample sessions
            sessions = create_sample_sessions(db, users)
            logger.info(f"✅ Created {len(sessions)} interview sessions")
            
            # Create sample questions
            questions = create_sample_questions(db, sessions)
            logger.info(f"✅ Created {len(questions)} questions")
            
            # Create sample answers
            answers = create_sample_answers(db, questions, sessions)
            logger.info(f"✅ Created {len(answers)} answers")
            
            # Create user performance data
            create_user_performance(db, users, sessions)
            logger.info("✅ Created user performance data")
            
            # Create analytics events
            create_analytics_events(db, users, sessions)
            logger.info("✅ Created analytics events")
            
            # Create agent configurations
            create_agent_configurations(db)
            logger.info("✅ Created agent configurations")
            
        logger.info("🎉 Database seeding completed successfully!")
        logger.info("\n📋 Demo Users Created:")
        for i, user_data in enumerate(DEMO_USERS):
            logger.info(f"  - {user_data['email']} (password: {user_data['password']})")
        
        logger.info("\n🚀 You can now start the application and test with these demo accounts!")
        
    except Exception as e:
        logger.error(f"❌ Error seeding database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
