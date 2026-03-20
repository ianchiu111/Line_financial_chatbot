"""
flex_bank_table.py

Converts List[Dict] of bank exchange rates into a Line Flex Message table.

Usage:
    from flex_bank_table import build_bank_rate_table

    rates = [{'bank': '台灣銀行(004)', 'spot_buy': '32.03', ...}, ...]
    msg = build_bank_rate_table(rates)
    line_api.reply_message(ReplyMessageRequest(reply_token=..., messages=[msg]))
"""

from linebot.v3.messaging import FlexMessage, FlexContainer


# ── Design tokens ─────────────────────────────────────────────────────────────
HEADER_BG    = "#1a73e8"
HEADER_TEXT  = "#ffffff"
ROW_ODD_BG   = "#f0f4ff"
ROW_EVEN_BG  = "#ffffff"
TEXT_PRIMARY = "#1a1a2e"
TEXT_MUTED   = "#6b7280"
BORDER_COLOR = "#e2e8f0"
ACCENT_BUY   = "#0d6e3f"   # green  — buying rate  (bank buys USD from you)
ACCENT_SELL  = "#b91c1c"   # red    — selling rate  (bank sells USD to you)


# ── Cell builders ─────────────────────────────────────────────────────────────

def _header_cell(text: str, flex: int = 1, align: str = "center") -> dict:
    return {
        "type": "text",
        "text": text,
        "flex": flex,
        "size": "xs",
        "weight": "bold",
        "color": HEADER_TEXT,
        "align": align,
        "wrap": False,
    }


def _data_cell(
    text: str,
    flex: int = 1,
    align: str = "center",
    color: str = TEXT_PRIMARY,
    bold: bool = False,
) -> dict:
    return {
        "type": "text",
        "text": text if text not in ("", None) else "—",
        "flex": flex,
        "size": "xs",
        "weight": "bold" if bold else "regular",
        "color": color,
        "align": align,
        "wrap": False,
    }


def _header_row(labels: list[tuple[str, int]]) -> dict:
    """A styled header row. labels = [(text, flex), ...]"""
    return {
        "type": "box",
        "layout": "horizontal",
        "contents": [_header_cell(t, f) for t, f in labels],
        "paddingTop": "8px",
        "paddingBottom": "8px",
        "paddingStart": "10px",
        "paddingEnd": "10px",
    }


def _data_row(bank: dict, is_odd: bool) -> dict:
    """One bank row with alternating background."""

    # Strip bank code from name for compactness: '台灣銀行(004)' → '台灣銀行'
    name = bank["bank"].split("(")[0]

    def rate_color(val: str, is_buy: bool) -> str:
        if val in ("--", "", None):
            return TEXT_MUTED
        return ACCENT_BUY if is_buy else ACCENT_SELL

    cells = [
        _data_cell(name,                 flex=3, align="start", bold=True),
        _data_cell(bank.get("spot_buy",  "—"), flex=2, color=rate_color(bank.get("spot_buy"),  True)),
        _data_cell(bank.get("spot_sell", "—"), flex=2, color=rate_color(bank.get("spot_sell"), False)),
        _data_cell(bank.get("cash_buy",  "—"), flex=2, color=rate_color(bank.get("cash_buy"),  True)),
        _data_cell(bank.get("cash_sell", "—"), flex=2, color=rate_color(bank.get("cash_sell"), False)),
    ]

    return {
        "type": "box",
        "layout": "horizontal",
        "contents": cells,
        "paddingTop": "7px",
        "paddingBottom": "7px",
        "paddingStart": "10px",
        "paddingEnd": "10px",
        "backgroundColor": ROW_ODD_BG if is_odd else ROW_EVEN_BG,
    }


def _separator() -> dict:
    return {"type": "separator", "color": BORDER_COLOR}


# ── Main builder ──────────────────────────────────────────────────────────────

