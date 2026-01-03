"""Adaptive threshold system for intelligent score filtering

Replaces arbitrary static thresholds with dynamic per-query analysis.
Calculates thresholds based on score distribution and query characteristics.
"""
import numpy as np
from typing import List, Dict, Tuple
from src.logger import setup_logger

logger = setup_logger(__name__)


class AdaptiveThreshold:
    """Production-grade adaptive threshold calculator"""
    
    def __init__(
        self,
        min_absolute_threshold: float = 0.3,
        std_dev_multiplier: float = 0.5,
        top_score_ratio: float = 0.7,
        min_docs_required: int = 1
    ):
        """
        Args:
            min_absolute_threshold: Absolute minimum score to ever accept
            std_dev_multiplier: How many std devs below mean to set threshold
            top_score_ratio: Minimum ratio of top score for acceptance
            min_docs_required: Minimum documents to return if any exist
        """
        self.min_absolute_threshold = min_absolute_threshold
        self.std_dev_multiplier = std_dev_multiplier
        self.top_score_ratio = top_score_ratio
        self.min_docs_required = min_docs_required
    
    def calculate_threshold(
        self, 
        scores: List[float],
        intent: str = None
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculate adaptive threshold based on score distribution
        
        Args:
            scores: List of similarity scores from retrieval
            intent: Optional query intent for intent-specific tuning
        
        Returns:
            Tuple of (threshold, metadata_dict)
        """
        if not scores:
            return self.min_absolute_threshold, {
                "method": "default_empty",
                "threshold": self.min_absolute_threshold
            }
        
        scores_array = np.array(scores)
        
        # Calculate statistical measures
        mean_score = np.mean(scores_array)
        std_score = np.std(scores_array)
        top_score = np.max(scores_array)
        
        # Method 1: Statistical threshold (mean - std_dev * multiplier)
        statistical_threshold = max(
            self.min_absolute_threshold,
            mean_score - (std_score * self.std_dev_multiplier)
        )
        
        # Method 2: Top score ratio (percentage of best result)
        top_ratio_threshold = max(
            self.min_absolute_threshold,
            top_score * self.top_score_ratio
        )
        
        # Method 3: Intent-specific adjustment
        intent_threshold = self._get_intent_specific_threshold(
            intent, mean_score, std_score
        )
        
        # Choose the most permissive threshold (give benefit of doubt)
        # But ensure minimum quality bar
        threshold = max(
            self.min_absolute_threshold,
            min(statistical_threshold, top_ratio_threshold, intent_threshold)
        )
        
        # Ensure we don't filter out everything
        docs_above_threshold = sum(1 for s in scores if s >= threshold)
        if docs_above_threshold < self.min_docs_required and len(scores) > 0:
            # Adjust threshold to ensure minimum docs
            sorted_scores = sorted(scores, reverse=True)
            threshold = sorted_scores[self.min_docs_required - 1] * 0.99  # Slight buffer
            method_used = "min_docs_override"
        else:
            method_used = "adaptive"
        
        metadata = {
            "method": method_used,
            "threshold": threshold,
            "mean_score": float(mean_score),
            "std_dev": float(std_score),
            "top_score": float(top_score),
            "statistical_threshold": statistical_threshold,
            "top_ratio_threshold": top_ratio_threshold,
            "intent_threshold": intent_threshold,
            "docs_above_threshold": docs_above_threshold,
            "total_docs": len(scores)
        }
        
        logger.info(
            f"Adaptive threshold calculated: {threshold:.3f} "
            f"(mean={mean_score:.3f}, std={std_score:.3f}, top={top_score:.3f}) "
            f"-> {docs_above_threshold}/{len(scores)} docs pass"
        )
        
        return threshold, metadata
    
    def _get_intent_specific_threshold(
        self, 
        intent: str, 
        mean_score: float, 
        std_score: float
    ) -> float:
        """
        Intent-specific threshold adjustments
        
        Different query types have different quality requirements:
        - ELIGIBILITY: Need precise matches
        - DISCOVERY: Can be more permissive
        - COMPARISON: Need balanced retrieval
        """
        if intent == "ELIGIBILITY":
            # Stricter for eligibility - need precise info
            return max(0.45, mean_score - std_score * 0.3)
        
        elif intent == "DISCOVERY":
            # More permissive for discovery - want variety
            return max(0.35, mean_score - std_score * 0.7)
        
        elif intent == "COMPARISON":
            # Balanced for comparison
            return max(0.4, mean_score - std_score * 0.5)
        
        elif intent == "BENEFITS":
            # Stricter - need specific numbers
            return max(0.45, mean_score - std_score * 0.4)
        
        elif intent == "PROCEDURE":
            # Moderate - need clear steps
            return max(0.4, mean_score - std_score * 0.5)
        
        else:  # GENERAL or unknown
            # Default moderate threshold
            return max(0.4, mean_score - std_score * 0.5)
    
    def filter_documents(
        self,
        documents: List[Dict],
        intent: str = None
    ) -> Tuple[List[Dict], Dict[str, any]]:
        """
        Filter documents using adaptive threshold
        
        Args:
            documents: List of retrieved documents with 'score' field
            intent: Optional query intent
        
        Returns:
            Tuple of (filtered_docs, threshold_metadata)
        """
        if not documents:
            return [], {"method": "empty_input", "threshold": 0.0}
        
        scores = [doc.get('score', 0.0) for doc in documents]
        threshold, metadata = self.calculate_threshold(scores, intent)
        
        filtered_docs = [
            doc for doc in documents 
            if doc.get('score', 0.0) >= threshold
        ]
        
        filtered_count = len(documents) - len(filtered_docs)
        if filtered_count > 0:
            logger.info(
                f"Filtered out {filtered_count} docs below adaptive threshold {threshold:.3f}"
            )
        
        metadata['filtered_count'] = filtered_count
        metadata['returned_count'] = len(filtered_docs)
        
        return filtered_docs, metadata


# Global instance for easy import
adaptive_threshold = AdaptiveThreshold()
