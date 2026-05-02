def save_result(result):
    db.collection("toto_results").add(result)


def get_unchecked_tickets():
    docs = db.collection("toto_system8") \
        .where("checked", "==", False).stream()

    return [(doc.id, doc.to_dict()) for doc in docs]


def update_ticket_result(doc_id, matches, prize):
    db.collection("toto_system8").document(doc_id).update({
        "matches": matches,
        "prize": prize,
        "checked": True
    })