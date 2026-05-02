def calculate_roi(tickets):
    total_spent = len(tickets) * 28  # System 8 cost
    total_return = 0

    prize_map = {
        "Group 5": 50,
        "Group 4": 200,
        "Group 3": 1000,
        "Group 2/3": 5000
    }

    for t in tickets:
        prize = t.get("prize")
        if prize in prize_map:
            total_return += prize_map[prize]

    roi = (total_return - total_spent) / total_spent * 100

    return total_spent, total_return, roi