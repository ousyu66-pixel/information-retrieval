"""Persistent memory for personalization and conversation compaction."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from retrieval import tokenize


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class MemoryHit:
    text: str
    score: float
    created_at: str
    kind: str


class MemoryStore:
    """A file-backed memory store with profile, episodic memory, and summary."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(
                json.dumps(
                    {
                        "profile": {},
                        "summary": "",
                        "events": [],
                    },
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

    def read(self) -> dict[str, Any]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def write(self, data: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def profile(self) -> dict[str, Any]:
        return dict(self.read().get("profile", {}))

    def update_profile(self, **fields: str) -> dict[str, Any]:
        data = self.read()
        profile = data.setdefault("profile", {})
        for key, value in fields.items():
            if value:
                profile[key] = value
        profile["updated_at"] = utc_now()
        self.write(data)
        return dict(profile)

    def add_event(self, kind: str, text: str) -> None:
        data = self.read()
        events = data.setdefault("events", [])
        events.append({"kind": kind, "text": text, "created_at": utc_now()})
        if len(events) > 24:
            data["summary"] = self._compact(events, data.get("summary", ""))
            data["events"] = events[-12:]
        self.write(data)

    def search(self, query: str, limit: int = 4) -> list[MemoryHit]:
        data = self.read()
        query_terms = set(tokenize(query))
        hits: list[MemoryHit] = []
        for event in data.get("events", []):
            text = event.get("text", "")
            terms = set(tokenize(text))
            overlap = query_terms.intersection(terms)
            if overlap:
                score = len(overlap) / max(len(query_terms), 1)
                hits.append(
                    MemoryHit(
                        text=text,
                        score=round(score, 4),
                        created_at=event.get("created_at", ""),
                        kind=event.get("kind", "event"),
                    )
                )
        return sorted(hits, key=lambda hit: hit.score, reverse=True)[:limit]

    def summary(self) -> str:
        return self.read().get("summary", "")

    @staticmethod
    def _compact(events: list[dict[str, str]], previous_summary: str) -> str:
        recent = events[:-12]
        important = [
            event["text"]
            for event in recent
            if event.get("kind") in {"profile", "preference", "forecast"}
        ]
        compacted = " ".join(important[-10:])
        if previous_summary:
            return f"{previous_summary} {compacted}".strip()
        return compacted.strip()
