"""
Winter AI -- Retrieval Engine.

Pure-Python TF-IDF + cosine similarity search over the whole knowledge base
(no external ML dependencies -- runs anywhere Python runs). This also owns
loading the knowledge base from disk: the curated files in api/info/, plus
anything the user drops into api/inf/teach/ (the "teach Winter something new"
folder), and exposes a reload() so new files can be picked up without a
restart.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

TOKEN_RE = re.compile(r"[a-zà-ÿ0-9']+")
LANG_LINE_RE = re.compile(r"^(EN|FR|RW):\s*(.+)$", re.IGNORECASE)

# Generic function words filtered out of the TF-IDF vectors. Without this, a
# short line like "what is your name" can outscore a long, genuinely
# on-topic answer just because "what"/"is" are a bigger share of its tiny
# vector -- classic short-document bias in raw cosine similarity.
STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "what", "who", "whom", "which", "how", "why", "when", "where",
    "do", "does", "did", "to", "of", "in", "on", "at", "for", "with",
    "and", "or", "but", "i", "you", "your", "me", "my", "it", "this",
    "that", "these", "those", "can", "could", "will", "would", "should",
    "le", "la", "les", "de", "du", "des", "et", "que", "qui", "est",
    "ni", "na", "ku", "mu",
}


def tokenize(text: str) -> list[str]:
    return [t for t in TOKEN_RE.findall(text.lower()) if t not in STOPWORDS]


@dataclass
class Document:
    doc_id: str
    text: str
    source: str
    lang: str = "en"
    tf: Counter = field(default_factory=Counter)


class TfIdfIndex:
    """A small but real TF-IDF vector space model with cosine similarity."""

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
        self.docs.append(Document(doc_id, text, source, lang, tf))
        for term in tf:
            self.df[term] += 1
        self._idf_cache = {}

    def idf(self, term: str) -> float:
        if term not in self._idf_cache:
            n_docs = len(self.docs) or 1
            df = self.df.get(term, 0)
            self._idf_cache[term] = math.log((1 + n_docs) / (1 + df)) + 1.0
        return self._idf_cache[term]

    def _norm(self, tf: Counter) -> float:
        return math.sqrt(sum((c * self.idf(t)) ** 2 for t, c in tf.items())) or 1.0

    def search(self, query: str, top_k: int = 5) -> list[tuple[float, Document]]:
        query_tf = Counter(tokenize(query))
        if not query_tf or not self.docs:
            return []
        q_norm = self._norm(query_tf)
        scored = []
        for doc in self.docs:
            dot = sum((q_count * self.idf(t)) * (doc.tf[t] * self.idf(t))
                      for t, q_count in query_tf.items() if t in doc.tf)
            if dot == 0:
                continue
            scored.append((dot / (q_norm * self._norm(doc.tf)), doc))
        scored.sort(key=lambda p: p[0], reverse=True)
        return scored[:top_k]


def _add_line(index: TfIdfIndex, line: str, source: str, counter: list[int]) -> None:
    line = line.strip()
    if not line or line.startswith("#"):
        return
    if "|" in line and any(tag in line.upper() for tag in ("EN:", "FR:", "RW:")):
        for part in (p.strip() for p in line.split("|")):
            m = LANG_LINE_RE.match(part)
            if m:
                counter[0] += 1
                index.add_document(f"{source}:{counter[0]}", m.group(2), source, m.group(1).lower())
        return
    m = LANG_LINE_RE.match(line)
    lang_tag, text = (m.group(1).lower(), m.group(2)) if m else ("en", line)
    counter[0] += 1
    index.add_document(f"{source}:{counter[0]}", text, source, lang_tag)


class KnowledgeIndex:
    """Owns knowledge-file loading (curated + user-taught) and search."""

    def __init__(self, info_dir: Path, teach_dir: Path):
        self.info_dir = info_dir
        self.teach_dir = teach_dir
        self.index = TfIdfIndex()
        self.loaded_files: dict[str, int] = {}  # filename -> line count
        self._primary_corpus_path: Path | None = None

    def reload(self) -> dict:
        self.index.clear()
        self.loaded_files = {}
        counter = [0]

        self.info_dir.mkdir(parents=True, exist_ok=True)
        self.teach_dir.mkdir(parents=True, exist_ok=True)

        merged_lines: list[str] = []

        for folder, tag in ((self.info_dir, "info"), (self.teach_dir, "teach")):
            for path in sorted(folder.rglob("*")):
                if not path.is_file() or path.suffix.lower() not in (".txt", ".md"):
                    continue
                try:
                    content = path.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue
                source_name = f"{tag}/{path.relative_to(folder)}"
                lines = content.splitlines()
                self.loaded_files[source_name] = len(lines)
                for raw_line in lines:
                    _add_line(self.index, raw_line, source_name, counter)
                    if raw_line.strip():
                        merged_lines.append(raw_line.strip())

        # Write a merged flat corpus file the Common Lisp layer can read
        # directly. This MUST live outside info_dir/teach_dir -- otherwise
        # the next reload() would scan its own output back in as a "new"
        # knowledge file and duplicate every fact on every reload.
        cache_dir = self.info_dir.parent / ".cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        merged_path = cache_dir / "merged_corpus.txt"
        try:
            merged_path.write_text("\n".join(merged_lines), encoding="utf-8")
            self._primary_corpus_path = merged_path
        except Exception:
            self._primary_corpus_path = None

        return {"files": self.loaded_files, "documents": len(self.index.docs)}

    def primary_corpus_path(self) -> Path | None:
        return self._primary_corpus_path

    def search(self, query: str, lang: str | None = None, top_k: int = 5) -> list[dict]:
        results = self.index.search(query, top_k=top_k * 2)
        if lang:
            preferred = [r for r in results if r[1].lang == lang]
            if preferred:
                results = preferred
        return [
            {"line": doc.text, "source": doc.source, "score": round(score, 4), "lang": doc.lang}
            for score, doc in results[:top_k]
        ]
