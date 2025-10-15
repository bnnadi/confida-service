"""
Enhanced role analysis service for intelligent question selection.
Extracts skills, industry, seniority, and other role characteristics.
"""
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
from app.utils.logger import get_logger
from app.services.dynamic_prompt_service import DynamicPromptService

logger = get_logger(__name__)

class Industry(Enum):
    TECHNOLOGY = "technology"
    FINANCE = "finance"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    RETAIL = "retail"
    MANUFACTURING = "manufacturing"
    CONSULTING = "consulting"
    MEDIA = "media"
    GOVERNMENT = "government"
    NONPROFIT = "nonprofit"
    OTHER = "other"

class SeniorityLevel(Enum):
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    STAFF = "staff"
    PRINCIPAL = "principal"
    LEAD = "lead"
    MANAGER = "manager"
    DIRECTOR = "director"
    VP = "vp"
    C_LEVEL = "c_level"

class CompanySize(Enum):
    STARTUP = "startup"  # 1-50 employees
    SMALL = "small"      # 51-200 employees
    MEDIUM = "medium"    # 201-1000 employees
    LARGE = "large"      # 1001-5000 employees
    ENTERPRISE = "enterprise"  # 5000+ employees

@dataclass
class RoleAnalysis:
    """Comprehensive role analysis result."""
    primary_role: str
    required_skills: List[str]
    industry: Industry
    seniority_level: SeniorityLevel
    company_size: CompanySize
    tech_stack: List[str]
    soft_skills: List[str]
    job_function: str
    experience_years: Optional[int] = None
    education_requirements: List[str] = None
    certifications: List[str] = None

