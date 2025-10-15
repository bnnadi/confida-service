"""
Dynamic Prompt Service for AI-Generated Interview Questions.

This service generates role-specific prompts using AI based on role analysis
to create highly relevant interview questions for any industry or job function.
"""
from typing import Dict, Any, Optional
from app.services.role_analysis_service import RoleAnalysis, IndustryType, JobFunction, SeniorityLevel
from app.utils.logger import get_logger
from app.utils.service_initializer import ServiceInitializer
import os

logger = get_logger(__name__)


class DynamicPromptService:
    """Service for generating dynamic prompts based on role analysis."""
    
    def __init__(self):
        self.openai_client = ServiceInitializer.init_openai_client()
        self.anthropic_client = ServiceInitializer.init_anthropic_client()
    
    def generate_question_prompt(self, role: str, job_description: str, 
                               analysis: RoleAnalysis) -> str:
        """
        Generate a dynamic prompt for question generation based on role analysis.
        
        Args:
            role: Job title/role
            job_description: Full job description text
            analysis: Role analysis result
            
        Returns:
            Generated prompt for AI question generation
        """
        try:
            # Use AI to generate the prompt
            if self.openai_client:
                return self._generate_prompt_with_openai(role, job_description, analysis)
            elif self.anthropic_client:
                return self._generate_prompt_with_anthropic(role, job_description, analysis)
            else:
                # Fallback to template-based prompt
                return self._generate_template_prompt(role, job_description, analysis)
                
        except Exception as e:
            logger.error(f"Error generating dynamic prompt: {e}")
            return self._generate_template_prompt(role, job_description, analysis)
    
    def _generate_prompt_with_openai(self, role: str, job_description: str, 
                                   analysis: RoleAnalysis) -> str:
        """Generate prompt using OpenAI."""
        system_prompt = self._get_prompt_generation_system_prompt()
        
        user_prompt = f"""
        Generate a comprehensive interview question prompt for the following role and job description.
        
        Role: {role}
        Job Description: {job_description}
        
        Role Analysis:
        - Industry: {analysis.industry.value}
        - Job Function: {analysis.job_function.value}
        - Seniority Level: {analysis.seniority_level.value}
        - Key Skills: {', '.join(analysis.key_skills)}
        - Confidence Score: {analysis.confidence_score}
        
        Create a detailed prompt that will generate 10 highly relevant interview questions for this specific role.
        The prompt should be tailored to the industry, job function, and seniority level.
        Include specific guidance on what types of questions to ask and what to focus on.
        
        Return only the generated prompt, ready to be used for question generation.
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=800,
                temperature=0.7
            )
            
            generated_prompt = response.choices[0].message.content.strip()
            logger.info(f"Generated dynamic prompt using OpenAI for {analysis.industry.value} {analysis.job_function.value}")
            return generated_prompt
            
        except Exception as e:
            logger.error(f"OpenAI prompt generation failed: {e}")
            return self._generate_template_prompt(role, job_description, analysis)
    
    def _generate_prompt_with_anthropic(self, role: str, job_description: str, 
                                      analysis: RoleAnalysis) -> str:
        """Generate prompt using Anthropic Claude."""
        system_prompt = self._get_prompt_generation_system_prompt()
        
        user_prompt = f"""
        Generate a comprehensive interview question prompt for the following role and job description.
        
        Role: {role}
        Job Description: {job_description}
        
        Role Analysis:
        - Industry: {analysis.industry.value}
        - Job Function: {analysis.job_function.value}
        - Seniority Level: {analysis.seniority_level.value}
        - Key Skills: {', '.join(analysis.key_skills)}
        - Confidence Score: {analysis.confidence_score}
        
        Create a detailed prompt that will generate 10 highly relevant interview questions for this specific role.
        The prompt should be tailored to the industry, job function, and seniority level.
        Include specific guidance on what types of questions to ask and what to focus on.
        
        Return only the generated prompt, ready to be used for question generation.
        """
        
        try:
            response = self.anthropic_client.messages.create(
                model=os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229"),
                max_tokens=800,
                temperature=0.7,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            generated_prompt = response.content[0].text.strip()
            logger.info(f"Generated dynamic prompt using Anthropic for {analysis.industry.value} {analysis.job_function.value}")
            return generated_prompt
            
        except Exception as e:
            logger.error(f"Anthropic prompt generation failed: {e}")
            return self._generate_template_prompt(role, job_description, analysis)
    
    def _get_prompt_generation_system_prompt(self) -> str:
        """Get the system prompt for prompt generation."""
        return """You are an expert interview prompt generator with deep knowledge across all industries.
        
        Your task is to create highly specific, role-appropriate interview question prompts that will generate
        relevant questions for any job role, industry, or seniority level.
        
        Guidelines for prompt generation:
        1. Tailor the prompt to the specific industry and job function
        2. Adjust difficulty and focus based on seniority level
        3. Include industry-specific terminology and context
        4. Focus on relevant skills and competencies
        5. Consider both technical and soft skills as appropriate
        6. Make the prompt clear and actionable for AI question generation
        
        The generated prompt should be comprehensive enough to produce 10 high-quality,
        role-specific interview questions that would effectively assess a candidate's
        suitability for the position."""
    
    def _generate_template_prompt(self, role: str, job_description: str, 
                                analysis: RoleAnalysis) -> str:
        """Generate template-based prompt as fallback."""
        industry_context = self._get_industry_context(analysis.industry)
        seniority_context = self._get_seniority_context(analysis.seniority_level)
        function_context = self._get_function_context(analysis.job_function)
        
        return f"""
        You are an expert {industry_context} interviewer specializing in {analysis.job_function.value} roles.
        
        Generate 10 highly relevant interview questions for a {analysis.seniority_level.value} {role} position.
        
        Role: {role}
        Job Description: {job_description}
        
        Industry Context: {industry_context}
        Seniority Level: {seniority_context}
        Job Function Focus: {function_context}
        Key Skills to Assess: {', '.join(analysis.key_skills)}
        
        Create questions that cover:
        1. Role-specific technical skills and knowledge
        2. Industry experience and understanding
        3. Problem-solving and critical thinking
        4. Past experience relevant to this {analysis.seniority_level.value} level
        5. Soft skills and cultural fit
        
        Ensure questions are appropriate for a {analysis.seniority_level.value} level position
        in the {analysis.industry.value} industry.
        
        Return only the questions as a numbered list, one per line. Do not include any other text.
        """
    
    def _get_industry_context(self, industry: IndustryType) -> str:
        """Get industry-specific context."""
        contexts = {
            IndustryType.TECHNOLOGY: "technology and software development",
            IndustryType.HEALTHCARE: "healthcare and medical services",
            IndustryType.FINANCE: "finance and banking",
            IndustryType.SALES_MARKETING: "sales and marketing",
            IndustryType.UNKNOWN: "general business"
        }
        return contexts.get(industry, "general business")
    
    def _get_seniority_context(self, seniority: SeniorityLevel) -> str:
        """Get seniority-specific context."""
        contexts = {
            SeniorityLevel.JUNIOR: "entry-level position requiring foundational knowledge and eagerness to learn",
            SeniorityLevel.MID: "mid-level position requiring solid experience and independent work capability",
            SeniorityLevel.SENIOR: "senior-level position requiring deep expertise and leadership potential",
            SeniorityLevel.LEAD: "leadership position requiring technical expertise and team management skills",
            SeniorityLevel.UNKNOWN: "position requiring relevant experience and skills"
        }
        return contexts.get(seniority, "position requiring relevant experience and skills")
    
    def _get_function_context(self, job_function: JobFunction) -> str:
        """Get job function-specific context."""
        contexts = {
            JobFunction.DEVELOPMENT: "software development and programming",
            JobFunction.DATA_SCIENCE: "data science and analytics",
            JobFunction.DEVOPS: "DevOps and infrastructure management",
            JobFunction.NURSING: "nursing and patient care",
            JobFunction.MEDICAL: "medical practice and patient treatment",
            JobFunction.BANKING: "banking and financial services",
            JobFunction.INSURANCE: "insurance and risk management",
            JobFunction.SALES: "sales and business development",
            JobFunction.MARKETING: "marketing and brand management",
            JobFunction.MANAGEMENT: "management and leadership",
            JobFunction.OPERATIONS: "operations and process management",
            JobFunction.UNKNOWN: "general professional responsibilities"
        }
        return contexts.get(job_function, "general professional responsibilities")
    
    def get_prompt_metadata(self, analysis: RoleAnalysis) -> Dict[str, Any]:
        """Get metadata about the generated prompt."""
        return {
            "industry": analysis.industry.value,
            "job_function": analysis.job_function.value,
            "seniority_level": analysis.seniority_level.value,
            "key_skills": analysis.key_skills,
            "confidence_score": analysis.confidence_score,
            "analysis_hash": analysis.analysis_hash,
            "prompt_type": "dynamic_ai_generated"
        }
