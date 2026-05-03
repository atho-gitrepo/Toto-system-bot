from flask import Flask, request
from services.telegram_service import send_message
from services.firebase_service import db

app = Flask(__name__)

@app.route("/")
def home():
    return "Toto Bot Running ✅"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    if "message" not in data:
        return "ok"

    text = data["message"].get("text", "")
    chat_id = data["message"]["chat"]["id"]

    # 🔹 Commands
    if text == "/start":
        send_message("🤖 Toto Bot Active!", chat_id)

    elif text == "/last":
        docs = db.collection("toto_system8") \
            .order_by("timestamp", direction="DESCENDING") \
            .limit(1).stream()

        for doc in docs:
            send_message(f"🎟️ Last: {doc.to_dict()['numbers']}", chat_id)

    elif text == "/history":
        docs = db.collection("toto_system8") \
            .order_by("timestamp", direction="DESCENDING") \
            .limit(5).stream()

        msg = "📜 History:\n"
        for doc in docs:
            msg += f"{doc.to_dict()['numbers']}\n"

        send_message(msg, chat_id)

    else:
        send_message("Unknown command", chat_id)

    return "ok"