from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import json
import os
from datetime import datetime

# Constants
CURRENT_TIME = "2025-04-08 21:56:56"
CURRENT_USER = "saurabhbisht076"

# Pydantic Models
class RecommendationRequest(BaseModel):
    query: str
    job_level: Optional[str] = None
    max_duration: Optional[int] = None
    languages: Optional[List[str]] = None
    test_type: Optional[str] = None
    top_n: Optional[int] = 5

class AssessmentResponse(BaseModel):
    id: str
    name: str
    description: str
    score: float
    job_levels: List[str]
    duration: int
    test_type: str

class CleanRecommendationResponse(BaseModel):
    recommended_assessments: List[AssessmentResponse]

app = FastAPI(
    title="SHL Assessment Recommender API",
    description="API for recommending SHL assessments based on job descriptions and criteria",
    version="1.0.0"
)

# CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock data for initial deployment
MOCK_ASSESSMENTS = {
    "assessments": [
        {
            "id": "SHL001",
            "name": "Verbal Reasoning",
            "description": "Evaluates ability to understand and analyze written information",
            "score": 0.95,
            "duration": 30,
            "job_levels": ["entry", "mid"],
            "test_type": "cognitive",
            "languages": ["en"]
        },
        {
            "id": "SHL002",
            "name": "Numerical Reasoning",
            "description": "Tests ability to analyze numerical data and make logical decisions",
            "score": 0.88,
            "duration": 45,
            "job_levels": ["mid", "senior"],
            "test_type": "cognitive",
            "languages": ["en", "es"]
        },
        {
            "id": "SHL003",
            "name": "Leadership Assessment",
            "description": "Evaluates leadership potential and management capabilities",
            "score": 0.92,
            "duration": 60,
            "job_levels": ["senior"],
            "test_type": "behavioral",
            "languages": ["en"]
        }
    ]
}

@app.get("/")
async def read_root():
    return {
        "message": "Welcome to SHL Assessment Recommender API",
        "timestamp": CURRENT_TIME,
        "user": CURRENT_USER,
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": CURRENT_TIME,
        "user": CURRENT_USER
    }

@app.get("/assessments", response_model=Dict[str, Any])
async def get_all_assessments():
    return MOCK_ASSESSMENTS

@app.post("/recommend", response_model=CleanRecommendationResponse)
async def get_recommendations(request: RecommendationRequest):
    try:
        # Filter assessments based on criteria
        filtered_assessments = MOCK_ASSESSMENTS["assessments"]
        
        if request.job_level:
            filtered_assessments = [
                a for a in filtered_assessments 
                if request.job_level in a["job_levels"]
            ]
            
        if request.max_duration:
            filtered_assessments = [
                a for a in filtered_assessments 
                if a["duration"] <= request.max_duration
            ]
            
        if request.languages:
            filtered_assessments = [
                a for a in filtered_assessments 
                if any(lang in a["languages"] for lang in request.languages)
            ]
            
        if request.test_type:
            filtered_assessments = [
                a for a in filtered_assessments 
                if a["test_type"] == request.test_type
            ]
        
        # Limit to top_n results
        if request.top_n:
            filtered_assessments = filtered_assessments[:request.top_n]
        
        return CleanRecommendationResponse(
            recommended_assessments=filtered_assessments
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendation error: {str(e)}")

@app.get("/job-levels")
async def get_job_levels():
    job_levels = set()
    for assessment in MOCK_ASSESSMENTS["assessments"]:
        job_levels.update(assessment["job_levels"])
    return {"job_levels": sorted(job_levels)}

@app.get("/test-types")
async def get_test_types():
    test_types = set()
    for assessment in MOCK_ASSESSMENTS["assessments"]:
        test_types.add(assessment["test_type"])
    return {"test_types": sorted(test_types)}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)