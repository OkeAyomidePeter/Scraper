import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from models import Base, Lead
import datetime
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./outreach.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def save_lead(db, lead_data: dict):
    """Saves a lead to the database. Updates if maps_url exists."""
    existing = db.query(Lead).filter(Lead.maps_url == lead_data.get('maps_url')).first()
    
    if existing:
        for key, value in lead_data.items():
            # Map keys to model attributes
            if key == 'name':
                setattr(existing, 'business_name', value)
            elif key == 'phone':
                setattr(existing, 'phone_number', value)
            elif key == 'website':
                setattr(existing, 'website_url', value)
            elif hasattr(existing, key):
                setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing
    
    new_lead = Lead(
        business_name=lead_data.get('name'),
        category=lead_data.get('category'),
        phone_number=lead_data.get('phone'),
        email=lead_data.get('email'),
        website_url=lead_data.get('website'),
        maps_url=lead_data.get('maps_url'),
        rating=lead_data.get('rating'),
        reviews=lead_data.get('reviews'),
        primary_channel=lead_data.get('primary_channel'),
        email_draft=lead_data.get('email_draft'),
        email_subject=lead_data.get('email_subject'),
        whatsapp_draft=lead_data.get('whatsapp_draft'),
        state=lead_data.get('state', 'DISCOVERED')
    )
    db.add(new_lead)
    db.commit()
    db.refresh(new_lead)
    return new_lead
