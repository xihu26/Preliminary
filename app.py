import base64
import hashlib
import hmac
import json
import os

import requests
from flask import Flask, request
from testing import analysis

app = Flask(__name__)

@app.post("/callback")
def callback():
    body = request.get_data()
    signature = request.headers.get("X-Line-Signature", "")
    secret = os.environ["CHANNEL_SECRET"]

    expected = base64.b64encode(
        hmac.new(secret.encode(), body, hashlib.sha256).digest()
    ).decode()

    if not hmac.compare_digest(signature, expected):
        return "Invalid signature", 401

    events = json.loads(body).get("events", [])
    for event in events:
        if event.get("type") != "message":
            continue
        if event.get("message", {}).get("type") != "text":
            continue

        text = event["message"]["text"]
        food, _, goal = text.partition("|")
        if not goal:
            reply = "Send food and goal like: oatmeal | fat loss"
        else:
            try:
                reply = analysis(food.strip(), goal.strip()) or "I couldn't analyse that. Please try again."
            except Exception:
                reply = "Sorry, the analysis failed. Please try again."

        requests.post(
            "https://api.line.me/v2/bot/message/reply",
            headers={
                "Authorization": f"Bearer {os.environ['CHANNEL_ACCESS_TOKEN']}",
                "Content-Type": "application/json",
            },
            json={
                "replyToken": event["replyToken"],
                "messages": [{"type": "text", "text": reply[:4500]}],
            },
            timeout=15,
        )

    return "OK", 200