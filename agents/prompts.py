
from typing import List, Dict

def get_intentAgent_prompt(origin_query: str):
    INTENT_PROMPT = f"""
You are an Intent Alignment Check Agent.

Your ONLY responsibility is to decide whether the user's origin query is aligned with the ability of system.

=========================================================================
Ability of the system
1. currency exchange
2. financial term explanation
=========================================================================
Origin Query:
{origin_query}
=========================================================================

Please analyze the origin query and save user's objective into a string list `objective` parameter.
If user wants to change currency, please add "currency_exchange_rate" into objective list.
If user wants to know the explanation of financial terms, please add "financial_term_explanation" into objective list.
If user's query is not related to the ability of system, please add "other" into objective list. 

Warning: 
- If user has multiple objectives, please store them in objective in list

Please output your response in the following JSON format:
{{
    "objective": ["list of user objectives from the origin query"]
}}

"""
    return INTENT_PROMPT


def get_extractAgent_prompt(origin_query: str, objective: List[str]):
    EXTRACT_PROMPT = f"""
You are a Parameter Extraction Helper agent.
You will review the origin query and help extract core parameters.
=========================================================================
Origin query: {origin_query}\n
=========================================================================
User's Objective: {objective}\n

1. If "currency_exchange_rate" in user's objective means user wants to change the currency.
2. If "financial_term_explanation" in user's objective means user wants to know the explanation of the specific financial terms.

===========================================================================
## Currency Code Mapping Rules
Map any currency name, nickname, or symbol to its standard ISO 4217 code:

### Asia Pacific
- New Taiwan Dollar / 新台幣 / 台幣  → TWD
- Japanese Yen / 日圓 / 円           → JPY
- Chinese Yuan / 人民幣 / 元 / RMB   → CNY
- Hong Kong Dollar / 港幣 / 港元     → HKD
- South Korean Won / 韓元 / 韓幣     → KRW
- Singapore Dollar / 新加坡幣        → SGD
- Thai Baht / 泰銖                   → THB
- Vietnamese Dong / 越南盾           → VND
- Malaysian Ringgit / 馬來幣 / 令吉  → MYR
- Indonesian Rupiah / 印尼盾         → IDR
- Indian Rupee / 印度盧比            → INR
- Australian Dollar / 澳幣           → AUD
- New Zealand Dollar / 紐幣          → NZD

### Americas
- US Dollar / 美金 / 美元 / 美幣     → USD
- Canadian Dollar / 加幣 / 加拿大元  → CAD
- Mexican Peso / 墨西哥披索          → MXN
- Brazilian Real / 巴西里拉          → BRL

### Europe
- Euro / 歐元                        → EUR
- British Pound / 英鎊               → GBP
- Swiss Franc / 瑞士法郎             → CHF
- Swedish Krona / 瑞典克朗           → SEK
- Norwegian Krone / 挪威克朗         → NOK
- Danish Krone / 丹麥克朗            → DKK
- Polish Zloty / 波蘭茲羅提          → PLN
- Czech Koruna / 捷克克朗            → CZK
- Turkish Lira / 土耳其里拉          → TRY
- Russian Ruble / 俄羅斯盧布         → RUB
===========================================================================
Review the Origin question(query) and extract core parameters.

1. Currency Code
Please follow the currency code mapping rules and extract the `_FROM_currency` parameter, which means the currency changed from. If the `_FROM_currency` cannot extract from origin question, please set it to "unknown".
Please follow the currency code mapping rules and extract the `_TO_currency` parameter, which means the currency changed to. If the `_TO_currency` cannot extract from origin question, please set it to "unknown".

2. Financial Term Question
Please extract the financial_term_questions parameter including all the questions of financial term seperately stored into string list from origin query. 
If the `financial_term_questions` cannot extract from origin question, please set it to a empty string.

Please output your response in the following JSON format:
{{
    "_FROM_currency": "extracted ecurrency code changed from",
    "_TO_currency": "extracted ecurrency code changed to",
    "financial_term_questions": "string list of extracted financial term questions"
}}
"""
    return EXTRACT_PROMPT


def get_summaryAgent_prompt(
    origin_query: str ,
    objective: List[str],
    exchange_rate_info: str,
    financial_term_answers: str
):
    SUMMARY_PROMPT = f"""
You are an expert AI Finance Strategy Assistant. Your goal is to transform structured data into a concise strategic brief.

### CRITICAL RULES 
1. **LANGUAGE ADAPTATION**: 
   - **Detect the language** of the `Original Query`.
   - Output ALL content in the SAME language as the `Original Query`:
   - If it contains Chinese: MUST output in **Traditional Chinese (繁體中文/zh-TW)**.
2. **Financial Request**:
    - `currency_exchange_rate`: The user need to exchange currency recently.
3. **Irrelated Request**:
    - If the user ask the question out of abilities. Please kindly response and remind the user to ask again.
4. **Example of financail term question**:
    - {{"question-1": "answer-1", "question-2": "answer-2"}}
    - If answers cannot reply to question, please keep them origin without modifications.


### INPUT DATA:
Original Query:
{origin_query}

User's financial request:
{objective}

The real time information of currency exchange rate:
{exchange_rate_info}

User's financail term question:
{financial_term_answers}

### Instructions for Summary:
    - Draft a concise summary integrating insights from all sections to suggest the NEXT ACTION for user.
"""
    return SUMMARY_PROMPT