from services import NumberGenerator, FirebaseService, TelegramService, ResultChecker, ROIService
from config import config

class TotoBot:
    def __init__(self):
        self.firebase = FirebaseService(config.FIREBASE_CREDENTIALS_JSON, config.FIREBASE_DB_URL)
        self.generator = NumberGenerator(self.firebase)
        self.telegram = TelegramService()
        self.result_checker = ResultChecker()
        self.roi_service = ROIService(self.firebase)
    
    def generate_weekly_numbers(self) -> dict:
        prev_numbers = self.generator.get_previous_numbers()
        numbers = self.generator.generate_system8_numbers(prev_numbers)
        
        if self.firebase.save_generation(numbers, {'strategy': '70_30_balanced'}):
            from datetime import datetime
            self.telegram.send_numbers(numbers)
            return {'numbers': numbers, 'saved': True}
        return {'numbers': numbers, 'saved': False}
    
    def check_results(self) -> dict:
        last_gen = self.firebase.get_last_generation()
        if not last_gen:
            return {'error': 'No generation found'}
        
        result = self.result_checker.check_generation(last_gen)
        if result:
            self.roi_service.update_roi(result.get('prize_amount', 0))
            self.telegram.send_result_notification(result)
        return result or {'error': 'Check failed'}
    
    def get_history(self, limit: int = 5) -> list:
        return self.firebase.get_history(limit)
