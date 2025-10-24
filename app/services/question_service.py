"""
Question Service for Confida

This is the main question generation service that replaces 11+ overcomplicated
services with a single, clean, maintainable solution.

Replaces:
- QuestionEngine
- QuestionBankService  
- AsyncQuestionBankService
- AIFallbackService
- IntelligentQuestionSelector
- FunctionalQuestionSelector
- QuestionSelectionPipeline
- QuestionMatcher
- QuestionDiversityEngine
- AIServiceOrchestrator
- ServiceFactory
- DynamicPromptService
"""
import time
import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.database.models import Question
from app.database.question_database_models import QuestionTemplate
from app.services.smart_token_optimizer import SmartTokenOptimizer
from app.services.cost_tracker import CostTracker
from app.utils.logger import get_logger
from app.utils.prompt_templates import PromptTemplates
from app.exceptions import AIServiceError

logger = get_logger(__name__)


class QuestionService:
    """
    Main question generation service for Confida.
    
    This service replaces 11+ overcomplicated services with a single,
    clean, maintainable solution that handles all question generation needs.
    
    Features:
    - Database-first approach with AI fallback
    - Token optimization and cost tracking
    - Simple, direct implementation
    - Easy to test and maintain
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.token_optimizer = SmartTokenOptimizer()
        self.cost_tracker = CostTracker()
        
        # Initialize AI clients lazily to avoid circular imports
        self._openai_client = None
        self._anthropic_client = None
        self._ollama_service = None
    
    def generate_questions(self, role: str, job_description: str, count: int = 10, user_context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Generate questions using intelligent database-first approach with AI fallback.
        
        This method provides intelligent question selection with:
        - Role analysis and skill extraction
        - Database-first approach with diversity optimization
        - AI fallback for missing question types
        - User personalization and history consideration
        
        Args:
            role: Job title/role
            job_description: Job description text
            count: Number of questions to generate
            
            user_context: Optional user context for personalization
            
        Returns:
            List of question dictionaries with id, text, type, and metadata
        """
        start_time = time.time()
        logger.info(f"Generating {count} questions for role: {role}")
        
        try:
            # Step 1: Analyze role requirements
            role_analysis = self._analyze_role_requirements(role, job_description)
            logger.info(f"Role analysis: {role_analysis['industry']} {role_analysis['seniority_level']} with skills: {role_analysis['required_skills']}")
            
            # Step 2: Get database questions with intelligent selection
            db_questions = self._get_database_questions(role, job_description, count * 2)  # Get more for selection
            logger.info(f"Found {len(db_questions)} questions in database")
            
            # Step 3: Score and rank questions based on role analysis and user context
            if db_questions:
                scored_questions = self._calculate_question_scores(db_questions, role_analysis, user_context)
                # Sort by combined score
                scored_questions.sort(key=lambda x: x.get('combined_score', 0), reverse=True)
                # Ensure diversity
                diverse_questions = self._ensure_question_diversity(scored_questions, count, user_context)
            else:
                diverse_questions = []
            
            # Step 4: Fill gaps with AI if needed
            ai_questions = []
            if len(diverse_questions) < count:
                needed = count - len(diverse_questions)
                logger.info(f"Need {needed} more questions from AI")
                ai_questions = self._generate_ai_questions(role, job_description, needed)
            
            # Step 5: Combine and format results
            all_questions = diverse_questions + ai_questions
            formatted_questions = self._format_questions(all_questions, role, start_time)
            
            # Step 6: Add intelligent metadata
            for i, question in enumerate(formatted_questions):
                if i < len(diverse_questions):
                    # Add intelligent selection metadata
                    question['selection_method'] = 'intelligent_database'
                    question['role_relevance_score'] = diverse_questions[i].get('role_relevance_score', 0.5)
                    question['user_preference_score'] = diverse_questions[i].get('user_preference_score', 0.5)
                else:
                    question['selection_method'] = 'ai_fallback'
            
            # Step 7: Log generation metrics
            self._log_generation_metrics(role, job_description, len(diverse_questions), len(ai_questions), start_time)
            
            logger.info(f"Generated {len(formatted_questions)} questions total ({len(diverse_questions)} intelligent, {len(ai_questions)} AI)")
            return formatted_questions
            
        except Exception as e:
            logger.error(f"Error generating questions for role {role}: {e}")
            raise AIServiceError(f"Failed to generate questions: {e}")
    
    def _get_database_questions(self, role: str, job_description: str, count: int) -> List[QuestionTemplate]:
        """Get questions from database using simple, direct queries."""
        try:
            # Simple role-based query - use basic filtering for now
            role_lower = role.lower()
            
            # Query for active questions (simplified approach)
            questions = self.db.query(QuestionTemplate).filter(
                QuestionTemplate.is_active == True
            ).order_by(
                QuestionTemplate.quality_score.desc(),
                QuestionTemplate.usage_count.asc()  # Prefer less used questions
            ).limit(count).all()
            
            # Update usage count for analytics
            from datetime import datetime
            for question in questions:
                question.usage_count += 1
                question.last_used = datetime.utcnow()
            
            self.db.commit()
            return questions
            
        except Exception as e:
            logger.error(f"Error querying database questions: {e}")
            return []
    
    def _generate_ai_questions(self, role: str, job_description: str, count: int) -> List[Dict[str, Any]]:
        """Generate questions using AI with token optimization."""
        try:
            # Get token optimization using the correct method name
            optimization = self.token_optimizer.optimize_request(role, job_description, "ollama")
            optimal_tokens = optimization.optimal_tokens
            recommended_service = "ollama"  # Default to ollama for simplicity
            
            logger.info(f"Using {recommended_service} with {optimal_tokens} tokens")
            
            # Generate questions using Ollama (simplified approach)
            questions = self._generate_with_ollama(role, job_description, count, optimal_tokens)
            
            # Track cost using legacy method
            self.cost_tracker.track_request_legacy(
                service=recommended_service,
                operation="generate_questions",
                tokens_used=optimal_tokens,
                estimated_cost=optimization.estimated_cost,
                success=True
            )
            
            return questions
            
        except Exception as e:
            logger.error(f"Error generating AI questions: {e}")
            return []
    
    def _generate_with_ollama(self, role: str, job_description: str, count: int, max_tokens: int) -> List[Dict[str, Any]]:
        """Generate questions using Ollama service."""
        try:
            if not self._ollama_service:
                from app.services.ollama_service import OllamaService
                self._ollama_service = OllamaService()
            
            # Use the correct method name
            response = self._ollama_service.generate_interview_questions(role, job_description)
            
            # Extract questions from response
            questions = []
            for i, question_text in enumerate(response.questions, 1):
                questions.append({
                    "question_text": question_text,
                    "question_type": self._classify_question_type(question_text),
                    "difficulty_level": "medium",
                    "category": "ai_generated",
                    "source": "ollama",
                    "quality_score": 0.8,
                    "usage_count": 0
                })
            
            return questions
            
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            return []
    
    def _generate_with_openai(self, role: str, job_description: str, count: int, max_tokens: int) -> List[Dict[str, Any]]:
        """Generate questions using OpenAI service."""
        try:
            if not self._openai_client:
                from app.utils.service_initializer import ServiceInitializer
                self._openai_client = ServiceInitializer.init_openai_client()
            
            import os
            model = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
            prompt = PromptTemplates.get_question_generation_prompt(role, job_description)
            
            response = self._openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": PromptTemplates.QUESTION_GENERATION_SYSTEM},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            return self._parse_ai_response(content, "openai")
            
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            return []
    
    def _generate_with_anthropic(self, role: str, job_description: str, count: int, max_tokens: int) -> List[Dict[str, Any]]:
        """Generate questions using Anthropic service."""
        try:
            if not self._anthropic_client:
                from app.utils.service_initializer import ServiceInitializer
                self._anthropic_client = ServiceInitializer.init_anthropic_client()
            
            import os
            model = os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229")
            prompt = PromptTemplates.get_question_generation_prompt(role, job_description)
            
            response = self._anthropic_client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=PromptTemplates.QUESTION_GENERATION_SYSTEM,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text
            return self._parse_ai_response(content, "anthropic")
            
        except Exception as e:
            logger.error(f"Anthropic generation failed: {e}")
            return []
    
    def _parse_ai_response(self, response: str, service: str) -> List[Dict[str, Any]]:
        """Parse AI response into question format."""
        try:
            questions = []
            lines = response.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if line and (line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')) or 
                           line.startswith(('•', '-', '*'))):
                    # Clean up the question text
                    question_text = line
                    for prefix in ['1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '•', '-', '*']:
                        if question_text.startswith(prefix):
                            question_text = question_text[len(prefix):].strip()
                            break
                    
                    if question_text:
                        questions.append({
                            "question_text": question_text,
                            "question_type": self._classify_question_type(question_text),
                            "difficulty_level": "medium",
                            "category": "ai_generated",
                            "source": service,
                            "quality_score": 0.8,  # Default quality for AI questions
                            "usage_count": 0
                        })
            
            return questions
            
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
            return []
    
    def _format_questions(self, questions: List, role: str, start_time: float) -> List[Dict[str, Any]]:
        """Format questions into consistent dictionary format."""
        formatted = []
        
        for i, question in enumerate(questions, 1):
            if hasattr(question, 'question_text'):
                # Database question
                formatted.append({
                    "id": str(question.id),
                    "text": question.question_text,
                    "type": question.question_type or self._classify_question_type(question.question_text),
                    "difficulty_level": question.difficulty_level,
                    "category": question.question_type,  # Use question_type as category
                    "source": "database",
                    "quality_score": question.quality_score,
                    "metadata": {
                        "generation_method": "database",
                        "processing_time_ms": int((time.time() - start_time) * 1000)
                    }
                })
            else:
                # AI question
                formatted.append({
                    "id": f"ai_{hash(role)}_{i}",
                    "text": question["question_text"],
                    "type": question["question_type"],
                    "difficulty_level": question["difficulty_level"],
                    "category": question["category"],
                    "source": question["source"],
                    "quality_score": question["quality_score"],
                    "metadata": {
                        "generation_method": "ai",
                        "processing_time_ms": int((time.time() - start_time) * 1000)
                    }
                })
        
        return formatted
    
    def _classify_question_type(self, question_text: str) -> str:
        """Classify question type based on content."""
        question_lower = question_text.lower()
        
        if any(keyword in question_lower for keyword in [
            "code", "programming", "algorithm", "database", "system", "architecture",
            "debug", "optimize", "performance", "security", "testing"
        ]):
            return "technical"
        
        if any(keyword in question_lower for keyword in [
            "tell me about a time", "describe a situation", "give me an example",
            "how did you handle", "what did you do when", "share an experience"
        ]):
            return "behavioral"
        
        if any(keyword in question_lower for keyword in [
            "what would you do if", "how would you handle", "imagine you",
            "suppose you", "if you were", "scenario"
        ]):
            return "situational"
        
        return "general"
    
    def _extract_seniority(self, role: str) -> str:
        """Extract seniority level from role."""
        role_lower = role.lower()
        
        if any(level in role_lower for level in ["senior", "sr", "lead", "principal", "staff", "architect"]):
            return "senior"
        elif any(level in role_lower for level in ["junior", "jr", "entry", "associate"]):
            return "junior"
        elif any(level in role_lower for level in ["manager", "director", "vp", "cto", "head"]):
            return "manager"
        else:
            return "mid"
    
    def _extract_tech_domains(self, job_description: str) -> List[str]:
        """Extract technical domains from job description."""
        domains = []
        desc_lower = job_description.lower()
        
        tech_mapping = {
            "frontend": ["react", "angular", "vue", "javascript", "typescript", "html", "css"],
            "backend": ["python", "java", "node", "api", "server", "database"],
            "cloud": ["aws", "azure", "gcp", "cloud", "kubernetes", "docker"],
            "mobile": ["ios", "android", "mobile", "swift", "kotlin"],
            "data": ["data", "analytics", "machine learning", "ai", "sql", "python"]
        }
        
        for domain, keywords in tech_mapping.items():
            if any(keyword in desc_lower for keyword in keywords):
                domains.append(domain)
        
        return domains
    
    def _log_generation_metrics(self, role: str, job_description: str, db_count: int, ai_count: int, start_time: float):
        """Log generation metrics for analytics."""
        try:
            processing_time = int((time.time() - start_time) * 1000)
            
            logger.info(f"Question generation metrics - Role: {role}, "
                       f"DB questions: {db_count}, AI questions: {ai_count}, "
                       f"Processing time: {processing_time}ms")
            
            # Could store in database for analytics if needed
            # self._store_generation_log(role, job_description, db_count, ai_count, processing_time)
            
        except Exception as e:
            logger.error(f"Error logging generation metrics: {e}")
    
    def get_available_scenarios(self) -> List[Dict[str, str]]:
        """
        Get available practice scenarios.
        
        This method provides backward compatibility with the old QuestionEngine.
        """
        try:
            from app.services.scenario_service import ScenarioService
            scenario_service = ScenarioService(self.db)
            scenarios = scenario_service.get_all_scenarios()
            
            scenario_list = []
            for scenario in scenarios:
                scenario_list.append({
                    "id": scenario.id,
                    "name": scenario.name,
                    "description": scenario.description or f"Practice questions for {scenario.name} roles",
                    "category": scenario.category,
                    "difficulty_level": scenario.difficulty_level,
                    "compatible_roles": scenario.compatible_roles
                })
            
            return scenario_list
            
        except Exception as e:
            logger.error(f"Error retrieving scenarios: {e}")
            return []
    
    def generate_questions_from_scenario(self, scenario_id: str) -> List[Dict[str, Any]]:
        """
        Generate questions from a practice scenario.
        
        This method provides backward compatibility with the old QuestionEngine.
        """
        try:
            from app.services.scenario_service import ScenarioService
            scenario_service = ScenarioService(self.db)
            questions = scenario_service.get_scenario_questions(scenario_id)
            
            if questions:
                scenario_service.increment_usage_count(scenario_id)
            
            return questions
            
        except Exception as e:
            logger.error(f"Error generating questions from scenario {scenario_id}: {e}")
            return []
    
    def _analyze_role_requirements(self, role: str, job_description: str) -> Dict[str, Any]:
        """
        Analyze role requirements using the consolidated role analysis processor.
        
        Returns:
            Dictionary with extracted role information
        """
        try:
            # Use the consolidated role analysis processor
            from app.services.role_analysis_processor import RoleAnalysisProcessor
            
            processor = RoleAnalysisProcessor()
            
            # Process job description for detailed analysis
            job_summary = processor.process_job_description(job_description)
            
            # Perform role analysis
            role_analysis = processor.analyze_role(role, job_description)
            
            return {
                'industry': role_analysis.industry.value if role_analysis.industry else 'technology',
                'seniority_level': role_analysis.seniority_level.value if role_analysis.seniority_level else 'mid',
                'required_skills': role_analysis.required_skills,
                'company_size': role_analysis.company_size.value if role_analysis.company_size else 'medium',
                'tech_stack': role_analysis.tech_stack,
                'soft_skills': role_analysis.soft_skills,
                'experience_years': role_analysis.experience_years,
                'job_function': role_analysis.job_function,
                'education_requirements': job_summary.education_requirements,
                'certifications': job_summary.certifications
            }
            
        except Exception as e:
            logger.warning(f"Error analyzing role requirements: {e}")
            return {
                'industry': 'technology',
                'seniority_level': 'mid',
                'required_skills': [],
                'company_size': 'medium',
                'tech_stack': [],
                'soft_skills': ['communication', 'teamwork', 'problem solving'],
                'experience_years': None,
                'job_function': 'engineering',
                'education_requirements': [],
                'certifications': []
            }
    
    def _ensure_question_diversity(self, questions: List[Dict[str, Any]], target_count: int, user_context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Ensure question diversity using simple category-based selection."""
        if len(questions) <= target_count:
            return questions
        
        # Simple category-based selection
        categories = ['technical', 'behavioral', 'system_design']
        selected = []
        per_category = target_count // len(categories)
        
        for category in categories:
            cat_questions = [q for q in questions if q.get('category') == category]
            selected.extend(cat_questions[:per_category])
        
        return selected[:target_count]
    
    
    def _calculate_question_scores(self, questions: List[Dict[str, Any]], role_analysis: Dict[str, Any], user_context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Calculate relevance scores for questions based on role analysis and user context.
        
        Args:
            questions: List of questions to score
            role_analysis: Role analysis results
            user_context: Optional user context for personalization
            
        Returns:
            Questions with calculated scores
        """
        scored_questions = []
        
        for question in questions:
            # Base quality score
            quality_score = question.get('quality_score', 0.5)
            
            # Role relevance score
            role_relevance = self._calculate_role_relevance(question, role_analysis)
            
            # User preference score
            user_preference = 0.5  # default
            if user_context:
                user_preference = self._calculate_user_preference(question, user_context)
            
            # Combined score
            combined_score = (quality_score * 0.4 + role_relevance * 0.4 + user_preference * 0.2)
            
            question_with_score = question.copy()
            question_with_score.update({
                'role_relevance_score': role_relevance,
                'user_preference_score': user_preference,
                'combined_score': combined_score
            })
            
            scored_questions.append(question_with_score)
        
        return scored_questions
    
    def _calculate_role_relevance(self, question: Dict[str, Any], role_analysis: Dict[str, Any]) -> float:
        """Calculate how relevant a question is to the role."""
        try:
            question_text = question.get('text', '').lower()
            question_tags = question.get('tags', [])
            
            # Check for skill matches
            required_skills = role_analysis.get('required_skills', [])
            skill_matches = sum(1 for skill in required_skills if skill.lower() in question_text or skill.lower() in [tag.lower() for tag in question_tags])
            
            # Check for industry relevance
            industry = role_analysis.get('industry', 'technology')
            industry_keywords = {
                'technology': ['software', 'code', 'programming', 'development', 'engineering'],
                'finance': ['financial', 'banking', 'investment', 'trading', 'risk'],
                'healthcare': ['medical', 'health', 'clinical', 'patient', 'treatment'],
                'education': ['teaching', 'learning', 'education', 'academic', 'curriculum']
            }
            
            industry_relevance = 0.5  # default
            if industry in industry_keywords:
                industry_matches = sum(1 for keyword in industry_keywords[industry] if keyword in question_text)
                industry_relevance = min(1.0, industry_matches / len(industry_keywords[industry]))
            
            # Combine scores
            skill_relevance = min(1.0, skill_matches / max(1, len(required_skills)))
            role_relevance = (skill_relevance * 0.7 + industry_relevance * 0.3)
            
            return min(1.0, role_relevance)
            
        except Exception as e:
            logger.warning(f"Error calculating role relevance: {e}")
            return 0.5
    
    def _calculate_user_preference(self, question: Dict[str, Any], user_context: Dict[str, Any]) -> float:
        """Calculate user preference score based on history and preferences."""
        try:
            # Check if user has seen this question before
            previous_questions = user_context.get('previous_questions', [])
            question_id = question.get('id', '')
            
            if question_id in previous_questions:
                return 0.2  # Lower score for previously seen questions
            
            # Check difficulty preference
            preferred_difficulty = user_context.get('preferred_difficulty')
            question_difficulty = question.get('difficulty', 'medium')
            
            if preferred_difficulty and preferred_difficulty.lower() == question_difficulty.lower():
                return 0.8  # Higher score for preferred difficulty
            
            # Check weak areas (avoid questions in weak areas unless specifically requested)
            weak_areas = user_context.get('weak_areas', [])
            question_tags = question.get('tags', [])
            
            if any(area.lower() in [tag.lower() for tag in question_tags] for area in weak_areas):
                return 0.3  # Lower score for weak areas
            
            return 0.5  # Default score
            
        except Exception as e:
            logger.warning(f"Error calculating user preference: {e}")
            return 0.5
