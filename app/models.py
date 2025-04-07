from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class AssessmentMeta(BaseModel):
    scrape_time: str
    scraper_user: str

class Assessment(BaseModel):
    name: str
    url: str
    description: str
    job_levels: List[str] = []
    languages: List[str] = []
    duration: str = ""
    remote_testing_support: bool = False
    adaptive_irt_support: bool = False
    pdf_link: Optional[str] = None
    test_type: str = "General Assessment"
    metadata: AssessmentMeta
    embedding: Optional[List[float]] = None

class CatalogMetadata(BaseModel):
    scrape_time: str
    scraper_user: str
    total_assessments: int

class SHLCatalog(BaseModel):
    metadata: CatalogMetadata
    assessments: List[Assessment]
    embeddings: bool = False

class RecommendationRequest(BaseModel):
    query: str = Field(..., description="Search query or job description")
    job_level: Optional[str] = Field(None, description="Filter by job level")
    max_duration: Optional[int] = Field(None, description="Maximum test duration in minutes")
    languages: Optional[List[str]] = Field(None, description="Filter by languages")
    test_type: Optional[str] = Field(None, description="Filter by test type")
    top_n: int = Field(5, description="Number of recommendations to return")

class RecommendationResponse(BaseModel):
    recommendations: List[Dict[str, Any]]
    query: str
    filters_applied: Dict[str, Any]