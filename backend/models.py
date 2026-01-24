from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

SQLALCHEMY_DATABASE_URL = "sqlite:///./leads.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Lead(Base):
    __tablename__ = "leads"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    category = Column(String)
    location = Column(String)
    phone = Column(String)
    normalized_phone = Column(String, index=True)
    address = Column(Text)
    website = Column(String)
    has_website = Column(Boolean, default=False)
    rating = Column(Float, default=0.0)
    reviews = Column(Integer, default=0)
    maps_url = Column(Text)
    status = Column(String, default="new") # new, message_generated, sent, failed, responded
    generated_message = Column(Text)
    priority_score = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

Base.metadata.create_all(bind=engine)
