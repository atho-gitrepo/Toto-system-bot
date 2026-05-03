from services import NumberGenerator, FirebaseService, TelegramService, ResultChecker, ROIService
from config import config
from datetime import datetime

class TotoBot:
    def __init__(self):
        # Initialize Firebase with credentials JSON and project ID
        self.firebase = FirebaseService(
            credentials_json=config.FIREBASE_CREDENTIALS_JSON,
            project_id=config.FIREBASE_PROJECT_ID
        )
        self.generator = NumberGenerator(self.firebase)
        self.telegram = TelegramService()
        self.result_checker = ResultChecker()
        self.roi_service = ROIService(self.firebase)
    
    def generate_weekly_numbers(self) -> dict:
        """Generate weekly System 8 numbers"""
        try:
            prev_numbers = self.generator.get_previous_numbers()
            numbers = self.generator.generate_system8_numbers(prev_numbers)
            
            # Save to Firebase
            doc_id = self.firebase.save_generation(numbers, {
                'strategy': '70_30_balanced',
                'previous_numbers': prev_numbers
            })
            
            if doc_id:
                # Send to Telegram
                self.telegram.send_numbers(numbers)
                return {'numbers': numbers, 'saved': True, 'id': doc_id}
            return {'numbers': numbers, 'saved': False}
            
        except Exception as e:
            print(f"Error generating numbers: {e}")
            return {'error': str(e)}
    
    def check_results(self) -> dict:
        """Check results for last generation"""
        try:
            last_gen = self.firebase.get_last_generation()
            if not last_gen:
                return {'error': 'No generation found'}
            
            # Check results
            result = self.result_checker.check_generation(last_gen)
            if result:
                # Save result
                self.firebase.save_result(last_gen['id'], result)
                
                # Update ROI
                self.roi_service.update_roi(result.get('prize_amount', 0))
                
                # Send notification
                self.telegram.send_result_notification(result)
                return result
            
            return {'error': 'Check failed'}
            
        except Exception as e:
            print(f"Error checking results: {e}")
            return {'error': str(e)}
    
    def get_history(self, limit: int = 5) -> list:
        """Get generation history"""
        return self.firebase.get_history(limit)
    
    def get_roi_summary(self) -> str:
        """Get ROI summary"""
        stats = self.firebase.get_roi_stats()
        return f"ROI: {stats.get('roi', 0):.2f}% | Net: ${stats.get('net_profit', 0):,}"
    
    def get_statistics(self) -> dict:
        """Get overall statistics"""
        return self.firebase.get_statistics()