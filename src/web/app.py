"""FastAPI web application for Archive-RAG."""

import os
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from ..services.query_service import create_query_service
from ..lib.config import DEFAULT_TOP_K, DEFAULT_SEED, INDEXES_DIR
from ..lib.logging import get_logger

logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Archive-RAG API",
    description="REST API for querying archived meeting records using RAG",
    version="0.1.0"
)

# Enable CORS for public access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class QueryRequest(BaseModel):
    """Query request model."""
    query: str = Field(..., description="Natural language question")
    index_file: Optional[str] = Field(None, description="Path to FAISS index file (optional, uses default if not provided)")
    top_k: int = Field(DEFAULT_TOP_K, ge=1, le=20, description="Number of chunks to retrieve")
    model: Optional[str] = Field(None, description="LLM model name (optional)")
    model_version: Optional[str] = Field(None, description="LLM model version (optional)")
    seed: int = Field(DEFAULT_SEED, description="Random seed for reproducibility")


class CitationResponse(BaseModel):
    """Citation response model."""
    meeting_id: str
    date: str
    workgroup_name: Optional[str] = None
    excerpt: str
    chunk_type: Optional[str] = None


class QueryResponse(BaseModel):
    """Query response model."""
    query_id: str
    query: str
    answer: str
    citations: list[CitationResponse]
    evidence_found: bool
    model_version: Optional[str] = None
    embedding_version: Optional[str] = None
    timestamp: str