class RoleAnalysisService:
    """Enhanced role analysis service for intelligent question selection."""
    
    def __init__(self):
        self.dynamic_prompt_service = DynamicPromptService()
        
        # Common skill patterns
        self.technical_skills = {
            'programming': ['python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'go', 'rust', 'php', 'ruby'],
            'databases': ['sql', 'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch', 'cassandra'],
            'cloud': ['aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform', 'cloudformation'],
            'frameworks': ['react', 'angular', 'vue', 'django', 'flask', 'spring', 'express', 'fastapi'],
            'tools': ['git', 'jenkins', 'ci/cd', 'agile', 'scrum', 'jira', 'confluence'],
            'ai_ml': ['machine learning', 'deep learning', 'tensorflow', 'pytorch', 'nlp', 'computer vision']
        }
        
        self.soft_skills = [
            'leadership', 'communication', 'teamwork', 'problem solving', 'critical thinking',
            'time management', 'adaptability', 'creativity', 'emotional intelligence',
            'mentoring', 'collaboration', 'presentation', 'negotiation'
        ]
        
        # Industry keywords
        self.industry_keywords = {
            Industry.TECHNOLOGY: ['software', 'tech', 'startup', 'saas', 'platform', 'api', 'development'],
            Industry.FINANCE: ['banking', 'finance', 'fintech', 'investment', 'trading', 'risk', 'compliance'],
            Industry.HEALTHCARE: ['healthcare', 'medical', 'pharma', 'clinical', 'patient', 'health'],
            Industry.EDUCATION: ['education', 'learning', 'training', 'academic', 'university', 'school'],
            Industry.RETAIL: ['retail', 'ecommerce', 'shopping', 'customer', 'sales', 'marketing'],
            Industry.MANUFACTURING: ['manufacturing', 'production', 'industrial', 'supply chain', 'logistics'],
            Industry.CONSULTING: ['consulting', 'advisory', 'strategy', 'management', 'business'],
            Industry.MEDIA: ['media', 'entertainment', 'content', 'publishing', 'broadcast'],
            Industry.GOVERNMENT: ['government', 'public sector', 'policy', 'regulatory', 'federal'],
            Industry.NONPROFIT: ['nonprofit', 'ngo', 'charity', 'social impact', 'volunteer']
        }
        
        # Seniority indicators
        self.seniority_indicators = {
            SeniorityLevel.JUNIOR: ['junior', 'entry', 'graduate', 'intern', '0-2 years', '1-3 years'],
            SeniorityLevel.MID: ['mid', 'intermediate', '3-5 years', '4-6 years', 'experienced'],
            SeniorityLevel.SENIOR: ['senior', '5+ years', '6+ years', 'expert', 'advanced'],
            SeniorityLevel.STAFF: ['staff', 'staff engineer', 'principal engineer'],
            SeniorityLevel.LEAD: ['lead', 'tech lead', 'team lead', 'technical lead'],
            SeniorityLevel.MANAGER: ['manager', 'engineering manager', 'product manager'],
            SeniorityLevel.DIRECTOR: ['director', 'head of', 'vp engineering'],
            SeniorityLevel.VP: ['vp', 'vice president', 'vp of'],
            SeniorityLevel.C_LEVEL: ['cto', 'ceo', 'cfo', 'coo', 'chief']
        }
        
        # Company size indicators
        self.company_size_indicators = {
            CompanySize.STARTUP: ['startup', 'early stage', 'seed', 'series a', 'small team'],
            CompanySize.SMALL: ['small company', 'growing team', '50-200', 'medium company'],
            CompanySize.MEDIUM: ['mid-size', 'established', '200-1000', 'growing company'],
            CompanySize.LARGE: ['large company', 'enterprise', '1000+', 'fortune 500'],
            CompanySize.ENTERPRISE: ['enterprise', 'fortune 500', 'global', 'multinational']
        }
        
        # Job function keywords for simplified detection
        self.job_function_keywords = {
            "frontend_development": ['frontend', 'front-end', 'ui', 'ux', 'react', 'angular', 'vue'],
            "backend_development": ['backend', 'api', 'server', 'database', 'microservices'],
            "fullstack_development": ['fullstack', 'full-stack', 'full stack'],
            "devops": ['devops', 'sre', 'infrastructure', 'deployment'],
            "data_science": ['data', 'analytics', 'ml', 'ai', 'machine learning'],
            "mobile_development": ['mobile', 'ios', 'android', 'react native'],
            "quality_assurance": ['qa', 'testing', 'test', 'quality assurance'],
            "product_management": ['product', 'product manager', 'pm'],
            "design": ['design', 'designer', 'ux', 'ui']
        }

    async def analyze_role(self, role: str, job_description: str) -> RoleAnalysis:
        """Perform comprehensive role analysis."""
        try:
            logger.info(f"Analyzing role: {role}")
            
            # Extract skills
            required_skills = await self._extract_skills(job_description)
            tech_stack = await self._extract_tech_stack(job_description)
            soft_skills = await self._extract_soft_skills(job_description)
            
            # Detect characteristics
            industry = await self._detect_industry(job_description)
            seniority_level = await self._detect_seniority(job_description)
            company_size = await self._detect_company_size(job_description)
            job_function = await self._detect_job_function(role, job_description)
            experience_years = await self._extract_experience_years(job_description)
            education_requirements = await self._extract_education_requirements(job_description)
            certifications = await self._extract_certifications(job_description)
            
            analysis = RoleAnalysis(
                primary_role=role,
                required_skills=required_skills,
                industry=industry,
                seniority_level=seniority_level,
                company_size=company_size,
                tech_stack=tech_stack,
                soft_skills=soft_skills,
                job_function=job_function,
                experience_years=experience_years,
                education_requirements=education_requirements or [],
                certifications=certifications or []
            )
            
            logger.info(f"Role analysis completed: {industry.value}, {seniority_level.value}, {len(required_skills)} skills")
            return analysis
            
        except Exception as e:
            logger.error(f"Error in role analysis: {e}")
            # Return default analysis
            return RoleAnalysis(
                primary_role=role,
                required_skills=[],
                industry=Industry.OTHER,
                seniority_level=SeniorityLevel.MID,
                company_size=CompanySize.MEDIUM,
                tech_stack=[],
                soft_skills=[],
                job_function="software_development"
            )

    def _find_matching_items(self, text: str, item_dict: Dict[Any, List[str]]) -> List[str]:
        """Generic method to find matching items in text."""
        text_lower = text.lower()
        matches = []
        for category, items in item_dict.items():
            for item in items:
                if item in text_lower:
                    matches.append(item)
        return list(set(matches))
    
    async def _extract_skills(self, job_description: str) -> List[str]:
        """Extract required skills from job description."""
        return self._find_matching_items(job_description, self.technical_skills)

    async def _extract_tech_stack(self, job_description: str) -> List[str]:
        """Extract technology stack from job description."""
        return self._find_matching_items(job_description, self.technical_skills)

    async def _extract_soft_skills(self, job_description: str) -> List[str]:
        """Extract soft skills from job description."""
        return self._find_matching_items(job_description, {"soft_skills": self.soft_skills})

    async def _detect_industry(self, job_description: str) -> Industry:
        """Detect industry from job description."""
        text_lower = job_description.lower()
        
        for industry, keywords in self.industry_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return industry
        
        return Industry.OTHER

    async def _detect_seniority(self, job_description: str) -> SeniorityLevel:
        """Detect seniority level from job description."""
        text_lower = job_description.lower()
        
        for seniority, indicators in self.seniority_indicators.items():
            if any(indicator in text_lower for indicator in indicators):
                return seniority
        
        return SeniorityLevel.MID

    async def _detect_company_size(self, job_description: str) -> CompanySize:
        """Detect company size from job description."""
        text_lower = job_description.lower()
        
        for size, indicators in self.company_size_indicators.items():
            if any(indicator in text_lower for indicator in indicators):
                return size
        
        return CompanySize.MEDIUM

    async def _detect_job_function(self, role: str, job_description: str) -> str:
        """Detect job function from role and description."""
        text_lower = f"{role} {job_description}".lower()
        
        for function, keywords in self.job_function_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return function
        
        return "software_development"

    async def _extract_experience_years(self, job_description: str) -> Optional[int]:
        """Extract required experience years from job description."""
        # Look for patterns like "3-5 years", "5+ years", etc.
        patterns = [
            r'(\d+)[\+\-]?\s*years?',
            r'(\d+)\s*to\s*(\d+)\s*years?',
            r'minimum\s*(\d+)\s*years?'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, job_description.lower())
            if matches:
                if isinstance(matches[0], tuple):
                    # Range like "3-5 years"
                    return int(matches[0][1])  # Take the higher number
                else:
                    # Single number
                    return int(matches[0])
        
        return None

    async def _extract_education_requirements(self, job_description: str) -> List[str]:
        """Extract education requirements from job description."""
        education = []
        text_lower = job_description.lower()
        
        if 'bachelor' in text_lower or 'bs' in text_lower or 'ba' in text_lower:
            education.append('bachelor')
        if 'master' in text_lower or 'ms' in text_lower or 'ma' in text_lower:
            education.append('master')
        if 'phd' in text_lower or 'doctorate' in text_lower:
            education.append('phd')
        if 'computer science' in text_lower or 'cs' in text_lower:
            education.append('computer_science')
        if 'engineering' in text_lower:
            education.append('engineering')
        
        return education

    async def _extract_certifications(self, job_description: str) -> List[str]:
        """Extract required certifications from job description."""
        certifications = []
        text_lower = job_description.lower()
        
        cert_keywords = [
            'aws certified', 'azure certified', 'gcp certified', 'pmp', 'scrum master',
            'certified', 'certification', 'cissp', 'itil', 'six sigma'
        ]
        
        for cert in cert_keywords:
            if cert in text_lower:
                certifications.append(cert)
        
        return certifications

    def get_question_categories_for_role(self, role_analysis: RoleAnalysis) -> List[str]:
        """Get relevant question categories for a role analysis."""
        categories = ['technical', 'behavioral']
        
        # Add role-specific categories
        if role_analysis.seniority_level in [SeniorityLevel.LEAD, SeniorityLevel.MANAGER, SeniorityLevel.DIRECTOR]:
            categories.append('leadership')
        
        if role_analysis.seniority_level in [SeniorityLevel.SENIOR, SeniorityLevel.STAFF, SeniorityLevel.PRINCIPAL]:
            categories.append('system_design')
        
        if role_analysis.job_function in ['backend_development', 'fullstack_development']:
            categories.append('system_design')
        
        if role_analysis.job_function == 'data_science':
            categories.append('data_analysis')
        
        return categories

    def get_difficulty_levels_for_role(self, role_analysis: RoleAnalysis) -> List[str]:
        """Get appropriate difficulty levels for a role analysis."""
        if role_analysis.seniority_level == SeniorityLevel.JUNIOR:
            return ['easy', 'medium']
        elif role_analysis.seniority_level in [SeniorityLevel.MID, SeniorityLevel.SENIOR]:
            return ['easy', 'medium', 'hard']
        else:  # Senior+ roles
            return ['medium', 'hard']