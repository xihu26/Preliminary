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

        message = event.get("message", {})
        message_type = message.get("type")

        try:
            if message_type == "text":
                text = message["text"]
                food, separator, goal = text.partition("|")

                if not separator or not food.strip() or not goal.strip():
                    reply = "Send food and goal like: oatmeal | fat loss"
                else:
                    reply = analysis(food.strip(), goal.strip())

            elif message_type == "image":
                image_response = requests.get(
                    f"https://api-data.line.me/v2/bot/message/{message['id']}/content",
                    headers={
                        "Authorization":
                            f"Bearer {os.environ['CHANNEL_ACCESS_TOKEN']}"
                    },
                    timeout=30,
                )
                image_response.raise_for_status()

                mime_type = image_response.headers.get(
                    "Content-Type", "image/jpeg"
                ).split(";")[0]

                reply = analysis(
                    food="",
                    goal="",
                    image_bytes=image_response.content,
                    mime_type=mime_type,
                )

            else:
                reply = "Please send a food description or a food photo."

            if not reply:
                reply = "I couldn't analyse that. Please try again."

        except Exception as e:
            print(f"Message processing failed: {type(e).__name__}: {e}")
            reply = "Sorry, the analysis failed. Please try again."

        reply_response = requests.post(
            "https://api.line.me/v2/bot/message/reply",
            headers={
                "Authorization":
                    f"Bearer {os.environ['CHANNEL_ACCESS_TOKEN']}",
                "Content-Type": "application/json",
            },
            json={
                "replyToken": event["replyToken"],
                "messages": [{"type": "text", "text": str(reply)[:4500]}],
            },
            timeout=15,
        )
        reply_response.raise_for_status()

    return "OK", 200