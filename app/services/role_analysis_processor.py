"""
Enhanced Role Analysis and Job Description Processing Service

This service combines comprehensive role analysis with advanced job description processing,
eliminating the need for separate RoleAnalysisService and JobDescriptionProcessor classes.
"""
import re
import html
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from app.utils.logger import get_logger
from app.models.role_analysis_models import RoleAnalysis, Industry, SeniorityLevel, CompanySize

logger = get_logger(__name__)


@dataclass
class JobDescriptionSummary:
    """Summary of job description with key information extracted."""
    original_length: int
    summary_length: int
    compression_ratio: float
    key_requirements: List[str]
    technical_skills: List[str]
    soft_skills: List[str]
    experience_years: Optional[int]
    education_requirements: List[str]
    certifications: List[str]
    industry: Optional[str]
    company_size: Optional[str]
    seniority_level: Optional[str]
    processing_issues: List[str]  # Track any issues encountered


class RoleAnalysisProcessor:
    """Enhanced service combining role analysis and job description processing."""
    
    def __init__(self):
        # DynamicPromptService will be imported when needed to avoid circular imports
        self.dynamic_prompt_service = None
        
        # Simplified extraction patterns
        self.skill_patterns = [
            r'proficient in\s+([\w\s+]+)',
            r'experience with\s+([\w\s+]+)',
            r'knowledge of\s+([\w\s+]+)',
            r'skills in\s+([\w\s+]+)'
        ]
        
        self.experience_patterns = [
            r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp)',
            r'(?:minimum|at least)\s*(\d+)\s*(?:years?|yrs?)',
            r'(\d+)\s*-\s*(\d+)\s*(?:years?|yrs?)'
        ]
        
        self.education_patterns = [
            r'(?:bachelor|master|phd|doctorate|degree)\s*(?:in|of)?\s*([\w\s]+)',
            r'(?:bs|ms|phd|mba)\s*(?:in|of)?\s*([\w\s]+)'
        ]
        
        self.certification_patterns = [
            r'(?:certified|certification)\s*(?:in|for)?\s*([\w\s]+)',
            r'(?:aws|azure|gcp|pmp|scrum|agile)\s*(?:certified|certification)'
        ]
        
        # Technical skill categories
        self.tech_categories = {
            'programming': ['python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'go', 'rust', 'php', 'ruby'],
            'databases': ['sql', 'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch', 'cassandra'],
            'cloud': ['aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform'],
            'frameworks': ['react', 'angular', 'vue', 'django', 'flask', 'spring', 'express'],
            'tools': ['git', 'jenkins', 'ci/cd', 'agile', 'scrum', 'jira', 'confluence']
        }
        
        # Industry detection patterns
        self.industry_patterns = {
            'technology': ['software', 'tech', 'it', 'saas', 'startup', 'fintech', 'edtech'],
            'finance': ['banking', 'finance', 'financial', 'investment', 'trading', 'fintech'],
            'healthcare': ['healthcare', 'medical', 'pharma', 'biotech', 'health'],
            'ecommerce': ['ecommerce', 'retail', 'shopping', 'marketplace', 'online'],
            'consulting': ['consulting', 'advisory', 'strategy', 'management'],
            'design': ['design', 'designer', 'ux', 'ui']
        }
        
        # HTML cleanup patterns
        self.html_patterns = [
            (r'<[^>]+>', ''),  # Remove HTML tags
            (r'&nbsp;', ' '),  # Replace non-breaking spaces
            (r'&amp;', '&'),   # Replace HTML entities
            (r'&lt;', '<'),
            (r'&gt;', '>'),
            (r'&quot;', '"'),
            (r'&#39;', "'"),
        ]
        
        # Common formatting issues
        self.formatting_patterns = [
            (r'\s+', ' '),  # Multiple spaces to single space
            (r'\n\s*\n', '\n\n'),  # Multiple newlines to double newline
            (r'[^\w\s\.\,\!\?\;\:\-\(\)]', ''),  # Remove special characters except common punctuation
        ]
    
    async def analyze_role(self, role: str, job_description: str) -> RoleAnalysis:
        """Perform comprehensive role analysis with declarative configuration."""
        try:
            logger.info(f"Analyzing role: {role}")
            
            # Use declarative configuration for analysis tasks
            analysis_config = self._get_analysis_config(role)
            results = await self._execute_analysis_pipeline(analysis_config, job_description)
            
            return self._build_role_analysis(role, results)
            
        except Exception as e:
            logger.error(f"Error in role analysis: {e}")
            return self._get_default_analysis(role)
    
    def process_job_description(self, job_description: str, max_length: int = 2000) -> JobDescriptionSummary:
        """
        Process and summarize job description with comprehensive extraction.
        
        Args:
            job_description: Raw job description text
            max_length: Maximum length for summary
            
        Returns:
            JobDescriptionSummary with extracted information
        """
        try:
            logger.info(f"Processing job description (length: {len(job_description)})")
            
            # Step 1: Clean and normalize text
            cleaned_text = self._clean_job_description(job_description)
            
            # Step 2: Extract key information
            extracted_info = self._extract_job_information(cleaned_text)
            
            # Step 3: Generate summary
            summary = self._generate_summary(cleaned_text, max_length)
            
            # Step 4: Calculate metrics
            compression_ratio = len(summary) / len(job_description) if job_description else 0
            
            return JobDescriptionSummary(
                original_length=len(job_description),
                summary_length=len(summary),
                compression_ratio=compression_ratio,
                key_requirements=extracted_info.get('requirements', []),
                technical_skills=extracted_info.get('technical_skills', []),
                soft_skills=extracted_info.get('soft_skills', []),
                experience_years=extracted_info.get('experience_years'),
                education_requirements=extracted_info.get('education', []),
                certifications=extracted_info.get('certifications', []),
                industry=extracted_info.get('industry'),
                company_size=extracted_info.get('company_size'),
                seniority_level=extracted_info.get('seniority_level'),
                processing_issues=extracted_info.get('issues', [])
            )
            
        except Exception as e:
            logger.error(f"Error processing job description: {e}")
            return self._get_default_job_summary(job_description)
    
    def _clean_job_description(self, text: str) -> str:
        """Clean and normalize job description text."""
        if not text:
            return ""
        
        # HTML decode
        cleaned = html.unescape(text)
        
        # Remove HTML tags and entities
        for pattern, replacement in self.html_patterns:
            cleaned = re.sub(pattern, replacement, cleaned)
        
        # Fix formatting issues
        for pattern, replacement in self.formatting_patterns:
            cleaned = re.sub(pattern, replacement, cleaned)
        
        # Final cleanup
        cleaned = cleaned.strip()
        
        return cleaned
    
    def _extract_job_information(self, text: str) -> Dict[str, Any]:
        """Extract key information from job description."""
        extracted = {
            'requirements': [],
            'technical_skills': [],
            'soft_skills': [],
            'experience_years': None,
            'education': [],
            'certifications': [],
            'industry': None,
            'company_size': None,
            'seniority_level': None,
            'issues': []
        }
        
        try:
            # Extract technical skills
            extracted['technical_skills'] = self._extract_technical_skills(text)
            
            # Extract soft skills
            extracted['soft_skills'] = self._extract_soft_skills(text)
            
            # Extract experience requirements
            extracted['experience_years'] = self._extract_experience_years(text)
            
            # Extract education requirements
            extracted['education'] = self._extract_education_requirements(text)
            
            # Extract certifications
            extracted['certifications'] = self._extract_certifications(text)
            
            # Detect industry
            extracted['industry'] = self._detect_industry(text)
            
            # Detect company size
            extracted['company_size'] = self._detect_company_size(text)
            
            # Detect seniority level
            extracted['seniority_level'] = self._detect_seniority_level(text)
            
            # Extract general requirements
            extracted['requirements'] = self._extract_general_requirements(text)
            
        except Exception as e:
            extracted['issues'].append(f"Extraction error: {str(e)}")
            logger.warning(f"Error extracting job information: {e}")
        
        return extracted
    
    def _extract_technical_skills(self, text: str) -> List[str]:
        """Extract technical skills from job description."""
        skills = []
        text_lower = text.lower()
        
        # Extract using keyword patterns
        for keywords in self.tech_categories.values():
            skills.extend([keyword.title() for keyword in keywords if keyword in text_lower])
        
        # Extract using regex patterns
        for pattern in self.skill_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            skills.extend([match if isinstance(match, str) else ' '.join(match) for match in matches])
        
        return list(set([skill.strip() for skill in skills if skill.strip()]))
    
    def _extract_soft_skills(self, text: str) -> List[str]:
        """Extract soft skills from job description."""
        soft_skills = [
            'communication', 'leadership', 'teamwork', 'problem solving',
            'analytical', 'creative', 'adaptable', 'organized', 'detail-oriented',
            'time management', 'collaboration', 'mentoring', 'presentation'
        ]
        
        text_lower = text.lower()
        return [skill.title() for skill in soft_skills if skill in text_lower]
    
    def _extract_experience_years(self, text: str) -> Optional[int]:
        """Extract experience requirements in years."""
        for pattern in self.experience_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                if isinstance(matches[0], tuple):
                    # Range format (e.g., "3-5 years")
                    min_years = int(matches[0][0])
                    max_years = int(matches[0][1])
                    return (min_years + max_years) // 2
                else:
                    return int(matches[0])
        return None
    
    def _extract_education_requirements(self, text: str) -> List[str]:
        """Extract education requirements."""
        education = []
        for pattern in self.education_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            education.extend([match if isinstance(match, str) else ' '.join(match) for match in matches])
        return list(set([req.strip() for req in education if req.strip()]))
    
    def _extract_certifications(self, text: str) -> List[str]:
        """Extract certification requirements."""
        certifications = []
        for pattern in self.certification_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            certifications.extend([match if isinstance(match, str) else ' '.join(match) for match in matches])
        return list(set([cert.strip() for cert in certifications if cert.strip()]))
    
    def _detect_industry(self, text: str) -> Optional[str]:
        """Detect industry from job description."""
        text_lower = text.lower()
        
        for industry, keywords in self.industry_patterns.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return industry.title()
        
        return None
    
    def _detect_company_size(self, text: str) -> Optional[str]:
        """Detect company size indicators."""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['startup', 'small', 'boutique']):
            return 'small'
        elif any(word in text_lower for word in ['enterprise', 'fortune', 'large', 'global']):
            return 'large'
        elif any(word in text_lower for word in ['medium', 'mid-size', 'growing']):
            return 'medium'
        
        return None
    
    def _detect_seniority_level(self, text: str) -> Optional[str]:
        """Detect seniority level from job description."""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['senior', 'lead', 'principal', 'staff', 'architect']):
            return 'senior'
        elif any(word in text_lower for word in ['junior', 'entry', 'graduate', 'intern']):
            return 'junior'
        elif any(word in text_lower for word in ['mid', 'intermediate', 'experienced']):
            return 'mid'
        
        return None
    
    def _extract_general_requirements(self, text: str) -> List[str]:
        """Extract general requirements and qualifications."""
        requirements = []
        
        # Look for bullet points or numbered lists
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if line and (line.startswith('•') or line.startswith('-') or line.startswith('*') or re.match(r'^\d+\.', line)):
                # Clean up the requirement
                requirement = re.sub(r'^[•\-\*\d+\.\s]+', '', line)
                if len(requirement) > 10:  # Only include substantial requirements
                    requirements.append(requirement)
        
        return requirements[:10]  # Limit to top 10 requirements
    
    def _generate_summary(self, text: str, max_length: int) -> str:
        """Generate a concise summary of the job description."""
        if len(text) <= max_length:
            return text
        
        # Simple summarization by taking the first part and key sections
        sentences = text.split('. ')
        
        summary_parts = []
        current_length = 0
        
        # Add first few sentences
        for sentence in sentences[:3]:
            if current_length + len(sentence) < max_length * 0.6:
                summary_parts.append(sentence)
                current_length += len(sentence)
            else:
                break
        
        # Add key requirements if space allows
        if current_length < max_length * 0.8:
            remaining = max_length - current_length
            # Add some key sentences from the middle
            for sentence in sentences[3:6]:
                if len(sentence) < remaining:
                    summary_parts.append(sentence)
                    remaining -= len(sentence)
                else:
                    break
        
        return '. '.join(summary_parts) + '.'
    
    def _get_analysis_config(self, role: str) -> Dict[str, Any]:
        """Get analysis configuration for the role."""
        return {
            'extractions': [
                'required_skills',
                'tech_stack', 
                'soft_skills',
                'experience_years'
            ],
            'detections': [
                'industry',
                'seniority',
                'company_size',
                'job_function'
            ],
            'requirements': [
                'education',
                'certifications'
            ]
        }
    
    async def _execute_analysis_pipeline(self, config: Dict[str, Any], job_description: str) -> List[Any]:
        """Execute the analysis pipeline with declarative configuration."""
        results = []
        
        # Process job description first
        job_summary = self.process_job_description(job_description)
        
        # Extract information based on configuration
        for extraction_type in config.get('extractions', []):
            if extraction_type == 'required_skills':
                results.append(job_summary.technical_skills)
            elif extraction_type == 'tech_stack':
                results.append(job_summary.technical_skills)
            elif extraction_type == 'soft_skills':
                results.append(job_summary.soft_skills)
            elif extraction_type == 'experience_years':
                results.append(job_summary.experience_years)
        
        # Detect characteristics
        for detection_type in config.get('detections', []):
            if detection_type == 'industry':
                results.append(job_summary.industry)
            elif detection_type == 'seniority':
                results.append(job_summary.seniority_level)
            elif detection_type == 'company_size':
                results.append(job_summary.company_size)
            elif detection_type == 'job_function':
                results.append('engineering')  # Default assumption
        
        return results
    
    def _build_role_analysis(self, role: str, results: List[Any]) -> RoleAnalysis:
        """Build RoleAnalysis object from pipeline results."""
        # Extract results in order
        required_skills = results[0] if len(results) > 0 else []
        tech_stack = results[1] if len(results) > 1 else []
        soft_skills = results[2] if len(results) > 2 else []
        experience_years = results[3] if len(results) > 3 else None
        industry = results[4] if len(results) > 4 else None
        seniority = results[5] if len(results) > 5 else None
        company_size = results[6] if len(results) > 6 else None
        job_function = results[7] if len(results) > 7 else 'engineering'
        
        return RoleAnalysis(
            primary_role=role,
            industry=Industry(industry) if industry else Industry.TECHNOLOGY,
            seniority_level=SeniorityLevel(seniority) if seniority else SeniorityLevel.MID,
            company_size=CompanySize(company_size) if company_size else CompanySize.MEDIUM,
            required_skills=required_skills,
            tech_stack=tech_stack,
            soft_skills=soft_skills,
            experience_years=experience_years,
            job_function=job_function
        )
    
    def _get_default_analysis(self, role: str) -> RoleAnalysis:
        """Get default analysis when processing fails."""
        return RoleAnalysis(
            primary_role=role,
            industry=Industry.TECHNOLOGY,
            seniority_level=SeniorityLevel.MID,
            company_size=CompanySize.MEDIUM,
            required_skills=[],
            tech_stack=[],
            soft_skills=['communication', 'teamwork', 'problem solving'],
            experience_years=None,
            job_function='engineering'
        )
    
    def _get_default_job_summary(self, job_description: str) -> JobDescriptionSummary:
        """Get default job summary when processing fails."""
        return JobDescriptionSummary(
            original_length=len(job_description) if job_description else 0,
            summary_length=0,
            compression_ratio=0.0,
            key_requirements=[],
            technical_skills=[],
            soft_skills=[],
            experience_years=None,
            education_requirements=[],
            certifications=[],
            industry=None,
            company_size=None,
            seniority_level=None,
            processing_issues=['Processing failed']
        )
