# Data Model: Archive Meeting RAG

**Created**: 2025-11-02  
**Feature**: Archive Meeting Retrieval & Grounded Interpretation RAG

## Entities

### MeetingRecord

**Description**: Represents an archived meeting log entry in JSON format.

**Fields**:
- `id` (string, required): Unique meeting identifier
- `date` (datetime, required): Meeting date and time
- `participants` (list[string], required): List of participant names or IDs
- `transcript` (string, required): Full meeting transcript text
- `decisions` (list[string], optional): List of decisions made in meeting
- `tags` (list[string], optional): Categorization tags for meeting

**Validation Rules**:
- `id` must be unique across all meeting records
- `date` must be valid ISO 8601 datetime
- `transcript` must not be empty
- JSON structure must be valid and parseable
- SHA-256 hash computed at ingestion time (FR-011)
- PII detection and redaction applied before indexing (FR-012)

**Relationships**:
- One-to-many: One MeetingRecord can have multiple chunks in EmbeddingIndex
- One-to-many: One MeetingRecord can be cited in multiple RAGQuery results

**State Transitions**:
1. **Ingested**: JSON file read and validated
2. **Hashed**: SHA-256 hash computed and stored
3. **PII-scanned**: Personal information detected and redacted
4. **Indexed**: Content chunked and embedded in FAISS index
5. **Available**: Ready for retrieval in RAG queries

---

### RAGQuery

**Description**: Represents a user query and its processed response with citations.

**Fields**:
- `query_id` (string, required): Unique query identifier (UUID)
- `user_input` (string, required): Original user question
- `timestamp` (datetime, required): Query execution timestamp
- `retrieved_chunks` (list[dict], required): Retrieved document chunks with metadata
  - Each chunk: `{meeting_id, text, score, chunk_index}`
- `output` (string, required): Generated answer text
- `citations` (list[dict], required): Verifiable citations in format `[meeting_id | date | speaker]`
  - Each citation: `{meeting_id, date, speaker, excerpt}`
- `model_version` (string, required): Version of LLM used for generation
- `embedding_version` (string, required): Version of embedding model used
- `user_id` (string, optional): SSO user identifier (from FR-013)
- `evidence_found` (boolean, required): Whether credible evidence was found (FR-008)
- `audit_log_path` (string, required): Path to immutable audit log entry (FR-005)

**Validation Rules**:
- `query_id` must be unique UUID
- `citations` must match format `[meeting_id | date | speaker]` (constitution principle II)
- `citations` must have traceable source in retrieved_chunks (constitution principle I)
- If `evidence_found` is false, `output` must be "No evidence found" (FR-008)
- All citations must reference meeting_id present in retrieved_chunks

**Relationships**:
- Many-to-many: One RAGQuery cites multiple MeetingRecord chunks
- One-to-one: One RAGQuery has one audit log entry

**State Transitions**:
1. **Submitted**: User query received
2. **Embedded**: Query converted to embedding vector
3. **Retrieved**: Similar chunks retrieved from FAISS index
4. **Generated**: Answer generated from retrieved context
5. **Cited**: Citations extracted and formatted
6. **Logged**: Audit record created and persisted
7. **Complete**: Response returned to user

---

### EmbeddingIndex

**Description**: Represents the FAISS vector index containing embedded meeting document chunks.

**Fields**:
- `index_id` (string, required): Unique index identifier
- `version_hash` (string, required): SHA-256 hash of index configuration and model versions
- `embedding_model` (string, required): Name and version of embedding model used
- `embedding_dimension` (integer, required): Dimension of embedding vectors
- `index_type` (string, required): FAISS index type (e.g., IndexFlatIP, IndexIVFFlat)
- `document_vectors` (FAISS index, required): FAISS index containing document embeddings
- `metadata` (dict, required): Mapping from vector index to document metadata
  - Format: `{vector_index: {meeting_id, chunk_index, text, date, participants}}`
- `total_documents` (integer, required): Total number of document chunks indexed
- `created_at` (datetime, required): Index creation timestamp
- `index_path` (string, required): File system path to FAISS index file

**Validation Rules**:
- `version_hash` must include embedding model version, FAISS index type, and configuration
- `metadata` must align with document_vectors (one entry per vector)
- Index file must be deterministic for same input and seed (constitution principle III)
- Index must be reproducible given same meeting JSON and model versions

**Relationships**:
- One-to-many: One EmbeddingIndex contains multiple MeetingRecord chunks
- One-to-many: One EmbeddingIndex serves multiple RAGQuery retrievals

**State Transitions**:
1. **Initialized**: Index structure created
2. **Embedded**: Meeting documents chunked and embedded
3. **Built**: FAISS index constructed with vectors
4. **Versioned**: Version hash computed and stored
5. **Persisted**: Index saved to disk
6. **Loaded**: Index loaded from disk for retrieval

---

### EvaluationCase

