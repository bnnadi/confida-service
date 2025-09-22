"""
Centralized prompt templates to eliminate duplication across AI services.
"""

class PromptTemplates:
    """Centralized prompt templates for all AI services."""
    
    QUESTION_GENERATION_SYSTEM = """You are an expert technical interviewer with deep knowledge of software engineering roles. 
    Your task is to generate relevant interview questions based on job descriptions."""
    
    ANALYSIS_SYSTEM = """You are an expert interview coach with deep knowledge of technical interviews. 
    Your task is to analyze candidate answers and provide constructive feedback."""
    
    @staticmethod
    def get_question_generation_prompt(role: str, job_description: str) -> str:
        """Generate the user prompt for question generation."""
        return f"""
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
    
    @staticmethod
    def get_analysis_prompt(job_description: str, question: str, answer: str) -> str:
        """Generate the user prompt for answer analysis."""
        return f"""
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
