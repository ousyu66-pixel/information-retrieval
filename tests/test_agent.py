from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from agent import AstroRAGAgent
from retrieval import KnowledgeBase


class RetrievalTests(unittest.TestCase):
    def test_relationship_query_finds_venus_or_libra(self) -> None:
        kb = KnowledgeBase.from_json(ROOT / "data" / "astro_knowledge.json")
        results = kb.search("relationship love partnership", limit=5)
        titles = {hit.document.title for hit in results}
        self.assertTrue({"Venus Symbolism", "Libra / 天秤座"}.intersection(titles))

    def test_plural_normalization(self) -> None:
        kb = KnowledgeBase.from_json(ROOT / "data" / "astro_knowledge.json")
        results = kb.search("relationships", limit=3)
        matched = {term for hit in results for term in hit.matched_terms}
        self.assertIn("relationship", matched)

    def test_chinese_bazi_query_finds_bazi_context(self) -> None:
        kb = KnowledgeBase.from_json(ROOT / "data" / "astro_knowledge.json")
        results = kb.search("八字 五行 日主 学习", limit=5)
        titles = {hit.document.title for hit in results}
        self.assertTrue(any("八字" in title or "五行" in title or "日主" in title for title in titles))


class AgentTests(unittest.TestCase):
    def test_agent_runs_without_api_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = AstroRAGAgent(memory_path=Path(tmp) / "memory.json")
            agent.update_profile(sun_sign="Leo", focus="study")
            response = agent.answer("What should I focus on for study today?", target_date="2026-05-18")
            self.assertFalse(response.used_llm)
            self.assertIn("Retrieved context used", response.answer)
            self.assertGreaterEqual(len(response.tool_trace), 5)

    def test_agent_extracts_profile_from_chinese_chat(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = AstroRAGAgent(memory_path=Path(tmp) / "memory.json")
            response = agent.answer(
                "我的生日是2001年8月5日，我想关注学习、感情和八字五行。",
                target_date="2026-05-20",
            )
            profile = response.context["profile"]
            self.assertEqual(profile["birth_date"], "2001-08-05")
            self.assertEqual(profile["sun_sign"], "Leo")
            self.assertIn("study", profile["focus"])
            self.assertIn("relationship", profile["focus"])
            self.assertIn("bazi", profile["focus"])


if __name__ == "__main__":
    unittest.main()

