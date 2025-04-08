from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.utils import clean_recommendations
from typing import List, Dict, Any
import json
import os

from app.models import RecommendationRequest, CleanRecommendationResponse
from app.recommender import SHLRecommender

# Constants
CURRENT_TIME = "2025-04-08 20:51:39"
CURRENT_USER = "saurabhbisht076"

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

# Data path
CATALOG_PATH = os.path.join("data", "processed", "shl_assessments_detailed.json")

# Initialize recommender
recommender = SHLRecommender()

@app.get("/")
def read_root():
    return {
        "message": "Welcome to SHL Assessment Recommender API",
        "timestamp": CURRENT_TIME,
        "user": CURRENT_USER,
        "status": "running"
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": CURRENT_TIME,
        "user": CURRENT_USER
    }

@app.get("/assessments", response_model=Dict[str, Any])
def get_all_assessments():
    try:
        with open(CATALOG_PATH, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading assessments: {str(e)}")

@app.post("/recommend", response_model=CleanRecommendationResponse)
def get_recommendations(request: RecommendationRequest):
    try:
        recommendations = recommender.get_recommendations(
            query=request.query,
            job_level=request.job_level,
            duration_max=request.max_duration,
            languages=request.languages,
            test_type=request.test_type,
            top_n=request.top_n
        )
        
        # Transform to clean format
        cleaned_recommendations = clean_recommendations(recommendations)
        
        return CleanRecommendationResponse(
            recommended_assessments=cleaned_recommendations
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendation error: {str(e)}")

@app.get("/job-levels")
def get_job_levels():
    try:
        with open(CATALOG_PATH, 'r') as f:
            data = json.load(f)
        job_levels = set()
        for assessment in data.get('assessments', []):
            job_levels.update(assessment.get('job_levels', []))
        return {"job_levels": sorted(job_levels)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading job levels: {str(e)}")

@app.get("/test-types")
def get_test_types():
    try:
        with open(CATALOG_PATH, 'r') as f:
            data = json.load(f)
        test_types = set()
        for assessment in data.get('assessments', []):
            test_types.add(assessment.get('test_type', 'Unknown'))
        return {"test_types": sorted(test_types)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading test types: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)