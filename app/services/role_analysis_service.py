"""
Role Analysis Service for Dynamic Prompt Generation.

This service analyzes job descriptions and roles to determine industry,
job function, seniority level, and other characteristics for generating
role-specific interview questions.
"""
import re
import hashlib
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
from app.utils.logger import get_logger

logger = get_logger(__name__)


class IndustryType(str, Enum):
    """Supported industry types."""
    TECHNOLOGY = "technology"
    HEALTHCARE = "healthcare"
    FINANCE = "finance"
    SALES_MARKETING = "sales_marketing"
    UNKNOWN = "unknown"


class JobFunction(str, Enum):
    """Supported job functions."""
    DEVELOPMENT = "development"
    DATA_SCIENCE = "data_science"
    DEVOPS = "devops"
    NURSING = "nursing"
    MEDICAL = "medical"
    BANKING = "banking"
    INSURANCE = "insurance"
    SALES = "sales"
    MARKETING = "marketing"
    MANAGEMENT = "management"
    OPERATIONS = "operations"
    UNKNOWN = "unknown"


class SeniorityLevel(str, Enum):
    """Seniority levels."""
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    UNKNOWN = "unknown"


@dataclass
class RoleAnalysis:
    """Result of role analysis."""
    industry: IndustryType
    job_function: JobFunction
    seniority_level: SeniorityLevel
    key_skills: List[str]
    confidence_score: float
    analysis_hash: str


