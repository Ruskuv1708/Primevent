import os
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .database import engine, Base, get_db
from .models import Lead

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Party Show API")

# CORS
cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=bool(cors_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)

class LeadCreate(BaseModel):
    name: Optional[str] = None
    contact: str
    message: Optional[str] = None

class LeadRead(BaseModel):
    id: int
    name: Optional[str]
    contact: str
    message: Optional[str]
    created_at: str

    class Config:
        from_attributes = True

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "party_show"}

@app.post("/api/leads")
def create_lead(lead: LeadCreate, db: Session = Depends(get_db)):
    db_lead = Lead(name=lead.name, contact=lead.contact, message=lead.message)
    db.add(db_lead)
    db.commit()
    db.refresh(db_lead)
    return {"status": "ok", "id": db_lead.id}

@app.get("/api/leads")
def list_leads(db: Session = Depends(get_db), x_admin_key: Optional[str] = Header(None)):
    admin_key = os.getenv("BACKEND_ADMIN_KEY")
    if not admin_key or x_admin_key != admin_key:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    # Simple list for internal use
    return db.query(Lead).order_by(Lead.created_at.desc()).all()
