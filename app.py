import base64
import hashlib
import hmac
import json
import os

import requests
from dotenv import load_dotenv
from flask import Flask, request

from gindee import GinDee, line_text, message_action

load_dotenv()
app = Flask(__name__)

# Standalone Gemini mode keeps goals until the server restarts.
user_goals = {}


def line_headers():
    return {"Authorization": f"Bearer {os.environ['CHANNEL_ACCESS_TOKEN']}"}


def download_image(message_id):
    response = requests.get(
        f"https://api-data.line.me/v2/bot/message/{message_id}/content",
        headers=line_headers(),
        timeout=30,
    )
    response.raise_for_status()
    mime_type = response.headers.get("Content-Type", "image/jpeg").split(";")[0]
    return response.content, mime_type


def standalone_reply(event, user_id):
    from testing import analysis

    message = event["message"]
    if message["type"] == "text":
        text = message.get("text", "").strip()
        if text.lower().startswith("goal="):
            goal = text.partition("=")[2].strip()
            if not goal:
                return "Send your goal in this format: goal= fat loss"
            user_goals[user_id] = goal
            return f"Understood. Your goal is {goal}. Now please send your food photo."

        food, separator, goal = text.partition("|")
        if separator and food.strip() and goal.strip():
            user_goals[user_id] = goal.strip()
            return analysis(food.strip(), goal.strip())
        if user_id in user_goals:
            return analysis(text, user_goals[user_id])
        return "First send your goal in the format: goal= fat loss"

    if message["type"] == "image":
        goal = user_goals.get(user_id)
        if not goal:
            return "First send your goal, in the format: goal= fat loss. Then send your photo."
        data, mime = download_image(message["id"])
        return analysis(food="", goal=goal, image_bytes=data, mime_type=mime)
    return "Please send a goal, food description, or valid food photo."


def handle_event(event, sync_enabled):
    event_type = event.get("type")
    if event_type == "follow":
        if sync_enabled:
            return line_text(
                "Send a meal photo or description to get an estimate and log it in GinDee.",
                message_action("Connect GinDee"), message_action("Today's summary"),
            )
        return line_text(
            "🥗 Send Goal= followed by your nutrition goal, then send a meal photo or description."
        )
    if event_type not in ("message", "postback"):
        return None

    source = event.get("source", {})
    user_id = source.get("userId")
    if event_type == "postback" and not sync_enabled:
        return None
    if not user_id or (sync_enabled and source.get("type") != "user"):
        return line_text("Please message me in a one-to-one chat.")

    if sync_enabled:
        return GinDee(user_id).handle(event, download_image)
    reply = standalone_reply(event, user_id)
    return line_text(str(reply or "I couldn't analyse that. Please try again."))


@app.post("/callback")
def callback():
    body = request.get_data()
    signature = request.headers.get("X-Line-Signature", "")
    secret = os.environ["CHANNEL_SECRET"]
    expected = base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()
    if not hmac.compare_digest(signature.encode(), expected.encode()):
        return "Invalid signature", 401

    sync_enabled = bool(os.environ.get("GINDEE_BASE_URL") or os.environ.get("GINDEE_SYNC_SECRET"))
    for event in json.loads(body).get("events", []):
        if not event.get("replyToken"):
            continue
        try:
            reply = handle_event(event, sync_enabled)
        except Exception as exc:
            # Exceptions from HTTP libraries can include private request URLs.
            app.logger.warning("Message processing failed (%s)", type(exc).__name__)
            error = "GinDee couldn't complete that request. Please try again." if sync_enabled else (
                "Sorry, the analysis failed. Please try again."
            )
            reply = line_text(error)
        if reply is not None:
            response = requests.post(
                "https://api.line.me/v2/bot/message/reply",
                headers=line_headers(),
                json={"replyToken": event["replyToken"], "messages": [reply]},
                timeout=15,
            )
            response.raise_for_status()
    return "OK", 200
