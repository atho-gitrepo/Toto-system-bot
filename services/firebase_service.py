import firebase_admin
from firebase_admin import credentials, firestore
import os

# Prevent re-initialization (IMPORTANT for Railway)
if not firebase_admin._apps:
    cred = credentials.Certificate(os.getenv("FIREBASE_CREDENTIALS"))
    firebase_admin.initialize_app(cred)

# ✅ THIS is what your webhook needs
db = firestore.client()


# -------------------------------
# Save generated numbers
# -------------------------------
def save_numbers(numbers):
    db.collection("toto_system8").add({
        "numbers": numbers,
        "timestamp": firestore.SERVER_TIMESTAMP,
        "checked": False
    })


# -------------------------------
# Get last numbers
# -------------------------------
def get_last_numbers():
    docs = db.collection("toto_system8") \
        .order_by("timestamp", direction=firestore.Query.DESCENDING) \
        .limit(1).stream()

    for doc in docs:
        return doc.to_dict()["numbers"]

    return None