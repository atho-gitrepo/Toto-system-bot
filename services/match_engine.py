def count_matches(user_numbers, winning_numbers):
    return len(set(user_numbers) & set(winning_numbers))


def calculate_prize(matches):
    if matches == 6:
        return "Group 1"
    elif matches == 5:
        return "Group 2/3"
    elif matches == 4:
        return "Group 4"
    elif matches == 3:
        return "Group 5"
    else:
        return "No Win"