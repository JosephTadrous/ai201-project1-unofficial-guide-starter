"""
Chunking script for the Unofficial Guide RAG pipeline.

Reads cleaned Markdown files from documents/clean/ and produces chunks
according to the strategy in planning.md:

- Review sites (RateMyDorm): 1 chunk per dorm section (split on --- and ## headings).
  No overlap. Each chunk contains all reviews for that dorm.
- Articles/newspapers: Recursive character splitting at 1,200 chars with 200-char
  overlap, using separator hierarchy ["\n## ", "\n### ", "\n\n", "\n", ". ", " "].

Each chunk carries metadata: source_file, source_url, university, source_type,
and (for reviews) dorm_name.
"""

import json
import re
from pathlib import Path

from ingest import SOURCE_META

CLEAN_DIR = Path("documents") / "clean"
CHUNKS_PATH = Path("chunks.json")

# Map cleaned filename back to raw filename for metadata lookup
_CLEAN_TO_RAW = {Path(raw).stem + ".md": raw for raw in SOURCE_META}

CHUNK_SIZE = 1200  # characters
OVERLAP = 200      # characters
SEPARATORS = ["\n## ", "\n### ", "\n\n", "\n", ". ", " "]


# ── Review chunking ─────────────────────────────────────────────────

def chunk_reviews(text: str, meta: dict) -> list[dict]:
    """Split RateMyDorm Markdown into one chunk per dorm section."""
    # Remove the top-level # title line
    text = re.sub(r"^#\s+.+\n*", "", text).strip()

    # Split into dorm sections by ## heading
    # Each section starts with "## Dorm Name"
    parts = re.split(r"(?=^## )", text, flags=re.MULTILINE)
    chunks = []

    for part in parts:
        part = part.strip().strip("-").strip()
        if not part:
            continue

        # Extract dorm name from ## heading
        dorm_match = re.match(r"^##\s+(.+)", part)
        if not dorm_match:
            continue
        dorm_name = dorm_match.group(1).strip()

        # Body is everything after the heading line
        body = part[dorm_match.end():].strip()
        if not body:
            continue

        chunks.append({
            "text": f"## {dorm_name}\n\n{body}",
            "metadata": {
                **meta,
                "dorm_name": dorm_name,
            },
        })

    return chunks


# ── Recursive character splitting ────────────────────────────────────

def _recursive_split(text: str, separators: list[str], chunk_size: int) -> list[str]:
    """
    Recursively split text using a hierarchy of separators.
    Tries the first separator; if any resulting piece exceeds chunk_size,
    recurse with the next separator. Merges small pieces back together
    up to chunk_size. No overlap applied here — overlap is added in a
    separate pass after splitting.
    """
    if len(text) <= chunk_size:
        return [text]

    # Find the first separator that exists in the text
    sep = None
    for s in separators:
        if s in text:
            sep = s
            break

    if sep is None:
        # No separator found — hard split at chunk_size
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunks.append(text[start:end])
            start = end
        return chunks

    # Split on the chosen separator
    raw_pieces = text.split(sep)

    # Re-attach separator to the beginning of each piece (except the first)
    pieces = [raw_pieces[0]]
    for p in raw_pieces[1:]:
        pieces.append(sep + p)

    # Recursively split any piece that's still too large
    split_pieces = []
    remaining_seps = separators[separators.index(sep) + 1:]
    for piece in pieces:
        if len(piece) > chunk_size:
            sub_seps = remaining_seps if remaining_seps else separators[-1:]
            split_pieces.extend(_recursive_split(piece, sub_seps, chunk_size))
        else:
            split_pieces.append(piece)

    # Merge small adjacent pieces back together up to chunk_size
    return _merge_pieces(split_pieces, chunk_size)


def _merge_pieces(pieces: list[str], chunk_size: int) -> list[str]:
    """Merge small adjacent pieces into chunks up to chunk_size."""
    if not pieces:
        return []

    merged = []
    current = pieces[0]

    for piece in pieces[1:]:
        if len(current) + len(piece) <= chunk_size:
            current += piece
        else:
            merged.append(current.strip())
            current = piece

    if current.strip():
        merged.append(current.strip())

    return merged


def _add_overlap(chunks: list[str], overlap: int) -> list[str]:
    """Add overlap by prepending the tail of each chunk to the next one."""
    if overlap <= 0 or len(chunks) <= 1:
        return chunks

    result = [chunks[0]]
    for i in range(1, len(chunks)):
        prev = chunks[i - 1]
        if len(prev) > overlap:
            overlap_text = prev[-overlap:]
            # Start at a word boundary
            space_idx = overlap_text.find(" ")
            if space_idx != -1:
                overlap_text = overlap_text[space_idx + 1:]
            result.append(overlap_text + chunks[i])
        else:
            result.append(chunks[i])

    return result


def chunk_article(text: str, meta: dict) -> list[dict]:
    """Split article/newspaper Markdown using recursive character splitting."""
    raw_chunks = _recursive_split(text, SEPARATORS, CHUNK_SIZE)
    raw_chunks = _add_overlap(raw_chunks, OVERLAP)

    chunks = []
    for chunk_text in raw_chunks:
        chunk_text = chunk_text.strip()
        if not chunk_text:
            continue
        chunks.append({
            "text": chunk_text,
            "metadata": {**meta},
        })

    return chunks


# ── Main ─────────────────────────────────────────────────────────────

def chunk_all() -> list[dict]:
    all_chunks = []

    for clean_file in sorted(CLEAN_DIR.glob("*.md")):
        raw_name = _CLEAN_TO_RAW.get(clean_file.name)
        if not raw_name:
            print(f"SKIP  {clean_file.name} (no metadata mapping)")
            continue

        meta = SOURCE_META[raw_name]
        text = clean_file.read_text(encoding="utf-8")

        if meta["source_type"] == "review":
            chunks = chunk_reviews(text, meta)
        else:
            chunks = chunk_article(text, meta)

        # Add source_file to each chunk's metadata
        for chunk in chunks:
            chunk["metadata"]["source_file"] = clean_file.name

        all_chunks.extend(chunks)
        print(f"OK    {clean_file.name:35s}  → {len(chunks):>3} chunks")

    return all_chunks


if __name__ == "__main__":
    chunks = chunk_all()

    # Write chunks to JSON for inspection and downstream use
    CHUNKS_PATH.write_text(
        json.dumps(chunks, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Summary stats
    lengths = [len(c["text"]) for c in chunks]
    print(f"\nTotal chunks: {len(chunks)}")
    print(f"Avg chunk size: {sum(lengths) // len(lengths)} chars")
    print(f"Min: {min(lengths)} chars, Max: {max(lengths)} chars")
    print(f"Written to {CHUNKS_PATH}")
