"""
Winter AI - Retrieval Engine
Pure-Python TF-IDF + cosine similarity search over the knowledge base.
No external ML dependencies required (CPU-only, no terminal / no internet needed).
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field


TOKEN_RE = re.compile(r"[a-zà-ÿ0-9']+")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


@dataclass
class Document:
    doc_id: str
    text: str
    source: str
    lang: str = "en"
    tf: Counter = field(default_factory=Counter)


class Retriever:
    """A minimal but real TF-IDF vector space model.

    Each line of the knowledge base becomes a searchable document.
    At query time we compute cosine similarity between the query vector
    and every document vector, weighted by inverse document frequency.
    This gives Winter genuine ranked semantic-ish retrieval instead of
    naive substring counting.
    """

    def __init__(self) -> None:
        self.docs: list[Document] = []
        self.df: Counter = Counter()
        self._idf_cache: dict[str, float] = {}

    def clear(self) -> None:
        self.docs = []
        self.df = Counter()
        self._idf_cache = {}

    def add_document(self, doc_id: str, text: str, source: str, lang: str = "en") -> None:
        tf = Counter(tokenize(text))
        if not tf:
            return
        doc = Document(doc_id=doc_id, text=text, source=source, lang=lang, tf=tf)
        self.docs.append(doc)
        for term in tf:
            self.df[term] += 1
        self._idf_cache = {}

    def index_corpus(self, corpus: list[dict]) -> None:
        """corpus: list of {id, text, source, lang}"""
        self.clear()
        for entry in corpus:
            self.add_document(entry["id"], entry["text"], entry["source"], entry.get("lang", "en"))

    def idf(self, term: str) -> float:
        if term not in self._idf_cache:
            n_docs = len(self.docs) or 1
            df = self.df.get(term, 0)
            self._idf_cache[term] = math.log((1 + n_docs) / (1 + df)) + 1.0
        return self._idf_cache[term]

    def _vector_norm(self, tf: Counter) -> float:
        return math.sqrt(sum((count * self.idf(term)) ** 2 for term, count in tf.items())) or 1.0

    def score(self, query_tf: Counter, doc: Document, q_norm: float) -> float:
        dot = 0.0
        for term, q_count in query_tf.items():
            if term in doc.tf:
                dot += (q_count * self.idf(term)) * (doc.tf[term] * self.idf(term))
        d_norm = self._vector_norm(doc.tf)
        if dot == 0:
            return 0.0
        return dot / (q_norm * d_norm)

    def search(self, query: str, top_k: int = 5) -> list[tuple[float, Document]]:
        query_tf = Counter(tokenize(query))
        if not query_tf or not self.docs:
            return []
        q_norm = self._vector_norm(query_tf)
        scored = [(self.score(query_tf, doc, q_norm), doc) for doc in self.docs]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [pair for pair in scored[:top_k] if pair[0] > 0]

    def best_match(self, query: str, lang: str | None = None) -> tuple[float, Document | None]:
        results = self.search(query, top_k=8)
        if lang:
            # Prefer documents tagged with the requested language, without
            # discarding good generic matches entirely.
            preferred = [r for r in results if r[1].lang == lang]
            if preferred:
                return preferred[0]
        if results:
            return results[0]
        return (0.0, None)


def build_corpus_from_knowledge(brain_text: str, knowledge_base: dict[str, str]) -> list[dict]:
    """Turn brain.txt + the info/*.txt knowledge files into a flat, searchable corpus.

    Lines following the pattern `EN: ... | FR: ... | RW: ...` are split into
    three separate language-tagged documents so retrieval can prefer the
    user's active language.
    """
    corpus: list[dict] = []
    counter = 0

    def add_line(line: str, source: str) -> None:
        nonlocal counter
        line = line.strip()
        if not line:
            return
        # Trilingual pipe-delimited line
        if "|" in line and any(tag in line for tag in ("EN:", "FR:", "RW:")):
            parts = [p.strip() for p in line.split("|")]
            for part in parts:
                m = re.match(r"^(EN|FR|RW):\s*(.+)$", part, flags=re.IGNORECASE)
                if m:
                    lang_tag = m.group(1).lower()
                    text = m.group(2)
                    counter += 1
                    corpus.append({
                        "id": f"{source}:{counter}",
                        "text": text,
                        "source": source,
                        "lang": lang_tag,
                    })
            return
        # Single language-tagged line: "EN: text"
        m = re.match(r"^(EN|FR|RW):\s*(.+)$", line, flags=re.IGNORECASE)
        if m:
            lang_tag = m.group(1).lower()
            text = m.group(2)
        else:
            lang_tag = "en"
            text = line
        counter += 1
        corpus.append({"id": f"{source}:{counter}", "text": text, "source": source, "lang": lang_tag})

    for raw_line in brain_text.splitlines():
        add_line(raw_line, "brain.txt")

    for fname, content in knowledge_base.items():
        for raw_line in content.splitlines():
            add_line(raw_line, fname)

    return corpus
