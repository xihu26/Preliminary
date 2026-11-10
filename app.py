from flask import Flask, request

app = Flask(__name__)

@app.get("/")
def home():
    return "Nutrition bot is running"

@app.post("/callback")
def callback():
    # LINE will send message events here.
    # Add signature verification and bot handling next.
    return "OK", 200