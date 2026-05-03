from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Toto Bot Running ✅"

@app.route("/webhook", methods=["POST"])
def webhook():
    return "ok"