import os
import time
import threading
import numpy as np
import pandas as pd
import pytz
import logging
import traceback
import requests
from datetime import datetime, timezone
from utils.CSS.flex_bank_table import build_bank_rate_table
from typing import Dict, Any, Optional
from pathlib import Path
from graph import run_agent

## Line Chatbot
from flask import Flask, request, jsonify, abort
from flask_cors import CORS
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent
)
from dotenv import load_dotenv
load_dotenv(".env")

# ====================================================

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

taiwan_tz = pytz.timezone("Asia/Taipei")
current_time_taiwan = datetime.now(taiwan_tz)
version = current_time_taiwan.strftime("v%Y-%m%d-%H%M")

configuration = Configuration(
    access_token=os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")  
)
handler = WebhookHandler(os.environ.get("LINE_CHANNEL_SECRET")) 
# ====================================================


class APIResponse:
    """Static class for generating API responses"""

    @staticmethod
    def success(
        data: Any = None, message: str = "Success", meta: Optional[Dict] = None
    ):
        response = {
            "success": True,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }
        if data is not None:
            response["data"] = data
        if meta:
            response["meta"] = meta
        return response

    @staticmethod
    def error(
        message: str,
        error_code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[str] = None,
    ):
        response = {
            "success": False,
            "error": {
                "message": message,
                "code": error_code,
                "timestamp": datetime.now().isoformat(),
            },
        }
        if details:
            response["error"]["details"] = details
        return response, status_code


# ====================================================
# LINE Webhook Endpoint
# ====================================================
@app.route("/callback", methods=["POST"])
def callback():
    """Receive webhook from LINE"""
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    logger.info(f"Webhook received. Body: {body}")

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        logger.error("Invalid signature. Check your LINE_CHANNEL_SECRET.")
        abort(400)

    return "OK"


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    """Handle incoming text messages from LINE users"""
    user_message = event.message.text
    logger.info(f"User message: {user_message}")
 
    # ── Agent Response ────────────────────────────────────────────────────
    try:
        agent_response, taiwan_bank_rates, _FROM_currency, _TO_currency = run_agent(query=user_message)
        messages = [TextMessage(text=str(agent_response))]

    except Exception as e:
        logger.error(f"Agent error: {e}")
        logger.error(traceback.format_exc())

        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="Sorry, agent response went wrong. Please access our engineer.")]
                )
            )
        return
 
    # ── Rate Table Response ────────────────────────────────────────────────────
    if taiwan_bank_rates != []:            

        try:
            updated_time_taiwan = datetime.now(taiwan_tz)

            taiwan_bank_rates_table = build_bank_rate_table(
                rates = taiwan_bank_rates, 
                _FROM_currency = _FROM_currency,
                _TO_currency = _TO_currency, 
                updated = updated_time_taiwan.strftime("%Y-%m/%d-%H:%M")
            )
            messages.append(taiwan_bank_rates_table)
        except Exception as e:
            logger.error(f"Table error: {e}")
            logger.error(traceback.format_exc())

            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                line_bot_api.reply_message_with_http_info(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text="Sorry, table building went wrong. Please access our engineer.")]
                    )
                )
            return
 
    # ── Reply ─────────────────────────────────────────────────────────────────
    # Line allows max 5 messages per reply
    messages = messages[:5]

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=messages,
            )
        )

@app.route("/api/finance_agent", methods=["POST"])
def ask_agent():
    """
    Endpoint to update topic mapping file.

    Body:
    {
        "query": string, - user queries.
    }
    """
    try: 
    
        query = request.json.get("query", None)
        if query is None:
            return jsonify( 
                APIResponse.error(
                    message="User query is required.",
                )
            )
        
        response, taiwan_bank_rates = run_agent(query = query)
        return jsonify(
            APIResponse.success(
                message=(taiwan_bank_rates, response),
            )
        )
    except Exception as e:
        logger.error(f"Error during asking finance questions: {e}")
        logger.error(traceback.format_exc())
        return jsonify(
            APIResponse.error(
                message="An error occurred during asking finance questions.",
                details=str(e),
            )
        )

@app.get("/health")
def health():
    return {"status": f"server is running {version}"}

# ====================================================
# Keep-Alive: prevent Render free-tier from sleeping
# ====================================================
def _keep_alive():
    """
    Ping the /health endpoint every 13 minutes to prevent the Render
    free-tier server from sleeping due to inactivity (sleep threshold: 15 min).

    The outer loop ensures the ping loop is restarted automatically if it
    exits due to any unexpected exception (including BaseException subclasses
    such as SystemExit that are not caught by a plain ``except Exception``).
    """
    base_url = os.environ.get("RENDER_EXTERNAL_URL_DEV", "")
    ping_url = f"{base_url.rstrip('/')}/health"
    interval = 13 * 60  # seconds

    while True:
        try:
            while True:
                try:
                    resp = requests.get(ping_url, timeout=10)
                    logger.info(f"Keep-alive ping successful: {ping_url} [{resp.status_code}]")
                except Exception as exc:
                    logger.warning(f"Keep-alive ping failed: {exc}")

                time.sleep(interval)
        except BaseException as exc:
            logger.error(f"Keep-alive loop exited unexpectedly: {exc}. Restarting in 60 s…")
            time.sleep(60)


def _start_keep_alive():
    """Start the keep-alive background thread (no-op if one is already running)."""
    if any(t.name == "keep-alive" and t.is_alive() for t in threading.enumerate()):
        return None
    t = threading.Thread(target=_keep_alive, daemon=True, name="keep-alive")
    t.start()
    return t


_keep_alive_thread = _start_keep_alive()


if __name__ == "__main__":
    port = 5001  # Default port
    logger.info(f"Starting Flask app on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
