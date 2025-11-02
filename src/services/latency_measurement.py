"""Retrieval latency measurement (<2s target per SC-003)."""

import time
from typing import Callable, Any
from ..lib.logging import get_logger

logger = get_logger(__name__)


def measure_latency(func: Callable[..., Any], *args, **kwargs) -> tuple[Any, float]:
    """
    Measure execution latency of a function.
    
    Args:
        func: Function to measure
        *args: Function arguments
        **kwargs: Function keyword arguments
        
    Returns:
        Tuple of (function_result, latency_in_seconds)
    """
    start_time = time.time()
    result = func(*args, **kwargs)
    end_time = time.time()
    
    latency = end_time - start_time
    
    logger.info(
        "latency_measured",
        function=func.__name__,
        latency=latency
    )
    
    return result, latency


def validate_latency_threshold(latency: float, threshold: float = 2.0) -> bool:
    """
    Validate latency meets threshold (<2s per SC-003).
    
    Args:
        latency: Latency in seconds
        threshold: Maximum latency threshold (default: 2.0 seconds)
        
    Returns:
        True if latency meets threshold, False otherwise
    """
    return latency < threshold

