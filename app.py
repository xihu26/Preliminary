import base64
import hashlib
import hmac
import json
import os

import requests
from flask import Flask, request
from testing import analysis

app = Flask(__name__)

# Temporary per-user goal storage. This resets if Render restarts the app.
user_goals = {}


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
        user_id = event.get("source", {}).get("userId")

        try:
            if not user_id:
                reply = "Please message me in a one-to-one chat."

            elif message_type == "text":
                text = message.get("text", "").strip()

                if text.lower().startswith("goal:"):
                    goal = text.partition(":")[2].strip()

                    if goal:
                        user_goals[user_id] = goal
                        reply = f"Got it. Your goal is {goal}. Now send your food photo."
                    else:
                        reply = "Send your goal like this: goal: fat loss"

                else:
                    food, separator, goal = text.partition("|")

                    if separator and food.strip() and goal.strip():
                        user_goals[user_id] = goal.strip()
                        reply = analysis(food.strip(), goal.strip())

                    elif user_id in user_goals:
                        reply = analysis(text, user_goals[user_id])

                    else:
                        reply = "First send your goal, like: goal: fat loss"

            elif message_type == "image":
                goal = user_goals.get(user_id)

                if not goal:
                    reply = "First send your goal, like: goal: fat loss. Then send your photo."
                else:
                    image_response = requests.get(
                        f"https://api-data.line.me/v2/bot/message/{message['id']}/content",
                        headers={
                            "Authorization": (
                                f"Bearer {os.environ['CHANNEL_ACCESS_TOKEN']}"
                            )
                        },
                        timeout=30,
                    )
                    image_response.raise_for_status()

                    mime_type = image_response.headers.get(
                        "Content-Type", "image/jpeg"
                    ).split(";")[0]

                    reply = analysis(
                        food="",
                        goal=goal,
                        image_bytes=image_response.content,
                        mime_type=mime_type,
                    )

            else:
                reply = "Please send a goal, food description, or food photo."

            if not reply:
                reply = "I couldn't analyse that. Please try again."

        except Exception as e:
            print(f"Message processing failed: {type(e).__name__}: {e}")
            reply = "Sorry, the analysis failed. Please try again."

        reply_response = requests.post(
            "https://api.line.me/v2/bot/message/reply",
            headers={
                "Authorization": (
                    f"Bearer {os.environ['CHANNEL_ACCESS_TOKEN']}"
                ),
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