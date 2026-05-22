"""Command line interface for the Horoscope and BaZi Memory Retrieval Agent."""

from __future__ import annotations

import argparse
import json
from typing import Any

from agent import HoroscopeMemoryAgent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Horoscope and BaZi Memory Retrieval Agent")
    parser.add_argument("--ask", help="Ask the agent a question")
    parser.add_argument("--date", help="Target date in YYYY-MM-DD format")
    parser.add_argument("--trace", action="store_true", help="Show tool calls and retrieved context")
    parser.add_argument("--profile", action="append", default=[], help="Set profile field, e.g. sun_sign=Leo")
    return parser


def parse_profile(items: list[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"Invalid --profile value: {item}. Use key=value.")
        key, value = item.split("=", 1)
        fields[key.strip()] = value.strip()
    return fields


def print_trace(response: Any) -> None:
    print("\n=== Tool trace ===")
    for index, call in enumerate(response.tool_trace, start=1):
        print(f"{index}. {call.name}({json.dumps(call.arguments, ensure_ascii=False)})")
    print("\n=== Retrieved context ===")
    print(json.dumps(response.context, ensure_ascii=False, indent=2))


def interactive(agent: HoroscopeMemoryAgent) -> None:
    print("Horoscope and BaZi Memory Retrieval Agent. Type 'exit' to quit.")
    while True:
        question = input("\nAsk> ").strip()
        if question.lower() in {"exit", "quit"}:
            return
        if not question:
            continue
        response = agent.answer(question)
        print("\n" + response.answer)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    agent = HoroscopeMemoryAgent()

    profile_fields = parse_profile(args.profile)
    if profile_fields:
        profile = agent.update_profile(**profile_fields)
        print("Updated profile:")
        print(json.dumps(profile, ensure_ascii=False, indent=2))

    if args.ask:
        response = agent.answer(args.ask, target_date=args.date)
        print(response.answer)
        if args.trace:
            print_trace(response)
    elif not profile_fields:
        interactive(agent)


if __name__ == "__main__":
    main()
