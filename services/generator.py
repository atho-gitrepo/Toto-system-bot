import random

def generate_system8(previous_numbers=None):
    numbers = set()

    # If previous exists → keep 5 numbers
    if previous_numbers:
        keep = random.sample(previous_numbers, 5)
        numbers.update(keep)

    # Fill remaining with balanced distribution
    while len(numbers) < 8:
        n = random.randint(1, 49)
        numbers.add(n)

    final = sorted(numbers)

    return final


def format_numbers(nums):
    return " - ".join(map(str, nums))