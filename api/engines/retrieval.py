"""
Winter AI - Retrieval Engine (BM25)

Pure-Python BM25 ranking over the knowledge base. No external ML
dependencies required.

Why BM25 instead of plain cosine/TF-IDF: plain cosine similarity can let a
short, generic line (e.g. "what is your name") outrank a long, specific,
correct answer (e.g. a full sentence about photosynthesis) purely because
the short document's vector norm is tiny, so a couple of shared common
words dominate its similarity score. BM25 fixes this with (a) term-frequency
saturation, so repeating a common word doesn't help much, and (b) document
length normalization relative to the *average* document length rather than
the query, so rare/informative terms (like "photosynthesis") dominate the
score regardless of how long the containing document is.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field

TOKEN_RE = re.compile(r"[a-zà-ÿ0-9']+")

# BM25 hyperparameters (standard defaults)
K1 = 1.5
B = 0.75

# Function/stop words across the three supported languages. Excluding these
# from query scoring (not from indexing) is what actually fixes short,
# generic lines outranking long, specific, correct answers: without this,
# "what"/"is"/"comment"/"iki" etc. can dominate a short match's score
# regardless of BM25 length normalization, especially on smaller corpora.
STOPWORDS = {
    "en": {"a", "an", "the", "is", "are", "was", "were", "be", "been", "am",
           "what", "who", "how", "why", "where", "when", "do", "does", "did",
           "you", "your", "i", "me", "my", "it", "to", "of", "in", "on",
           "and", "or", "for", "with", "can", "could", "will", "would"},
    "fr": {"le", "la", "les", "un", "une", "des", "est", "es", "suis",
           "qui", "que", "quoi", "comment", "pourquoi", "où", "vous",
           "je", "tu", "il", "elle", "de", "du", "et", "ou", "pour", "avec"},
    "rw": {"ni", "ese", "iki", "nde", "he", "ryari", "kandi", "cyangwa"},
}
ALL_STOPWORDS = STOPWORDS["en"] | STOPWORDS["fr"] | STOPWORDS["rw"]


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


@dataclass
class Document:
    doc_id: str
    text: str
    source: str
    lang: str = "en"
    tf: Counter = field(default_factory=Counter)
    length: int = 0


class Retriever:
    def __init__(self) -> None:
        self.docs: list[Document] = []
        self.df: Counter = Counter()
        self.avgdl: float = 0.0
        self._idf_cache: dict[str, float] = {}

    def clear(self) -> None:
        self.docs = []
        self.df = Counter()
        self.avgdl = 0.0
        self._idf_cache = {}

    def add_document(self, doc_id: str, text: str, source: str, lang: str = "en") -> None:
        tokens = tokenize(text)
        if not tokens:
            return
        tf = Counter(tokens)
        doc = Document(doc_id=doc_id, text=text, source=source, lang=lang, tf=tf, length=len(tokens))
        self.docs.append(doc)
        for term in tf:
            self.df[term] += 1

    def index_corpus(self, corpus: list[dict]) -> None:
        self.clear()
        for entry in corpus:
            self.add_document(entry["id"], entry["text"], entry["source"], entry.get("lang", "en"))
        n = len(self.docs) or 1
        self.avgdl = sum(d.length for d in self.docs) / n
        self._idf_cache = {}

    def idf(self, term: str) -> float:
        if term not in self._idf_cache:
            n_docs = len(self.docs) or 1
            df = self.df.get(term, 0)
            # BM25 IDF (Robertson-Sparck Jones), floored at a small positive
            # value so very common terms don't go negative and flip scores.
            raw = math.log((n_docs - df + 0.5) / (df + 0.5) + 1.0)
            self._idf_cache[term] = max(raw, 1e-4)
        return self._idf_cache[term]

    def _bm25_score(self, query_tokens: list[str], doc: Document) -> float:
        score = 0.0
        avgdl = self.avgdl or 1.0
        for term in set(query_tokens):
            f = doc.tf.get(term, 0)
            if f == 0:
                continue
            idf = self.idf(term)
            numerator = f * (K1 + 1)
            denominator = f + K1 * (1 - B + B * (doc.length / avgdl))
            score += idf * (numerator / denominator)
        return score

    def search(self, query: str, top_k: int = 5) -> list[tuple[float, Document]]:
        raw_tokens = tokenize(query)
        if not raw_tokens or not self.docs:
            return []
        # Prefer content words; if the whole query is stopwords (e.g. a
        # bare greeting like "how are you"), fall back to the raw tokens.
        query_tokens = [t for t in raw_tokens if t not in ALL_STOPWORDS] or raw_tokens
        scored = [(self._bm25_score(query_tokens, doc), doc) for doc in self.docs]
        scored = [(s, d) for s, d in scored if s > 0]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return scored[:top_k]

    def best_match(self, query: str, lang: str | None = None) -> tuple[float, Document | None]:
        results = self.search(query, top_k=8)
        if lang:
            preferred = [r for r in results if r[1].lang == lang]
            if preferred:
                return preferred[0]
        if results:
            return results[0]
        return (0.0, None)


def build_corpus_from_knowledge(brain_text: str, knowledge_base: dict[str, str]) -> list[dict]:
    """Turn brain.txt + api/info/*.txt (+ api/info/teach/*) into a flat,
    searchable corpus. Lines like `EN: ... | FR: ... | RW: ...` are split
    into separate language-tagged documents."""
    corpus: list[dict] = []
    counter = 0

    def add_line(line: str, source: str) -> None:
        nonlocal counter
        line = line.strip()
        if not line:
            return
        if "|" in line and any(tag in line for tag in ("EN:", "FR:", "RW:")):
            parts = [p.strip() for p in line.split("|")]
            for part in parts:
                m = re.match(r"^(EN|FR|RW):\s*(.+)$", part, flags=re.IGNORECASE)
                if m:
                    counter += 1
                    corpus.append({
                        "id": f"{source}:{counter}",
                        "text": m.group(2),
                        "source": source,
                        "lang": m.group(1).lower(),
                    })
            return
        m = re.match(r"^(EN|FR|RW):\s*(.+)$", line, flags=re.IGNORECASE)
        lang_tag, text = (m.group(1).lower(), m.group(2)) if m else ("en", line)
        counter += 1
        corpus.append({"id": f"{source}:{counter}", "text": text, "source": source, "lang": lang_tag})

    for raw_line in brain_text.splitlines():
        add_line(raw_line, "brain.txt")

    for fname, content in knowledge_base.items():
        for raw_line in content.splitlines():
            add_line(raw_line, fname)

    return corpus
