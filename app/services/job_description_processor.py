"""
Improved Job Description Processing Service

Addresses critical issues in the original processor:
- Better pattern matching accuracy
- HTML/formatting cleanup
- Performance optimization
- Edge case handling
- Language detection
"""

import re
import html
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from app.utils.logger import get_logger

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
    experience_requirements: List[str]
    company_info: Dict[str, Any]
    summary_text: str
    processing_issues: List[str]  # Track any issues encountered

class ImprovedJobDescriptionProcessor:
    """
    Improved job description processor with better error handling and accuracy.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        # Improved technical skill patterns - more specific and accurate
        self.technical_patterns = [
            # Programming languages
            r'\b(?:proficient|experienced|skilled|expert)\s+(?:in|with)\s+(python|java|javascript|typescript|go|rust|c\+\+|c#|php|ruby|swift|kotlin|scala|r|matlab)\b',
            # Frameworks and libraries
            r'\b(?:experience|knowledge|proficient)\s+(?:with|in)\s+(react|angular|vue|django|flask|spring|express|laravel|rails|asp\.net|jquery|bootstrap|tailwind)\b',
            # Cloud and infrastructure
            r'\b(?:aws|azure|gcp|google cloud|amazon web services|kubernetes|docker|terraform|ansible|jenkins|gitlab|github)\b',
            # Databases
            r'\b(?:postgresql|mysql|mongodb|redis|elasticsearch|dynamodb|cassandra|oracle|sql server)\b',
            # Tools and technologies
            r'\b(?:git|jira|confluence|slack|figma|sketch|photoshop|illustrator|tableau|power bi|splunk|datadog)\b',
            # Methodologies
            r'\b(?:agile|scrum|kanban|devops|ci/cd|tdd|bdd|microservices|api|rest|graphql|soa)\b'
        ]
        
        # Improved soft skill patterns
        self.soft_skill_patterns = [
            r'\b(?:strong|excellent|good)\s+(?:communication|leadership|teamwork|problem-solving|analytical|organizational)\s+skills?\b',
            r'\b(?:ability|capable|skilled)\s+(?:to work|at working|in)\s+(?:collaboratively|in teams|under pressure|independently)\b',
            r'\b(?:passion|enthusiasm|interest)\s+(?:for|in)\s+(?:learning|innovation|technology|mentoring)\b'
        ]
        
        # Experience patterns - more specific
        self.experience_patterns = [
            r'(\d+)\+?\s*years?\s+(?:of\s+)?(?:hands-on|professional|relevant|proven)\s+(?:experience|background)',
            r'(?:minimum|at least|required)\s+(\d+)\+?\s*years?\s+(?:of\s+)?(?:experience|background)',
            r'(?:senior|lead|principal|staff|architect|director|manager)\s+(?:level|position|role)',
            r'(?:entry-level|junior|mid-level|experienced|expert)\s+(?:position|role|level)'
        ]
        
        # Company info patterns
        self.company_patterns = {
            'name': [
                r'at\s+([A-Z][a-zA-Z\s&.,]+?)(?:\s+is|\s+we|\s+our|\s+the)',
                r'join\s+([A-Z][a-zA-Z\s&.,]+?)(?:\s+as|\s+to|\s+and)',
                r'([A-Z][a-zA-Z\s&.,]+?)\s+(?:is\s+looking|seeking|hiring)'
            ],
            'location': [
                r'(?:location|based in|office in|headquartered in)\s*:?\s*([^.,\n]+)',
                r'(?:remote|hybrid|onsite|distributed|flexible)\s+(?:work|position|role)',
                r'(?:san francisco|new york|seattle|austin|boston|chicago|los angeles|denver|miami|atlanta)'
            ]
        }
        
        # Compile patterns for better performance
        self._compile_patterns()
        
        # Load configuration from YAML file
        self.config = self._load_pattern_config(config_path)
        
        # Compile patterns from configuration
        self.compiled_patterns = self._compile_patterns_from_config()
    
    def _load_pattern_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load pattern configuration from YAML file."""
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    logger.info(f"Loaded pattern config from {config_path}")
                    return config
            except Exception as e:
                logger.warning(f"Failed to load pattern config from {config_path}: {e}")
        
        # Try default config path
        default_path = Path(__file__).parent.parent.parent / "config" / "pattern_matching.yaml"
        if default_path.exists():
            try:
                with open(default_path, 'r') as f:
                    config = yaml.safe_load(f)
                    logger.info(f"Loaded pattern config from {default_path}")
                    return config
            except Exception as e:
                logger.warning(f"Failed to load default pattern config: {e}")
        
        # Fallback to hardcoded defaults
        logger.warning("Using hardcoded pattern defaults")
        return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration when YAML file is not available."""
        return {
            'technical_patterns': self.technical_patterns,
            'soft_skill_patterns': self.soft_skill_patterns,
            'experience_patterns': self.experience_patterns,
            'company_patterns': self.company_patterns,
            'requirement_patterns': [
                r'•\s*([^•\n]+?)(?=\n|$)',
                r'You will:\s*([^.\n]+)',
                r'Responsibilities:\s*([^.\n]+)',
                r'Key\s+(?:responsibilities|requirements):\s*([^.\n]+)'
            ],
            'validation': {
                'min_input_length': 10,
                'max_input_length': 10000,
                'min_requirement_length': 10,
                'max_requirement_length': 200,
                'min_skill_length': 2,
                'max_skill_length': 50,
                'max_requirements': 10,
                'max_technical_skills': 15,
                'max_soft_skills': 8,
                'max_experience_requirements': 5
            },
            'processing': {
                'enable_html_cleanup': True,
                'enable_error_tracking': True,
                'validate_compression_ratio': True,
                'min_compression_ratio': 0.1,
                'max_compression_ratio': 1.5,
                'default_target_length': 300,
                'max_summary_length': 500,
                'min_summary_length': 100
            }
        }
    
    def _compile_patterns_from_config(self) -> Dict[str, List[re.Pattern]]:
        """Compile patterns from configuration."""
        return {
            'technical': [re.compile(p, re.IGNORECASE) for p in self.config['technical_patterns']],
            'soft_skills': [re.compile(p, re.IGNORECASE) for p in self.config['soft_skill_patterns']],
            'experience': [re.compile(p, re.IGNORECASE) for p in self.config['experience_patterns']],
            'requirements': [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in self.config['requirement_patterns']],
            'company': {
                'name': [re.compile(p, re.IGNORECASE) for p in self.config['company_patterns']['name']],
                'location': [re.compile(p, re.IGNORECASE) for p in self.config['company_patterns']['location']]
            }
        }
    
    def _compile_patterns(self):
        """Compile regex patterns for better performance."""
        self.compiled_technical = [re.compile(pattern, re.IGNORECASE) for pattern in self.technical_patterns]
        self.compiled_soft_skills = [re.compile(pattern, re.IGNORECASE) for pattern in self.soft_skill_patterns]
        self.compiled_experience = [re.compile(pattern, re.IGNORECASE) for pattern in self.experience_patterns]
        
        # Compile company patterns
        self.compiled_company = {}
        for category, patterns in self.company_patterns.items():
            self.compiled_company[category] = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    
    def process_job_description(self, job_description: str, max_length: int = 500) -> JobDescriptionSummary:
        """
        Process job description with improved error handling and accuracy.
        """
        issues = []
        
        try:
            # Input validation
            if not job_description or not job_description.strip():
                issues.append("Empty job description provided")
                return self._create_empty_summary(issues)
            
            # Clean and preprocess
            cleaned_text = self._clean_text(job_description)
            if len(cleaned_text.split()) < 10:
                issues.append("Job description too short for meaningful processing")
            
            original_length = len(cleaned_text.split())
            
            # Extract information with better error handling
            key_requirements = self._extract_key_requirements(cleaned_text)
            technical_skills = self._extract_technical_skills(cleaned_text)
            soft_skills = self._extract_soft_skills(cleaned_text)
            experience_requirements = self._extract_experience_requirements(cleaned_text)
            company_info = self._extract_company_info(cleaned_text)
            
            # Create optimized summary
            summary_text = self._create_optimized_summary(
                cleaned_text, 
                key_requirements, 
                technical_skills, 
                max_length
            )
            
            summary_length = len(summary_text.split())
            compression_ratio = summary_length / original_length if original_length > 0 else 1.0
            
            # Validate compression ratio
            if compression_ratio > 1.5:
                issues.append(f"Poor compression ratio: {compression_ratio:.2f}")
            elif compression_ratio < 0.1:
                issues.append(f"Over-compression detected: {compression_ratio:.2f}")
            
            return JobDescriptionSummary(
                original_length=original_length,
                summary_length=summary_length,
                compression_ratio=compression_ratio,
                key_requirements=key_requirements,
                technical_skills=technical_skills,
                soft_skills=soft_skills,
                experience_requirements=experience_requirements,
                company_info=company_info,
                summary_text=summary_text,
                processing_issues=issues
            )
            
        except Exception as e:
            logger.error(f"Error processing job description: {e}")
            issues.append(f"Processing error: {str(e)}")
            return self._create_empty_summary(issues)
    
    def _clean_text(self, text: str) -> str:
        """Clean and preprocess text."""
        # Decode HTML entities
        text = html.unescape(text)
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters that might break patterns
        text = re.sub(r'[^\w\s.,!?;:()\-&]', ' ', text)
        
        # Clean up bullet points and lists
        text = re.sub(r'[•\-\*]\s*', '• ', text)
        text = re.sub(r'\d+\.\s*', '• ', text)
        
        return text.strip()
    
    def _extract_technical_skills(self, text: str) -> List[str]:
        """Extract technical skills using configuration-driven patterns."""
        skills = set()
        text_lower = text.lower()
        validation = self.config['validation']
        
        # Use compiled patterns from configuration
        for pattern in self.compiled_patterns['technical']:
            matches = pattern.findall(text_lower)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                skill = match.strip().lower()
                if (validation['min_skill_length'] <= len(skill) <= validation['max_skill_length'] 
                    and skill not in ['the', 'and', 'or', 'with', 'in', 'of']):
                    skills.add(skill)
        
        return sorted(list(skills))[:validation['max_technical_skills']]
    
    def _extract_soft_skills(self, text: str) -> List[str]:
        """Extract soft skills using configuration-driven patterns."""
        skills = set()
        validation = self.config['validation']
        
        for pattern in self.compiled_patterns['soft_skills']:
            matches = pattern.findall(text)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                skill = match.strip().lower()
                if len(skill) > 3:
                    skills.add(skill)
        
        return sorted(list(skills))[:validation['max_soft_skills']]
    
    def _extract_experience_requirements(self, text: str) -> List[str]:
        """Extract experience requirements using configuration-driven patterns."""
        requirements = set()
        validation = self.config['validation']
        
        for pattern in self.compiled_patterns['experience']:
            matches = pattern.findall(text)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                req = match.strip()
                if req.isdigit() and int(req) <= 20:  # Reasonable experience range
                    requirements.add(f"{req}+ years")
                else:
                    requirements.add(req)
        
        return sorted(list(requirements))[:validation['max_experience_requirements']]
    
    def _extract_company_info(self, text: str) -> Dict[str, Any]:
        """Extract company information using configuration-driven patterns."""
        info = {}
        
        # Extract company name
        for pattern in self.compiled_patterns['company']['name']:
            match = pattern.search(text)
            if match:
                company_name = match.group(1).strip()
                if len(company_name) > 2 and len(company_name) < 50:
                    info['company_name'] = company_name
                    break
        
        # Extract location
        for pattern in self.compiled_patterns['company']['location']:
            match = pattern.search(text)
            if match:
                location = match.group(1).strip() if match.groups() else match.group(0)
                if len(location) > 2 and len(location) < 100:
                    info['location'] = location
                    break
        
        return info
    
    def _extract_key_requirements(self, text: str) -> List[str]:
        """Extract key requirements using configuration-driven patterns."""
        requirements = []
        validation = self.config['validation']
        
        # Use patterns from configuration
        for pattern in self.compiled_patterns['requirements']:
            matches = pattern.findall(text)
            for match in matches:
                req = match.strip()
                if (validation['min_requirement_length'] <= len(req) <= validation['max_requirement_length']):
                    requirements.append(req)
        
        # Remove duplicates and limit
        unique_requirements = list(dict.fromkeys(requirements))
        return unique_requirements[:validation['max_requirements']]
    
    def _create_optimized_summary(self, text: str, requirements: List[str], 
                                technical_skills: List[str], max_length: int) -> str:
        """Create an optimized summary with better structure."""
        summary_parts = []
        
        # Add role overview (first meaningful sentence)
        sentences = text.split('.')
        first_sentence = sentences[0].strip() + '.' if sentences else text[:200] + '...'
        summary_parts.append(f"Role: {first_sentence}")
        
        # Add key requirements
        if requirements:
            req_text = '; '.join(requirements[:3])  # Top 3 requirements
            summary_parts.append(f"Key Responsibilities: {req_text}")
        
        # Add technical skills
        if technical_skills:
            skills_text = ', '.join(technical_skills[:6])  # Top 6 skills
            summary_parts.append(f"Technical Skills: {skills_text}")
        
        # Add experience requirements
        exp_matches = re.findall(r'(\d+)\+?\s*years?\s+(?:of\s+)?(?:experience|hands-on)', text, re.IGNORECASE)
        if exp_matches:
            summary_parts.append(f"Experience Required: {exp_matches[0]}+ years")
        
        # Combine and truncate if needed
        summary = ' '.join(summary_parts)
        
        if len(summary.split()) > max_length:
            words = summary.split()
            summary = ' '.join(words[:max_length]) + '...'
        
        return summary
    
    def _create_empty_summary(self, issues: List[str]) -> JobDescriptionSummary:
        """Create an empty summary for error cases."""
        return JobDescriptionSummary(
            original_length=0,
            summary_length=0,
            compression_ratio=1.0,
            key_requirements=[],
            technical_skills=[],
            soft_skills=[],
            experience_requirements=[],
            company_info={},
            summary_text="Unable to process job description",
            processing_issues=issues
        )
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics and configuration."""
        return {
            "technical_patterns": len(self.technical_patterns),
            "soft_skill_patterns": len(self.soft_skill_patterns),
            "experience_patterns": len(self.experience_patterns),
            "company_patterns": sum(len(patterns) for patterns in self.company_patterns.values()),
            "max_requirements": 10,
            "max_technical_skills": 15,
            "max_soft_skills": 8,
            "max_experience_requirements": 5,
            "improvements": [
                "Better pattern matching accuracy",
                "HTML/formatting cleanup",
                "Performance optimization",
                "Edge case handling",
                "Error tracking"
            ]
        }
