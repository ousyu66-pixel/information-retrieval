"""Horoscope and BaZi agent: retrieval planning, tool use, and answer synthesis."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from llm import LLMConfig, OpenAICompatibleClient
from memory import MemoryStore
from retrieval import KnowledgeBase
from tools import AstroTools, ToolCall


ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class AgentResponse:
    answer: str
    context: dict
    tool_trace: list[ToolCall]
    used_llm: bool


class HoroscopeMemoryAgent:
    """An IR-augmented astrology agent built to make retrieval visible."""

    def __init__(
        self,
        knowledge_path: Path | None = None,
        memory_path: Path | None = None,
        transit_path: Path | None = None,
    ) -> None:
        self.knowledge_path = knowledge_path or ROOT / "data" / "astro_knowledge.json"
        self.memory_path = memory_path or ROOT / "memory" / "user_memory.json"
        self.transit_path = transit_path or ROOT / "data" / "transits_2026.json"
        self.memory = MemoryStore(self.memory_path)
        self.kb = KnowledgeBase.from_json(self.knowledge_path)
        self.tools = AstroTools(self.kb, self.memory, self.transit_path)

    def update_profile(self, **fields: str) -> dict:
        return self.tools.save_user_profile(**fields)

    def answer(self, question: str, target_date: str | None = None) -> AgentResponse:
        self.tools.reset_trace()
        inferred_profile = self._extract_profile_from_text(question)
        if inferred_profile:
            self.tools.save_user_profile(**inferred_profile)
        profile = self.tools.get_user_profile()
        enriched_query = self._build_retrieval_query(question, profile)
        knowledge = self.tools.search_astro_knowledge(enriched_query, limit=6)
        memory_hits = self.tools.retrieve_user_memory(question, limit=4)
        temporal = self.tools.get_temporal_context(target_date)
        summary = self.memory.summary()
        context = {
            "profile": profile,
            "memory_summary": summary,
            "memory_hits": memory_hits,
            "knowledge": knowledge,
            "temporal_context": temporal,
        }

        config = LLMConfig.from_env()
        if config:
            answer = self._generate_with_llm(question, context, config)
            used_llm = True
        else:
            answer = self._offline_answer(question, context)
            used_llm = False

        self.tools.save_forecast(question, answer)
        return AgentResponse(
            answer=answer,
            context=context,
            tool_trace=list(self.tools.calls),
            used_llm=used_llm,
        )

    @staticmethod
    def _extract_profile_from_text(text: str) -> dict[str, str]:
        fields: dict[str, str] = {}

        birth_match = re.search(
            r"(?:birthday|birth date|生日|出生日期|出生).*?(\d{4})[-/.年](\d{1,2})[-/.月](\d{1,2})",
            text,
            re.IGNORECASE,
        )
        if birth_match:
            year, month, day = (int(part) for part in birth_match.groups())
            fields["birth_date"] = f"{year:04d}-{month:02d}-{day:02d}"
            fields["sun_sign"] = HoroscopeMemoryAgent._sun_sign_from_month_day(month, day)

        sign_aliases = {
            "白羊": "Aries",
            "金牛": "Taurus",
            "双子": "Gemini",
            "巨蟹": "Cancer",
            "狮子": "Leo",
            "处女": "Virgo",
            "天秤": "Libra",
            "天蝎": "Scorpio",
            "射手": "Sagittarius",
            "摩羯": "Capricorn",
            "水瓶": "Aquarius",
            "双鱼": "Pisces",
        }
        for chinese, english in sign_aliases.items():
            if f"太阳{chinese}" in text or f"我是{chinese}" in text:
                fields.setdefault("sun_sign", english)
            if f"月亮{chinese}" in text:
                fields["moon_sign"] = english
            if f"上升{chinese}" in text:
                fields["rising_sign"] = english

        focus_terms = []
        for keyword, normalized in {
            "学习": "study",
            "考试": "study",
            "论文": "study",
            "沟通": "communication",
            "感情": "relationship",
            "恋爱": "relationship",
            "关系": "relationship",
            "事业": "career",
            "工作": "career",
            "健康": "health",
            "八字": "bazi",
            "五行": "bazi",
        }.items():
            if keyword in text and normalized not in focus_terms:
                focus_terms.append(normalized)
        if focus_terms:
            fields["focus"] = ",".join(focus_terms)

        return fields

    @staticmethod
    def _sun_sign_from_month_day(month: int, day: int) -> str:
        boundaries = [
            ((1, 20), "Aquarius"),
            ((2, 19), "Pisces"),
            ((3, 21), "Aries"),
            ((4, 20), "Taurus"),
            ((5, 21), "Gemini"),
            ((6, 21), "Cancer"),
            ((7, 23), "Leo"),
            ((8, 23), "Virgo"),
            ((9, 23), "Libra"),
            ((10, 23), "Scorpio"),
            ((11, 22), "Sagittarius"),
            ((12, 22), "Capricorn"),
        ]
        for (boundary_month, boundary_day), sign in reversed(boundaries):
            if (month, day) >= (boundary_month, boundary_day):
                return sign
        return "Capricorn"

    @staticmethod
    def _build_retrieval_query(question: str, profile: dict) -> str:
        profile_terms = " ".join(
            str(value)
            for key, value in profile.items()
            if key in {"sun_sign", "moon_sign", "rising_sign", "focus", "birth_date"}
        )
        return f"{question} {profile_terms}".strip()

    @staticmethod
    def _generate_with_llm(question: str, context: dict, config: LLMConfig) -> str:
        client = OpenAICompatibleClient(config)
        system = (
            "You are a Horoscope and BaZi Memory Retrieval Agent. "
            "Use only the provided retrieved context, user memory, and temporal data. "
            "Be clear that astrology is reflective entertainment, not factual prediction. "
            "Cite context by title when useful. End with a short 'Retrieved context used' section."
        )
        user = (
            f"User question:\n{question}\n\n"
            f"Retrieved context JSON:\n{json.dumps(context, ensure_ascii=False, indent=2)}"
        )
        return client.chat(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.45,
        )

    @staticmethod
    def _offline_answer(question: str, context: dict) -> str:
        profile = context["profile"]
        sign = profile.get("sun_sign", "your sign")
        focus = profile.get("focus", "the topic you care about")
        top_docs = context["knowledge"][:3]
        exact_events = context["temporal_context"].get("exact_events", [])
        nearby_events = context["temporal_context"].get("nearby_events", [])
        lines = [
            "Offline retrieval preview: set OPENAI_API_KEY for full model synthesis.",
            "",
            f"Question: {question}",
            f"Personal context: sun sign={sign}, focus={focus}.",
            "",
            "Retrieved interpretation:",
        ]
        if top_docs:
            for doc in top_docs:
                lines.append(f"- {doc['title']}: {doc['text']}")
        else:
            lines.append("- No strong knowledge matches were found.")

        if exact_events:
            lines.append("")
            lines.append("Temporal context for today:")
            for event in exact_events:
                lines.append(f"- {event['title']}: {event['meaning']}")
        elif nearby_events:
            lines.append("")
            lines.append("Nearby temporal context:")
            for event in nearby_events[:3]:
                lines.append(f"- {event['date']} {event['title']}: {event['meaning']}")

        lines.extend(
            [
                "",
                "Retrieved context used:",
                ", ".join(doc["title"] for doc in top_docs) or "none",
            ]
        )
        return "\n".join(lines)
