import numpy as np
from sklearn.metrics import ndcg_score
import pandas as pd

def calculate_ndcg(relevance_scores, predictions, k=10):
    """
    Calculate Normalized Discounted Cumulative Gain
    
    Args:
        relevance_scores: True relevance scores
        predictions: Predicted rankings
        k: Number of top items to consider
        
    Returns:
        NDCG score
    """
    if len(predictions) < k:
        k = len(predictions)
    return ndcg_score([relevance_scores], [predictions], k=k)

def precision_at_k(relevance, predictions, k=10):
    """
    Calculate precision@k
    
    Args:
        relevance: Binary relevance list (1 if relevant, 0 if not)
        predictions: List of predicted items
        k: Number of top items to consider
        
    Returns:
        Precision@k score
    """
    if len(predictions) < k:
        k = len(predictions)
    
    # Get top k predictions
    top_k_predictions = predictions[:k]
    
    # Count number of relevant items in top k
    relevant_in_top_k = sum(1 for i in top_k_predictions if relevance[i] == 1)
    
    return relevant_in_top_k / k

def mean_reciprocal_rank(relevance, predictions):
    """
    Calculate Mean Reciprocal Rank
    
    Args:
        relevance: Binary relevance list (1 if relevant, 0 if not)
        predictions: List of predicted items
        
    Returns:
        MRR score
    """
    for i, pred in enumerate(predictions):
        if relevance[pred] == 1:
            return 1.0 / (i + 1)
    return 0.0

def diversity_score(recommendations, feature_field):
    """
    Calculate diversity based on a specific feature
    
    Args:
        recommendations: List of recommended assessments
        feature_field: Field to measure diversity on
        
    Returns:
        Diversity score (0-1)
    """
    unique_features = set()
    for rec in recommendations:
        if feature_field in rec['assessment']:
            if isinstance(rec['assessment'][feature_field], list):
                unique_features.update(rec['assessment'][feature_field])
            else:
                unique_features.add(rec['assessment'][feature_field])
    
    return len(unique_features) / len(recommendations) if recommendations else 0