import json
import os
import pandas as pd
import matplotlib.pyplot as plt
from app.recommender import SHLRecommender
from app.evaluation.metrics import (
    calculate_ndcg,
    precision_at_k,
    mean_reciprocal_rank,
    diversity_score
)

class RecommenderBenchmark:
    def __init__(self, test_queries_path='data/evaluation/test_queries.json'):
        """Initialize benchmark with test queries"""
        self.recommender = SHLRecommender()
        
        # Load test queries if available
        try:
            with open(test_queries_path, 'r') as f:
                self.test_queries = json.load(f)
        except FileNotFoundError:
            self.test_queries = self._generate_sample_queries()
    
    def _generate_sample_queries(self):
        """Generate sample test queries if no test file exists"""
        return [
            {
                "query": "Entry level administrative assistant role with focus on customer service",
                "relevant_assessments": ["Administrative Professional - Short Form"],
                "job_level": "Entry-Level",
                "languages": ["english"]
            },
            {
                "query": "Sales manager role requiring leadership skills",
                "relevant_assessments": ["Agency Manager Solution"],
                "job_level": "Manager",
                "languages": ["english"]
            },
        ]
    
    def run_benchmark(self, k=5):
        """Run benchmark on test queries"""
        results = []
        
        for query_data in self.test_queries:
            # Get recommendations
            recommendations = self.recommender.get_recommendations(
                query=query_data["query"],
                job_level=query_data.get("job_level"),
                languages=query_data.get("languages"),
                top_n=10
            )
            
            # Extract recommended assessment names
            rec_names = [r["assessment"]["name"] for r in recommendations]
            
            # Build catalog assessment list and binary relevance vector
            catalog_data = self.recommender.catalog_data
            all_assessments = [a["name"] for a in catalog_data["assessments"]]
            relevance = [1 if name in query_data["relevant_assessments"] else 0 for name in all_assessments]
            
            # Map recommendations to indices
            pred_indices = [all_assessments.index(name) for name in rec_names if name in all_assessments]
            
            # Create prediction score vector for NDCG
            pred_vector = [1 if i in pred_indices else 0 for i in range(len(all_assessments))]
            
            # Calculate evaluation metrics
            result = {
                "query": query_data["query"],
                "precision_at_k": precision_at_k(relevance, pred_indices, k=k),
                "ndcg_at_k": calculate_ndcg(relevance, pred_vector, k=k),
                "mrr": mean_reciprocal_rank(relevance, pred_indices),
                "diversity_job_levels": diversity_score(recommendations[:k], "job_levels"),
                "diversity_test_types": diversity_score(recommendations[:k], "test_type"),
                "top_recommendations": rec_names[:k]
            }
            results.append(result)
        
        # Compute average metrics across all queries
        avg_precision = sum(r["precision_at_k"] for r in results) / len(results)
        avg_ndcg = sum(r["ndcg_at_k"] for r in results) / len(results)
        avg_mrr = sum(r["mrr"] for r in results) / len(results)
        avg_diversity_job = sum(r["diversity_job_levels"] for r in results) / len(results)
        avg_diversity_test = sum(r["diversity_test_types"] for r in results) / len(results)
        
        summary = {
            "avg_precision_at_k": avg_precision,
            "avg_ndcg_at_k": avg_ndcg,
            "avg_mrr": avg_mrr,
            "avg_diversity_job_levels": avg_diversity_job,
            "avg_diversity_test_types": avg_diversity_test,
            "detailed_results": results
        }
        
        return summary
    
    def plot_results(self, results):
        """Plot benchmark results"""
        df = pd.DataFrame([{
            "query": r["query"][:30] + "...",
            "precision@k": r["precision_at_k"],
            "ndcg@k": r["ndcg_at_k"],
            "mrr": r["mrr"],
            "diversity (job levels)": r["diversity_job_levels"],
            "diversity (test types)": r["diversity_test_types"]
        } for r in results["detailed_results"]])
        
        # Plot
        fig, ax = plt.subplots(figsize=(14, 6))
        df.plot(x="query", 
                y=["precision@k", "ndcg@k", "mrr", "diversity (job levels)", "diversity (test types)"],
                kind="bar", ax=ax)
        ax.set_title("SHL Recommender Benchmark Performance by Query")
        ax.set_ylabel("Score")
        ax.set_ylim(0, 1)
        plt.tight_layout()
        plt.savefig("data/evaluation/benchmark_results.png")
        plt.close()
        
        return "data/evaluation/benchmark_results.png"

if __name__ == "__main__" and os.getenv("ENV") != "prod":
    benchmark = RecommenderBenchmark()
    results = benchmark.run_benchmark()
    print(json.dumps(results, indent=2))
    benchmark.plot_results(results)
