# The Unofficial Guide — Project 1

> **How to use this template:**
> Complete each section *after* you've built and tested the corresponding part of your system.
> Do not write placeholder text — if a section isn't done yet, leave it blank and come back.
> Every section below is required for submission. One-liners will not receive full credit.

---

## Domain
Student and College reviews of dorms at Ivy League Universities. It's useful because there is not a lot of dorms information available on universities websites. In addition, these pieces of information are usually general and do not reflect students experiences and testimonials.



## Document Sources
<!-- List every source you collected documents from.
     Be specific: include URLs, subreddit names, forum thread titles, or file names.
     Aim for variety — sources that together cover different subtopics or perspectives. -->

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 | RateMyDorm — Harvard University | Review Aggregator | https://www.ratemydorm.com/dorms/harvard-university |
| 2 | RateMyDorm — Princeton University | Review Aggregator | https://www.ratemydorm.com/dorms/princeton-university|
| 3 | RateMyDorm — Yale University | Review Aggregator | https://www.ratemydorm.com/dorms/yale |
| 4 | Prked — An Insider's Guide to the Best Dorms at Cornell| Article | https://prked.com/post/insiders-guide-best-dorms-cornell |
| 5 | Prked - A Yalie's Unofficial Guide to the Best Dorms at Yale University | Article | https://prked.com/post/a-yalies-unofficial-guide-to-the-best-dorms-at-yale-university |
| 6 | The Daily Pennsylvanian — "The do's and don'ts of living in a Penn dorm" | Student Newspaper | https://www.thedp.com/article/2016/06/new-student-issue-tips-dorm-living |
| 7 | The Daily Pennsylvanian — "Upperclassmen offer advice on navigating housing" | Student Newspaper | https://www.thedp.com/article/2022/10/penn-upperclassmen-tips-advice-housing-process |
| 8 | Columbia Spectator — Housing Guide 2023 | Student Newspaper | https://www.columbiaspectator.com/spectrum/2026/03/09/the-ultimate-guide-to-first-year-housing/ |
| 9 | A sense of camaraderie’: Exploring Dartmouth’s freshman residence halls | Student Newspaper| https://www.thedartmouth.com/article/2024/09/a-sense-of-camaraderie-exploring-dartmouths-freshman-residence-halls |
| 10 | Decoding the Dorms: An Insider's Guide to the Best Places to Live at Brown University | Article | https://prked.com/post/decoding-the-dorms-an-insiders-guide-to-the-best-places-to-live-at-brown-university |


---

## Chunking Strategy

<!-- Describe your chunking approach with enough specificity that someone else could reproduce it.
     Include:
     - Chunk size (characters or tokens) and why that size fits your documents
     - Overlap size and why (or why not) you used overlap
     - Any preprocessing you did before chunking (e.g., stripping HTML, removing headers)
     - What your final chunk count was across all documents -->

This corpus is structurally mixed. Individual student reviews are naturally short and
self-contained, while newspaper and long-form articles need to be split.

**Chunk size:**
- Review sites (RateMyDorm): 1 review per dorm = 1 chunk, naturally 80–350 tokens.
  No fixed size applied. Dorms are separated by `---` and `## Dorm Name` headings.
- Articles and newspapers (Prked, Daily Pennsylvanian, Columbia Spectator, The Dartmouth):
  1,200 characters (~300 tokens), recursive on ["\n## ", "\n### ", "\n\n", "\n", ". ", " "].
  Articles without headings (DP, Dartmouth) fall through to paragraph-level splits on "\n\n".

**Overlap:**
- Review sites: 0. Review boundaries are hard — no context bleeds across reviews.
- Articles and newspapers: 200 characters (~50 tokens). Articles have continuous prose
  where a sentence at a paragraph boundary often sets up the next paragraph's point.

**Reasoning:**
This corpus has two structurally distinct source types, so a single chunk size would
either over-split short reviews or under-split long articles. Review sites are parsed
structurally (by `---` and `## heading` boundaries), not split by algorithm. Articles
and newspapers use recursive chunking because their heading and paragraph conventions
give the separator hierarchy clean boundaries to exploit; 300 tokens is large enough
to capture a complete point without merging unrelated sections. Overlap is zero for reviews
because redundancy across chunk boundaries adds index noise without retrieval benefit
when boundaries are already semantically clean.

**Final chunk count:**
99 chunks across all 10 resources
---

## Embedding Model

