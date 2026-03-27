
import json, re
from typing import Dict, Any

from langchain_core.messages import HumanMessage
from langgraph.types import Command
from agents.base import BaseAgent
from agents.prompts import get_extractAgent_prompt

class ExtractAgent(BaseAgent):
    def __init__(self, llm_client=None):
        self.llm = llm_client.llm

    def _safe_parse_json(self, text: str) -> dict:
        if isinstance(text, dict):
            return text
        if not text or not isinstance(text, str):
            return {}
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            cleaned = re.sub(r"```json|```", "", text).strip()
            m = re.search(r"\{[\s\S]*\}", cleaned)
            if m:
                try:
                    return json.loads(m.group())
                except json.JSONDecodeError as e:
                    print(f"fallback decode error: {e}\nOrigin Content: {text}")
                    return {}
            else:
                print(f"無法找到 json object, Origin Content: {text}")
                return {}

    def run(self, state: Dict[str, Any]) -> Command:
        print(">>>>Extract Working<<<<")
        prompt = get_extractAgent_prompt(
            origin_query=state.get("origin_query", ""),
            objective=state.get("objective", []),
        )
        response = self.llm.invoke([HumanMessage(content=prompt)])

        content = self._safe_parse_json(response.content)
        _FROM_currency = content.get("_FROM_currency", "unknown")
        _TO_currency = content.get("_TO_currency", "unknown")

        # New fields — default safely if absent or wrong type
        try:
            amount_to_exchange = float(content.get("amount_to_exchange") or 0)
        except (TypeError, ValueError):
            amount_to_exchange = 0.0

        try:
            history_days = int(content.get("history_days") or 7)
        except (TypeError, ValueError):
            history_days = 7

        stock_ticker = str(content.get("stock_ticker") or "").strip()

        update = {
            "_FROM_currency": _FROM_currency,
            "_TO_currency": _TO_currency,
            "amount_to_exchange": amount_to_exchange,
            "history_days": history_days,
            "stock_ticker": stock_ticker,
        }
        return Command(update=update)

    