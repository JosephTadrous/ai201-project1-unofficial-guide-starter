# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is **Project 1: The Unofficial Guide** for AI201 — a RAG (Retrieval-Augmented Generation) pipeline that answers questions about Ivy League university dorms using student reviews and articles.

**Domain:** Student and college reviews of dorms at Ivy League universities (Harvard, Yale, Princeton, Penn, Cornell, Columbia).

**Key files:**
- `planning.md` — Spec written before implementation: chunking strategy, retrieval approach, evaluation plan, architecture diagram
- `README.md` — Final submission report (fill in after each milestone is built and tested)
- `documents/` — Collected source documents (reviews, articles, Reddit threads)
- `requirements.txt` — Python dependencies

## Tech Stack

- **Python 3.14** with virtualenv at `.venv/`
- **Embeddings:** `sentence-transformers` (all-MiniLM-L6-v2, 384-dim vectors, 256-token max)
- **Vector store:** ChromaDB (local, persisted to `chroma_db/` or `chroma/`)
- **LLM:** Groq API (`groq` SDK) — requires `GROQ_API_KEY` in `.env`
- **Config:** `python-dotenv` for env loading
- **Optional:** `gradio` or `streamlit` for query interface (Milestone 5), `pdfplumber` for PDF ingestion

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then add your GROQ_API_KEY
```

## Pipeline Architecture

Five-stage RAG pipeline (see `planning.md` Architecture section):

1. **Document Ingestion** — scrape/collect sources into `documents/`
2. **Chunking** — source-type-aware splitting:
   - Review sites: 1 review = 1 chunk (no splitting), ~80–350 tokens
   - Newspaper articles: 1200 chars (~300 tokens), recursive split on headings/paragraphs, 200-char overlap
   - Reddit comments: 1200 chars per comment, recursive split only for long comments, 200-char overlap
3. **Embedding + Vector Store** — embed chunks with all-MiniLM-L6-v2, store in ChromaDB
4. **Retrieval** — top-k=5 by default, k=7 for cross-school comparison queries
5. **Generation** — Groq LLM with grounded system prompt, source attribution

## Project Milestones

1. Identify domain and document sources (done)
2. Planning spec in `planning.md` (done)
3. Ingestion and chunking
4. Embedding and retrieval
5. Generation and query interface

## Conventions

- Never commit `.env` — it's in `.gitignore`
- ChromaDB storage dirs (`chroma_db/`, `chroma/`) are gitignored
- Chunk boundaries must respect source structure (don't split mid-review)
- Overlap is zero for review chunks, 200 chars for article/Reddit chunks
