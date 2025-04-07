import json
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

class SHLRecommender:
    def __init__(self, catalog_path='data/processed/shl_assessments_detailed.json'):
        # Load the model for creating embeddings
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Load and process catalog data from the detailed file
        with open(catalog_path, 'r', encoding='utf-8') as f:
            self.catalog_data = json.load(f)
        
        # Process embeddings (generate if not already present)
        self.process_embeddings(catalog_path)
    
    def process_embeddings(self, catalog_path):
        """Process catalog data and create embeddings if they don't exist"""
        if 'embeddings' not in self.catalog_data:
            print("Generating embeddings for assessments...")
            assessments = self.catalog_data.get('assessments', [])
            
            # Create description embeddings by combining name and description
            for assessment in assessments:
                rich_text = f"{assessment.get('name', '')} {assessment.get('description', '')}"
                assessment['embedding'] = self.model.encode(rich_text).tolist()
            
            self.catalog_data['embeddings'] = True
            
            # Save back the enriched data
            with open(catalog_path, 'w', encoding='utf-8') as f:
                json.dump(self.catalog_data, f, indent=2)
    
    def get_recommendations(self, query, job_level=None, duration_max=None, 
                            languages=None, test_type=None, top_n=5):
        """Get recommendations based on query and optional filters"""
        query_embedding = self.model.encode(query)
        filtered_assessments = []

        for assessment in self.catalog_data.get('assessments', []):
            # Defensive checks for optional fields
            if job_level and job_level not in (assessment.get('job_levels') or []):
                continue

            if duration_max is not None:
                duration_mins = self._parse_duration(assessment.get('duration', '0 minutes'))
                if duration_mins > duration_max:
                    continue

            if languages and not any(lang in (assessment.get('languages') or []) for lang in languages):
                continue

            if test_type and test_type != assessment.get('test_type'):
                continue

            # Skip if embedding is missing or malformed
            embedding = assessment.get('embedding')
            if embedding is None:
                continue

            sim_score = cosine_similarity(
                [query_embedding],
                [embedding]
            )[0][0]

            filtered_assessments.append({
                'assessment': assessment,
                'similarity': float(sim_score)
            })

        filtered_assessments.sort(key=lambda x: x['similarity'], reverse=True)
        return filtered_assessments[:top_n]
    
    def _parse_duration(self, duration_str):
        if not duration_str:
            return 0
        try:
            minutes = int(''.join(filter(str.isdigit, duration_str)))
            return minutes
        except ValueError:
            return 0

# ---------------- Test the recommender ---------------- #
if __name__ == "__main__":
    recommender = SHLRecommender()
    
    test_query = "I am hiring for a manager with experience in financial institutions and need an assessment under 55 minutes."
    results = recommender.get_recommendations(test_query, duration_max=55, top_n=5)
    
    for res in results:
        assessment = res['assessment']
        print("Name:", assessment.get('name'))
        print("URL:", assessment.get('url'))
        print("Remote Testing:", "Yes" if assessment.get('remote_testing_support') else "No")
        print("Adaptive/IRT:", "Yes" if assessment.get('adaptive_irt_support') else "No")
        print("Duration:", assessment.get('duration'))
        print("Test Type:", assessment.get('test_type'))
        print("Similarity:", res['similarity'])
        print("-----")
