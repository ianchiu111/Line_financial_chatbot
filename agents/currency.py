
import csv
import io
import json
import re
import time
import random
from typing import List, Dict, Any

import yfinance as yf
import requests
from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from agents.base import BaseAgent

# Browser profile used by curl_cffi to impersonate a real browser TLS fingerprint.
# Update this string when a newer Chrome profile becomes available in curl_cffi.
_IMPERSONATE_BROWSER = "chrome136"

# Headers that mimic a real browser navigation request.
_BROWSER_HEADERS = {
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,image/apng,*/*;"
        "q=0.8,application/signed-exchange;v=b3;q=0.7"
    ),
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "max-age=0",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

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

    # ================= Functions to fetch bank rate comparison table information =================
    def fetch_taiwan_bank_rates(self, target_currency: str) -> list[dict]:
        """
        Fetch multi-bank Taiwan exchange rates comparison.
        """
        rates = self._fetch_fintechgo_rates(target_currency)
        return rates

    def _fetch_fintechgo_rates(self, target_currency: str) -> list[dict]:
        """
        Scrape real-time multi-bank rates from fintechgo.com.tw.
        """
        url = f"https://www.fintechgo.com.tw/FinInfo/ForexRate/BankRealExRate/Currency/{target_currency}"

        headers = {
            **_BROWSER_HEADERS,
            "Referer": "https://www.fintechgo.com.tw/",
            "Sec-Fetch-Site": "same-origin",
        }

        response = None
        last_status = None
        last_error = None

        for _ in range(3):
            try:
                # Use curl_cffi to impersonate a real Chrome browser TLS fingerprint,
                # bypassing Cloudflare/WAF blocks that reject cloud-datacenter IPs.
                response = cffi_requests.get(
                    url,
                    headers=headers,
                    impersonate=_IMPERSONATE_BROWSER,
                    timeout=15,
                )

                last_status = response.status_code

                if response.status_code == 200:
                    break

                time.sleep(1 + random.random())

            except cffi_requests.RequestException as e:
                last_error = e
                time.sleep(1 + random.random())
        else:
            if last_error:
                print(f"[fetch_taiwan_bank_rates] request exception: {last_error}")
            else:
                print(
                    f"[fetch_taiwan_bank_rates] request failed: "
                    f"fintechgo returned status={last_status} for {url}"
                )
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        rows = soup.find_all("div", class_="cc-div-table-row")

        rates = []

        def extract_rate(cell):
            spans = cell.find_all("span")
            for span in spans:
                text = span.get_text(strip=True)
                if text and text != "👍":
                    return text

            text = cell.get_text(" ", strip=True)
            return text if text else "--"

        for row in rows[1:]:
            cells = row.find_all("div", class_="cc-div-table-cell")
            if len(cells) < 5:
                continue

            rates.append({
                "bank": cells[0].get_text(strip=True),
                "spot_buy": extract_rate(cells[1]),
                "spot_sell": extract_rate(cells[2]),
                "cash_buy": extract_rate(cells[3]),
                "cash_sell": extract_rate(cells[4]),
            })

        return rates

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
        else:
            taiwan_bank_rates = []

        exchange_rate_info = self.fetch_exchange_rate(from_currency, to_currency)
        
        update = {
            "exchange_rate_info": exchange_rate_info,
            "taiwan_bank_rates": taiwan_bank_rates
        }
        return Command(update=update)
    