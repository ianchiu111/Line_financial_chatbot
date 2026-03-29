import json, re
from typing import Dict, Any, List

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from agents.base import BaseAgent

from utils.RAG.ask_financail_question import ask_question

class TermExplanationAgent(BaseAgent):
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
        print(">>>>Term Explanation Working<<<<")

        question_list : List[str] = state.get("financial_term_questions")
        answer_list : Dict[str, str] = {}

        for question in question_list:
            result = ask_question(question)
            print("=" * 80)
            print("Financial Question:", question)
            print("RAG Response:")
            print(result)
            print("=" * 80)

            answer_list[question] = result

        update = {
            "financial_term_answers": answer_list,
        }
        return Command(update=update)
