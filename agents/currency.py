
import os, json, re
from typing import List, Dict, Any

import yfinance as yf
import requests
from bs4 import BeautifulSoup
from langchain_core.messages import HumanMessage
from langchain_openai import AzureChatOpenAI
from langgraph.types import Command
from utils.AI_utils.openai_api_helper import LLMClient
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

    def fetch_exchange_rate(self, from_currency: str, to_currency: str) -> str:
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


        return exchange_rate_info     

    def fetch_taiwan_bank_rates(self, target_currency: str) -> str:
        """
        compare different banks
        url: https://www.fintechgo.com.tw/FinInfo/ForexRate/BankRealExRate/Currency/USD
        """        
    
        url = f"https://www.fintechgo.com.tw/FinInfo/ForexRate/BankRealExRate/Currency/{target_currency}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
            "Referer": "https://www.fintechgo.com.tw/",
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        rows = soup.find_all("div", class_="cc-div-table-row")

        print("aaaaaaaaa", rows)
        
        taiwan_bank_rates: List[Dict[str, Any]] = []
        for row in rows[1:]:  # Skip header row
            cells = row.find_all("div", class_="cc-div-table-cell")
            if len(cells) < 5:
                continue
            
            # Bank name (remove code like "(004)")
            bank_name = cells[0].get_text(strip=True)
            
            # Get rate values — each cell has inner spans
            def get_rate(cell):
                spans = cell.find_all("span", style=lambda s: s and "table-cell" in s)
                # Second span has the actual number
                for span in spans:
                    text = span.get_text(strip=True)
                    if text and text != "👍":
                        return text
                return "--"
            
            spot_buy  = get_rate(cells[1])
            spot_sell = get_rate(cells[2])
            cash_buy  = get_rate(cells[3])
            cash_sell = get_rate(cells[4])
            
            taiwan_bank_rates.append({
                "bank": bank_name,      # bank name
                "spot_buy": spot_buy,   # 即期匯率(買入)
                "spot_sell": spot_sell, # 即期匯率(賣出)
                "cash_buy": cash_buy,   # 現金匯率(買入)
                "cash_sell": cash_sell, # 現金匯率(賣出)
            })

        return taiwan_bank_rates

    def run(self, state: Dict[str, Any]) -> Command:
        print(">>>>Currency Working<<<<")
        
        from_currency = state.get("_FROM_currency", "")
        to_currency = state.get("_TO_currency", "")
        
        SUPPORTED_CURRENCIES = [
            "TWD", "USD", "EUR", "JPY", "GBP", "AUD",
            "CAD", "HKD", "CNY", "NZD", "ZAR",
        ]

        # Use Taiwan bank rates if converting to TWD
        if "TWD" in (from_currency, to_currency):
            if from_currency in SUPPORTED_CURRENCIES and to_currency.upper() in SUPPORTED_CURRENCIES:
                if from_currency == "TWD":
                    target_currency = to_currency
                else:
                    target_currency = from_currency

                taiwan_bank_rates = self.fetch_taiwan_bank_rates(target_currency=target_currency)

        exchange_rate_info = self.fetch_exchange_rate(from_currency, to_currency)
        
        update = {
            "exchange_rate_info": exchange_rate_info,
            "taiwan_bank_rates": taiwan_bank_rates
        }
        return Command(update=update)
    