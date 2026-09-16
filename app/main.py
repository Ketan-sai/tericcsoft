import json
from pathlib import Path
from typing import List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.config import GROQ_MODEL
from app.database import engine, Base, get_db
import app.models  # ensure models are registered with Base
from app.models import Lead
from app.schemas import LeadCreateRequest, LeadResponse, HealthResponse
from app.retrieval import get_retriever
from app.llm import analyze_lead_with_groq, LLMServiceError

# Create tables on module load and ensure readiness
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup hook: ensure tables and retriever are ready
    Base.metadata.create_all(bind=engine)
    _ = get_retriever()
    yield

app = FastAPI(
    title="Sales Lead Qualification Assistant",
    description="FastAPI + SQLite + TF-IDF Retrieval + Groq LLM Assistant for Nimbus Software",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(LLMServiceError)
async def llm_service_error_handler(request: Request, exc: LLMServiceError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )

# ----------------- API Endpoints -----------------

@app.get("/api/health", response_model=HealthResponse)
def health_check():
    retriever = get_retriever()
    return HealthResponse(
        status="ok",
        kb_entries=len(retriever.get_all()),
        model=GROQ_MODEL
    )

@app.get("/api/knowledge-base", response_model=List[Dict[str, Any]])
def get_knowledge_base():
    retriever = get_retriever()
    return retriever.get_all()

@app.post("/api/leads", response_model=LeadResponse)
def create_lead(payload: LeadCreateRequest, db: Session = Depends(get_db)):
    retriever = get_retriever()
    retrieved_docs = retriever.search(payload.requirement, top_k=3)

    analysis = analyze_lead_with_groq(payload.requirement, retrieved_docs)

    lead = Lead(
        company_name=payload.company_name,
        contact_email=payload.contact_email,
        requirement=payload.requirement,
        retrieved_context=json.dumps(retrieved_docs),
        lead_summary=analysis.lead_summary,
        relevant_products=json.dumps([p.model_dump() for p in analysis.relevant_products]),
        customer_needs=json.dumps(analysis.customer_needs),
        recommended_next_step=analysis.recommended_next_step,
        follow_up_questions=json.dumps(analysis.follow_up_questions),
        lead_score=analysis.lead_score,
        priority=analysis.priority
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)

    return LeadResponse.from_orm_model(lead)

@app.get("/api/leads", response_model=List[LeadResponse])
def list_leads(limit: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db)):
    leads = db.query(Lead).order_by(Lead.created_at.desc()).limit(limit).all()
    return [LeadResponse.from_orm_model(l) for l in leads]

@app.get("/api/leads/{lead_id}", response_model=LeadResponse)
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead with ID {lead_id} not found")
    return LeadResponse.from_orm_model(lead)

# ----------------- Mount Static Files -----------------
static_dir = Path(__file__).resolve().parent.parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
