import os
import json
import requests
from typing import List, Dict, Any
from app.models.schemas import ParseJDResponse, AnalyzeAnswerResponse, Score

class OllamaService:
    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "llama2")  # or "mistral", "codellama", etc.
        self.api_url = f"{self.base_url}/api/generate"
    
    def _call_ollama(self, prompt: str, system_prompt: str = None) -> str:
        """Make a call to Ollama API."""
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 2000
                }
            }
            
            if system_prompt:
                payload["system"] = system_prompt
            
            response = requests.post(self.api_url, json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "").strip()
            
        except requests.exceptions.RequestException as e:
            print(f"Error calling Ollama: {e}")
            raise Exception(f"Failed to communicate with Ollama: {str(e)}")
    
    def generate_interview_questions(self, role: str, job_description: str) -> ParseJDResponse:
        """Generate role-specific interview questions using Ollama."""
        
        system_prompt = """You are an expert technical interviewer with deep knowledge of software engineering roles. 
        Your task is to generate relevant interview questions based on job descriptions."""
        
        prompt = f"""
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
        
        try:
            response = self._call_ollama(prompt, system_prompt)
            
            # Parse the response to extract questions
            lines = [line.strip() for line in response.split('\n') if line.strip()]
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
            
            # Limit to 10 questions and ensure we have some
            questions = questions[:10]
            if not questions:
                questions = self._get_fallback_questions(role)
            
            return ParseJDResponse(questions=questions)
            
        except Exception as e:
            print(f"Error generating questions with Ollama: {e}")
            return self._get_fallback_questions(role)
    
    def analyze_answer(self, job_description: str, question: str, answer: str) -> AnalyzeAnswerResponse:
        """Analyze candidate's answer using Ollama."""
        
        system_prompt = """You are an expert interview coach with deep knowledge of technical interviews. 
        Your task is to analyze candidate answers and provide constructive feedback."""
        
        prompt = f"""
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
        
        try:
            response = self._call_ollama(prompt, system_prompt)
            
            # Try to extract JSON from the response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
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
            else:
                # Fallback if JSON parsing fails
                return self._get_fallback_analysis()
                
        except Exception as e:
            print(f"Error analyzing answer with Ollama: {e}")
            return self._get_fallback_analysis()
    
    def _get_fallback_questions(self, role: str) -> ParseJDResponse:
        """Fallback questions if Ollama fails."""
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
        """Fallback analysis if Ollama fails."""
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
    
    def list_available_models(self) -> List[str]:
        """List available Ollama models."""
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            return [model["name"] for model in data.get("models", [])]
        except Exception as e:
            print(f"Error listing models: {e}")
            return []
    
    def pull_model(self, model_name: str) -> bool:
        """Pull a model to Ollama."""
        try:
            response = requests.post(f"{self.base_url}/api/pull", json={"name": model_name})
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Error pulling model {model_name}: {e}")
            return False 