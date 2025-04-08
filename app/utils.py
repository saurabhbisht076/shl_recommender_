from datetime import datetime
import os
import json
from typing import List, Dict, Any, Optional

def get_current_timestamp() -> str:
    """Get current timestamp in UTC"""
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

def parse_duration(duration_str) -> Optional[int]:
    """Parse duration string to minutes"""
    if not duration_str:
        return None
        
    try:
        minutes = int(''.join(filter(str.isdigit, str(duration_str))))
        return minutes
    except ValueError:
        return None

def clean_recommendations(recommendations: list) -> List[Dict[str, Any]]:
    """Clean and transform recommendations to match API spec"""
    cleaned = []
    for rec in recommendations[:10]:  # Limit to 10 recommendations
        if "assessment" in rec:
            assessment = rec["assessment"]
            cleaned_assessment = {
                "url": assessment.get("url", ""),
                "adaptive_support": "Yes" if assessment.get("adaptive_irt_support") else "No",
                "description": assessment.get("description", ""),
                "duration": parse_duration(assessment.get("duration", "0")) or 0,
                "remote_support": "Yes" if assessment.get("remote_testing_support") else "No",
                "test_type": [assessment.get("test_type")] if isinstance(assessment.get("test_type"), str) else assessment.get("test_type", [])
            }
            cleaned.append(cleaned_assessment)
    return cleaned

def load_catalog() -> Dict:
    """Load the catalog data"""
    try:
        with open('data/processed/shl_catalog.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        try:
            with open('data/raw/shl_catalog.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"metadata": {}, "assessments": []}

def save_catalog(catalog_data: Dict, processed: bool = True) -> None:
    """Save catalog data to appropriate location"""
    path = 'data/processed/shl_catalog.json' if processed else 'data/raw/shl_catalog.json'
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(catalog_data, f, indent=2)

def get_unique_values(catalog_data: Dict, field: str) -> List[str]:
    """Extract unique values for a given field across all assessments"""
    values = set()
    for assessment in catalog_data.get('assessments', []):
        if field in assessment:
            if isinstance(assessment[field], list):
                values.update(assessment[field])
            else:
                values.add(assessment[field])
    return sorted(list(values))