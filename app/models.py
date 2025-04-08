from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class RecommendationRequest(BaseModel):
    query: str = Field(..., description="Search query or job description")
    job_level: Optional[str] = Field(None, description="Filter by job level")
    max_duration: Optional[int] = Field(None, description="Maximum test duration in minutes")
    languages: Optional[List[str]] = Field(None, description="Filter by languages")
    test_type: Optional[str] = Field(None, description="Filter by test type")
    top_n: int = Field(5, description="Number of recommendations to return")

class CleanAssessment(BaseModel):
    url: str
    adaptive_support: str
    description: str
    duration: int
    remote_support: str
    test_type: List[str]
    
    class Config:
        extra = "forbid"

class CleanRecommendationResponse(BaseModel):
    recommended_assessments: List[CleanAssessment]
    
    class Config:
        extra = "forbid"