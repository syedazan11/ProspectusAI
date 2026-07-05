# ProspectusAI Sprint

## Milestone 1 - Backend Foundation
- [x] Project Structure
- [x] Git Initialization
- [ ] Dependencies Installed
- [ ] Configuration
- [ ] Logging
- [ ] FastAPI
- [ ] Health Endpoint
- [ ] Router
- [ ] Environment Variables
- [ ] First Commit

---

## Milestone 2 - Ingestion
- [ ] Docling
- [ ] OCR
- [ ] Table Extraction
- [ ] Layout Detection

---

## Milestone 3 - Processing
- [ ] Cleaning
- [ ] Chunking
- [ ] Metadata
- [ ] Table Processing

---

## Milestone 4 - Embeddings
- [ ] BGE-M3
- [ ] Embedding Service

---

## Milestone 5 - Vector Database
- [ ] Qdrant Setup
- [ ] Collection
- [ ] Store Chunks

---

## Milestone 6 - Retrieval
- [ ] Hybrid Search
- [ ] Metadata Filter
- [ ] Reranker

---

## Milestone 7 - Generation
- [ ] Groq
- [ ] Prompt Builder
- [ ] Citations
- [ ] RAG Orchestrator

---

## Milestone 8 - Frontend
- [ ] React
- [ ] Chat
- [ ] Upload
- [ ] Admin Dashboard

---

## Milestone 9 - Testing
- [ ] NED Prospectus
- [ ] FAST Prospectus
- [ ] IBA Prospectus



PHASE 3 — HYBRID GRAPHRAG CORE

Completed:
- Graph schemas
- LLM-based entity and relationship extraction
- Document-level graph builder
- Checkpoint/resume for graph extraction
- Local graph chunk selection to reduce API calls
- Graph retriever
- Vector + graph HybridRetriever
- Combined document and graph context
- RAGService orchestration
- Grounded answer generation
- Unsupported-answer rejection
- Retrieval evaluation: 2/2 passed

Known issues for later evaluation:
- Some false graph relationships may be extracted
- Vector retrieval can return duplicate or unnecessary chunks
- Retrieval parameters need tuning on the full prospectus
- Reranking should be evaluated only after full-document ingestion