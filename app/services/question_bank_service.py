"""
Question Bank Service for intelligent question selection and management.

This service provides the foundation for the database-first question bank system,
enabling 80-90% reduction in AI API calls while maintaining high-quality question sets.
"""
import hashlib
import json
import random
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from app.database.models import Question, SessionQuestion, InterviewSession
from app.database.question_database_models import QuestionTemplate, QuestionGenerationLog
from app.utils.logger import get_logger
from app.utils.validation_mixin import ValidationMixin
from app.services.difficulty_rule_engine import DifficultyRuleEngine, CategoryRuleEngine
# Lazy imports to avoid circular dependencies
# from app.services.hybrid_ai_service import HybridAIService
# from app.services.smart_token_optimizer import SmartTokenOptimizer
from app.models.schemas import ParseJDResponse
import time
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

logger = get_logger(__name__)

class QuestionBankService:
    """Service for managing the global question bank and intelligent question selection."""
    
    # Centralized categorization rules (shared with async service)
    CATEGORIZATION_RULES = {
        "behavioral": [
            "experience", "tell me about", "describe", "situation", "behavioral"
        ],
        "system_design": [
            "system", "architecture", "design", "scale", "distributed"
        ],
        "leadership": [
            "lead", "manage", "team", "mentor", "leadership"
        ],
        "technical": []  # Default category
    }
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.difficulty_engine = DifficultyRuleEngine()
        self.category_engine = CategoryRuleEngine()
        
        # Phase 2 enhancements (lazy initialization to avoid circular imports)
        self.ai_service = None
        self.token_optimizer = None
        
        # Configuration
        self.min_database_questions = 3
        self.max_ai_fallback_questions = 7
        self.min_confidence_threshold = 0.6
    
    def get_questions_for_role(self, role: str, job_description: str, count: int = 10) -> List[Question]:
        """
        Get questions for a specific role using intelligent selection algorithms.
        
        Args:
            role: The job role/title
            job_description: The job description text
            count: Number of questions to return
            
        Returns:
            List of selected questions
        """
        try:
            # Clear, step-by-step approach
            role_analysis = self._analyze_role(role, job_description)
            compatible_questions = self._find_compatible_questions(role_analysis)
            diverse_questions = self._ensure_question_diversity(compatible_questions, count)
            self._update_usage_stats(diverse_questions)
            
            logger.info(f"Selected {len(diverse_questions)} questions for role '{role}'")
            return diverse_questions
            
        except Exception as e:
            logger.error(f"Error selecting questions for role '{role}': {e}")
            return self._get_fallback_questions(role, count)
    
    def get_questions_hybrid(self, role: str, job_description: str, count: int = 10, 
                           preferred_service: Optional[str] = None) -> Dict[str, Any]:
        """
        Get questions using hybrid approach: database first, AI fallback.
        
        Args:
            role: The job role/title
            job_description: The job description text
            count: Number of questions to return
            preferred_service: Preferred AI service for fallback
            
        Returns:
            Dictionary with questions and metadata
        """
        start_time = time.time()
        
        try:
            # Try database first
            db_questions = self.get_questions_for_role(role, job_description, count)
            
            # Determine if we need AI fallback
            questions_needed = count - len(db_questions)
            ai_questions = []
            ai_service_used = None
            tokens_used = 0
            estimated_cost = 0.0
            
            if questions_needed > 0:
                logger.info(f"Need {questions_needed} more questions from AI")
                ai_questions, ai_service_used, tokens_used, estimated_cost = self._get_ai_questions(
                    role, job_description, questions_needed, preferred_service
                )
            
            # Combine questions
            all_questions = db_questions + ai_questions
            
            # Determine generation method
            if len(db_questions) >= count:
                generation_method = 'database'
            elif len(ai_questions) >= count:
                generation_method = 'ai'
            else:
                generation_method = 'hybrid'
            
            # Log the generation
            self._log_generation(
                role, job_description, generation_method, ai_service_used, 
                tokens_used, estimated_cost, len(all_questions), len(db_questions), 
                len(ai_questions), int((time.time() - start_time) * 1000)
            )
            
            return {
                'questions': all_questions,
                'generation_method': generation_method,
                'database_questions': len(db_questions),
                'ai_questions': len(ai_questions),
                'total_tokens_used': tokens_used,
                'estimated_cost': estimated_cost,
                'processing_time_ms': int((time.time() - start_time) * 1000),
                'ai_service_used': ai_service_used
            }
            
        except Exception as e:
            logger.error(f"Error in hybrid question generation: {e}")
            return self._fallback_to_ai(role, job_description, count, preferred_service, start_time)
    
    def _get_ai_questions(self, role: str, job_description: str, questions_needed: int, 
                         preferred_service: Optional[str]) -> Tuple[List[Question], str, int, float]:
        """Get questions from AI service as fallback."""
        try:
            # Lazy initialization to avoid circular imports
            if self.token_optimizer is None:
                from app.services.smart_token_optimizer import SmartTokenOptimizer
                self.token_optimizer = SmartTokenOptimizer()
            
            if self.ai_service is None:
                from app.services.hybrid_ai_service import HybridAIService
                self.ai_service = HybridAIService(self.db)
            
            # Optimize token usage for AI generation
            optimization_result = self.token_optimizer.optimize_request(
                role, job_description, preferred_service or 'openai', questions_needed
            )
            
            # Generate questions using AI service
            ai_response = self.ai_service.generate_interview_questions(role, job_description, preferred_service)
            
            # Convert to Question objects
            ai_questions = []
            for i, question_text in enumerate(ai_response.questions[:questions_needed]):
                question = Question(
                    question_text=question_text,
                    question_metadata={"source": "ai_generated", "ai_service": preferred_service or 'openai'},
                    difficulty_level="medium",
                    category="ai_generated"
                )
                ai_questions.append(question)
            
            # Calculate actual tokens used (simplified)
            tokens_used = optimization_result.optimal_tokens
            estimated_cost = optimization_result.estimated_cost
            
            logger.info(f"Generated {len(ai_questions)} AI questions using {preferred_service or 'openai'}")
            return ai_questions, preferred_service or 'openai', tokens_used, estimated_cost
            
        except Exception as e:
            logger.error(f"Error getting AI questions: {e}")
            return [], preferred_service or 'openai', 0, 0.0
    
    def _log_generation(self, role: str, job_description: str, generation_method: str,
                       ai_service_used: Optional[str], tokens_used: int, estimated_cost: float,
                       total_questions: int, db_questions: int, ai_questions: int, processing_time_ms: int):
        """Log the question generation for analytics."""
        try:
            # Lazy initialization to avoid circular imports
            if self.token_optimizer is None:
                from app.services.smart_token_optimizer import SmartTokenOptimizer
                self.token_optimizer = SmartTokenOptimizer()
            
            # Calculate complexity score
            complexity_score = self.token_optimizer._analyze_complexity(role, job_description)['total_score']
            
            log_entry = QuestionGenerationLog(
                role=role,
                job_description_length=len(job_description.split()),
                complexity_score=complexity_score,
                generation_method=generation_method,
                ai_service_used=ai_service_used,
                tokens_used=tokens_used,
                estimated_cost=estimated_cost,
                questions_generated=total_questions,
                questions_from_database=db_questions,
                questions_from_ai=ai_questions,
                match_quality_score=0.8 if db_questions > 0 else 0.0,
                processing_time_ms=processing_time_ms
            )
            
            self.db.add(log_entry)
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error logging generation: {e}")
            self.db.rollback()
    
    def _fallback_to_ai(self, role: str, job_description: str, count: int,
                       preferred_service: Optional[str], start_time: float) -> Dict[str, Any]:
        """Fallback to AI-only generation when database fails."""
        try:
            logger.warning("Falling back to AI-only generation")
            
            ai_questions, ai_service_used, tokens_used, estimated_cost = self._get_ai_questions(
                role, job_description, count, preferred_service
            )
            
            return {
                'questions': ai_questions,
                'generation_method': 'ai',
                'database_questions': 0,
                'ai_questions': len(ai_questions),
                'total_tokens_used': tokens_used,
                'estimated_cost': estimated_cost,
                'processing_time_ms': int((time.time() - start_time) * 1000),
                'ai_service_used': ai_service_used
            }
            
        except Exception as e:
            logger.error(f"Error in AI fallback: {e}")
            return {
                'questions': [],
                'generation_method': 'ai',
                'database_questions': 0,
                'ai_questions': 0,
                'total_tokens_used': 0,
                'estimated_cost': 0.0,
                'processing_time_ms': int((time.time() - start_time) * 1000),
                'ai_service_used': preferred_service or 'openai'
            }
    
    def store_generated_questions(self, questions: List[str], role: str, job_description: str, 
                                ai_service_used: str, prompt_hash: str) -> List[Question]:
        """
        Store AI-generated questions in the question bank for future reuse.
        
        Args:
            questions: List of question texts
            role: The job role
            job_description: The job description
            ai_service_used: Which AI service generated these questions
            prompt_hash: Hash of the generation prompt
            
        Returns:
            List of stored Question objects
        """
        try:
            role_analysis = self._analyze_role(role, job_description)
            stored_questions = []
            
            for question_text in questions:
                # Check if similar question already exists
                existing_question = self._find_similar_question(question_text)
                if existing_question:
                    logger.info(f"Similar question already exists, skipping: {question_text[:50]}...")
                    stored_questions.append(existing_question)
                    continue
                
                # Create new question
                question = Question(
                    question_text=question_text,
                    question_metadata=self._create_question_metadata(role_analysis),
                    difficulty_level=self._determine_difficulty(question_text, role_analysis),
                    category=self._categorize_question(question_text),
                    subcategory=self._get_subcategory(question_text),
                    compatible_roles=[role],
                    required_skills=role_analysis.get('required_skills', []),
                    industry_tags=role_analysis.get('industry_tags', []),
                    ai_service_used=ai_service_used,
                    generation_prompt_hash=prompt_hash
                )
                
                self.db.add(question)
                stored_questions.append(question)
            
            self.db.commit()
            logger.info(f"Stored {len(stored_questions)} new questions in question bank")
            return stored_questions
            
        except Exception as e:
            logger.error(f"Error storing questions: {e}")
            self.db.rollback()
            return []
    
    def link_questions_to_session(self, session_id: str, questions: List[Question], 
                                session_context: Optional[Dict] = None) -> List[SessionQuestion]:
        """
        Link questions to a session with ordering and context.
        
        Args:
            session_id: The session ID
            questions: List of questions to link
            session_context: Optional session-specific context
            
        Returns:
            List of SessionQuestion objects
        """
        try:
            session_questions = []
            
            for i, question in enumerate(questions):
                session_question = SessionQuestion(
                    session_id=session_id,
                    question_id=question.id,
                    question_order=i + 1,
                    session_specific_context=session_context
                )
                self.db.add(session_question)
                session_questions.append(session_question)
            
            self.db.commit()
            logger.info(f"Linked {len(session_questions)} questions to session {session_id}")
            return session_questions
            
        except Exception as e:
            logger.error(f"Error linking questions to session: {e}")
            self.db.rollback()
            return []
    
    def get_session_questions(self, session_id: str) -> List[Tuple[Question, SessionQuestion]]:
        """
        Get all questions for a session with their session-specific data.
        
        Args:
            session_id: The session ID
            
        Returns:
            List of (Question, SessionQuestion) tuples ordered by question_order
        """
        try:
            results = self.db.query(Question, SessionQuestion)\
                .join(SessionQuestion, Question.id == SessionQuestion.question_id)\
                .filter(SessionQuestion.session_id == session_id)\
                .order_by(SessionQuestion.question_order)\
                .all()
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting session questions: {e}")
            return []
    
    def update_question_performance(self, question_id: str, score: float, success: bool):
        """
        Update question performance metrics.
        
        Args:
            question_id: The question ID
            score: The score received (0-10)
            success: Whether the answer was considered successful
        """
        try:
            question = self.db.query(Question).filter(Question.id == question_id).first()
            if not question:
                logger.warning(f"Question {question_id} not found for performance update")
                return
            
            # Update usage count
            question.usage_count += 1
            
            # Update performance metrics using helper methods
            question.average_score = self._update_running_average(question.average_score, score, question.usage_count)
            question.success_rate = self._update_success_rate(question.success_rate, success, question.usage_count)
            
            self.db.commit()
            logger.debug(f"Updated performance for question {question_id}: score={score}, success={success}")
            
        except Exception as e:
            logger.error(f"Error updating question performance: {e}")
            self.db.rollback()
    
    def _analyze_role(self, role: str, job_description: str) -> Dict[str, Any]:
        """Analyze role and job description to extract key information."""
        # Simple role analysis - can be enhanced with NLP in the future
        role_lower = role.lower()
        jd_lower = job_description.lower()
        
        # Extract skills (basic keyword matching)
        skills = []
        skill_keywords = {
            'python': ['python', 'django', 'flask', 'fastapi'],
            'javascript': ['javascript', 'node.js', 'react', 'vue', 'angular'],
            'java': ['java', 'spring', 'hibernate'],
            'sql': ['sql', 'postgresql', 'mysql', 'database'],
            'aws': ['aws', 'amazon web services', 'cloud'],
            'docker': ['docker', 'kubernetes', 'containerization'],
            'machine_learning': ['ml', 'machine learning', 'ai', 'tensorflow', 'pytorch']
        }
        
        for skill, keywords in skill_keywords.items():
            if any(keyword in jd_lower for keyword in keywords):
                skills.append(skill)
        
        # Determine industry
        industry = 'technology'  # Default
        industry_keywords = {
            'finance': ['banking', 'finance', 'fintech', 'investment'],
            'healthcare': ['healthcare', 'medical', 'pharmaceutical'],
            'ecommerce': ['ecommerce', 'retail', 'shopping'],
            'education': ['education', 'learning', 'edtech']
        }
        
        for ind, keywords in industry_keywords.items():
            if any(keyword in jd_lower for keyword in keywords):
                industry = ind
                break
        
        # Determine seniority level
        seniority = 'mid'  # Default
        if any(word in jd_lower for word in ['senior', 'lead', 'principal', 'architect']):
            seniority = 'senior'
        elif any(word in jd_lower for word in ['junior', 'entry', 'graduate']):
            seniority = 'junior'
        
        return {
            'role': role,
            'required_skills': skills,
            'industry': industry,
            'seniority_level': seniority,
            'job_description': job_description
        }
    
    def _find_compatible_questions(self, role_analysis: Dict[str, Any]) -> List[Question]:
        """Find questions compatible with the role analysis."""
        try:
            # Build query conditions
            conditions = []
            
            # Filter by compatible roles
            if role_analysis.get('role'):
                conditions.append(
                    or_(
                        Question.compatible_roles.contains([role_analysis['role']]),
                        Question.compatible_roles.is_(None)  # Questions without role restrictions
                    )
                )
            
            # Filter by required skills
            if role_analysis.get('required_skills'):
                skill_conditions = []
                for skill in role_analysis['required_skills']:
                    skill_conditions.append(Question.required_skills.contains([skill]))
                if skill_conditions:
                    conditions.append(or_(*skill_conditions))
            
            # Filter by industry
            if role_analysis.get('industry'):
                conditions.append(
                    or_(
                        Question.industry_tags.contains([role_analysis['industry']]),
                        Question.industry_tags.is_(None)  # Questions without industry restrictions
                    )
                )
            
            # Base query
            query = self.db.query(Question)
            
            # Apply conditions
            if conditions:
                query = query.filter(and_(*conditions))
            
            # Order by quality metrics (success rate, usage count)
            query = query.order_by(
                desc(Question.success_rate),
                desc(Question.usage_count),
                desc(Question.average_score)
            )
            
            # Limit to reasonable number for diversity selection
            compatible_questions = query.limit(100).all()
            
            logger.debug(f"Found {len(compatible_questions)} compatible questions for role analysis")
            return compatible_questions
            
        except Exception as e:
            logger.error(f"Error finding compatible questions: {e}")
            return []
    
    def _ensure_question_diversity(self, questions: List[Question], count: int) -> List[Question]:
        """Ensure question diversity using functional approach."""
        if len(questions) <= count:
            return questions
        
        # Group questions by category and difficulty
        grouped = self._group_questions_by_diversity(questions)
        
        # Select diverse questions first, then fill remaining slots
        selected = self._select_diverse_questions(grouped, count)
        remaining_needed = count - len(selected)
        
        if remaining_needed > 0:
            remaining = [q for q in questions if q not in selected]
            remaining.sort(key=lambda q: (q.success_rate or 0, q.usage_count), reverse=True)
            selected.extend(remaining[:remaining_needed])
        
        return selected[:count]
    
    def _group_questions_by_diversity(self, questions: List[Question]) -> Dict[str, List[Question]]:
        """Group questions by category and difficulty."""
        from collections import defaultdict
        grouped = defaultdict(list)
        for question in questions:
            key = f"{question.category}_{question.difficulty_level}"
            grouped[key].append(question)
        return grouped
    
    def _select_diverse_questions(self, grouped: Dict[str, List[Question]], count: int) -> List[Question]:
        """Select one question from each diversity group."""
        selected = []
        for questions in grouped.values():
            if questions and len(selected) < count:
                # Select best question from this group
                best_question = max(questions, key=lambda q: (q.success_rate or 0, q.usage_count))
                selected.append(best_question)
        return selected
    
    def _update_usage_stats(self, questions: List[Question]):
        """Update usage statistics for selected questions."""
        try:
            for question in questions:
                question.usage_count += 1
            self.db.commit()
        except Exception as e:
            logger.error(f"Error updating usage stats: {e}")
            self.db.rollback()
    
    def _get_fallback_questions(self, role: str, count: int) -> List[Question]:
        """Get fallback questions when intelligent selection fails."""
        try:
            # Get most popular questions as fallback
            questions = self.db.query(Question)\
                .order_by(desc(Question.usage_count))\
                .limit(count)\
                .all()
            
            if not questions:
                logger.warning("No questions found in question bank for fallback")
                return []
            
            return questions
            
        except Exception as e:
            logger.error(f"Error getting fallback questions: {e}")
            return []
    
    def _find_similar_question(self, question_text: str) -> Optional[Question]:
        """Find if a similar question already exists in the database."""
        try:
            # Use database-level similarity search for better performance
            words = set(question_text.lower().split())
            if not words:
                return None
            
            # Create a search pattern for database query
            search_pattern = ' '.join(f'%{word}%' for word in words)
            
            # Query with similarity threshold at database level
            similar_questions = self.db.query(Question)\
                .filter(Question.question_text.ilike(f'%{search_pattern}%'))\
                .limit(10)\
                .all()
            
            # Find best match using similarity calculation
            best_match = None
            best_similarity = 0.0
            
            for question in similar_questions:
                similarity = self._calculate_similarity(question_text, question.question_text)
                if similarity > 0.8 and similarity > best_similarity:
                    best_match = question
                    best_similarity = similarity
            
            return best_match
            
        except Exception as e:
            logger.error(f"Error finding similar question: {e}")
            return None
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity based on word overlap."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _create_question_metadata(self, role_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Create metadata for a question based on role analysis."""
        return {
            'role_analysis': role_analysis,
            'generated_at': '2024-01-15T10:00:00Z',  # Will be set by database
            'version': '1.0'
        }
    
    # Data-driven difficulty rules
    DIFFICULTY_RULES = [
        ('seniority', {'senior': 'hard', 'junior': 'easy', 'mid': 'medium'}),
        ('keywords', {
            'hard': ['complex', 'advanced', 'architecture', 'design', 'optimize'],
            'easy': ['basic', 'simple', 'explain', 'what is']
        })
    ]

    def _determine_difficulty(self, question_text: str, role_analysis: Dict[str, Any]) -> str:
        """Determine question difficulty using rule engine."""
        return self.difficulty_engine.determine_difficulty(question_text, role_analysis)
    
    def _categorize_question(self, question_text: str) -> str:
        """Categorize question using data-driven configuration."""
        scores = {}
        text_lower = question_text.lower()
        
        for category, config in self.CATEGORIZATION_CONFIG.items():
            score = 0
            for keyword in config["keywords"]:
                if keyword in text_lower:
                    score += config["weight"]
            scores[category] = score
        
        # Return category with highest score, or technical as default
        return max(scores, key=scores.get) if any(scores.values()) else "technical"
    
    def _categorize_by_keywords(self, text: str, rules: Dict[str, List[str]]) -> str:
        """Generic keyword-based categorization."""
        return ValidationMixin.categorize_by_keywords(text, rules)
    
    def _update_running_average(self, current_avg: Optional[float], new_value: float, count: int) -> float:
        """Calculate running average with null handling."""
        return new_value if current_avg is None else (current_avg * (count - 1) + new_value) / count

    def _update_success_rate(self, current_rate: Optional[float], success: bool, count: int) -> float:
        """Calculate running success rate with null handling."""
        if current_rate is None:
            return 1.0 if success else 0.0
        
        total_successes = current_rate * (count - 1)
        if success:
            total_successes += 1
        return total_successes / count

    def _get_subcategory(self, question_text: str) -> Optional[str]:
        """Get question subcategory based on content."""
        text_lower = question_text.lower()
        
        # Technical subcategories
        if 'algorithm' in text_lower or 'data structure' in text_lower:
            return 'algorithms'
        elif 'database' in text_lower or 'sql' in text_lower:
            return 'database'
        elif 'api' in text_lower or 'rest' in text_lower:
            return 'api_design'
        elif 'security' in text_lower or 'auth' in text_lower:
            return 'security'
        elif 'testing' in text_lower or 'test' in text_lower:
            return 'testing'
        
        return None
    
    def get_question_bank_stats(self) -> Dict[str, Any]:
        """Get statistics about the question bank."""
        try:
            total_questions = self.db.query(Question).count()
            categories = self.db.query(Question.category, func.count(Question.id))\
                .group_by(Question.category)\
                .all()
            difficulties = self.db.query(Question.difficulty_level, func.count(Question.id))\
                .group_by(Question.difficulty_level)\
                .all()
            
            return {
                'total_questions': total_questions,
                'categories': dict(categories),
                'difficulties': dict(difficulties),
                'avg_usage_count': self.db.query(func.avg(Question.usage_count)).scalar() or 0,
                'avg_success_rate': self.db.query(func.avg(Question.success_rate)).scalar() or 0
            }
            
        except Exception as e:
            logger.error(f"Error getting question bank stats: {e}")
            return {}
