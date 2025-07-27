from typing import List
from app.models.schemas import ParseJDResponse, AnalyzeAnswerResponse, Score

def generate_mock_questions(role: str, job_description: str) -> ParseJDResponse:
    """
    Generate mock interview questions based on role and job description.
    
    TODO: Replace with GPT integration to analyze job description
    and generate role-specific questions.
    """
    # Mock questions - in real implementation, this would use AI to analyze JD
    mock_questions = [
        "Tell me about yourself",
        "How have you worked with React?",
        "What's your experience with accessibility?",
        f"Can you describe your experience with {role}?",
        "What challenges have you faced in your previous roles?",
        "How do you stay updated with industry trends?",
        "Describe a complex project you've worked on",
        "How do you handle tight deadlines?",
        "What's your approach to code review?",
        "How do you ensure code quality?"
    ]
    
    return ParseJDResponse(questions=mock_questions)

def analyze_mock_answer(job_description: str, question: str, answer: str) -> AnalyzeAnswerResponse:
    """
    Analyze candidate's answer and provide feedback.
    
    TODO: Replace with GPT integration to:
    1. Analyze answer against job description
    2. Extract relevant keywords and concepts
    3. Generate personalized feedback
    4. Create ideal answer examples
    """
    # Mock analysis - in real implementation, this would use AI to analyze the answer
    mock_response = AnalyzeAnswerResponse(
        score=Score(clarity=7, confidence=6),
        missingKeywords=["WCAG", "ARIA", "accessibility compliance", "design systems"],
        improvements=[
            "Mention accessibility compliance",
            "Highlight design system experience", 
            "Provide specific examples of React projects",
            "Include metrics or quantifiable results",
            "Demonstrate problem-solving approach"
        ],
        idealAnswer=(
            "I've built accessible React apps following WCAG guidelines, implemented ARIA "
            "attributes for screen readers, and worked extensively with design systems to "
            "ensure consistency across applications. In my previous role, I led the development "
            "of a component library that improved accessibility scores by 40% and reduced "
            "development time by 25% through reusable components."
        )
    )
    
    return mock_response 