"""Small dependency-free retrieval utilities for the AstroRAG agent."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


TOKEN_RE = re.compile(r"[a-zA-Z0-9']+|[\u4e00-\u9fff]")
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "me",
    "my",
    "of",
    "on",
    "or",
    "should",
    "the",
    "to",
    "today",
    "what",
    "with",
    "我",
    "的",
    "在",
    "和",
    "也",
    "请",
    "应",
    "为",
    "作",
    "么",
    "什",
    "今",
    "天",
    "方",
    "面",
}
CHINESE_TERMS = (
    "八字",
    "五行",
    "日主",
    "用神",
    "十天干",
    "十二地支",
    "天干",
    "地支",
    "星座",
    "学习",
    "沟通",
    "感情",
    "关系",
    "事业",
    "记忆",
    "检索",
    "反思",
    "伦理",
)


def tokenize(text: str) -> list[str]:
    """Tokenize English words, known Chinese phrases, and Chinese characters."""
    lowered = text.lower()
    tokens = [term for term in CHINESE_TERMS if term in text]
    for raw_token in TOKEN_RE.findall(lowered):
        if re.fullmatch(r"[\u4e00-\u9fff]", raw_token):
            continue
        token = _normalize_token(raw_token)
        if token and token not in STOPWORDS:
            tokens.append(token)
    return tokens


def _normalize_token(token: str) -> str:
    token = token.lower()
    if token.isascii() and len(token) > 4 and token.endswith("ies"):
        return f"{token[:-3]}y"
    if token.isascii() and len(token) > 4 and token.endswith("s") and not token.endswith(("ss", "us", "is")):
        return token[:-1]
    return token


@dataclass(frozen=True)
class Document:
    id: str
    title: str
    category: str
    text: str
    tags: tuple[str, ...]
    source: str

    @property
    def searchable_text(self) -> str:
        return " ".join([self.title, self.category, self.text, " ".join(self.tags)])


@dataclass(frozen=True)
class SearchResult:
    document: Document
    score: float
    matched_terms: tuple[str, ...]


class KnowledgeBase:
    """A compact BM25-like retriever over local JSON documents."""

    def __init__(self, documents: list[Document]) -> None:
        self.documents = documents
        self._doc_tokens = [tokenize(doc.searchable_text) for doc in documents]
        self._doc_lengths = [len(tokens) for tokens in self._doc_tokens]
        self._avg_doc_len = sum(self._doc_lengths) / max(len(self._doc_lengths), 1)
        self._df = self._build_document_frequency(self._doc_tokens)

    @classmethod
    def from_json(cls, path: str | Path) -> "KnowledgeBase":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        docs = [
            Document(
                id=item["id"],
                title=item["title"],
                category=item["category"],
                text=item["text"],
                tags=tuple(item.get("tags", [])),
                source=item.get("source", "local knowledge base"),
            )
            for item in data["documents"]
        ]
        return cls(docs)

    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        query_terms = tokenize(query)
        if not query_terms:
            return []

        scores: list[SearchResult] = []
        for doc, tokens, doc_len in zip(self.documents, self._doc_tokens, self._doc_lengths):
            term_counts = self._term_counts(tokens)
            matched = sorted(set(query_terms).intersection(term_counts))
            if not matched:
                continue

            score = sum(self._bm25(term, term_counts.get(term, 0), doc_len) for term in set(query_terms))
            if score > 0:
                scores.append(SearchResult(doc, round(score, 4), tuple(matched)))

        return sorted(scores, key=lambda result: result.score, reverse=True)[:limit]

    def _bm25(self, term: str, frequency: int, doc_len: int) -> float:
        if frequency <= 0:
            return 0.0
        total_docs = len(self.documents)
        df = self._df.get(term, 0)
        idf = math.log(1 + (total_docs - df + 0.5) / (df + 0.5))
        k1 = 1.5
        b = 0.75
        denominator = frequency + k1 * (1 - b + b * doc_len / max(self._avg_doc_len, 1))
        return idf * (frequency * (k1 + 1)) / denominator

    @staticmethod
    def _build_document_frequency(doc_tokens: Iterable[list[str]]) -> dict[str, int]:
        df: dict[str, int] = {}
        for tokens in doc_tokens:
            for token in set(tokens):
                df[token] = df.get(token, 0) + 1
        return df

    @staticmethod
    def _term_counts(tokens: list[str]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for token in tokens:
            counts[token] = counts.get(token, 0) + 1
        return counts


