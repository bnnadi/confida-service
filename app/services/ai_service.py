import os
from typing import List
from openai import OpenAI
from app.models.schemas import ParseJDResponse, AnalyzeAnswerResponse, Score
from dotenv import load_dotenv

load_dotenv()

class AIService:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
    
    def generate_interview_questions(self, role: str, job_description: str) -> ParseJDResponse:
        """Generate role-specific interview questions using AI."""
        
        prompt = f"""
        You are an expert technical interviewer. Based on the following job description and role, 
        generate 10 relevant interview questions that would help assess a candidate's suitability.
        
        Role: {role}
        Job Description: {job_description}
        
        Generate questions that cover:
        1. Technical skills specific to the role
        2. Problem-solving and critical thinking
        3. Past experience and projects
        4. Soft skills and teamwork
        5. Industry knowledge and trends
        
        Return only the questions as a numbered list, one per line.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.7
            )
            
            questions_text = response.choices[0].message.content.strip()
            questions = [q.strip() for q in questions_text.split('\n') if q.strip()]
            
            # Clean up numbering if present
            questions = [q.split('. ', 1)[-1] if '. ' in q else q for q in questions]
            
            return ParseJDResponse(questions=questions[:10])  # Limit to 10 questions
            
        except Exception as e:
            print(f"Error generating questions: {e}")
            # Fallback to basic questions
            return self._get_fallback_questions(role)
    
    def analyze_answer(self, job_description: str, question: str, answer: str) -> AnalyzeAnswerResponse:
        """Analyze candidate's answer using AI."""
        
        prompt = f"""
        You are an expert interview coach. Analyze the following candidate's answer to an interview question.
        
        Job Description: {job_description}
        Question: {question}
        Candidate's Answer: {answer}
        
        Provide a comprehensive analysis including:
        
        1. Score the answer on clarity (1-10) and confidence (1-10)
        2. Identify missing keywords or concepts from the job description
        3. Suggest specific improvements
        4. Provide an ideal answer example
        
        Format your response as JSON:
        {{
            "score": {{"clarity": X, "confidence": Y}},
            "missingKeywords": ["keyword1", "keyword2"],
            "improvements": ["improvement1", "improvement2"],
            "idealAnswer": "detailed ideal answer here"
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1500,
                temperature=0.3
            )
            
            # Parse JSON response
            import json
            analysis_text = response.choices[0].message.content.strip()
            
            # Extract JSON from response (handle cases where AI adds extra text)
            start_idx = analysis_text.find('{')
            end_idx = analysis_text.rfind('}') + 1
            json_str = analysis_text[start_idx:end_idx]
            
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
            print(f"Error analyzing answer: {e}")
            return self._get_fallback_analysis()
    
    def _get_fallback_questions(self, role: str) -> ParseJDResponse:
        """Fallback questions if AI fails."""
        return ParseJDResponse(questions=[
            f"Tell me about your experience with {role}",
            "Describe a challenging project you've worked on",
            "How do you handle tight deadlines?",
            "What's your approach to problem-solving?",
            "How do you stay updated with industry trends?"
        ])
    
    def _get_fallback_analysis(self) -> AnalyzeAnswerResponse:
        """Fallback analysis if AI fails."""
        return AnalyzeAnswerResponse(
            score=Score(clarity=5, confidence=5),
            missingKeywords=["specific examples", "metrics"],
            improvements=["Provide more specific examples", "Include quantifiable results"],
            idealAnswer="Please provide a more detailed answer with specific examples and measurable outcomes."
        ) 