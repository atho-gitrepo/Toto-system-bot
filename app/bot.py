from flask import Flask, request
from firebase_service import db

app = Flask(__name__)

@app.route(f"/webhook", methods=["POST"])
def telegram_webhook():
    data = request.json

    text = data["message"]["text"]
    chat_id = data["message"]["chat"]["id"]

    if text == "/last":
        docs = db.collection("toto_system8") \
            .order_by("timestamp", direction="DESCENDING") \
            .limit(1).stream()

        for doc in docs:
            send_message(f"Last: {doc.to_dict()['numbers']}")

    elif text == "/history":
        docs = db.collection("toto_system8") \
            .order_by("timestamp", direction="DESCENDING") \
            .limit(5).stream()

        msg = "📜 History:\n"
        for doc in docs:
            msg += f"{doc.to_dict()['numbers']}\n"

        send_message(msg)

    return "ok"