
import os, json, re
from typing import Dict, Any

import yfinance as yf
from langchain_core.messages import HumanMessage
from langchain_openai import AzureChatOpenAI
from langgraph.types import Command
from utils.openai_api_helper import LLMClient
from agents.base import BaseAgent

class CurrencyAgent(BaseAgent):
    def __init__(self, llm_client=None):
        self.llm = llm_client.llm

    def _stringify(self, obj: Any) -> str:
        """Pretty-print dict / list, otherwise str()."""
        if isinstance(obj, (dict, list)):
            return json.dumps(obj, ensure_ascii=False, indent=2)
        return str(obj)

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

    def fetch_exchange_rate(self, from_currency: str, to_currency: str) -> dict | None:
        """
        Fetch exchange rate between any two currencies.
        
        Args:
            from_currency: Base currency code (e.g., "USD", "TWD", "JPY")
            to_currency:   Target currency code (e.g., "TWD", "JPY", "EUR")
        
        Returns:
            dict with rate, and ticker info
        """
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()
        
        # !!! yfinance forex ticker format: "FROMTO=X"
        ticker_symbol = f"{from_currency}{to_currency}=X"
        
        try:
            ticker = yf.Ticker(ticker_symbol)
            rate = ticker.fast_info.last_price

            if rate is None:
                raise ValueError(f"[NO_DATA] '{ticker_symbol}' returned no price. "
                                 f"This pair may not be supported on Yahoo Finance. "
                                 f"Try reversing: '{to_currency}{from_currency}=X'.")

            rate = round(float(rate), 3)

            if rate <= 0:
                raise ValueError(f"[INVALID_RATE] '{ticker_symbol}' returned a non-positive rate: {rate}.")

        except ValueError:
            raise  # re-raise our own descriptive errors as-is

        except Exception as e:
            raise RuntimeError(
                f"[FETCH_FAILED] Failed to fetch '{ticker_symbol}' from Yahoo Finance.\n"
                f"  Reason: {e}\n"
                f"  Hint: Check your internet connection or run `pip install -U yfinance`."
            ) from e
        
        exchange_rate_info = f"\n目前 1 {from_currency} = {rate} {to_currency}。"
        print("Currency response:", exchange_rate_info)


        return {
            "from": from_currency,
            "to": to_currency,
            "rate": rate,                       
            "exchange_rate_info": exchange_rate_info     
        }

    def run(self, state: Dict[str, Any]) -> Command:
        """
        暫時不需要 Agent 介入
        """
        print(">>>>Currency Working<<<<")

        exchange_rate = self.fetch_exchange_rate(
            from_currency = state.get("_FROM_currency", ""),
            to_currency = state.get("_TO_currency", "")
        )

        update = {
            "exchange_rate_info": exchange_rate.get("exchange_rate_info", "")
        }
        return Command(update=update)
    