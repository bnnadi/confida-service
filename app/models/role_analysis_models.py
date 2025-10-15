"""
Role analysis models and enums.
Separated to avoid circular imports.
"""

from typing import List, Optional
from dataclasses import dataclass
from enum import Enum

class Industry(Enum):
    TECHNOLOGY = "technology"
    FINANCE = "finance"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    RETAIL = "retail"
    MANUFACTURING = "manufacturing"
    GOVERNMENT = "government"
    NON_PROFIT = "non_profit"
    CONSULTING = "consulting"
    MEDIA = "media"
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

# Legacy enums for backward compatibility
class IndustryType(Enum):
    TECHNOLOGY = "technology"
    HEALTHCARE = "healthcare"
    FINANCE = "finance"
    SALES_MARKETING = "sales_marketing"
    UNKNOWN = "unknown"

class JobFunction(Enum):
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