<!-- Name the embedding model you used and explain your choice.
     Then answer: if you were deploying this system for real users and cost wasn't a constraint,
     what tradeoffs would you weigh in choosing a different model?
     Consider: context length limits, multilingual support, accuracy on domain-specific text,
     latency, and local vs. API-hosted. -->

**Model used:**
all-MiniLM-L6-v2 via sentence-transformers

**Production tradeoff reflection:**
Two tradeoffs would drive model selection in production:

- Context length: all-MiniLM-L6-v2 truncates at 256 tokens, silently cutting longer
  article chunks. text-embedding-3-large (8,191 tokens) or instructor-xl (512 tokens)
  eliminate this risk.

- Multilingual: irrelevant for this corpus but multilingual-e5-large would be the
  right call if the domain expanded to international housing sources.

---

## Grounded Generation

<!-- Explain how your system enforces grounding — how does it prevent the LLM from answering
     beyond the retrieved documents?
     Describe both your system prompt (what instruction you gave the model) and any structural
     choices (e.g., how you formatted the context, whether you filtered low-relevance chunks).
     Do not just say "I told it to use the documents" — show the actual instruction or explain
     the mechanism. -->

**System prompt grounding instruction:**

The system prompt explicitly constrains the LLM with five rules:

1. "Answer ONLY based on the information in the CONTEXT below. Do not use any outside knowledge."
2. If the context is insufficient, respond with "I don't have enough information in my sources to answer that." — this prevents hallucination on off-topic or unanswerable questions.
3. Cite inline using descriptive source tags like `[Source: ratemydorm.com — Harvard — Thayer]` that match labels prepended to each context passage.
4. Be specific — mention dorm names, universities, and concrete details from the sources.
5. Keep the answer concise and directly responsive.

**How source attribution is surfaced in the response:**

After generation, the system parses the answer for `[Source: ...]` tags and matches them against the source labels provided in the context. Only sources the LLM actually cited appear in the output — unused retrieved sources are filtered out. The final output has two sections: the answer with inline citations, and a deduplicated source list showing the site name, university, and full URL for each cited source.

---

## Evaluation Report

<!-- Run your 5 test questions from planning.md through your system and record the results.
     Be honest — a partially accurate or inaccurate result that you explain well is more
     valuable than a suspiciously perfect result. -->

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | How far is Thayer dorm from other on-campus buildings at Harvard? | 2 min walk to dining hall, 3 min walk to Science Center | Correctly states 2 min to dining hall and 3 min to Science Center. Cited ratemydorm.com Harvard Thayer. | Relevant | Accurate |
| 2 | Which dorms at Brown are close to the fitness center? | Pembroke Campus and Metcalf & Miller Halls are close to the fitness center | Returned "not enough information in sources" — no answer produced | Off-target | Inaccurate |
| 3 | Does any dorm at Columbia have an esports lounge? | John Jay and Wallach Hall have a shared esports game lounge downstairs | Correctly identifies an esports lounge aand attributes it to John Jay AND Wallach sharing it | Relevant | Accurate |
| 4 | Which freshman dorms at Cornell have AC? | Toni Morrison, Ganędagǫ:, Mews, and CKB all have AC | Only returns Toni Morrison and Ganędagǫ: — misses Mews Hall and Court-Kay-Bauer Hall entirely | Partially relevant | Partially accurate |
| 5 | How is Forbes College Main dorms | Two-section dorm: new wing (large rooms, no AC, roaches) vs. main inn (smaller, more communal). Rooms 220, 216, 268 called out specifically. | Covers large rooms, natural light, elevator issue, plumbing problems. Misses the new wing vs. main inn distinction, no AC, roaches, and specific room callouts. | Relevant | Partially accurate |


**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

<!-- Identify at least one question where retrieval or generation did not work as expected.
     Write a specific explanation of *why* it failed, tied to a part of the pipeline.

     "The answer was wrong" is not an explanation.

     "The relevant information was split across a chunk boundary, so retrieval returned
     only half the context — the model didn't have enough to answer correctly" is an explanation.

     "The embedding model treated the professor's nickname as out-of-vocabulary and returned
     results from an unrelated review" is an explanation. -->

**Question that failed:** Which freshman dorms have AC at Cornell?

**What the system returned:** Toni Morrison Hall and Ganędagǫ: Hall — but missed Mews Hall and Court-Kay-Bauer Hall (CKB), which also have AC according to the source article.

