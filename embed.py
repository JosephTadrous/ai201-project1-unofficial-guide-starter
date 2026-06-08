"""
Embedding and retrieval script for the Unofficial Guide RAG pipeline.

Embeds chunks from chunks.json using all-MiniLM-L6-v2 (sentence-transformers),
stores them in a local ChromaDB collection with source metadata,
and provides a retrieve() function for querying.

Usage:
    # Build the vector store (run once, or after re-chunking):
    python embed.py

    # Interactive query mode:
    python embed.py --query "Which dorms at Cornell have AC?"
"""

import argparse
import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

CHUNKS_PATH = Path("chunks.json")
CHROMA_DIR = Path("chroma_db")
COLLECTION_NAME = "dorm_reviews"
MODEL_NAME = "all-MiniLM-L6-v2"

DEFAULT_K = 5
COMPARISON_K = 7
# Keywords that suggest a cross-school comparison query
COMPARISON_KEYWORDS = [
    "which ivy", "compare", "best ivy", "across", "all schools",
    "ranking", "vs", "versus",
]


def load_chunks() -> list[dict]:
    return json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))


def build_index(chunks: list[dict]) -> None:
    """Embed all chunks and store in ChromaDB."""
    print(f"Loading embedding model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    # Delete existing collection if present (fresh rebuild)
    existing = [c.name for c in client.list_collections()]
    if COLLECTION_NAME in existing:
        client.delete_collection(COLLECTION_NAME)

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    texts = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]
    ids = [f"chunk_{i}" for i in range(len(chunks))]

    print(f"Embedding {len(texts)} chunks...")
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=32)

    collection.add(
        ids=ids,
        embeddings=embeddings.tolist(),
        documents=texts,
        metadatas=metadatas,
    )

    print(f"Stored {len(texts)} chunks in ChromaDB at {CHROMA_DIR}/")


def _detect_top_k(query: str) -> int:
    """Return k=7 for cross-school comparison queries, k=5 otherwise."""
    query_lower = query.lower()
    for kw in COMPARISON_KEYWORDS:
        if kw in query_lower:
            return COMPARISON_K
    return DEFAULT_K


def retrieve(query: str, k: int | None = None) -> list[dict]:
    """
    Retrieve top-k most relevant chunks for a query.

    Returns a list of dicts with keys: text, metadata, distance.
    """
    if k is None:
        k = _detect_top_k(query)

    model = SentenceTransformer(MODEL_NAME)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_collection(COLLECTION_NAME)

    query_embedding = model.encode([query]).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=k,
    )

    retrieved = []
    for i in range(len(results["ids"][0])):
        retrieved.append({
            "text": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
        })

    return retrieved


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Embed chunks or query the vector store")
    parser.add_argument("--query", "-q", type=str, help="Query to retrieve chunks for")
    parser.add_argument("--k", type=int, help="Number of results (default: auto-detect)")
    args = parser.parse_args()

    if args.query:
        results = retrieve(args.query, k=args.k)
        print(f"\nTop {len(results)} results for: \"{args.query}\"\n")
        for i, r in enumerate(results):
            m = r["metadata"]
            print(f"--- Result {i+1} | dist={r['distance']:.4f} | {m['university']} | {m['source_file']} ---")
            if "dorm_name" in m:
                print(f"    Dorm: {m['dorm_name']}")
            print(r["text"][:300])
            print("..." if len(r["text"]) > 300 else "")
            print()
    else:
        chunks = load_chunks()
        build_index(chunks)