class RoleAnalysisService:
    """Service for analyzing roles and job descriptions."""
    
    # Industry detection keywords
    INDUSTRY_KEYWORDS = {
        IndustryType.TECHNOLOGY: [
            "software", "programming", "developer", "engineer", "coding", "python", "javascript",
            "java", "react", "node", "api", "database", "cloud", "aws", "azure", "devops",
            "data science", "machine learning", "ai", "artificial intelligence", "backend",
            "frontend", "full stack", "mobile", "ios", "android", "web development"
        ],
        IndustryType.HEALTHCARE: [
            "nurse", "nursing", "doctor", "physician", "medical", "healthcare", "hospital",
            "clinic", "patient", "treatment", "diagnosis", "pharmaceutical", "pharmacy",
            "therapist", "counselor", "health", "medicine", "clinical", "surgery", "emergency"
        ],
        IndustryType.FINANCE: [
            "banking", "finance", "financial", "investment", "trading", "portfolio", "risk",
            "compliance", "audit", "accounting", "insurance", "fintech", "payments", "loans",
            "credit", "wealth management", "hedge fund", "private equity", "analyst"
        ],
        IndustryType.SALES_MARKETING: [
            "sales", "marketing", "advertising", "promotion", "brand", "customer", "client",
            "revenue", "leads", "conversion", "campaign", "digital marketing", "social media",
            "seo", "content", "copywriting", "account manager", "business development"
        ]
    }
    
    # Job function detection keywords
    JOB_FUNCTION_KEYWORDS = {
        JobFunction.DEVELOPMENT: [
            "developer", "programmer", "software engineer", "coding", "programming",
            "frontend", "backend", "full stack", "mobile developer", "web developer"
        ],
        JobFunction.DATA_SCIENCE: [
            "data scientist", "data analyst", "machine learning", "ai engineer", "ml engineer",
            "statistics", "analytics", "data mining", "predictive modeling", "deep learning"
        ],
        JobFunction.DEVOPS: [
            "devops", "sre", "site reliability", "infrastructure", "deployment", "ci/cd",
            "kubernetes", "docker", "aws", "azure", "cloud engineer", "platform engineer"
        ],
        JobFunction.NURSING: [
            "nurse", "nursing", "rn", "registered nurse", "lpn", "cna", "nurse practitioner",
            "clinical nurse", "nurse manager", "nurse educator"
        ],
        JobFunction.MEDICAL: [
            "doctor", "physician", "surgeon", "specialist", "resident", "intern", "medical",
            "clinical", "diagnosis", "treatment", "patient care"
        ],
        JobFunction.BANKING: [
            "banker", "loan officer", "credit analyst", "investment banker", "financial advisor",
            "wealth manager", "commercial banking", "retail banking"
        ],
        JobFunction.INSURANCE: [
            "insurance", "underwriter", "claims adjuster", "actuary", "insurance agent",
            "risk analyst", "insurance broker"
        ],
        JobFunction.SALES: [
            "sales rep", "sales representative", "account executive", "business development",
            "sales manager", "sales director", "territory manager"
        ],
        JobFunction.MARKETING: [
            "marketing manager", "marketing coordinator", "brand manager", "digital marketing",
            "content marketing", "social media manager", "marketing analyst"
        ],
        JobFunction.MANAGEMENT: [
            "manager", "director", "vp", "vice president", "ceo", "cto", "cfo", "lead",
            "team lead", "project manager", "product manager", "operations manager"
        ],
        JobFunction.OPERATIONS: [
            "operations", "supply chain", "logistics", "procurement", "manufacturing",
            "production", "quality assurance", "process improvement"
        ]
    }
    
    # Seniority level detection keywords
    SENIORITY_KEYWORDS = {
        SeniorityLevel.JUNIOR: [
            "junior", "entry level", "associate", "trainee", "intern", "graduate",
            "0-2 years", "1-2 years", "new grad", "recent graduate"
        ],
        SeniorityLevel.MID: [
            "mid level", "intermediate", "2-5 years", "3-5 years", "experienced",
            "mid-level", "mid level"
        ],
        SeniorityLevel.SENIOR: [
            "senior", "sr", "5+ years", "experienced", "expert", "specialist",
            "advanced", "lead", "principal"
        ],
        SeniorityLevel.LEAD: [
            "lead", "principal", "staff", "architect", "tech lead", "team lead",
            "senior lead", "staff engineer", "distinguished"
        ]
    }
    
    def __init__(self):
        self.cache: Dict[str, RoleAnalysis] = {}
    
    def analyze_role(self, role: str, job_description: str) -> RoleAnalysis:
        """
        Analyze role and job description to determine industry, function, and seniority.
        
        Args:
            role: Job title/role
            job_description: Full job description text
            
        Returns:
            RoleAnalysis with detected characteristics
        """
        # Generate cache key
        cache_key = self._generate_cache_key(role, job_description)
        
        # Check cache first
        if cache_key in self.cache:
            logger.debug(f"Using cached role analysis for: {role}")
            return self.cache[cache_key]
        
        # Perform analysis
        analysis = self._perform_analysis(role, job_description)
        
        # Cache the result
        self.cache[cache_key] = analysis
        
        logger.info(f"Analyzed role '{role}': {analysis.industry.value}, {analysis.job_function.value}, {analysis.seniority_level.value}")
        return analysis
    
    def _generate_cache_key(self, role: str, job_description: str) -> str:
        """Generate cache key for role analysis."""
        content = f"{role.lower()}|{job_description.lower()}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _perform_analysis(self, role: str, job_description: str) -> RoleAnalysis:
        """Perform the actual role analysis."""
        combined_text = f"{role} {job_description}".lower()
        
        # Detect industry
        industry = self._detect_industry(combined_text)
        
        # Detect job function
        job_function = self._detect_job_function(combined_text, industry)
        
        # Detect seniority level
        seniority_level = self._detect_seniority_level(combined_text)
        
        # Extract key skills
        key_skills = self._extract_key_skills(combined_text, industry, job_function)
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence(industry, job_function, seniority_level, combined_text)
        
        # Generate analysis hash
        analysis_hash = self._generate_analysis_hash(industry, job_function, seniority_level, key_skills)
        
        return RoleAnalysis(
            industry=industry,
            job_function=job_function,
            seniority_level=seniority_level,
            key_skills=key_skills,
            confidence_score=confidence_score,
            analysis_hash=analysis_hash
        )
    
    def _detect_industry(self, text: str) -> IndustryType:
        """Detect industry using keyword matching."""
        industry_scores = {}
        
        for industry, keywords in self.INDUSTRY_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                industry_scores[industry] = score
        
        if not industry_scores:
            return IndustryType.UNKNOWN
        
        # Return industry with highest score
        return max(industry_scores.items(), key=lambda x: x[1])[0]
    
    def _detect_job_function(self, text: str, industry: IndustryType) -> JobFunction:
        """Detect job function using keyword matching."""
        function_scores = {}
        
        for job_function, keywords in self.JOB_FUNCTION_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                function_scores[job_function] = score
        
        if not function_scores:
            return JobFunction.UNKNOWN
        
        # Return job function with highest score
        return max(function_scores.items(), key=lambda x: x[1])[0]
    
    def _detect_seniority_level(self, text: str) -> SeniorityLevel:
        """Detect seniority level using keyword matching."""
        seniority_scores = {}
        
        for seniority, keywords in self.SENIORITY_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                seniority_scores[seniority] = score
        
        if not seniority_scores:
            return SeniorityLevel.MID  # Default to mid-level
        
        # Return seniority with highest score
        return max(seniority_scores.items(), key=lambda x: x[1])[0]
    
    def _extract_key_skills(self, text: str, industry: IndustryType, job_function: JobFunction) -> List[str]:
        """Extract key skills from the text."""
        # Common technical skills
        technical_skills = [
            "python", "javascript", "java", "react", "node", "sql", "aws", "azure",
            "docker", "kubernetes", "git", "linux", "api", "database", "machine learning",
            "data analysis", "project management", "agile", "scrum"
        ]
        
        # Industry-specific skills
        industry_skills = {
            IndustryType.HEALTHCARE: ["patient care", "medical terminology", "clinical", "hipaa"],
            IndustryType.FINANCE: ["financial modeling", "risk management", "compliance", "regulatory"],
            IndustryType.SALES_MARKETING: ["crm", "lead generation", "digital marketing", "seo"]
        }
        
        # Job function specific skills
        function_skills = {
            JobFunction.DATA_SCIENCE: ["statistics", "pandas", "numpy", "tensorflow", "pytorch"],
            JobFunction.DEVOPS: ["ci/cd", "infrastructure", "monitoring", "automation"],
            JobFunction.MANAGEMENT: ["leadership", "team management", "strategic planning"]
        }
        
        # Combine all skill lists
        all_skills = technical_skills.copy()
        all_skills.extend(industry_skills.get(industry, []))
        all_skills.extend(function_skills.get(job_function, []))
        
        # Find skills mentioned in text
        found_skills = [skill for skill in all_skills if skill in text]
        
        return found_skills[:10]  # Limit to top 10 skills
    
    def _calculate_confidence(self, industry: IndustryType, job_function: JobFunction, 
                            seniority_level: SeniorityLevel, text: str) -> float:
        """Calculate confidence score for the analysis."""
        confidence = 0.0
        
        # Base confidence for each detection
        if industry != IndustryType.UNKNOWN:
            confidence += 0.4
        if job_function != JobFunction.UNKNOWN:
            confidence += 0.3
        if seniority_level != SeniorityLevel.UNKNOWN:
            confidence += 0.2
        
        # Bonus for text length (more context = higher confidence)
        if len(text) > 500:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _generate_analysis_hash(self, industry: IndustryType, job_function: JobFunction,
                              seniority_level: SeniorityLevel, key_skills: List[str]) -> str:
        """Generate hash for the analysis result."""
        content = f"{industry.value}|{job_function.value}|{seniority_level.value}|{','.join(sorted(key_skills))}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get_analysis_summary(self, analysis: RoleAnalysis) -> Dict[str, Any]:
        """Get a summary of the role analysis for logging/debugging."""
        return {
            "industry": analysis.industry.value,
            "job_function": analysis.job_function.value,
            "seniority_level": analysis.seniority_level.value,
            "key_skills": analysis.key_skills,
            "confidence_score": analysis.confidence_score,
            "analysis_hash": analysis.analysis_hash
        }