**Description**: Represents a benchmark test case for evaluating RAG system performance.

**Fields**:
- `case_id` (string, required): Unique evaluation case identifier
- `prompt` (string, required): Test query prompt
- `ground_truth` (string, required): Expected answer content
- `expected_citations` (list[dict], required): Expected citations in format `[meeting_id | date | speaker]`
  - Each citation: `{meeting_id, date, speaker, excerpt}`
- `evaluation_metrics` (dict, required): Scoring results
  - Keys: `citation_accuracy`, `factuality`, `hallucination_count`, `retrieval_precision`
- `run_timestamp` (datetime, required): Evaluation run timestamp
- `model_version` (string, required): LLM version used for evaluation
- `embedding_version` (string, required): Embedding model version used

**Validation Rules**:
- `expected_citations` must match format `[meeting_id | date | speaker]` (constitution principle II)
- `ground_truth` must be non-empty
- `evaluation_metrics` must include citation_accuracy (≥90% per SC-001)
- `evaluation_metrics.hallucination_count` must be 0 (SC-002)

**Relationships**:
- Many-to-many: One EvaluationCase validates multiple MeetingRecord citations
- One-to-one: One EvaluationCase has one evaluation result set

**State Transitions**:
1. **Defined**: Test case created with prompt and ground truth
2. **Executed**: Query run against RAG system
3. **Scored**: Metrics computed (citation accuracy, factuality, etc.)
4. **Validated**: Results compared against ground truth
5. **Reported**: Results included in evaluation report

---

## Data Flow

### Ingestion Flow

1. **Meeting JSON Read** → MeetingRecord created
2. **Validation** → JSON structure and required fields validated
3. **Hashing** → SHA-256 hash computed (FR-011)
4. **PII Detection** → spaCy NER detects personal information (FR-012)
5. **PII Redaction** → Personal information redacted before indexing
6. **Chunking** → Transcript split into chunks (overlapping windows)
7. **Embedding** → Chunks converted to embeddings using sentence-transformers
8. **Indexing** → Embeddings added to FAISS index in EmbeddingIndex
9. **Metadata Storage** → Chunk metadata stored in index metadata mapping

### Query Flow

1. **Query Submission** → RAGQuery created with user_input
2. **Query Embedding** → User query converted to embedding vector
3. **FAISS Retrieval** → Similar chunks retrieved from EmbeddingIndex
4. **Context Assembly** → Retrieved chunks assembled with metadata
5. **LLM Generation** → Answer generated from retrieved context only
6. **Citation Extraction** → Citations formatted as `[meeting_id | date | speaker]`
7. **Evidence Check** → If no credible evidence, output set to "No evidence found"
8. **Audit Logging** → Immutable audit record created with full query details
9. **Response Return** → RAGQuery completed with output and citations

### Audit Flow

1. **Query Execution** → RAGQuery state transitions to Submitted
2. **Processing** → Query processed through embedding, retrieval, generation
3. **Log Creation** → Audit log entry created with:
   - Query ID, user ID (from SSO), timestamp
   - User input, retrieved sources, model versions
   - Output, citations, evidence_found flag
4. **Persistence** → Structured JSON log written to audit_logs/ directory
5. **Retention** → Log retained for 3 years per FR-014

## Validation Rules Summary

### MeetingRecord
- ✅ Unique ID validation
- ✅ Date format validation (ISO 8601)
- ✅ Transcript non-empty validation
- ✅ JSON structure validation
- ✅ SHA-256 hash computation
- ✅ PII detection and redaction

### RAGQuery
- ✅ Citation format validation: `[meeting_id | date | speaker]`
- ✅ Citation traceability: citations must reference retrieved_chunks
- ✅ Evidence check: "No evidence found" when evidence_found is false
- ✅ Citation-source alignment: citations must match retrieved chunks

### EmbeddingIndex
- ✅ Version hash includes model version and configuration
- ✅ Metadata alignment with document vectors
- ✅ Deterministic index construction with fixed seed
- ✅ Reproducibility validation

### EvaluationCase
- ✅ Citation format validation
- ✅ Ground truth non-empty validation
- ✅ Citation accuracy ≥90% (SC-001)
- ✅ Hallucination count = 0 (SC-002)

---

## Data Integrity

### Tamper Detection
- SHA-256 hash computed for each MeetingRecord at ingestion (FR-011)
- Hash stored in EmbeddingIndex metadata
- Hash verified on index access
- Hash mismatches logged as security events

### Reproducibility
- Fixed seeds for all random operations (embeddings, LLM inference, FAISS)
- Model versions pinned and tracked
- Index construction deterministic
- Same input + data state → identical output (constitution principle III)

### Auditability
- Immutable audit logs for every RAGQuery (constitution principle V)
- Full provenance: query, sources, model versions, output
- User ID from SSO included (FR-013)
- Logs retained for 3 years (FR-014)
- Structured JSON format enables parsing and analysis
