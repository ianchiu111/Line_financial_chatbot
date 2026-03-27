
# Welcome
This project conducts a Line Chatbot to solve users' financial questions.

## Chatbot Abilities

### Currency
1. Real-time currency exchange rate
2. Bank rate comparison
3. **[NEW] Historical exchange rate trend** — 7-day or 30-day trend for any currency pair
4. **[NEW] Best exchange amount calculator** — rank Taiwan banks by the best deal for a specific amount

### Stock
1. **[NEW] Stock price query** — current price, change, market cap, P/E ratio, and 52-week range for any listed stock

### Present
<img src="images/present.png" alt="image" width="300"/>


## New Features — Proof of Concept (POC)

### 🆕 Feature 1: Historical Exchange Rate Trend (`currency_history`)

**What it does:** Shows the exchange rate movement over the past 7 or 30 days for any currency pair. Useful for users deciding _when_ to exchange.

**How to trigger:** Ask about a currency pair's recent trend.

| Example Query | Language |
|---|---|
| `美金兌台幣最近7天走勢如何？` | Traditional Chinese |
| `What is the USD/TWD trend over the past 30 days?` | English |
| `日圓最近一個月的匯率變化？` | Traditional Chinese |

**Expected Response:**
```
📊 USD/TWD 近 7 天匯率走勢
目前匯率：32.3500
區間最高：32.6200
區間最低：32.1800
7 天漲跌：+0.45%（📈 上漲）

近一週美元走強，若有換匯需求建議盡快操作，避免成本增加。
```

**How it works:**
- Uses `yfinance` to fetch OHLC data for the forex ticker (e.g. `USDTWD=X`).
- Calculates: current rate, period high/low, and % change from the first to the last close.
- The new `CurrencyAgent.fetch_currency_history()` helper method powers this feature.
- Graph path: `intent → extract → currency → summary`

---

### 🆕 Feature 2: Best Exchange Amount Calculator (`currency_best_amount`)

**What it does:** Given a specific amount to exchange (e.g. USD 10,000 → TWD), calculates how much each Taiwan bank would give you and ranks them from best to worst. Helps users maximise the amount received.

**How to trigger:** Mention a concrete amount and ask which bank is best.

| Example Query | Language |
|---|---|
| `我想換10000美金到台幣，哪家銀行最划算？` | Traditional Chinese |
| `Which bank gives the best rate to exchange 5000 USD to TWD?` | English |
| `換5萬台幣的日圓哪家銀行最好？` | Traditional Chinese |

**Expected Response:**
```
💱 10,000 USD → TWD 各銀行試算
🥇 台灣銀行：323,850.00 TWD（匯率 30.855）
🥈 兆豐銀行：323,500.00 TWD（匯率 30.882）
🥉 第一銀行：323,200.00 TWD（匯率 30.910）
4. 合作金庫：323,000.00 TWD（匯率 30.930）
5. 永豐銀行：322,700.00 TWD（匯率 30.960）

建議前往台灣銀行換匯，可多得約 1,150 TWD！
```

**How it works:**
- Reuses the existing `fetch_taiwan_bank_rates()` scraper (fintechgo.com.tw).
- The new `CurrencyAgent.calculate_best_exchange_amount()` helper applies the correct rate type:
  - Buying foreign (TWD → foreign): bank's **sell rate** is used.
  - Selling foreign (foreign → TWD): bank's **buy rate** is used.
- Banks are ranked by the converted amount received (higher is better).
- Graph path: `intent → extract → currency → summary`

---

### 🆕 Feature 3: Stock Price Query (`stock_price`)

**What it does:** Fetches the current stock price and key metrics (price change, 52-week range, P/E ratio, market cap) for any listed company — both Taiwan-listed (`.TW`) and US-listed stocks.

**How to trigger:** Ask about a stock's current price or performance.

| Example Query | Language |
|---|---|
| `台積電現在股價多少？` | Traditional Chinese |
| `AAPL stock price` | English |
| `查一下00878的現在多少錢` | Traditional Chinese |
| `What is Tesla's current stock price?` | English |

**Expected Response:**
```
📈 Taiwan Semiconductor Manufacturing Company (2330.TW)
現價: 985.00 TWD
漲跌: +15.00 (+1.55%)
52週區間: 620.00 - 1,080.00 TWD
本益比 (P/E): 22.35
市值: 25.55T TWD

台積電目前走勢強勁，近52週已從最低點上漲約58.7%，P/E 22.35 在半導體產業屬合理估值。
```

**How it works:**
- Uses `yfinance` to fetch live stock data via `yf.Ticker(ticker).info`.
- A new `StockAgent` node (`agents/stock.py`) handles all stock queries.
- The `ExtractAgent` uses LLM to resolve company names to tickers (e.g. `台積電 → 2330.TW`, `Apple → AAPL`).
- Taiwan-listed stocks automatically get the `.TW` suffix appended.
- Graph path: `intent → extract → stock → summary`

---

## Agent Graph Architecture

```
START → intent
          │
          ├─[currency_exchange_rate / currency_history / currency_best_amount]→ extract → currency → summary → END
          ├─[stock_price]→ extract → stock → summary → END
          └─[other]→ summary → END
```

## Deployment

### Deploy the chatbot in local(ngrok)
1. Terminal 1 — Flask app:
```bash
python app.py
```
2.Terminal 2 — ngrok:
```bash
ngrok http 5001
```
3. Check the server is running on **https://prisonlike-sarky-floyd.ngrok-free.dev/health**
4. Setup Webhook URL setting in Line Developers
`https://prisonlike-sarky-floyd.ngrok-free.dev/callback`

### Deploy the chatbot on cloud(render)
- Different branches have responding Webhook URL
- Set `region` in Render as `Singapore (Southeast Asia)`

# References

## Pre-preparasion for connecting to Line Chatbot
- [How to get LINE Channel Access Token.](https://daily146.com/line-channel-access-token)
- [Python-to-Line Chatbot guidance 1](https://ithelp.ithome.com.tw/articles/10337794)
- [Python-to-Line Chatbot guidance 2](https://ithelp.ithome.com.tw/articles/10338062)

## Codings reference
- [pyhton-to-linebot](https://pypi.org/project/line-bot-sdk/)

## Websites / Services
- [Line Official Account Manager](https://manager.line.biz/account/@156qcdrh/setting/response)
    - Manage bot responses & settings
- [Line Developer](https://developers.line.biz/console/)
    - Webhook & API key settings
- [ngrok](https://ngrok.com)
    - Free HTTPS tunnel for **local deployment**
- [Render](https://dashboard.render.com)
    - For **cloud deployment**
    - ⭐️ Need to write **`.python-versioin`** to delpoy with setting python version
- [Gunicorn (Green Unicorn)](https://gunicorn.org)
- Other resources
    - [理財鴿：銀行即時匯率](https://www.fintechgo.com.tw/FinInfo/ForexRate/BankRealExRate/Currency/USD)
        - Deploy in **local** is available, but when in **render** is unavailable. → `IP Address Issue`
