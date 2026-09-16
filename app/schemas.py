import re
import json
from typing import List, Optional, Literal, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

class LeadCreateRequest(BaseModel):
    requirement: str
    company_name: Optional[str] = None
    contact_email: Optional[str] = None

    @field_validator("requirement")
    @classmethod
    def validate_requirement(cls, v: str) -> str:
        if v is None:
            raise ValueError("Requirement is required")
        v_stripped = v.strip()
        if not v_stripped:
            raise ValueError("Requirement cannot be blank")
        if len(v_stripped) < 15:
            raise ValueError("Requirement must be at least 15 characters")
        if len(v_stripped) > 2000:
            raise ValueError("Requirement must be at most 2000 characters")
        return v_stripped

    @field_validator("contact_email")
    @classmethod
    def validate_contact_email(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v_stripped = v.strip()
        if not v_stripped:
            return None
        if not EMAIL_REGEX.match(v_stripped):
            raise ValueError("Invalid contact email address format")
        return v_stripped

    @field_validator("company_name")
    @classmethod
    def validate_company_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v_stripped = v.strip()
        return v_stripped if v_stripped else None

class RelevantProduct(BaseModel):
    name: str = Field(..., description="Name of the relevant product")
    why: str = Field(..., description="Reason why this product is relevant")

class LLMLeadAnalysis(BaseModel):
    lead_summary: str = Field(..., min_length=10)
    relevant_products: List[RelevantProduct] = Field(..., min_length=1)
    customer_needs: List[str] = Field(..., min_length=1)
    recommended_next_step: str = Field(..., min_length=5)
    follow_up_questions: List[str] = Field(..., min_length=2)
    lead_score: int = Field(..., ge=0, le=100)
    priority: Literal["High", "Medium", "Low"]

class LeadResponse(BaseModel):
    id: int
    company_name: Optional[str] = None
    contact_email: Optional[str] = None
    requirement: str
    retrieved_context: List[Any]
    lead_summary: str
    relevant_products: List[Any]
    customer_needs: List[str]
    recommended_next_step: str
    follow_up_questions: List[str]
    lead_score: int
    priority: str
    created_at: datetime

    @classmethod
    def from_orm_model(cls, lead):
        def parse_field(field_val, fallback):
            if isinstance(field_val, (list, dict)):
                return field_val
            if not field_val:
                return fallback
            try:
                return json.loads(field_val)
            except Exception:
                return fallback

        return cls(
            id=lead.id,
            company_name=lead.company_name,
            contact_email=lead.contact_email,
            requirement=lead.requirement,
            retrieved_context=parse_field(lead.retrieved_context, []),
            lead_summary=lead.lead_summary or "",
            relevant_products=parse_field(lead.relevant_products, []),
            customer_needs=parse_field(lead.customer_needs, []),
            recommended_next_step=lead.recommended_next_step or "",
            follow_up_questions=parse_field(lead.follow_up_questions, []),
            lead_score=lead.lead_score or 0,
            priority=lead.priority or "Low",
            created_at=lead.created_at
        )

class HealthResponse(BaseModel):
    status: str
    kb_entries: int
    model: str
