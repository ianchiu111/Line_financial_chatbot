import os
import time
from typing import List, Dict, Any, TypedDict

from langgraph.graph import StateGraph, END, START

from agents.base import BaseAgent
from agents.intent import IntentAgent
from agents.extract import ExtractAgent
from agents.currency import CurrencyAgent
from agents.term_explanation import TermExplanationAgent
from agents.summary import SummaryAgent
from utils.AI_utils.openai_api_helper import LLMClient

from dotenv import load_dotenv
load_dotenv(".env")


class AgentState(TypedDict, total=False):
    origin_query: str
    original_objective: List[str] # for checking user's objective
    objective: List[str]          # for agent routing
    response: str

    _FROM_currency: str
    _TO_currency: str
    financial_term_questions: List[str]

    exchange_rate_info: str
    taiwan_bank_rates: List[Dict[str, Any]]
    financial_term_answers: Dict[str, str]

def run_agent(query: str) -> None:
    llm = LLMClient()

    intent_agent = IntentAgent(llm_client=llm)
    extract_agent = ExtractAgent(llm_client=llm)
    currency_agent = CurrencyAgent(llm_client=llm)
    term_explanation_agent = TermExplanationAgent(llm_client=llm)
    summary_agent = SummaryAgent(llm_client=llm)

    def _intent_router(state: AgentState) -> str:
        print(state.get("objective"))
        if state.get("objective") != []:
            return "extract" 
        else:
            return "summary" 

    def _objective_router(state: AgentState):
        objectives = state.get("objective")
        current = objectives.pop(0) if objectives else "return"   

        if current == "currency_exchange_rate":
            print(f"Routing based on: {current}")
            return "currency"
        elif current == "financial_term_explanation":
            print(f"Routing based on: {current}")
            return "term_explanation"
        else:
            print("return to summary")
            return "summary"         

    graph = StateGraph(state_schema=AgentState)
    graph.add_node("intent", intent_agent)
    graph.add_node("extract", extract_agent)
    graph.add_node("currency", currency_agent)
    graph.add_node("term_explanation", term_explanation_agent)
    graph.add_node("summary", summary_agent)

    graph.add_edge(START, "intent")
    graph.add_conditional_edges("intent", _intent_router, ["extract", "summary"]) 
    graph.add_conditional_edges("extract", _objective_router, ["currency", "term_explanation", "summary"])
    graph.add_conditional_edges("currency", _objective_router, ["term_explanation", "summary"])
    graph.add_edge("term_explanation", "summary")
    graph.add_edge("summary", END)

    agent_graph = graph.compile()

    init_state: AgentState = {
        "origin_query": query,
        "original_objective": [],
        "objective": [],
        "response": "",

        "_FROM_currency": "",
        "_TO_currency": "",
        "financial_term_questions": [],

        "exchange_rate_info": "",
        "taiwan_bank_rates": [],
        "financial_term_answers": {}
    }

    result = agent_graph.invoke(init_state)

    print("\n=== Final Response ===\n", result)

    return result


# if __name__ == "__main__":
#     start_time = time.time()
#     # result = run_agent("現在美金換成台幣的匯率是多少") 
#     # result = run_agent("我想知道股息、股東個別是什麼") 
#     result = run_agent("現在美金換成台幣的匯率是多少，此外我想知道股息、股東是什麼") 

#     response = result.get("response", "")
#     taiwan_bank_rates = result.get("taiwan_bank_rates", [])
#     from_currency = result.get("_FROM_currency", [])
#     to_currency = result.get("_TO_currency", [])
    
#     print("\n=== Final Response ===\n")
#     print(taiwan_bank_rates)
#     print(response)
#     print(f"⏰ Total process time: {time.time()-start_time}")
