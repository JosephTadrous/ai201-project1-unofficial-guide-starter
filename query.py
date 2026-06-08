"""
Generation module for the Unofficial Guide RAG pipeline.

Retrieves relevant chunks via embed.retrieve(), builds a grounded prompt,
and calls Groq LLM to generate an answer strictly from the retrieved context.

Returns both the answer and the list of sources used.
"""

import os
import re

from dotenv import load_dotenv
from groq import Groq

from embed import retrieve

load_dotenv()

GROQ_MODEL = "llama-3.1-8b-instant"

SYSTEM_PROMPT = """\
You are a helpful assistant that answers questions about Ivy League university dorms \
using ONLY the provided context passages.

RULES:
1. Answer ONLY based on the information in the CONTEXT below. Do not use any outside knowledge.
2. If the context does not contain enough information to answer the question, say \
"I don't have enough information in my sources to answer that."
3. When you use information from a passage, cite it inline using the source tag provided \
at the start of each passage, e.g. [Source: RateMyDorm — Harvard].
4. Be specific — mention dorm names, universities, and concrete details from the sources.
5. Keep your answer concise and directly responsive to the question.
"""


def _make_source_tag(meta: dict) -> str:
    """Build a short, readable source tag from chunk metadata."""
    university = meta.get("university", "Unknown")
    dorm = meta.get("dorm_name", "")
    url = meta.get("source_url", "")

    # Extract site name from URL
    site = url.split("//")[-1].split("/")[0].replace("www.", "") if url else ""

    tag = f"{site} — {university}"
    if dorm:
        tag += f" — {dorm}"
    return tag


def _build_context(results: list[dict]) -> tuple[str, dict[str, str]]:
    """
    Format retrieved chunks into a context block with descriptive source tags.
    Returns (context_string, tag_to_url mapping).
    """
    context_parts = []
    tag_to_url = {}

    for r in results:
        meta = r["metadata"]
        tag = _make_source_tag(meta)
        url = meta.get("source_url", "")
        tag_to_url[tag] = url

        context_parts.append(
            f"[Source: {tag}]\n{r['text']}"
        )

    context = "\n\n---\n\n".join(context_parts)
    return context, tag_to_url


def ask(question: str, k: int | None = None) -> dict:
    """
    End-to-end RAG: retrieve context, generate grounded answer.

    Returns:
        {"answer": str, "sources": list[str]}
    """
    results = retrieve(question, k=k)
    context, tag_to_url = _build_context(results)

    user_prompt = f"CONTEXT:\n{context}\n\nQUESTION: {question}"

    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=1024,
    )

    answer = response.choices[0].message.content

    # Clean up any stray [Source N] numeric references the LLM may produce
    answer = re.sub(r"\[Source \d+\]", "", answer).strip()

    # Only return sources the LLM actually cited in its answer
    cited_sources = []
    for tag, url in tag_to_url.items():
        if tag in answer:
            cited_sources.append(f"{tag} ({url})")

    return {"answer": answer, "sources": cited_sources}


if __name__ == "__main__":
    import sys

    question = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "How far is Thayer dorm from other on-campus buildings at Harvard?"
    result = ask(question)
    print(f"Q: {question}\n")
    print(f"A: {result['answer']}\n")
    print("Sources:")
    for s in result["sources"]:
        print(f"  • {s}")