def build_bank_rate_table(
    rates: list[dict],
    _FROM_currency: str,
    _TO_currency: str, 
    updated: str = "",
) -> FlexMessage:
    """
    Build a Flex Message table from a list of bank rate dicts.

    Each dict must have keys:
        bank, spot_buy, spot_sell, cash_buy, cash_sell

    Line limits a single bubble to ~50KB JSON.
    """
    CHUNK = 8   # rows per bubble (keeps JSON under limit)

    if _FROM_currency == "TWD":
        currency_code = _TO_currency
    else:
        currency_code = _FROM_currency

    title= f"🏦 各銀行目前匯率 {currency_code}/TWD"

    if len(rates) <= CHUNK:
        bubbles = [_build_bubble(rates, title, updated, page=None)]
    else:
        chunks = [rates[i:i+CHUNK] for i in range(0, len(rates), CHUNK)]
        total  = len(chunks)
        bubbles = [
            _build_bubble(chunk, title, updated, page=(i+1, total))
            for i, chunk in enumerate(chunks)
        ]

    if len(bubbles) == 1:
        container = bubbles[0]
    else:
        container = {
            "type": "carousel",
            "contents": bubbles,
        }

    return FlexMessage(
        alt_text=f"{title} — {rates[0]['bank']} 即期買入 {rates[0].get('spot_buy', '?')}",
        contents=FlexContainer.from_dict(container),
    )


def _build_bubble(
    rates: list[dict],
    title: str,
    updated: str,
    page: tuple | None,
) -> dict:
    """Build a single bubble card."""

    subtitle_parts = []
    if updated:
        subtitle_parts.append(f"更新：{updated}")
    if page:
        subtitle_parts.append(f"第 {page[0]}/{page[1]} 頁")
    subtitle = "  ·  ".join(subtitle_parts) if subtitle_parts else ""

    # Header section
    header_contents = [
        {
            "type": "text",
            "text": title,
            "weight": "bold",
            "size": "sm",
            "color": "#ffffff",
        }
    ]
    if subtitle:
        header_contents.append({
            "type": "text",
            "text": subtitle,
            "size": "xxs",
            "color": "#ffffffaa",
            "margin": "xs",
        })

    # Column header row
    col_headers = [
        ("銀行",    3),
        ("即期買",  2),
        ("即期賣",  2),
        ("現金買",  2),
        ("現金賣",  2),
    ]

    # Data rows with separators
    row_contents = []
    for i, bank in enumerate(rates):
        row_contents.append(_data_row(bank, is_odd=(i % 2 == 0)))
        if i < len(rates) - 1:
            row_contents.append(_separator())

    # Legend footnote
    legend = {
        "type": "box",
        "layout": "vertical",
        "contents": [
            {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {"type": "text", "text": "■ 買入", "size": "xxs", "color": ACCENT_BUY,  "flex": 1},
                    {"type": "text", "text": "■ 賣出", "size": "xxs", "color": ACCENT_SELL, "flex": 1},
                ],
            },
            {
                "type": "text",
                "text": "單位為【新台幣】，「買入」價格愈低愈好；「賣出」價格愈高愈好。本資料僅供參考，實際以各銀行所揭露的資料為準。",
                "size": "xxs",
                "color": TEXT_MUTED,
                "wrap": True,
            },
        ],
        "paddingTop": "8px",
        "paddingStart": "10px",
        "paddingEnd": "10px",
        "paddingBottom": "4px",
    }

    return {
        "type": "bubble",
        "size": "giga",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": HEADER_BG,
            "paddingAll": "12px",
            "contents": header_contents,
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "0px",
            "spacing": "none",
            "contents": [
                # Column headers (sticky-looking)
                {
                    "type": "box",
                    "layout": "vertical",
                    "backgroundColor": "#2563eb",
                    "contents": [_header_row(col_headers)],
                },
                _separator(),
                # All data rows
                {
                    "type": "box",
                    "layout": "vertical",
                    "contents": row_contents,
                    "spacing": "none",
                },
                _separator(),
                legend,
            ],
        },
    }