**Root cause (tied to a specific pipeline stage):** The failure spans chunking and retrieval. The Mews/CKB AC information lives in a chunk that begins with ~190 characters of overlap text from the previous Ganędagǫ: Hall section ("...a really cool nod to the history of the land Cornell is built on. Like its neighbor, it's designed to foster community..."). The phrase "air conditioning" appears only once, buried in the middle of the chunk. When all-MiniLM-L6-v2 encodes this chunk into a single 384-dim vector, the dominant semantics come from the Ganędagǫ: Hall overlap and the general dorm-amenity language around Mews/CKB — not from the brief AC mention. This pushed the chunk to rank 10th (cosine distance 0.43) for the query "Which freshman dorms have AC at Cornell?", well outside the top-k=5 retrieval window. Meanwhile, the chunk containing Toni Morrison Hall and Ganędagǫ: Hall explicitly repeats "air conditioning" twice and ranked 3rd (distance 0.33).

**What you would change to fix it:** Stop overlap from crossing heading boundaries — when the next chunk starts with a new section heading (like `#### Mews Hall`), don't prepend overlap text from the previous section. This would keep each chunk's embedding semantically focused on its own topic, improving retrieval rank for specific queries.

---

## Spec Reflection

<!-- Reflect on how planning.md shaped your implementation.
     Answer both questions with at least 2–3 sentences each. -->

**One way the spec helped you during implementation:**

The chunking strategy section in planning.md was the most useful part of the spec during implementation. Because it spelled out exact chunk sizes (1,200 chars for articles, natural boundaries for reviews), overlap values (200 chars for articles, 0 for reviews), and the recursive separator hierarchy.

**One way your implementation diverged from the spec, and why:**

The spec originally included Reddit (r/harvard, r/yale) as two of the ten sources, with a dedicated chunking strategy for comment-based content (split per comment, 200-char overlap only for long comments). During implementation, Reddit turned out to be completely blocked from automated fetching, so I replaced both Reddit sources with Prked articles (Brown, Yale) and a Dartmouth student newspaper article. This changed the corpus from three source types (reviews, articles, Reddit comments) to two (reviews, articles/newspapers), which simplified the chunking logic — the Reddit-specific per-comment splitting was no longer needed.

---

## AI Usage

<!-- Describe at least 2 specific instances where you used an AI tool during this project.
     For each: what did you give the AI as input, what did it produce, and what did you
     change, override, or direct differently?

     "I used Claude to help me code" is not sufficient.
     "I gave Claude my Chunking Strategy section from planning.md and asked it to implement
     chunk_text(). It returned a function using a fixed character split. I overrode the
     chunk size from 500 to 200 because my documents are short reviews, not long guides." -->

**Instance 1**

- *What I gave the AI:* I gave Claude Code the list of 10 source URLs from planning.md and asked it to implement an ingestion script that loads and cleans each source. I specified that sources were saved as `.html` files (browser "Save as") and needed to be parsed into structured Markdown preserving headings and paragraph breaks for downstream chunking.
- *What it produced:* It produced `ingest.py` with per-source-type parsers: a BeautifulSoup parser for Prked articles (`<article>` tag), a different parser for the Daily Pennsylvanian (`<div class="article-content">`), and a plain-text formatter for manually saved RateMyDorm files. Each parser output clean Markdown with `#`/`##`/`###` headings and paragraph breaks.
- *What I changed or overrode:* The initial Prked parser only extracted `<p>` tags, which missed all paragraph content in the Cornell article because it used `<div>` tags instead. I directed Claude to add `<div>` to the tag list with a leaf-node filter. I also had it add a `_promote_subheadings()` post-processing step to detect bare dorm-name lines (like "Toni Morrison Hall") in the Cornell article and convert them to `####` headings, since the HTML didn't use heading tags for individual dorm names.

**Instance 2**

- *What I gave the AI:* I gave Claude Code the Chunking Strategy section from planning.md (chunk sizes, overlap values, separator hierarchy) and asked it to implement the chunking script. I specified the two source types (reviews split on `---`/`##` boundaries with no overlap, articles split recursively at 1,200 chars with 200-char overlap).
- *What it produced:* It produced `chunk.py` with a `chunk_reviews()` function that splits on `## Dorm Name` headings, and a `_recursive_split()` function that walks the separator hierarchy `["\n## ", "\n### ", "\n#### ", "\n\n", "\n", ". ", " "]`. It included `_merge_pieces()` to recombine small fragments up to the chunk size limit, and `_add_overlap()` as a separate pass to prepend 200 chars from the previous chunk at word boundaries.
- *What I changed or overrode:* The first version applied overlap at every recursion level, which caused text duplication within chunks (the same sentence appeared 2–3 times). I directed Claude to restructure so overlap is only applied once as a final pass after all splitting and merging is complete.
