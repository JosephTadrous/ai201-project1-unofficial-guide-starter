"""
Document ingestion and cleaning script.

Loads raw source files from documents/, parses HTML or plain text,
and writes cleaned Markdown files to documents/clean/.

Each parser preserves structural markers (headings, paragraph breaks)
needed by the downstream chunking strategy in planning.md.
"""

import json
import re
from pathlib import Path

from bs4 import BeautifulSoup, Tag

DOCS_DIR = Path("documents")
CLEAN_DIR = DOCS_DIR / "clean"

# ── Source registry ──────────────────────────────────────────────────
# Maps raw filename → (parser function, source metadata)

SOURCE_META = {
    "ratedorm_harvard.txt": {
        "source_type": "review",
        "university": "Harvard",
        "source_url": "https://www.ratemydorm.com/dorms/harvard-university",
    },
    "ratedorm_princeton.txt": {
        "source_type": "review",
        "university": "Princeton",
        "source_url": "https://www.ratemydorm.com/dorms/princeton-university",
    },
    "ratedorm_yale.txt": {
        "source_type": "review",
        "university": "Yale",
        "source_url": "https://www.ratemydorm.com/dorms/yale",
    },
    "prked_cornell.html": {
        "source_type": "article",
        "university": "Cornell",
        "source_url": "https://prked.com/post/insiders-guide-best-dorms-cornell",
    },
    "prked_yale.html": {
        "source_type": "article",
        "university": "Yale",
        "source_url": "https://prked.com/post/a-yalies-unofficial-guide-to-the-best-dorms-at-yale-university",
    },
    "prked_brown.html": {
        "source_type": "article",
        "university": "Brown",
        "source_url": "https://prked.com/post/decoding-the-dorms-an-insiders-guide-to-the-best-places-to-live-at-brown-university",
    },
    "thedp_dorm_tips.html": {
        "source_type": "newspaper",
        "university": "Penn",
        "source_url": "https://www.thedp.com/article/2016/06/new-student-issue-tips-dorm-living",
    },
    "thedp_housing_advice.html": {
        "source_type": "newspaper",
        "university": "Penn",
        "source_url": "https://www.thedp.com/article/2022/10/penn-upperclassmen-tips-advice-housing-process",
    },
    "spectator_housing_guide.html": {
        "source_type": "newspaper",
        "university": "Columbia",
        "source_url": "https://www.columbiaspectator.com/spectrum/2026/03/09/the-ultimate-guide-to-first-year-housing/",
    },
    "dartmouth.html": {
        "source_type": "newspaper",
        "university": "Dartmouth",
        "source_url": "https://www.thedartmouth.com/article/2024/09/a-sense-of-camaraderie-exploring-dartmouths-freshman-residence-halls",
    },
}


# ── Parsers ──────────────────────────────────────────────────────────

def _collapse_whitespace(text: str) -> str:
    """Normalize runs of whitespace within a line, strip trailing spaces."""
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        cleaned.append(re.sub(r"[ \t]+", " ", line).strip())
    return "\n".join(cleaned)


def _collapse_blank_lines(text: str) -> str:
    """Reduce 3+ consecutive blank lines to 2 (one visual blank line)."""
    return re.sub(r"\n{3,}", "\n\n", text)


def parse_ratemydorm_txt(raw: str, meta: dict) -> str:
    """
    RateMyDorm .txt files are already manually structured:
    - Dorm name on its own line
    - Review text in paragraphs
    - '---' separating dorms
    Convert to Markdown with ## headings per dorm.
    """
    university = meta["university"]
    lines = raw.strip().split("\n")
    output_lines = [f"# RateMyDorm Reviews — {university}\n"]

    for line in lines:
        stripped = line.strip()
        if stripped == "---":
            output_lines.append("\n---\n")
        elif stripped == "":
            output_lines.append("")
        # Detect dorm name lines: short, no punctuation ending, appears after --- or at start
        elif (
            len(stripped) < 80
            and not stripped.endswith(".")
            and not stripped.endswith(":")
            and not stripped.startswith("-")
            and not stripped.startswith("Lived in")
            and not stripped.startswith("Verified")
            and not re.match(r"^\d+ years? ago$", stripped)
            and not stripped.startswith("PROS")
            and not stripped.startswith("CONS")
            and not stripped.startswith("Room ")
            and _looks_like_dorm_name(stripped, output_lines)
        ):
            output_lines.append(f"\n## {stripped}\n")
        else:
            output_lines.append(stripped)

    return _collapse_blank_lines("\n".join(output_lines))


