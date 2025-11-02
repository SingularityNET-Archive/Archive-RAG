"""Evaluation runner service for benchmark execution."""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..models.evaluation_case import EvaluationCase
from ..services.query_service import create_query_service
from ..services.citation_scorer import score_citation_accuracy, validate_citation_accuracy_threshold
from ..services.factuality_scorer import score_factuality, validate_hallucination_count
from ..services.latency_measurement import measure_latency, validate_latency_threshold
from ..lib.config import DEFAULT_SEED
from ..lib.logging import get_logger

logger = get_logger(__name__)


class EvaluationRunner:
    """Service for running evaluation benchmarks."""
    
    def __init__(
        self,
        index_name: str,
        model_name: Optional[str] = None,
        model_version: Optional[str] = None,
        seed: int = DEFAULT_SEED
    ):
        """
        Initialize evaluation runner.
        
        Args:
            index_name: Name of the FAISS index
            model_name: Name of LLM model (optional)
            model_version: LLM model version (optional)
            seed: Random seed for reproducibility
        """
        self.index_name = index_name
        self.model_name = model_name
        self.model_version = model_version
        self.seed = seed
        self.query_service = create_query_service(model_name=model_name, seed=seed)
    
    def run_evaluation(self, benchmark_file: Path) -> Dict[str, Any]:
        """
        Run evaluation benchmark.
        
        Args:
            benchmark_file: Path to benchmark JSON file (EvaluationCase format)
            
        Returns:
            Dictionary with evaluation results
        """
        # Load benchmark cases
        with open(benchmark_file, "r", encoding="utf-8") as f:
            benchmark_data = json.load(f)
        
        # Parse evaluation cases
        if isinstance(benchmark_data, list):
            cases = [EvaluationCase.from_dict(case_dict) for case_dict in benchmark_data]
        else:
            # Single case
            cases = [EvaluationCase.from_dict(benchmark_data)]
        
        # Run evaluation for each case
        results = []
        total_citation_accuracy = 0.0
        total_factuality = 0.0
        total_hallucination_count = 0
        total_latency = 0.0
        
        for case in cases:
            case_result = self._evaluate_case(case)
            results.append(case_result)
            
            # Aggregate metrics
            metrics = case_result.get("evaluation_metrics", {})
            total_citation_accuracy += metrics.get("citation_accuracy", 0.0)
            total_factuality += metrics.get("factuality", 0.0)
            total_hallucination_count += metrics.get("hallucination_count", 0)
            total_latency += metrics.get("retrieval_latency", 0.0)
        
        # Calculate averages
        num_cases = len(cases)
        avg_citation_accuracy = total_citation_accuracy / num_cases if num_cases > 0 else 0.0
        avg_factuality = total_factuality / num_cases if num_cases > 0 else 0.0
        avg_latency = total_latency / num_cases if num_cases > 0 else 0.0
        
        # Validate success criteria
        sc001_met = validate_citation_accuracy_threshold(avg_citation_accuracy, 0.9)  # SC-001
        sc002_met = validate_hallucination_count(total_hallucination_count)  # SC-002
        sc003_met = validate_latency_threshold(avg_latency, 2.0)  # SC-003
        
        evaluation_results = {
            "total_cases": num_cases,
            "citation_accuracy": avg_citation_accuracy,
            "factuality_score": avg_factuality,
            "hallucination_count": total_hallucination_count,
            "retrieval_latency_avg": avg_latency,
            "success_criteria": {
                "SC-001": {"met": sc001_met, "citation_accuracy": avg_citation_accuracy, "threshold": 0.9},
                "SC-002": {"met": sc002_met, "hallucination_count": total_hallucination_count, "threshold": 0},
                "SC-003": {"met": sc003_met, "latency": avg_latency, "threshold": 2.0}
            },
            "cases": results,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        logger.info(
            "evaluation_complete",
            total_cases=num_cases,
            citation_accuracy=avg_citation_accuracy,
            factuality=avg_factuality,
            hallucination_count=total_hallucination_count,
            latency=avg_latency
        )
        
        return evaluation_results
    
    def _evaluate_case(self, case: EvaluationCase) -> Dict[str, Any]:
        """
        Evaluate a single case.
        
        Args:
            case: EvaluationCase to evaluate
            
        Returns:
            Dictionary with case evaluation results
        """
        # Measure latency
        rag_query, latency = measure_latency(
            self.query_service.execute_query,
            index_name=self.index_name,
            query_text=case.prompt,
            top_k=5
        )
        
        # Score citation accuracy
        citation_accuracy = score_citation_accuracy(
            rag_query.citations,
            case.expected_citations
        )
        
        # Score factuality
        factuality, hallucination_count = score_factuality(
            rag_query.output,
            case.ground_truth
        )
        
        # Update case with metrics
        case.evaluation_metrics = {
            "citation_accuracy": citation_accuracy,
            "factuality": factuality,
            "hallucination_count": hallucination_count,
            "retrieval_latency": latency
        }
        case.run_timestamp = datetime.utcnow().isoformat() + "Z"
        case.model_version = self.model_version or rag_query.model_version
        case.embedding_version = rag_query.embedding_version
        
        return case.to_dict()


def create_evaluation_runner(
    index_name: str,
    model_name: Optional[str] = None,
    model_version: Optional[str] = None,
    seed: int = DEFAULT_SEED
) -> EvaluationRunner:
    """
    Create an evaluation runner instance.
    
    Args:
        index_name: Name of the FAISS index
        model_name: Name of LLM model
        model_version: LLM model version
        seed: Random seed for reproducibility
        
    Returns:
        EvaluationRunner instance
    """
    return EvaluationRunner(index_name, model_name, model_version, seed)

