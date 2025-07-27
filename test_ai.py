import asyncio
from app.services.ai_service import AIService

async def test_ai_integration():
    ai_service = AIService()
    
    # Test question generation
    role = "Senior Frontend Developer"
    jd = """
    We're looking for a Senior Frontend Developer with 5+ years of experience in React, 
    TypeScript, and modern web technologies. The ideal candidate should have experience 
    with accessibility, performance optimization, and working with design systems.
    """
    
    questions = ai_service.generate_interview_questions(role, jd)
    print("Generated Questions:", questions.questions)
    
    # Test answer analysis
    question = "Tell me about your experience with React"
    answer = "I've worked with React for about 3 years. I've built several applications and used hooks."
    
    analysis = ai_service.analyze_answer(jd, question, answer)
    print("Analysis:", analysis)

if __name__ == "__main__":
    asyncio.run(test_ai_integration()) 