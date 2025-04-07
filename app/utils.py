import re
from datetime import datetime
import os
import json

def parse_duration(duration_str):
    """Parse duration string to minutes"""
    if not duration_str:
        return None
        
    try:
        minutes = int(''.join(filter(str.isdigit, duration_str)))
        return minutes
    except ValueError:
        return None

def save_debug_html(html_content, filename):
    """Save HTML content for debugging"""
    debug_dir = 'data/debug'
    if not os.path.exists(debug_dir):
        os.makedirs(debug_dir)
    
    with open(os.path.join(debug_dir, filename), 'w', encoding='utf-8') as f:
        f.write(html_content)

def load_catalog():
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

def save_catalog(catalog_data, processed=True):
    """Save catalog data to appropriate location"""
    path = 'data/processed/shl_catalog.json' if processed else 'data/raw/shl_catalog.json'
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    with open(path, 'w') as f:
        json.dump(catalog_data, f, indent=2)

def get_unique_values(catalog_data, field):
    """Extract unique values for a given field across all assessments"""
    values = set()
    for assessment in catalog_data.get('assessments', []):
        if field in assessment:
            if isinstance(assessment[field], list):
                values.update(assessment[field])
            else:
                values.add(assessment[field])
    return sorted(list(values))