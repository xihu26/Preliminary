"""GinDee requests and LINE replies for the shared meal diary."""

import os
import re
from urllib.parse import urlsplit

import requests


class GinDee:
    def __init__(self, user_id):
        self.url = os.environ.get("GINDEE_BASE_URL", "").rstrip("/")
        self.secret = os.environ.get("GINDEE_SYNC_SECRET", "")
        self.user_id = user_id
        parsed = urlsplit(self.url)
        if (
            not self.secret or parsed.scheme != "https" or not parsed.hostname
            or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment
        ):
            raise ValueError("GinDee requires an HTTPS origin and sync secret")

    def request(self, method, path, **kwargs):
        response = requests.request(
            method, self.url + "/api/line/" + path,
            headers={"Authorization": f"Bearer {self.secret}", "X-Line-User": self.user_id},
            timeout=(5, 35),
            allow_redirects=False,
            **kwargs,
        )
        response.raise_for_status()
        return response.json()

    def handle(self, event, download_image):
        if event["type"] == "postback":
            match = re.fullmatch(r"gindee:log:([0-9]{1,32})", event["postback"]["data"])
            if not match:
                return None
            try:
                result = self.request("POST", "confirm/" + match[1])
            except requests.HTTPError as exc:
                if exc.response.status_code in (404, 410):
                    return line_text("This estimate expired. Send your meal again to log it.")
                raise
            text = "Already in your GinDee diary." if result.get("already_logged") else "✅ Added to your GinDee diary."
            return line_text(text, message_action("Today's summary"), message_action("Connect GinDee"))

        message = event["message"]
        message_id = message["id"]
        if message["type"] == "image":
            data, mime_type = download_image(message_id)
            result = self.request("POST", f"scan/{message_id}", files={"file": ("meal", data, mime_type)})
        elif message["type"] == "text":
            text = message.get("text", "").strip()
            command = text.casefold()
            if command == "connect gindee":
                token = self.request("POST", "link")["token"]
                return line_text(
                    "Open your GinDee diary with this one-time link. It expires in five minutes.",
                    {"type": "uri", "label": "Open GinDee", "uri": f"{self.url}/#line-link={token}"},
                )
            if command in {"today", "today's summary", "today’s summary"}:
                day = self.request("GET", "day")
                entries = day["entries"]
                if not entries:
                    return line_text("Your GinDee diary has no meals for today.", message_action("Connect GinDee"))
                lines = [f"Today's diary · {day['date']}", nutrition(day["totals"])]
                lines.extend(f"{item['time']} · {item['name_en']} · {item['kcal']:g} kcal" for item in entries[:15])
                if len(entries) > 15:
                    lines.append(f"+ {len(entries) - 15} more in GinDee")
                return line_text("\n".join(lines), message_action("Connect GinDee"))
            if command.startswith("goal="):
                return line_text("You can set your nutrition goal in GinDee.", message_action("Connect GinDee"))
            food = text.partition("|")[0].strip()
            if len(food) < 2:
                return line_text("Send a food photo or describe what you ate.")
            result = self.request("POST", "estimate", json={"text": food[:300], "message_id": message_id})
        else:
            return line_text("Send a food photo or describe what you ate.")

        if result.get("already_logged"):
            return line_text("Already in your GinDee diary.")
        if not result["is_food"]:
            return line_text("GinDee couldn't identify a meal. Try a clearer photo or description.")
        lines = ["GinDee's estimate"]
        lines.extend(f"{item['name_en']} · {nutrition(item)}" for item in result["items"])
        return line_text("\n".join(lines), {
            "type": "postback", "label": "Log meal", "data": f"gindee:log:{message_id}",
        })


def nutrition(item):
    return (
        f"{item['kcal']:g} kcal · {item['protein_g']:g} g protein · "
        f"{item['carbs_g']:g} g carbs · {item['fat_g']:g} g fat"
    )


def message_action(text):
    return {"type": "message", "label": text, "text": text}


def line_text(text, *actions):
    message = {"type": "text", "text": text[:4500]}
    if actions:
        message["quickReply"] = {"items": [{"type": "action", "action": action} for action in actions]}
    return message
