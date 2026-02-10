from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Lead
from datetime import datetime
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Outreach Action API")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/action/sent/{lead_id}")
async def mark_as_sent(lead_id: str, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    lead.state = 'SENT'
    lead.sent_at = datetime.utcnow()
    lead.last_interaction_at = lead.sent_at
    db.commit()
    logger.info(f"Lead {lead.business_name} marked as SENT")
    return {"status": "success", "message": f"{lead.business_name} marked as SENT"}

@app.get("/action/replied/{lead_id}")
async def mark_as_replied(lead_id: str, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    lead.state = 'REPLIED'
    lead.last_interaction_at = datetime.utcnow()
    db.commit()
    logger.info(f"Lead {lead.business_name} marked as REPLIED")
    return {"status": "success", "message": f"{lead.business_name} marked as REPLIED"}

@app.get("/action/closed/{lead_id}")
async def mark_as_closed(lead_id: str, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    lead.state = 'CLOSED'
    db.commit()
    logger.info(f"Lead {lead.business_name} marked as CLOSED")
    return {"status": "success", "message": f"{lead.business_name} marked as CLOSED"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3063)