def get_default_index() -> str:
    """Get default index file path from environment or use sample index."""
    # Check environment variable first
    index_path = os.getenv("ARCHIVE_RAG_INDEX_PATH")
    if index_path:
        return index_path
    
    # Try to find a default index
    # Look for sample-meetings.faiss first, then any .faiss file
    sample_index = INDEXES_DIR / "sample-meetings.faiss"
    if sample_index.exists():
        return str(sample_index)
    
    # Find any .faiss file
    faiss_files = list(INDEXES_DIR.glob("*.faiss"))
    if faiss_files:
        return str(faiss_files[0])
    
    raise FileNotFoundError(
        "No index file found. Please create an index first using:\n"
        "  archive-rag index <data> indexes/sample-meetings.faiss\n"
        "Or set ARCHIVE_RAG_INDEX_PATH environment variable."
    )


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the web interface."""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ArchiveRAG - Query Interface</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap" rel="stylesheet"/>
        <style>
            body {
                font-family: 'Inter', sans-serif;
            }
        </style>
    </head>
    <body class="bg-gray-50 dark:bg-gray-900">
        <div class="min-h-screen py-8">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div class="text-center mb-8">
                    <h1 class="text-4xl font-bold text-gray-900 dark:text-white mb-2">ArchiveRAG</h1>
                    <p class="text-gray-600 dark:text-gray-400">Query archived meeting records</p>
                </div>
                
                <div class="max-w-3xl mx-auto">
                    <form id="queryForm" class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
                        <div class="mb-4">
                            <label for="query" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                Enter your question
                            </label>
                            <textarea 
                                id="query" 
                                name="query" 
                                rows="4"
                                class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                                placeholder="e.g., What were the key decisions from the Q3 2023 budget meeting?"
                                required
                            ></textarea>
                        </div>
                        <button 
                            type="submit" 
                            id="submitBtn"
                            class="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded-md transition-colors"
                        >
                            Submit Query
                        </button>
                    </form>
                    
                    <div id="loading" class="hidden text-center py-8">
                        <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                        <p class="mt-2 text-gray-600 dark:text-gray-400">Processing your query...</p>
                    </div>
                    
                    <div id="response" class="hidden">
                        <div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
                            <h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-4">Answer</h2>
                            <div id="answer" class="text-gray-700 dark:text-gray-300 whitespace-pre-wrap"></div>
                        </div>
                        
                        <div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
                            <h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-4">Source Evidence</h2>
                            <div id="evidence" class="space-y-4"></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            const form = document.getElementById('queryForm');
            const loading = document.getElementById('loading');
            const response = document.getElementById('response');
            const answerDiv = document.getElementById('answer');
            const evidenceDiv = document.getElementById('evidence');
            const submitBtn = document.getElementById('submitBtn');
            
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const query = document.getElementById('query').value.trim();
                if (!query) return;
                
                loading.classList.remove('hidden');
                response.classList.add('hidden');
                submitBtn.disabled = true;
                
                try {
                    const response_data = await fetch('/api/query', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ query: query })
                    });
                    
                    if (!response_data.ok) {
                        const error = await response_data.json();
                        throw new Error(error.detail || 'Query failed');
                    }
                    
                    const data = await response_data.json();
                    
                    // Display answer
                    answerDiv.textContent = data.answer;
                    
                    // Display evidence
                    evidenceDiv.innerHTML = '';
                    if (data.citations && data.citations.length > 0) {
                        data.citations.forEach((citation, index) => {
                            const card = document.createElement('div');
                            card.className = 'border border-gray-200 dark:border-gray-700 rounded-md p-4';
                            card.innerHTML = `
                                <h3 class="font-semibold text-gray-900 dark:text-white mb-2">
                                    ${citation.workgroup_name || 'Meeting'} - ${citation.date}
                                </h3>
                                <p class="text-gray-700 dark:text-gray-300 text-sm">${citation.excerpt}</p>
                            `;
                            evidenceDiv.appendChild(card);
                        });
                    } else {
                        evidenceDiv.innerHTML = '<p class="text-gray-500 dark:text-gray-400">No evidence found.</p>';
                    }
                    
                    response.classList.remove('hidden');
                } catch (error) {
                    answerDiv.textContent = 'Error: ' + error.message;
                    evidenceDiv.innerHTML = '';
                    response.classList.remove('hidden');
                } finally {
                    loading.classList.add('hidden');
                    submitBtn.disabled = false;
                }
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.post("/api/query", response_model=QueryResponse)
async def query_rag(request: QueryRequest):
    """
    Query the RAG system.
    
    Returns evidence-bound answers with citations from archived meeting records.
    """
    try:
        # Determine index file to use
        index_file = request.index_file or get_default_index()
        
        # Create query service
        query_service = create_query_service(
            model_name=request.model,
            seed=request.seed
        )
        
        # Execute query
        rag_query = query_service.execute_query(
            index_name=index_file,
            query_text=request.query,
            top_k=request.top_k,
            user_id=None,  # Web interface doesn't track users
            model_version=request.model_version
        )
        
        # Convert citations to response format
        citations = [
            CitationResponse(
                meeting_id=citation.meeting_id,
                date=citation.date,
                workgroup_name=citation.workgroup_name,
                excerpt=citation.excerpt,
                chunk_type=citation.chunk_type
            )
            for citation in rag_query.citations
        ]
        
        # Build response
        response = QueryResponse(
            query_id=rag_query.query_id,
            query=rag_query.user_input,
            answer=rag_query.output,
            citations=citations,
            evidence_found=rag_query.evidence_found,
            model_version=rag_query.model_version,
            embedding_version=rag_query.embedding_version,
            timestamp=rag_query.timestamp
        )
        
        logger.info(
            "web_query_executed",
            query_id=rag_query.query_id,
            evidence_found=rag_query.evidence_found,
            citations_count=len(citations)
        )
        
        return response
        
    except FileNotFoundError as e:
        logger.error("web_query_index_not_found", error=str(e))
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("web_query_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Try to get default index to verify setup
        index_file = get_default_index()
        return {
            "status": "healthy",
            "index_file": index_file,
            "index_exists": Path(index_file).exists()
        }
    except FileNotFoundError:
        return {
            "status": "degraded",
            "message": "No index file found. Please create an index first."
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


def run_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    reload: bool = False
):
    """Run the FastAPI server."""
    uvicorn.run(
        "src.web.app:app",
        host=host,
        port=port,
        reload=reload
    )


if __name__ == "__main__":
    run_server()
