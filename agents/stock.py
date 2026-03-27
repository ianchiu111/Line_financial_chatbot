import re
from typing import Dict, Any

import yfinance as yf
from langgraph.types import Command

from agents.base import BaseAgent


class StockAgent(BaseAgent):
    def __init__(self, llm_client=None):
        self.llm = llm_client.llm

    def fetch_stock_info(self, ticker: str) -> str:
        """
        Fetch current stock price and key metrics using yfinance.

        Args:
            ticker: Stock ticker symbol (e.g. "AAPL", "2330.TW", "00878.TW")

        Returns:
            Formatted string with price, change, market cap, P/E, and 52-week range.
        """
        ticker = ticker.strip().upper()

        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            name = info.get("longName") or info.get("shortName") or ticker
            current_price = info.get("currentPrice") or info.get("regularMarketPrice")
            previous_close = (
                info.get("previousClose") or info.get("regularMarketPreviousClose")
            )
            market_cap = info.get("marketCap")
            pe_ratio = info.get("trailingPE")
            week_52_high = info.get("fiftyTwoWeekHigh")
            week_52_low = info.get("fiftyTwoWeekLow")
            currency = info.get("currency", "")

            if current_price is None:
                raise ValueError(
                    f"[NO_DATA] No price data returned for '{ticker}'. "
                    "The ticker may be invalid or delisted."
                )

            change = (
                current_price - previous_close
                if previous_close is not None
                else None
            )
            change_pct = (
                (change / previous_close * 100)
                if change is not None and previous_close
                else None
            )

            lines = [f"\n📈 {name} ({ticker})"]
            lines.append(f"現價: {current_price:.2f} {currency}")

            if change is not None and change_pct is not None:
                sign = "+" if change >= 0 else ""
                lines.append(
                    f"漲跌: {sign}{change:.2f} ({sign}{change_pct:.2f}%)"
                )

            if week_52_high is not None and week_52_low is not None:
                lines.append(
                    f"52週區間: {week_52_low:.2f} - {week_52_high:.2f} {currency}"
                )

            if pe_ratio is not None:
                lines.append(f"本益比 (P/E): {pe_ratio:.2f}")

            if market_cap is not None:
                if market_cap >= 1e12:
                    cap_str = f"{market_cap / 1e12:.2f}T {currency}"
                elif market_cap >= 1e9:
                    cap_str = f"{market_cap / 1e9:.2f}B {currency}"
                else:
                    cap_str = f"{market_cap / 1e6:.2f}M {currency}"
                lines.append(f"市值: {cap_str}")

            return "\n".join(lines)

        except ValueError:
            raise
        except Exception as e:
            raise RuntimeError(
                f"[STOCK_FETCH_FAILED] Unable to fetch stock data for '{ticker}'.\n"
                f"  Reason: {e}\n"
                f"  Hint: Make sure the ticker is valid (e.g. AAPL, 2330.TW)."
            ) from e

    def run(self, state: Dict[str, Any]) -> Command:
        print(">>>>Stock Working<<<<")

        ticker = state.get("stock_ticker", "").strip()

        if not ticker:
            return Command(update={"stock_info": "⚠️ 無法辨識股票代號，請確認輸入格式（例如：AAPL、2330.TW）。"})

        try:
            stock_info = self.fetch_stock_info(ticker)
        except Exception as e:
            stock_info = f"⚠️ 查詢股票資料失敗：{e}"

        print("Stock info:", stock_info)
        return Command(update={"stock_info": stock_info})
