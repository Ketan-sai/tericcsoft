from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime
from app.database import Base

def get_utc_now():
    return datetime.now(timezone.utc)

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    company_name = Column(String(255), nullable=True)
    contact_email = Column(String(255), nullable=True)
    requirement = Column(Text, nullable=False)
    retrieved_context = Column(Text, nullable=False, default="[]")
    lead_summary = Column(Text, nullable=False, default="")
    relevant_products = Column(Text, nullable=False, default="[]")
    customer_needs = Column(Text, nullable=False, default="[]")
    recommended_next_step = Column(Text, nullable=False, default="")
    follow_up_questions = Column(Text, nullable=False, default="[]")
    lead_score = Column(Integer, nullable=False, default=0)
    priority = Column(String(50), nullable=False, default="Low")
    created_at = Column(DateTime, default=get_utc_now)
