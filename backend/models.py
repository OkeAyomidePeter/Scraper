from datetime import datetime
import uuid
from sqlalchemy import Column, String, DateTime, Text, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID

Base = declarative_base()

class Lead(Base):
    __tablename__ = 'leads'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # Business identifiers
    maps_url = Column(Text, unique=True, nullable=False)
    business_name = Column(String(255), nullable=False)
    category = Column(String(255))
    phone_number = Column(String(50))
    email = Column(String(255))
    website_url = Column(Text)
    rating = Column(String(10))
    reviews = Column(String(10))
    
    # Channel and messaging
    primary_channel = Column(String(20))
    email_draft = Column(Text)
    email_subject = Column(String(255))
    whatsapp_draft = Column(Text)
    
    # State tracking
    state = Column(String(50), default='DISCOVERED')  # DISCOVERED, ENRICHED, DRAFTED, QUEUED, SENT, WAITING, NO_REPLY, FOLLOW_UP_ELIGIBLE, REPLIED, CLOSED, NEEDS_REVIEW
    is_queued = Column(Boolean, default=False)
    queued_at = Column(DateTime)
    sent_at = Column(DateTime)
    last_interaction_at = Column(DateTime)
    follow_up_count = Column(Float, default=0) # Using float just in case but int is fine
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Lead(name='{self.business_name}', state='{self.state}', channel='{self.primary_channel}')>"
