"""Pydantic schemas for structured answer generation

Enforces answer completeness and structure with type safety.
Each intent type has its own schema with validation rules.
"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict
from enum import Enum


class IntentType(str, Enum):
    """Supported intent types"""
    DISCOVERY = "DISCOVERY"
    ELIGIBILITY = "ELIGIBILITY"
    BENEFITS = "BENEFITS"
    COMPARISON = "COMPARISON"
    PROCEDURE = "PROCEDURE"
    GENERAL = "GENERAL"


class SchemeReference(BaseModel):
    """Reference to a government scheme"""
    scheme_name: str = Field(..., description="Name of the government scheme")
    ministry: Optional[str] = Field(None, description="Ministry/Department")
    url: Optional[str] = Field(None, description="Official scheme URL")


class DiscoveryAnswer(BaseModel):
    """Answer schema for DISCOVERY intent"""
    schemes_found: List[Dict[str, str]] = Field(
        ..., 
        description="List of relevant schemes with name and brief description",
        min_items=1
    )
    summary: str = Field(
        ..., 
        description="Brief overview of found schemes",
        min_length=50
    )
    total_count: int = Field(..., description="Number of schemes found", ge=1)
    sources: List[SchemeReference] = Field(..., description="Scheme references")
    
    @validator('schemes_found')
    def validate_schemes(cls, v):
        """Ensure each scheme has required fields"""
        for scheme in v:
            if 'name' not in scheme or 'description' not in scheme:
                raise ValueError(
                    "Each scheme must have 'name' and 'description' fields"
                )
        return v


class EligibilityAnswer(BaseModel):
    """Answer schema for ELIGIBILITY intent"""
    can_apply: Optional[bool] = Field(
        None, 
        description="Direct yes/no answer if applicable"
    )
    eligibility_criteria: List[str] = Field(
        ..., 
        description="List of eligibility criteria",
        min_items=1
    )
    age_requirements: Optional[str] = Field(
        None, 
        description="Age-related criteria if applicable"
    )
    income_requirements: Optional[str] = Field(
        None, 
        description="Income-related criteria if applicable"
    )
    special_categories: Optional[List[str]] = Field(
        None, 
        description="Special category eligibility (women, SC/ST, etc.)"
    )
    exclusions: Optional[List[str]] = Field(
        None, 
        description="Who cannot apply"
    )
    scheme_name: str = Field(..., description="Scheme being queried")
    sources: List[SchemeReference] = Field(..., description="Scheme references")
    
    @validator('eligibility_criteria')
    def validate_no_cop_out(cls, v):
        """Prevent 'not mentioned' cop-outs"""
        for criterion in v:
            if 'not mentioned' in criterion.lower() or 'not specified' in criterion.lower():
                raise ValueError(
                    "Eligibility criteria must be specific, not 'not mentioned'"
                )
        return v


class BenefitsAnswer(BaseModel):
    """Answer schema for BENEFITS intent"""
    scheme_name: str = Field(..., description="Scheme name")
    financial_benefits: Optional[Dict[str, str]] = Field(
        None,
        description="Financial benefits with amounts (subsidy, loan, grant, etc.)"
    )
    non_financial_benefits: Optional[List[str]] = Field(
        None,
        description="Non-financial benefits (training, mentorship, etc.)"
    )
    benefit_amounts: List[str] = Field(
        ...,
        description="Specific benefit amounts or ranges",
        min_items=1
    )
    conditions: Optional[List[str]] = Field(
        None,
        description="Conditions to receive benefits"
    )
    sources: List[SchemeReference] = Field(..., description="Scheme references")
    
    @validator('benefit_amounts')
    def validate_has_amounts(cls, v):
        """Ensure at least one benefit amount is specified"""
        if not v:
            raise ValueError("Must specify at least one benefit amount")
        # Check if at least one contains currency or numbers
        has_amount = any(
            '₹' in amount or any(char.isdigit() for char in amount)
            for amount in v
        )
        if not has_amount:
            raise ValueError(
                "Benefit amounts must include specific numbers or currency"
            )
        return v


class ComparisonAnswer(BaseModel):
    """Answer schema for COMPARISON intent"""
    scheme_a: Dict[str, any] = Field(
        ..., 
        description="Details of first scheme"
    )
    scheme_b: Dict[str, any] = Field(
        ..., 
        description="Details of second scheme"
    )
    key_differences: Dict[str, Dict[str, str]] = Field(
        ...,
        description="Key differences mapped by category",
        min_items=1
    )
    similarities: Optional[List[str]] = Field(
        None,
        description="Common features between schemes"
    )
    recommendation: Optional[str] = Field(
        None,
        description="Recommendation on which to choose"
    )
    sources: List[SchemeReference] = Field(
        ..., 
        description="Scheme references",
        min_items=2
    )
    
    @validator('key_differences')
    def validate_both_schemes_compared(cls, v, values):
        """Ensure both schemes are addressed in differences"""
        if not v:
            raise ValueError("Must provide key differences between schemes")
        return v
    
    @validator('sources')
    def validate_both_sources(cls, v):
        """Ensure both schemes are referenced"""
        if len(v) < 2:
            raise ValueError("Comparison must reference both schemes")
        return v


class ProcedureAnswer(BaseModel):
    """Answer schema for PROCEDURE intent"""
    scheme_name: str = Field(..., description="Scheme name")
    application_steps: List[str] = Field(
        ...,
        description="Step-by-step application process",
        min_items=1
    )
    required_documents: Optional[List[str]] = Field(
        None,
        description="Required documents for application"
    )
    application_portal: Optional[str] = Field(
        None,
        description="URL or portal name for application"
    )
    timeline: Optional[str] = Field(
        None,
        description="Processing timeline if available"
    )
    contact_information: Optional[Dict[str, str]] = Field(
        None,
        description="Contact details for queries"
    )
    sources: List[SchemeReference] = Field(..., description="Scheme references")


class GeneralAnswer(BaseModel):
    """Answer schema for GENERAL intent (fallback)"""
    answer: str = Field(
        ..., 
        description="Answer to the query",
        min_length=50
    )
    relevant_schemes: Optional[List[str]] = Field(
        None,
        description="Related schemes if applicable"
    )
    sources: List[SchemeReference] = Field(
        ..., 
        description="Scheme references",
        min_items=1
    )


# Schema mapping by intent
INTENT_SCHEMAS = {
    IntentType.DISCOVERY: DiscoveryAnswer,
    IntentType.ELIGIBILITY: EligibilityAnswer,
    IntentType.BENEFITS: BenefitsAnswer,
    IntentType.COMPARISON: ComparisonAnswer,
    IntentType.PROCEDURE: ProcedureAnswer,
    IntentType.GENERAL: GeneralAnswer,
}


def get_schema_for_intent(intent: str) -> type[BaseModel]:
    """Get the appropriate schema for an intent type"""
    try:
        intent_enum = IntentType(intent.upper())
        return INTENT_SCHEMAS[intent_enum]
    except (ValueError, KeyError):
        # Default to general for unknown intents
        return GeneralAnswer


def validate_answer(answer_data: dict, intent: str) -> tuple[bool, Optional[str]]:
    """Validate answer against intent schema
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    schema = get_schema_for_intent(intent)
    try:
        schema(**answer_data)
        return True, None
    except Exception as e:
        return False, str(e)
