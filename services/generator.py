import random
from typing import List, Set
from config import config

class NumberGenerator:
    def __init__(self, firebase_service=None):
        self.firebase_service = firebase_service
        
    def generate_system8_numbers(self, previous_numbers: List[int] = None) -> List[int]:
        numbers = set()
        
        if previous_numbers and len(previous_numbers) >= 4:
            reuse_count = min(5, len(previous_numbers))
            reused = random.sample(previous_numbers, reuse_count)
            numbers.update(reused)
            
            remaining_slots = config.SYSTEM_SIZE - len(numbers)
            if remaining_slots > 0:
                variation_numbers = self._generate_balanced_numbers(remaining_slots)
                numbers.update(variation_numbers)
        else:
            numbers = self._generate_balanced_numbers(config.SYSTEM_SIZE)
        
        while len(numbers) < config.SYSTEM_SIZE:
            new_num = random.randint(config.MIN_NUMBER, config.LOTTO_MAX_NUMBER)
            numbers.add(new_num)
        
        return sorted(list(numbers))[:config.SYSTEM_SIZE]
    
    def _generate_balanced_numbers(self, count: int) -> Set[int]:
        numbers = set()
        low_range = list(range(1, 17))
        mid_range = list(range(17, 33))
        high_range = list(range(33, 50))
        
        per_range = count // 3
        remainder = count % 3
        
        low_count = per_range + (1 if remainder > 0 else 0)
        mid_count = per_range + (1 if remainder > 1 else 0)
        high_count = per_range
        
        numbers.update(random.sample(low_range, min(low_count, len(low_range))))
        numbers.update(random.sample(mid_range, min(mid_count, len(mid_range))))
        numbers.update(random.sample(high_range, min(high_count, len(high_range))))
        
        while len(numbers) < count:
            numbers.add(random.randint(config.MIN_NUMBER, config.LOTTO_MAX_NUMBER))
        
        return numbers
    
    def get_previous_numbers(self) -> List[int]:
        if self.firebase_service:
            last_entry = self.firebase_service.get_last_generation()
            if last_entry and 'numbers' in last_entry:
                return last_entry['numbers']
        return None
