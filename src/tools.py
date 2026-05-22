"""Agent tools used for information retrieval and personalization actions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from memory import MemoryStore
from retrieval import KnowledgeBase


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any]
    result: Any


class AstroTools:
    """A small, inspectable tool layer for the agent."""

    def __init__(
        self,
        knowledge_base: KnowledgeBase,
        memory_store: MemoryStore,
        transit_path: str | Path,
    ) -> None:
        self.knowledge_base = knowledge_base
        self.memory_store = memory_store
        self.transit_path = Path(transit_path)
        self.calls: list[ToolCall] = []

    def reset_trace(self) -> None:
        self.calls = []

    def get_user_profile(self) -> dict[str, Any]:
        result = self.memory_store.profile()
        self._record("get_user_profile", {}, result)
        return result

    def save_user_profile(self, **fields: str) -> dict[str, Any]:
        result = self.memory_store.update_profile(**fields)
        self.memory_store.add_event("profile", f"Updated profile fields: {fields}")
        self._record("save_user_profile", fields, result)
        return result

    def search_astro_knowledge(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        results = [
            {
                "id": hit.document.id,
                "title": hit.document.title,
                "category": hit.document.category,
                "text": hit.document.text,
                "source": hit.document.source,
                "score": hit.score,
                "matched_terms": list(hit.matched_terms),
            }
            for hit in self.knowledge_base.search(query, limit)
        ]
        self._record("search_astro_knowledge", {"query": query, "limit": limit}, results)
        return results

    def retrieve_user_memory(self, query: str, limit: int = 4) -> list[dict[str, Any]]:
        hits = [
            {
                "kind": hit.kind,
                "text": hit.text,
                "score": hit.score,
                "created_at": hit.created_at,
            }
            for hit in self.memory_store.search(query, limit)
        ]
        self._record("retrieve_user_memory", {"query": query, "limit": limit}, hits)
        return hits

    def get_temporal_context(self, target_date: str | None = None) -> dict[str, Any]:
        target = target_date or date.today().isoformat()
        data = json.loads(self.transit_path.read_text(encoding="utf-8"))
        exact = [item for item in data["events"] if item["date"] == target]
        weekly = [item for item in data["events"] if item["date"][:7] == target[:7]][:8]
        result = {"date": target, "exact_events": exact, "nearby_events": weekly}
        self._record("get_temporal_context", {"target_date": target}, result)
        return result

    def save_forecast(self, question: str, answer: str) -> None:
        self.memory_store.add_event("forecast", f"Q: {question}\nA: {answer[:800]}")
        self._record("save_forecast", {"question": question}, "saved")

    def _record(self, name: str, arguments: dict[str, Any], result: Any) -> None:
        self.calls.append(ToolCall(name=name, arguments=arguments, result=result))
