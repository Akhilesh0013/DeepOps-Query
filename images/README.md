# RAG Architecture Diagrams

PNG flowcharts for the Enterprise Advanced RAG pipeline (CRAG, Self-RAG, HyDE, LangGraph, etc.).

| File | Description |
|------|-------------|
| [01-top-level-langgraph.png](./01-top-level-langgraph.png) | LangGraph API entry — intent routing, SQL approval |
| [02-full-rag-pipeline.png](./02-full-rag-pipeline.png) | `run_rag` — cache, intent, retrieve, generate |
| [03-retrieve-pipeline.png](./03-retrieve-pipeline.png) | `_retrieve()` — HyDE, search modes, rerank, CRAG |
| [04-generate-self-rag.png](./04-generate-self-rag.png) | `_generate()` — spotlighting + Self-RAG loop |
| [05-crag.png](./05-crag.png) | CRAG — grade chunks, web search fallback |
| [06-self-rag.png](./06-self-rag.png) | Self-Reflective generation loop |
| [07-hyde.png](./07-hyde.png) | HyDE — hypothetical document embeddings |
| [08-hybrid-intent.png](./08-hybrid-intent.png) | Hybrid intent — SQL + document synthesis |

## Source code reference

| Feature | File |
|---------|------|
| LangGraph | `app/core/graph.py` |
| RAG orchestration | `app/services/rag_service.py` |
| CRAG | `app/services/crag.py` |
| Self-RAG | `app/services/self_reflective.py` |
| HyDE | `app/services/hyde.py` |
| Rerank | `app/services/reranking.py` |
| Hybrid search | `app/services/vector_store.py` |
