import os
import time
from typing import List, Dict, Any, TypedDict

from langgraph.graph import StateGraph, END, START

from agents.base import BaseAgent
from agents.intent import IntentAgent
from agents.extract import ExtractAgent
from agents.currency import CurrencyAgent
from agents.summary import SummaryAgent
from utils.openai_api_helper import LLMClient

from dotenv import load_dotenv
load_dotenv(".env")


class AgentState(TypedDict, total=False):
    origin_query: str
    objective: List[str]
    response: str
    _FROM_currency: str
    _TO_currency: str
    exchange_rate_info: str

def run_agent(query: str) -> None:
    llm = LLMClient()

    intent_agent = IntentAgent(llm_client=llm)
    extract_agent = ExtractAgent(llm_client=llm)
    currency_agent = CurrencyAgent(llm_client=llm)
    summary_agent = SummaryAgent(llm_client=llm)

    def _intent_router(state: AgentState) -> str:
        print(state.get("objective"))
        if "currency_exchange_rate" in state.get("objective"):
            return "extract" 
        else:
            return "summary"


    graph = StateGraph(state_schema=AgentState)
    graph.add_node("intent", intent_agent)
    graph.add_node("extract", extract_agent)
    graph.add_node("currency", currency_agent)
    graph.add_node("summary", summary_agent)

    graph.add_edge(START, "intent")
    graph.add_conditional_edges("intent", _intent_router, ["extract", "summary"]) 
    graph.add_edge("extract", "currency")
    graph.add_edge("currency", "summary")
    graph.add_edge("summary", END)

    agent_graph = graph.compile()

    init_state: AgentState = {
        "origin_query": query,
        "next_action": "",
        "response": "",
        "_FROM_currency": "",
        "_TO_currency": "",
        "exchange_rate_info": ""
    }

    result = agent_graph.invoke(init_state)
    response = result.get("response", "")

    return response


# if __name__ == "__main__":
#     start_time = time.time()
#     response = run_agent("現在美金換成台幣的匯率是多少") 
    
#     print("\n=== Final Response ===\n")
#     print(response)
#     print(f"⏰ Total process time: {time.time()-start_time}")
