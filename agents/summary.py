
import json, re
from typing import Dict, Any

from langchain_core.messages import HumanMessage
from langgraph.types import Command
from agents.base import BaseAgent
from agents.prompts import get_summaryAgent_prompt

class SummaryAgent(BaseAgent):
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
        print(">>>>Summary Working<<<<")
        prompt = get_summaryAgent_prompt(
            origin_query = state.get("origin_query", ""),
            objective = state.get("objective", []),
            exchange_rate_info = state.get("exchange_rate_info", ""),
        )
        response = self.llm.invoke([HumanMessage(content=prompt)])

        # content = self._safe_parse_json(response.content)
        content = response.content
        print(f"content: {content}")

        update = {
            "response": content or "",
        }
        return Command(update=update)