def _looks_like_dorm_name(line: str, prior_lines: list[str]) -> bool:
    """Heuristic: a dorm name follows a --- separator or is the first content line."""
    # Walk backwards through prior lines to find last non-empty line
    for prev in reversed(prior_lines):
        prev = prev.strip()
        if prev == "":
            continue
        if prev == "---" or prev.startswith("# "):
            return True
        return False
    return True


def parse_prked_html(raw: str, meta: dict) -> str:
    """
    Prked articles use a standard <article> tag with h1/h2/h3/p elements.
    """
    soup = BeautifulSoup(raw, "lxml")
    article = soup.find("article")
    if not article:
        raise ValueError(f"No <article> tag found in {meta['source_url']}")

    output = []
    for el in article.find_all(["h1", "h2", "h3", "h4", "p", "div", "li", "blockquote"]):
        # Only use <div> if it's a leaf node (no child block elements)
        if el.name == "div" and el.find(["h1", "h2", "h3", "h4", "p", "div", "li", "blockquote"]):
            continue
        text = el.get_text(strip=True)
        if not text:
            continue
        # Skip date-only lines and "Share" / nav elements
        if re.match(r"^\d{1,2}/\d{1,2}/\d{2,4}$", text):
            continue
        if text.lower() in ("share", "copy link", "related posts"):
            continue

        if el.name == "h1":
            output.append(f"# {text}\n")
        elif el.name == "h2":
            output.append(f"\n## {text}\n")
        elif el.name == "h3":
            output.append(f"\n### {text}\n")
        elif el.name == "h4":
            output.append(f"\n#### {text}\n")
        elif el.name == "li":
            output.append(f"- {text}")
        elif el.name == "blockquote":
            output.append(f"> {text}\n")
        else:
            output.append(f"{text}\n")

    return _collapse_blank_lines("\n".join(output))


def parse_thedp_html(raw: str, meta: dict) -> str:
    """
    Daily Pennsylvanian articles use <div class="article-content"> with <p> tags.
    Title is in <h1> or og:title meta.
    """
    soup = BeautifulSoup(raw, "lxml")

    # Extract title
    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else ""
    if not title:
        og = soup.find("meta", property="og:title")
        title = og["content"] if og else "Untitled"

    # Extract author and date from meta
    author_el = soup.find("meta", attrs={"name": "author"})
    if not author_el:
        # Try schema.org JSON-LD
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                if "author" in data:
                    authors = data["author"]
                    if isinstance(authors, list):
                        author_el = authors[0] if authors else None
            except (json.JSONDecodeError, TypeError):
                pass

    output = [f"# {title}\n"]

    content_div = soup.find("div", class_="article-content")
    if not content_div:
        raise ValueError(f"No article-content div found for {meta['source_url']}")

    for el in content_div.find_all(["p", "h2", "h3", "h4", "blockquote"]):
        text = el.get_text(strip=True)
        if not text:
            continue
        # Skip ad/promo text
        if "advertisement" in text.lower() or "subscribe" in text.lower():
            continue

        if el.name == "h2":
            output.append(f"\n## {text}\n")
        elif el.name == "h3":
            output.append(f"\n### {text}\n")
        elif el.name == "blockquote":
            output.append(f"> {text}\n")
        else:
            output.append(f"{text}\n")

    return _collapse_blank_lines("\n".join(output))


