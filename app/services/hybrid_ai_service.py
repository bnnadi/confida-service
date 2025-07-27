import os
import json
import requests
from typing import List, Dict, Any, Optional
from enum import Enum
from app.models.schemas import ParseJDResponse, AnalyzeAnswerResponse, Score
from app.services.ollama_service import OllamaService

class AIServiceType(Enum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"

class HybridAIService:
    def __init__(self):
        self.ollama_service = OllamaService()
        self.service_priority = self._get_service_priority()
        self.openai_client = None
        self.anthropic_client = None
        
        # Initialize external services if configured
        self._init_external_services()
    
    def _get_service_priority(self) -> List[AIServiceType]:
        """Get service priority based on configuration."""
        priority = []
        
        # Check which services are configured
        if os.getenv("OLLAMA_BASE_URL"):
            priority.append(AIServiceType.OLLAMA)
        
        if os.getenv("OPENAI_API_KEY"):
            priority.append(AIServiceType.OPENAI)
        
        if os.getenv("ANTHROPIC_API_KEY"):
            priority.append(AIServiceType.ANTHROPIC)
        
        # Default to Ollama if nothing configured
        if not priority:
            priority.append(AIServiceType.OLLAMA)
        
        return priority
    
    def _init_external_services(self):
        """Initialize external AI service clients with better error handling."""
        # Initialize OpenAI
        if os.getenv("OPENAI_API_KEY"):
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                print("✅ OpenAI client initialized successfully")
            except ImportError:
                print("⚠️ OpenAI library not installed")
            except Exception as e:
                print(f"❌ Error initializing OpenAI client: {e}")
                self.openai_client = None
        
        # Initialize Anthropic
        if os.getenv("ANTHROPIC_API_KEY"):
            try:
                import anthropic
                self.anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
                print("✅ Anthropic client initialized successfully")
            except ImportError:
                print("⚠️ Anthropic library not installed")
            except Exception as e:
                print(f"❌ Error initializing Anthropic client: {e}")
                self.anthropic_client = None
    
    def generate_interview_questions(self, role: str, job_description: str, 
                                   preferred_service: Optional[str] = None) -> ParseJDResponse:
        """Generate questions using the best available service."""
        
        services_to_try = self._get_services_to_try(preferred_service)
        
        for service_type in services_to_try:
            try:
                if service_type == AIServiceType.OLLAMA:
                    return self.ollama_service.generate_interview_questions(role, job_description)
                elif service_type == AIServiceType.OPENAI:
                    return self._generate_questions_openai(role, job_description)
                elif service_type == AIServiceType.ANTHROPIC:
                    return self._generate_questions_anthropic(role, job_description)
            except Exception as e:
                print(f"Error with {service_type.value}: {e}")
                continue
        
        # If all services fail, return fallback
        return self._get_fallback_questions(role)
    
    def analyze_answer(self, job_description: str, question: str, answer: str,
                      preferred_service: Optional[str] = None) -> AnalyzeAnswerResponse:
        """Analyze answer using the best available service."""
        
        services_to_try = self._get_services_to_try(preferred_service)
        
        for service_type in services_to_try:
            try:
                if service_type == AIServiceType.OLLAMA:
                    return self.ollama_service.analyze_answer(job_description, question, answer)
                elif service_type == AIServiceType.OPENAI:
                    return self._analyze_answer_openai(job_description, question, answer)
                elif service_type == AIServiceType.ANTHROPIC:
                    return self._analyze_answer_anthropic(job_description, question, answer)
            except Exception as e:
                print(f"Error with {service_type.value}: {e}")
                continue
        
        # If all services fail, return fallback
        return self._get_fallback_analysis()
    
    def _get_services_to_try(self, preferred_service: Optional[str] = None) -> List[AIServiceType]:
        """Get list of services to try in order."""
        if preferred_service:
            # Try preferred service first
            for service_type in AIServiceType:
                if service_type.value == preferred_service.lower():
                    return [service_type] + [s for s in self.service_priority if s != service_type]
        
        return self.service_priority
    
    def _generate_questions_openai(self, role: str, job_description: str) -> ParseJDResponse:
        """Generate questions using OpenAI."""
        if not self.openai_client:
            raise Exception("OpenAI client not initialized")
        
        system_prompt = """You are an expert technical interviewer with deep knowledge of software engineering roles. 
        Your task is to generate relevant interview questions based on job descriptions."""
        
        user_prompt = f"""
        Based on the following job description and role, generate 10 relevant interview questions that would help assess a candidate's suitability.

        Role: {role}
        Job Description: {job_description}

        Generate questions that cover:
        1. Technical skills specific to the role
        2. Problem-solving and critical thinking
        3. Past experience and projects
        4. Soft skills and teamwork
        5. Industry knowledge and trends

        Return only the questions as a numbered list, one per line. Do not include any other text.
        """
        
        response = self.openai_client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        questions_text = response.choices[0].message.content.strip()
        questions = self._parse_questions_from_response(questions_text)
        
        return ParseJDResponse(questions=questions)
    
    def _generate_questions_anthropic(self, role: str, job_description: str) -> ParseJDResponse:
        """Generate questions using Anthropic Claude."""
        if not self.anthropic_client:
            raise Exception("Anthropic client not initialized")
        
        system_prompt = """You are an expert technical interviewer with deep knowledge of software engineering roles. 
        Your task is to generate relevant interview questions based on job descriptions."""
        
        user_prompt = f"""
        Based on the following job description and role, generate 10 relevant interview questions that would help assess a candidate's suitability.

        Role: {role}
        Job Description: {job_description}

        Generate questions that cover:
        1. Technical skills specific to the role
        2. Problem-solving and critical thinking
        3. Past experience and projects
        4. Soft skills and teamwork
        5. Industry knowledge and trends

        Return only the questions as a numbered list, one per line. Do not include any other text.
        """
        
        response = self.anthropic_client.messages.create(
            model=os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229"),
            max_tokens=1000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        
        questions_text = response.content[0].text.strip()
        questions = self._parse_questions_from_response(questions_text)
        
        return ParseJDResponse(questions=questions)
    
    def _analyze_answer_openai(self, job_description: str, question: str, answer: str) -> AnalyzeAnswerResponse:
        """Analyze answer using OpenAI."""
        if not self.openai_client:
            raise Exception("OpenAI client not initialized")
        
        system_prompt = """You are an expert interview coach with deep knowledge of technical interviews. 
        Your task is to analyze candidate answers and provide constructive feedback."""
        
        user_prompt = f"""
        Analyze the following candidate's answer to an interview question.

        Job Description: {job_description}
        Question: {question}
        Candidate's Answer: {answer}

        Provide a comprehensive analysis in the following JSON format:
        {{
            "score": {{
                "clarity": <score 1-10>,
                "confidence": <score 1-10>
            }},
            "missingKeywords": ["keyword1", "keyword2"],
            "improvements": ["improvement1", "improvement2"],
            "idealAnswer": "detailed ideal answer here"
        }}

        Focus on:
        1. How well the answer addresses the question
        2. Relevance to the job description
        3. Specific examples and metrics mentioned
        4. Technical depth and accuracy
        5. Communication clarity and confidence
        """
        
        response = self.openai_client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=1500,
            temperature=0.3
        )
        
        analysis_text = response.choices[0].message.content.strip()
        return self._parse_analysis_response(analysis_text)
    
    def _analyze_answer_anthropic(self, job_description: str, question: str, answer: str) -> AnalyzeAnswerResponse:
        """Analyze answer using Anthropic Claude."""
        if not self.anthropic_client:
            raise Exception("Anthropic client not initialized")
        
        system_prompt = """You are an expert interview coach with deep knowledge of technical interviews. 
        Your task is to analyze candidate answers and provide constructive feedback."""
        
        user_prompt = f"""
        Analyze the following candidate's answer to an interview question.

        Job Description: {job_description}
        Question: {question}
        Candidate's Answer: {answer}

        Provide a comprehensive analysis in the following JSON format:
        {{
            "score": {{
                "clarity": <score 1-10>,
                "confidence": <score 1-10>
            }},
            "missingKeywords": ["keyword1", "keyword2"],
            "improvements": ["improvement1", "improvement2"],
            "idealAnswer": "detailed ideal answer here"
        }}

        Focus on:
        1. How well the answer addresses the question
        2. Relevance to the job description
        3. Specific examples and metrics mentioned
        4. Technical depth and accuracy
        5. Communication clarity and confidence
        """
        
        response = self.anthropic_client.messages.create(
            model=os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229"),
            max_tokens=1500,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        
        analysis_text = response.content[0].text.strip()
        return self._parse_analysis_response(analysis_text)
    
    def _parse_questions_from_response(self, response_text: str) -> List[str]:
        """Parse questions from AI response."""
        lines = [line.strip() for line in response_text.split('\n') if line.strip()]
        questions = []
        
        for line in lines:
            # Remove numbering if present
            if '. ' in line:
                question = line.split('. ', 1)[-1]
            elif ') ' in line:
                question = line.split(') ', 1)[-1]
            else:
                question = line
            
            # Clean up the question
            question = question.strip()
            if question and not question.startswith('Here') and not question.startswith('These'):
                questions.append(question)
        
        # Limit to 10 questions
        return questions[:10]
    
    def _parse_analysis_response(self, response_text: str) -> AnalyzeAnswerResponse:
        """Parse analysis from AI response."""
        try:
            # Try to extract JSON from the response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                analysis = json.loads(json_str)
                
                return AnalyzeAnswerResponse(
                    score=Score(
                        clarity=analysis.get("score", {}).get("clarity", 5),
                        confidence=analysis.get("score", {}).get("confidence", 5)
                    ),
                    missingKeywords=analysis.get("missingKeywords", []),
                    improvements=analysis.get("improvements", []),
                    idealAnswer=analysis.get("idealAnswer", "")
                )
        except Exception as e:
            print(f"Error parsing analysis response: {e}")
        
        return self._get_fallback_analysis()
    
    def _get_fallback_questions(self, role: str) -> ParseJDResponse:
        """Fallback questions if all services fail."""
        return ParseJDResponse(questions=[
            f"Tell me about your experience with {role}",
            "Describe a challenging project you've worked on",
            "How do you handle tight deadlines?",
            "What's your approach to problem-solving?",
            "How do you stay updated with industry trends?",
            "Tell me about a time you had to learn a new technology quickly",
            "How do you handle conflicting priorities?",
            "What's your experience with code review?",
            "How do you ensure code quality?",
            "Describe a situation where you had to mentor junior developers"
        ])
    
    def _get_fallback_analysis(self) -> AnalyzeAnswerResponse:
        """Fallback analysis if all services fail."""
        return AnalyzeAnswerResponse(
            score=Score(clarity=5, confidence=5),
            missingKeywords=["specific examples", "metrics", "technical details"],
            improvements=[
                "Provide more specific examples",
                "Include quantifiable results",
                "Add more technical details",
                "Demonstrate problem-solving approach"
            ],
            idealAnswer="Please provide a more detailed answer with specific examples, measurable outcomes, and technical depth."
        )
    
    def get_available_services(self) -> Dict[str, bool]:
        """Get status of available AI services."""
        return {
            "ollama": bool(os.getenv("OLLAMA_BASE_URL")),
            "openai": bool(os.getenv("OPENAI_API_KEY") and self.openai_client is not None),
            "anthropic": bool(os.getenv("ANTHROPIC_API_KEY") and self.anthropic_client is not None)
        }
    
    def get_service_priority(self) -> List[str]:
        """Get current service priority order."""
        return [service.value for service in self.service_priority] 