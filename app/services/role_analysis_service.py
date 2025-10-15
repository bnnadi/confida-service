"""
Enhanced role analysis service for intelligent question selection.
Extracts skills, industry, seniority, and other role characteristics.
"""
import re
import asyncio
from typing import Dict, List, Any, Optional
from app.utils.logger import get_logger
from app.utils.validation_mixin import ValidationMixin
from app.models.role_analysis_models import RoleAnalysis, Industry, SeniorityLevel, CompanySize

logger = get_logger(__name__)

class RoleAnalysisService:
    """Enhanced role analysis service for intelligent question selection."""
    
    def __init__(self):
        # DynamicPromptService will be imported when needed to avoid circular imports
        self.dynamic_prompt_service = None
        
        # Centralized extraction patterns for unified processing
        self.extraction_patterns = {
            'required_skills': {
                'patterns': [
                    r'(?:proficient in|experience with|knowledge of|skills in)\s+([\w\s+]+)',
                    r'(?:required|must have|should have)\s+([\w\s+]+)\s+(?:experience|knowledge|skills)'
                ],
                'keywords': {
                    'programming': ['python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'go', 'rust', 'php', 'ruby'],
                    'databases': ['sql', 'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch', 'cassandra'],
                    'cloud': ['aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform', 'cloudformation'],
                    'frameworks': ['react', 'angular', 'vue', 'django', 'flask', 'spring', 'express', 'fastapi'],
                    'tools': ['git', 'jenkins', 'ci/cd', 'agile', 'scrum', 'jira', 'confluence'],
                    'ai_ml': ['machine learning', 'deep learning', 'tensorflow', 'pytorch', 'nlp', 'computer vision']
                },
                'default': []
            },
            'tech_stack': {
                'patterns': [
                    r'(?:tech stack|technologies|tools)\s*:?\s*([\w\s,]+)',
                    r'(?:using|working with|familiar with)\s+([\w\s,]+)'
                ],
                'keywords': {},
                'default': []
            },
            'soft_skills': {
                'patterns': [
                    r'(?:soft skills|interpersonal|communication)\s*:?\s*([\w\s,]+)',
                    r'(?:leadership|teamwork|problem solving|communication)'
                ],
                'keywords': {
                    'soft_skills': [
                        'leadership', 'communication', 'teamwork', 'problem solving', 'critical thinking',
                        'time management', 'adaptability', 'creativity', 'emotional intelligence',
                        'mentoring', 'collaboration', 'presentation', 'negotiation'
                    ]
                },
                'default': []
            },
            'experience_years': {
                'patterns': [
                    r'(\d+)[\+\-]?\s*years?',
                    r'(\d+)\s*to\s*(\d+)\s*years?',
                    r'minimum\s*(\d+)\s*years?'
                ],
                'default': 0
            }
        }
        
        # Industry detection patterns
        self.industry_patterns = {
            Industry.TECHNOLOGY: ['software', 'tech', 'startup', 'saas', 'platform', 'api', 'development'],
            Industry.FINANCE: ['banking', 'finance', 'fintech', 'investment', 'trading', 'risk', 'compliance'],
            Industry.HEALTHCARE: ['healthcare', 'medical', 'pharma', 'clinical', 'patient', 'health'],
            Industry.EDUCATION: ['education', 'learning', 'training', 'academic', 'university', 'school'],
            Industry.RETAIL: ['retail', 'ecommerce', 'shopping', 'customer', 'sales', 'marketing'],
            Industry.MANUFACTURING: ['manufacturing', 'production', 'industrial', 'supply chain', 'logistics'],
            Industry.CONSULTING: ['consulting', 'advisory', 'strategy', 'management', 'business'],
            Industry.MEDIA: ['media', 'entertainment', 'content', 'publishing', 'broadcast'],
            Industry.GOVERNMENT: ['government', 'public sector', 'policy', 'regulatory', 'federal'],
            Industry.NON_PROFIT: ['nonprofit', 'ngo', 'charity', 'social impact', 'volunteer']
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
        """Execute analysis pipeline using declarative configuration."""
        tasks = []
        
        # Add extraction tasks
        for extraction_type in config['extractions']:
            tasks.append(self._extract_with_pattern(extraction_type, job_description))
        
        # Add detection tasks
        for detection_type in config['detections']:
            if detection_type == 'job_function':
                tasks.append(self._detect_job_function('', job_description))  # Role will be handled in _build_role_analysis
            else:
                method_name = f"_detect_{detection_type}"
                method = getattr(self, method_name)
                tasks.append(method(job_description))
        
        # Add requirement tasks
        for requirement_type in config['requirements']:
            method_name = f"_extract_{requirement_type}_requirements"
            method = getattr(self, method_name)
            tasks.append(method(job_description))
        
        # Execute all tasks in parallel
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _extract_with_pattern(self, pattern_name: str, text: str) -> Any:
        """Generic pattern-based extraction using unified logic."""
        pattern_config = self.extraction_patterns.get(pattern_name)
        if not pattern_config:
            return pattern_config.get('default', None)
        
        text_lower = text.lower()
        
        # Try regex patterns first
        for pattern in pattern_config.get('patterns', []):
            matches = re.findall(pattern, text_lower)
            if matches:
                if pattern_name == 'experience_years':
                    # Handle experience years extraction
                    if isinstance(matches[0], tuple):
                        return int(matches[0][1])  # Take higher number from range
                    else:
                        return int(matches[0])
                else:
                    # Handle list extractions
                    return [match.strip() for match in matches if match.strip()]
        
        # Fall back to keyword matching
        keywords = pattern_config.get('keywords', {})
        if keywords:
            found_items = []
            for category, keyword_list in keywords.items():
                for keyword in keyword_list:
                    if keyword in text_lower:
                        found_items.append(keyword)
            if found_items:
                return found_items
        
        return pattern_config.get('default', None)
    
    def _build_role_analysis(self, role: str, results: List[Any]) -> RoleAnalysis:
        """Build RoleAnalysis from parallel extraction results with automatic type conversion."""
        # Define extraction schema with type information
        extraction_schema = {
            'required_skills': ([], list),
            'tech_stack': ([], list),
            'soft_skills': ([], list),
            'experience_years': (0, int),
            'industry': (Industry.OTHER, Industry),
            'seniority_level': (SeniorityLevel.MID, SeniorityLevel),
            'company_size': (CompanySize.MEDIUM, CompanySize),
            'job_function': ("software_development", str),
            'education_requirements': ([], list),
            'certifications': ([], list)
        }
        
        # Process results with automatic type conversion
        extracted_data = {}
        for i, (field_name, (default_value, expected_type)) in enumerate(extraction_schema.items()):
            result = results[i] if i < len(results) else default_value
            
            if isinstance(result, Exception):
                extracted_data[field_name] = default_value
            else:
                extracted_data[field_name] = self._convert_to_type(result, expected_type, default_value)
        
        analysis = RoleAnalysis(primary_role=role, **extracted_data)
        
        logger.info(f"Role analysis completed: {analysis.industry.value}, {analysis.seniority_level.value}, {len(analysis.required_skills)} skills")
        return analysis
    
    def _convert_to_type(self, value: Any, expected_type: type, default_value: Any) -> Any:
        """Convert value to expected type with fallback to default."""
        try:
            if expected_type == list and not isinstance(value, list):
                return [value] if value else []
            elif expected_type == int and not isinstance(value, int):
                return int(value) if value else default_value
            elif expected_type == str and not isinstance(value, str):
                return str(value) if value else default_value
            elif hasattr(expected_type, '__members__'):  # Enum type
                if isinstance(value, expected_type):
                    return value
                elif isinstance(value, str):
                    # Try to find enum by value
                    for enum_member in expected_type:
                        if enum_member.value.lower() == value.lower():
                            return enum_member
                    return default_value
                else:
                    return default_value
            else:
                return value if isinstance(value, expected_type) else default_value
        except (ValueError, TypeError, AttributeError):
            return default_value
    
    def _get_default_analysis(self, role: str) -> RoleAnalysis:
        """Get default analysis when extraction fails."""
        return RoleAnalysis(
            primary_role=role,
            required_skills=[],
            industry=Industry.OTHER,
            seniority_level=SeniorityLevel.MID,
            company_size=CompanySize.MEDIUM,
            tech_stack=[],
            soft_skills=[],
            job_function="software_development",
            experience_years=0,
            education_requirements=[],
            certifications=[]
        )

    def _find_matching_items(self, text: str, item_dict: Dict[Any, List[str]]) -> List[str]:
        """Generic method to find matching items in text."""
        return ValidationMixin.find_matching_items(text, item_dict)
    

    async def _detect_industry(self, job_description: str) -> Industry:
        """Detect industry from job description using pattern matching."""
        text_lower = job_description.lower()
        
        for industry, keywords in self.industry_patterns.items():
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