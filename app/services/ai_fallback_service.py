"""
AI fallback service for generating questions when database has insufficient variety.
Integrates with AI services to generate targeted questions for missing types.
"""
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from app.services.role_analysis_service import RoleAnalysis
from app.services.question_diversity_engine import Question, QuestionCategory, DifficultyLevel
from app.services.hybrid_ai_service import HybridAIService
from app.services.async_question_bank_service import AsyncQuestionBankService
from app.utils.logger import get_logger
from app.utils.metrics import metrics
import time
import hashlib

logger = get_logger(__name__)

@dataclass
class QuestionGenerationRequest:
    """Request for AI question generation."""
    role_analysis: RoleAnalysis
    missing_categories: List[str]
    missing_difficulties: List[str]
    target_count: int
    existing_questions: List[Question]
    user_context: Optional[Dict[str, Any]] = None

@dataclass
class QuestionGenerationResult:
    """Result of AI question generation."""
    generated_questions: List[Question]
    generation_time: float
    ai_service_used: str
    questions_stored: int
    success_rate: float

class AIFallbackService:
    """Service for AI-powered question generation when database has insufficient variety."""
    
    def __init__(self, db_session=None):
        self.ai_service = HybridAIService()
        self.question_bank_service = AsyncQuestionBankService(db_session) if db_session else None
        
        # Generation configuration
        self.max_questions_per_type = 3
        self.max_generation_attempts = 3
        self.generation_timeout = 30  # seconds
        
        # AI service preferences
        self.ai_service_preferences = ["openai", "anthropic", "ollama"]
        
        # Question templates for different categories
        self.question_templates = {
            QuestionCategory.TECHNICAL: {
                "prompt_template": "Generate {count} technical interview questions for a {role} position in {industry}. "
                                 "Focus on {skills}. Difficulty level: {difficulty}. "
                                 "Include questions about {tech_stack}.",
                "keywords": ["programming", "algorithms", "data structures", "system design", "debugging"]
            },
            QuestionCategory.BEHAVIORAL: {
                "prompt_template": "Generate {count} behavioral interview questions for a {role} position. "
                                 "Focus on {seniority_level} level scenarios. "
                                 "Include questions about {soft_skills}.",
                "keywords": ["teamwork", "leadership", "problem solving", "communication", "conflict resolution"]
            },
            QuestionCategory.SYSTEM_DESIGN: {
                "prompt_template": "Generate {count} system design interview questions for a {role} position. "
                                 "Difficulty: {difficulty}. Focus on {industry} domain. "
                                 "Include scalability and performance considerations.",
                "keywords": ["scalability", "performance", "architecture", "distributed systems", "databases"]
            },
            QuestionCategory.LEADERSHIP: {
                "prompt_template": "Generate {count} leadership interview questions for a {role} position. "
                                 "Seniority level: {seniority_level}. "
                                 "Focus on team management, decision making, and strategic thinking.",
                "keywords": ["team management", "decision making", "strategic thinking", "mentoring", "conflict resolution"]
            },
            QuestionCategory.DATA_ANALYSIS: {
                "prompt_template": "Generate {count} data analysis interview questions for a {role} position. "
                                 "Focus on {tech_stack}. Difficulty: {difficulty}. "
                                 "Include statistical analysis and data visualization.",
                "keywords": ["statistics", "data visualization", "machine learning", "analytics", "data modeling"]
            }
        }

    async def generate_missing_questions(self, 
                                       request: QuestionGenerationRequest) -> QuestionGenerationResult:
        """Generate questions for missing types and difficulties."""
        start_time = time.time()
        
        try:
            logger.info(f"Generating AI questions for missing categories: {request.missing_categories}")
            
            generated_questions = []
            successful_generations = 0
            total_attempts = 0
            
            # Generate questions for each missing category
            for category in request.missing_categories:
                try:
                    category_questions = await self._generate_questions_for_category(
                        category, request
                    )
                    generated_questions.extend(category_questions)
                    successful_generations += 1
                    total_attempts += 1
                    
                except Exception as e:
                    logger.error(f"Error generating questions for category {category}: {e}")
                    total_attempts += 1
                    continue
            
            # Generate questions for missing difficulties if needed
            if len(generated_questions) < request.target_count:
                difficulty_questions = await self._generate_questions_for_difficulties(request)
                generated_questions.extend(difficulty_questions)
            
            # Store generated questions in database
            stored_count = await self._store_generated_questions(generated_questions, request.role_analysis)
            
            # Calculate metrics
            generation_time = time.time() - start_time
            success_rate = successful_generations / max(1, total_attempts)
            
            result = QuestionGenerationResult(
                generated_questions=generated_questions,
                generation_time=generation_time,
                ai_service_used="hybrid",  # Using hybrid AI service
                questions_stored=stored_count,
                success_rate=success_rate
            )
            
            # Record metrics
            await self._record_generation_metrics(result)
            
            logger.info(f"AI question generation completed: {len(generated_questions)} questions generated, "
                       f"{stored_count} stored, success rate: {success_rate:.2%}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in AI fallback service: {e}")
            return QuestionGenerationResult(
                generated_questions=[],
                generation_time=time.time() - start_time,
                ai_service_used="error",
                questions_stored=0,
                success_rate=0.0
            )

    def _create_questions_from_ai_response(self, ai_response, category: str, 
                                         role_analysis: RoleAnalysis, max_count: int) -> List[Question]:
        """Create Question objects from AI response."""
        questions = []
        template_info = self.question_templates.get(QuestionCategory(category), {})
        
        for i, question_text in enumerate(ai_response.questions[:max_count]):
            question = Question(
                id=self._generate_question_id(category, role_analysis, i),
                question_text=question_text,
                category=QuestionCategory(category),
                difficulty_level=self._determine_difficulty_for_category(category, role_analysis),
                tags=self._extract_tags_from_question(question_text, template_info.get("keywords", [])),
                role_relevance_score=0.8,
                quality_score=0.7
            )
            questions.append(question)
        return questions
    
    async def _generate_questions_for_category(self, 
                                             category: str, 
                                             request: QuestionGenerationRequest) -> List[Question]:
        """Generate questions for a specific category."""
        try:
            # Get template for category
            template_info = self.question_templates.get(QuestionCategory(category), {})
            prompt_template = template_info.get("prompt_template", 
                "Generate {count} {category} interview questions for a {role} position.")
            
            # Build generation prompt
            prompt = self._build_generation_prompt(prompt_template, category, request)
            
            # Generate questions using AI service
            ai_response = await self._call_ai_service(prompt, request.role_analysis)
            
            # Convert AI response to Question objects using factory method
            return self._create_questions_from_ai_response(
                ai_response, category, request.role_analysis, self.max_questions_per_type
            )
            
        except Exception as e:
            logger.error(f"Error generating questions for category {category}: {e}")
            return []

    async def _generate_questions_for_difficulties(self, 
                                                 request: QuestionGenerationRequest) -> List[Question]:
        """Generate questions for missing difficulty levels."""
        try:
            # Determine which difficulties are missing
            existing_difficulties = set(q.difficulty_level.value for q in request.existing_questions)
            missing_difficulties = [d for d in request.missing_difficulties if d not in existing_difficulties]
            
            if not missing_difficulties:
                return []
            
            questions = []
            for difficulty in missing_difficulties:
                # Generate questions for this difficulty level
                prompt = self._build_difficulty_prompt(difficulty, request)
                ai_response = await self._call_ai_service(prompt, request.role_analysis)
                
                # Use factory method for consistency
                difficulty_questions = self._create_questions_from_ai_response(
                    ai_response, "technical", request.role_analysis, 2
                )
                
                # Override difficulty level for these questions
                for question in difficulty_questions:
                    question.difficulty_level = DifficultyLevel(difficulty)
                    question.id = self._generate_question_id(f"difficulty_{difficulty}", request.role_analysis, len(questions))
                
                questions.extend(difficulty_questions)
            
            return questions
            
        except Exception as e:
            logger.error(f"Error generating questions for difficulties: {e}")
            return []

    def _build_generation_prompt(self, 
                               template: str, 
                               category: str, 
                               request: QuestionGenerationRequest) -> str:
        """Build AI generation prompt from template."""
        role_analysis = request.role_analysis
        
        # Determine count based on missing categories
        count = min(3, max(1, request.target_count // len(request.missing_categories)))
        
        # Build prompt with role analysis data
        prompt = template.format(
            count=count,
            role=role_analysis.primary_role,
            industry=role_analysis.industry.value,
            skills=', '.join(role_analysis.required_skills[:5]),
            difficulty=self._get_difficulty_for_prompt(role_analysis),
            tech_stack=', '.join(role_analysis.tech_stack[:3]),
            seniority_level=role_analysis.seniority_level.value,
            soft_skills=', '.join(role_analysis.soft_skills[:3])
        )
        
        # Add specific instructions
        prompt += f"\n\nPlease generate {count} high-quality {category} interview questions. "
        prompt += "Each question should be specific, actionable, and relevant to the role. "
        prompt += "Include a mix of conceptual and practical questions."
        
        return prompt

    def _build_difficulty_prompt(self, 
                               difficulty: str, 
                               request: QuestionGenerationRequest) -> str:
        """Build prompt for specific difficulty level."""
        role_analysis = request.role_analysis
        
        prompt = f"Generate 2 {difficulty} level interview questions for a {role_analysis.primary_role} position. "
        prompt += f"Industry: {role_analysis.industry.value}. "
        prompt += f"Seniority: {role_analysis.seniority_level.value}. "
        prompt += f"Focus on: {', '.join(role_analysis.required_skills[:3])}. "
        
        if difficulty == "easy":
            prompt += "Questions should test basic knowledge and understanding."
        elif difficulty == "medium":
            prompt += "Questions should test practical application and problem-solving skills."
        else:  # hard
            prompt += "Questions should test advanced concepts, system design, and complex problem-solving."
        
        return prompt

    async def _call_ai_service(self, prompt: str, role_analysis: RoleAnalysis) -> Any:
        """Call AI service to generate questions."""
        try:
            # Use the hybrid AI service to generate questions
            response = await self.ai_service.generate_interview_questions(
                role=role_analysis.primary_role,
                job_description=prompt,
                preferred_service="openai"  # Prefer OpenAI for question generation
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error calling AI service: {e}")
            # Fallback to different AI service
            try:
                response = await self.ai_service.generate_interview_questions(
                    role=role_analysis.primary_role,
                    job_description=prompt,
                    preferred_service="anthropic"
                )
                return response
            except Exception as e2:
                logger.error(f"Error with fallback AI service: {e2}")
                raise

    def _determine_difficulty_for_category(self, 
                                         category: str, 
                                         role_analysis: RoleAnalysis) -> DifficultyLevel:
        """Determine appropriate difficulty level for a category."""
        # Map categories to typical difficulty levels
        category_difficulty_map = {
            QuestionCategory.TECHNICAL: DifficultyLevel.MEDIUM,
            QuestionCategory.BEHAVIORAL: DifficultyLevel.EASY,
            QuestionCategory.SYSTEM_DESIGN: DifficultyLevel.HARD,
            QuestionCategory.LEADERSHIP: DifficultyLevel.HARD,
            QuestionCategory.DATA_ANALYSIS: DifficultyLevel.MEDIUM
        }
        
        base_difficulty = category_difficulty_map.get(QuestionCategory(category), DifficultyLevel.MEDIUM)
        
        # Adjust based on seniority level
        if role_analysis.seniority_level.value in ['junior', 'entry']:
            if base_difficulty == DifficultyLevel.HARD:
                return DifficultyLevel.MEDIUM
        elif role_analysis.seniority_level.value in ['senior', 'staff', 'principal']:
            if base_difficulty == DifficultyLevel.EASY:
                return DifficultyLevel.MEDIUM
        
        return base_difficulty

    def _get_difficulty_for_prompt(self, role_analysis: RoleAnalysis) -> str:
        """Get difficulty level string for prompt generation."""
        return role_analysis.seniority_level.value

    def _extract_tags_from_question(self, 
                                  question_text: str, 
                                  category_keywords: List[str]) -> List[str]:
        """Extract relevant tags from question text."""
        tags = []
        question_lower = question_text.lower()
        
        for keyword in category_keywords:
            if keyword.lower() in question_lower:
                tags.append(keyword)
        
        return tags[:5]  # Limit to 5 tags

    def _generate_question_id(self, 
                            category: str, 
                            role_analysis: RoleAnalysis, 
                            index: int) -> str:
        """Generate unique ID for AI-generated question."""
        # Create a hash based on category, role, and index
        content = f"{category}_{role_analysis.primary_role}_{index}_{time.time()}"
        hash_id = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"ai_{category}_{hash_id}"

    async def _store_generated_questions(self, 
                                       questions: List[Question], 
                                       role_analysis: RoleAnalysis) -> int:
        """Store generated questions in the database."""
        if not self.question_bank_service or not questions:
            return 0
        
        try:
            stored_count = 0
            for question in questions:
                try:
                    # Convert Question to database format
                    question_data = {
                        'question_text': question.question_text,
                        'category': question.category.value,
                        'difficulty_level': question.difficulty_level.value,
                        'tags': question.tags,
                        'role': role_analysis.primary_role,
                        'industry': role_analysis.industry.value,
                        'seniority_level': role_analysis.seniority_level.value,
                        'quality_score': question.quality_score,
                        'source': 'ai_generated',
                        'metadata': {
                            'generated_at': time.time(),
                            'role_analysis': {
                                'required_skills': role_analysis.required_skills,
                                'tech_stack': role_analysis.tech_stack,
                                'company_size': role_analysis.company_size.value
                            }
                        }
                    }
                    
                    # Store in question bank
                    await self.question_bank_service.store_generated_questions(
                        [question_data], 
                        role_analysis.primary_role,
                        f"AI generated for {role_analysis.industry.value}",
                        "ai_fallback_service"
                    )
                    stored_count += 1
                    
                except Exception as e:
                    logger.error(f"Error storing question {question.id}: {e}")
                    continue
            
            return stored_count
            
        except Exception as e:
            logger.error(f"Error storing generated questions: {e}")
            return 0

    async def _record_generation_metrics(self, result: QuestionGenerationResult):
        """Record metrics for AI question generation."""
        try:
            # Record AI service usage
            metrics.record_ai_service_request(
                service=result.ai_service_used,
                operation="question_generation",
                status="success" if result.success_rate > 0.5 else "partial_success",
                duration=result.generation_time
            )
            
            logger.info(f"AI fallback metrics - "
                       f"Questions generated: {len(result.generated_questions)}, "
                       f"Questions stored: {result.questions_stored}, "
                       f"Success rate: {result.success_rate:.2%}, "
                       f"Generation time: {result.generation_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Error recording generation metrics: {e}")

    def get_generation_report(self, result: QuestionGenerationResult) -> Dict[str, Any]:
        """Generate a detailed generation report."""
        return {
            "generation_summary": {
                "total_generated": len(result.generated_questions),
                "questions_stored": result.questions_stored,
                "success_rate": result.success_rate,
                "generation_time": result.generation_time,
                "ai_service_used": result.ai_service_used
            },
            "question_breakdown": {
                "categories": [q.category.value for q in result.generated_questions],
                "difficulties": [q.difficulty_level.value for q in result.generated_questions],
                "average_quality_score": sum(q.quality_score for q in result.generated_questions) / max(1, len(result.generated_questions)),
                "average_relevance_score": sum(q.role_relevance_score for q in result.generated_questions) / max(1, len(result.generated_questions))
            },
            "storage_info": {
                "storage_success_rate": result.questions_stored / max(1, len(result.generated_questions)),
                "storage_failures": len(result.generated_questions) - result.questions_stored
            }
        }
