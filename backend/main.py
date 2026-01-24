from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from scraper import scrape_google_maps
import uuid

app = FastAPI(title="Nigerian Business Outreach System API")

class ScrapeRequest(BaseModel):
    business_type: str
    location: str
    max_results: Optional[int] = 50

# In-memory storage for now (will move to SQLite later)
jobs = {}
leads_db = []

@app.get("/")
async def root():
    return {"message": "Nigerian Business Outreach System API is running"}

@app.post("/scrape")
async def trigger_scrape(request: ScrapeRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "processing", "business_type": request.business_type, "location": request.location}
    
    background_tasks.add_task(run_scrape_job, job_id, request.business_type, request.location, request.max_results)
    
    return {"job_id": job_id, "status": "started"}

async def run_scrape_job(job_id: str, business_type: str, location: str, max_results: int):
    try:
        results = await scrape_google_maps(business_type, location, max_results)
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["results_count"] = len(results)
        
        # Add to global leads list
        for lead in results:
            lead['id'] = str(uuid.uuid4())
            leads_db.append(lead)
            
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)

@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    return jobs.get(job_id, {"status": "not_found"})

@app.get("/leads")
async def list_leads():
    return leads_db

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