def parse_spectator_html(raw: str, meta: dict) -> str:
    """
    Columbia Spectator embeds content in Fusion.globalContent JSON inside a <script> tag.
    Content elements are {type: "text", content: "..."} with inline HTML.
    """
    soup = BeautifulSoup(raw, "lxml")

    # Find Fusion.globalContent JSON
    fusion_data = None
    for script in soup.find_all("script"):
        text = script.string or ""
        if "Fusion.globalContent=" in text:
            match = re.search(r"Fusion\.globalContent=(\{.*?\});", text, re.DOTALL)
            if match:
                fusion_data = json.loads(match.group(1))
            break

    if not fusion_data:
        raise ValueError("Could not find Fusion.globalContent in Spectator HTML")

    title = fusion_data.get("headlines", {}).get("basic", "Untitled")
    elements = fusion_data.get("content_elements", [])

    output = [f"# {title}\n"]

    current_dorm = None
    in_pros = False
    in_cons = False

    for el in elements:
        if el["type"] != "text":
            continue
        content_html = el.get("content", "")
        if not content_html.strip():
            continue

        # Parse inline HTML
        inner = BeautifulSoup(content_html, "lxml")
        text = inner.get_text(strip=True)
        if not text:
            continue

        # Skip email/social boilerplate
        if "columbiaspectator.com" in text or "@CUSpectrum" in text:
            continue
        if "Subscribe to our" in text:
            continue

        # Detect dorm headers (bold name + description)
        bold = inner.find("b")
        if bold and " - " in content_html:
            # This is a dorm header like "Wallach Hall - Located on..."
            dorm_name = bold.get_text(strip=True).rstrip(" -")
            description = text.replace(bold.get_text(strip=True), "", 1).lstrip(" -–—").strip()
            output.append(f"\n## {dorm_name}\n")
            output.append(f"{description}\n")
            current_dorm = dorm_name
            in_pros = False
            in_cons = False
            continue

        # Detect Pros/Cons headers
        if text == "Pros":
            output.append(f"\n**Pros:**\n")
            in_pros = True
            in_cons = False
            continue
        if text == "Cons":
            output.append(f"\n**Cons:**\n")
            in_cons = True
            in_pros = False
            continue

        # Regular content
        if in_pros or in_cons:
            output.append(f"- {text}")
        else:
            output.append(f"{text}\n")

    return _collapse_blank_lines("\n".join(output))


def parse_dartmouth_html(raw: str, meta: dict) -> str:
    """
    The Dartmouth uses <article> with h1/h2 and <div class="article-content"> with <p> tags.
    """
    soup = BeautifulSoup(raw, "lxml")

    # Title and subtitle from article tag
    article = soup.find("article")
    title_tag = article.find("h1") if article else soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "Untitled"
    subtitle_tag = article.find("h2") if article else None
    subtitle = subtitle_tag.get_text(strip=True) if subtitle_tag else ""

    output = [f"# {title}\n"]
    if subtitle:
        output.append(f"*{subtitle}*\n")

    content_div = soup.find("div", class_="article-content")
    if not content_div:
        raise ValueError(f"No article-content div found for {meta['source_url']}")

    for el in content_div.find_all(["p", "h2", "h3", "h4", "blockquote"]):
        text = el.get_text(strip=True)
        if not text:
            continue

        if el.name == "h2":
            output.append(f"\n## {text}\n")
        elif el.name == "h3":
            output.append(f"\n### {text}\n")
        elif el.name == "blockquote":
            output.append(f"> {text}\n")
        else:
            output.append(f"{text}\n")

    return _collapse_blank_lines("\n".join(output))


# ── Parser dispatch ──────────────────────────────────────────────────

PARSERS = {
    "ratedorm_harvard.txt": parse_ratemydorm_txt,
    "ratedorm_princeton.txt": parse_ratemydorm_txt,
    "ratedorm_yale.txt": parse_ratemydorm_txt,
    "prked_cornell.html": parse_prked_html,
    "prked_yale.html": parse_prked_html,
    "prked_brown.html": parse_prked_html,
    "thedp_dorm_tips.html": parse_thedp_html,
    "thedp_housing_advice.html": parse_thedp_html,
    "spectator_housing_guide.html": parse_spectator_html,
    "dartmouth.html": parse_dartmouth_html,
}


# ── Main ─────────────────────────────────────────────────────────────

def ingest_all():
    CLEAN_DIR.mkdir(exist_ok=True)

    for filename, parser in PARSERS.items():
        filepath = DOCS_DIR / filename
        if not filepath.exists():
            print(f"SKIP  {filename} (file not found)")
            continue

        raw = filepath.read_text(encoding="utf-8", errors="replace")
        meta = SOURCE_META[filename]

        try:
            cleaned = parser(raw, meta)
            cleaned = _collapse_whitespace(cleaned)
            cleaned = _collapse_blank_lines(cleaned)
        except Exception as e:
            print(f"ERROR {filename}: {e}")
            continue

        # Write cleaned markdown
        out_name = filepath.stem + ".md"
        out_path = CLEAN_DIR / out_name
        out_path.write_text(cleaned, encoding="utf-8")

        # Stats
        line_count = len(cleaned.strip().split("\n"))
        char_count = len(cleaned)
        print(f"OK    {filename:40s} → {out_name:30s}  ({line_count} lines, {char_count:,} chars)")

    print(f"\nCleaned files written to {CLEAN_DIR}/")


if __name__ == "__main__":
    ingest_all()
