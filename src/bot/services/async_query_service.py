"""Async query service wrapper for bridging sync QueryService to async Discord bot."""

import asyncio
from typing import Optional
from datetime import datetime

from ...services.query_service import QueryService, create_query_service
from ...models.rag_query import RAGQuery
from ...lib.config import DEFAULT_TOP_K, DEFAULT_SEED
from ...lib.logging import get_logger

logger = get_logger(__name__)


class AsyncQueryService:
    """
    Async wrapper for QueryService to enable async integration with Discord bot.
    
    Bridges synchronous QueryService to async operations using asyncio.to_thread().
    """
    
    def __init__(
        self,
        query_service: Optional[QueryService] = None,
        index_name: Optional[str] = None,
        model_name: Optional[str] = None,
        seed: int = DEFAULT_SEED,
        timeout_seconds: float = 30.0
    ):
        """
        Initialize async query service.
        
        Args:
            query_service: Optional QueryService instance (creates new if not provided)
            index_name: Optional default index name
            model_name: Optional LLM model name
            seed: Random seed for reproducibility
            timeout_seconds: Timeout for query execution in seconds
        """
        self.query_service = query_service or create_query_service(model_name=model_name, seed=seed)
        self.index_name = index_name
        self.timeout_seconds = timeout_seconds
    
    async def execute_query_async(
        self,
        query_text: str,
        index_name: Optional[str] = None,
        top_k: int = DEFAULT_TOP_K,
        user_id: Optional[str] = None,
        model_version: Optional[str] = None
    ) -> RAGQuery:
        """
        Execute query asynchronously.
        
        Args:
            query_text: User query text
            index_name: Name of FAISS index (uses default if not provided)
            top_k: Number of chunks to retrieve
            user_id: Optional user identifier
            model_version: Optional model version
            
        Returns:
            RAGQuery with query results
            
        Raises:
            TimeoutError: If query execution exceeds timeout
            RuntimeError: If RAG pipeline is unavailable
        """
        index = index_name or self.index_name
        if not index:
            raise ValueError("index_name must be provided or set as default")
        
        start_time = datetime.utcnow()
        
        try:
            # Run sync QueryService in thread pool
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    self.query_service.execute_query,
                    index,
                    query_text,
                    top_k,
                    user_id,
                    model_version
                ),
                timeout=self.timeout_seconds
            )
            
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.info(
                "query_executed_async",
                query_id=result.query_id,
                execution_time_ms=execution_time,
                index_name=index
            )
            
            return result
            
        except asyncio.TimeoutError:
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(
                "query_timeout",
                query_text=query_text,
                timeout_seconds=self.timeout_seconds,
                execution_time_ms=execution_time
            )
            raise TimeoutError(
                f"Query execution exceeded timeout of {self.timeout_seconds}s. "
                "Try a simpler query or contact an admin."
            )
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(
                "query_execution_failed",
                query_text=query_text,
                error=str(e),
                execution_time_ms=execution_time
            )
            
            # Check for RAG pipeline unavailability
            error_str = str(e).lower()
            if "unavailable" in error_str or "connection" in error_str or "timeout" in error_str:
                raise RuntimeError("RAG service temporarily unavailable. Please try again later.") from e
            
            raise RuntimeError(f"Query execution failed: {str(e)}") from e


def create_async_query_service(
    index_name: Optional[str] = None,
    model_name: Optional[str] = None,
    seed: int = DEFAULT_SEED,
    timeout_seconds: float = 30.0
) -> AsyncQueryService:
    """
    Create an async query service instance.
    
    Args:
        index_name: Optional default index name
        model_name: Optional LLM model name
        seed: Random seed for reproducibility
        timeout_seconds: Timeout for query execution in seconds
        
    Returns:
        AsyncQueryService instance
    """
    return AsyncQueryService(
        index_name=index_name,
        model_name=model_name,
        seed=seed,
        timeout_seconds=timeout_seconds
    )


