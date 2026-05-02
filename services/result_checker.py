from result_service import fetch_latest_results
from firebase_service import save_result, get_unchecked_tickets, update_ticket_result
from match_engine import count_matches, calculate_prize
from telegram_service import send_message

def run_result_check():
    result = fetch_latest_results()
    winning_numbers = result["numbers"]

    save_result(result)

    tickets = get_unchecked_tickets()

    summary = []

    for doc_id, ticket in tickets:
        matches = count_matches(ticket["numbers"], winning_numbers)
        prize = calculate_prize(matches)

        update_ticket_result(doc_id, matches, prize)

        summary.append(f"{ticket['numbers']} → {matches} matches ({prize})")

    message = f"""
📊 *TOTO RESULT CHECK*

Winning: {winning_numbers}

Results:
{chr(10).join(summary)}
"""

    send_message(message)