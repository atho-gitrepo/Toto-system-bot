import firebase_admin
from firebase_admin import credentials, firestore
from typing import Dict, List, Optional
from datetime import datetime
import json
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FirebaseService:
    def __init__(self, credentials_json: str = None, project_id: str = None):
        self.db = None
        self.initialized = False
        self.error_message = None
        
        try:
            if not firebase_admin._apps:
                cred = None
                cred_dict = None
                
                if credentials_json:
                    cred_dict = json.loads(credentials_json)
                    cred = credentials.Certificate(cred_dict)
                elif os.path.exists('firebase-credentials.json'):
                    with open('firebase-credentials.json', 'r') as f:
                        cred_dict = json.load(f)
                    cred = credentials.Certificate(cred_dict)
                else:
                    raise Exception("No Firebase credentials found")
                
                app_options = {}
                if project_id:
                    app_options['projectId'] = project_id
                elif cred_dict and 'project_id' in cred_dict:
                    app_options['projectId'] = cred_dict['project_id']
                
                firebase_admin.initialize_app(cred, app_options)
                logger.info("Firebase initialized")
            
            self.db = firestore.client()
            self.initialized = True
            logger.info("Firestore connected")
            
        except Exception as e:
            logger.error(f"Firebase error: {e}")
            self.initialized = False
    
    def check_generation_exists(self, draw_no: str) -> bool:
        """Check if numbers already generated for a specific draw"""
        if not self.initialized:
            return False
        
        try:
            docs = self.db.collection('generations')\
                .where('draw_no', '==', draw_no)\
                .limit(1)\
                .stream()
            
            exists = False
            for doc in docs:
                exists = True
                logger.info(f"Generation already exists for draw {draw_no} (ID: {doc.id})")
                break
            
            return exists
            
        except Exception as e:
            logger.error(f"Error checking generation existence: {e}")
            return False
    
    def save_generation(self, numbers: List[int], draw_info: Dict = None) -> Optional[str]:
        """Save generated numbers with draw information - prevents duplicates"""
        if not self.initialized:
            logger.error("Firebase not initialized")
            return None
        
        draw_no = draw_info.get('draw_no') if draw_info else None
        
        # CRITICAL: Check if generation already exists for this draw
        if draw_no and self.check_generation_exists(draw_no):
            logger.warning(f"Generation already exists for draw {draw_no}. Skipping duplicate save.")
            return None
        
        try:
            doc_data = {
                'numbers': numbers,
                'timestamp': firestore.SERVER_TIMESTAMP,
                'date': datetime.now().isoformat(),
                'type': 'system8',
                'draw_no': draw_no,
                'draw_date': draw_info.get('draw_date') if draw_info else None,
                'status': 'pending',
                'checked': False,
                'generation_count': 1
            }
            
            doc_ref = self.db.collection('generations').document()
            doc_ref.set(doc_data)
            logger.info(f"✅ Generation saved for draw {draw_no} (ID: {doc_ref.id})")
            return doc_ref.id
            
        except Exception as e:
            logger.error(f"Error saving generation: {e}")
            return None
    
    def get_generation_by_draw(self, draw_no: str) -> Optional[Dict]:
        """Get the ONE generation for a specific draw number"""
        if not self.initialized:
            return None
        
        try:
            docs = self.db.collection('generations')\
                .where('draw_no', '==', draw_no)\
                .limit(1)\
                .stream()
            
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                return data
            return None
            
        except Exception as e:
            logger.error(f"Error getting generation: {e}")
            return None
    
    def get_last_generation(self) -> Optional[Dict]:
        """Get the most recent generation (by timestamp)"""
        if not self.initialized:
            return None
        
        try:
            docs = self.db.collection('generations')\
                .order_by('timestamp', direction=firestore.Query.DESCENDING)\
                .limit(1)\
                .stream()
            
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                return data
            return None
            
        except Exception as e:
            logger.error(f"Error getting last generation: {e}")
            return None
    
    def get_all_generations_for_draw(self, draw_no: str) -> List[Dict]:
        """Get ALL generations for a draw (for cleanup)"""
        if not self.initialized:
            return []
        
        try:
            docs = self.db.collection('generations')\
                .where('draw_no', '==', draw_no)\
                .stream()
            
            generations = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                generations.append(data)
            return generations
            
        except Exception as e:
            logger.error(f"Error getting generations: {e}")
            return []
    
    def delete_generation(self, doc_id: str) -> bool:
        """Delete a specific generation"""
        if not self.initialized:
            return False
        
        try:
            self.db.collection('generations').document(doc_id).delete()
            logger.info(f"Deleted generation {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting generation: {e}")
            return False
    
    def delete_all_generations_for_draw(self, draw_no: str) -> int:
        """Delete ALL generations for a draw (cleanup)"""
        if not self.initialized:
            return 0
        
        try:
            generations = self.get_all_generations_for_draw(draw_no)
            count = 0
            for gen in generations:
                if self.delete_generation(gen['id']):
                    count += 1
            logger.info(f"Deleted {count} generations for draw {draw_no}")
            return count
            
        except Exception as e:
            logger.error(f"Error cleaning up generations: {e}")
            return 0
    
    def get_history(self, limit: int = 5) -> List[Dict]:
        """Get generation history (one per draw, most recent first)"""
        if not self.initialized:
            return []
        
        try:
            # Get all generations, then deduplicate by draw_no
            docs = self.db.collection('generations')\
                .order_by('timestamp', direction=firestore.Query.DESCENDING)\
                .limit(limit * 2)\
                .stream()
            
            seen_draws = set()
            history = []
            
            for doc in docs:
                data = doc.to_dict()
                draw_no = data.get('draw_no')
                
                # Only include one generation per draw
                if draw_no and draw_no not in seen_draws:
                    seen_draws.add(draw_no)
                    data['id'] = doc.id
                    history.append(data)
                    
                    if len(history) >= limit:
                        break
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting history: {e}")
            return []
    
    def save_result(self, generation_id: str, result_data: Dict) -> bool:
        """Save result checking data"""
        if not self.initialized:
            return False
        
        try:
            result_data['checked_at'] = firestore.SERVER_TIMESTAMP
            result_data['checked_at_iso'] = datetime.now().isoformat()
            
            doc_ref = self.db.collection('results').document(generation_id)
            doc_ref.set(result_data)
            
            generation_ref = self.db.collection('generations').document(generation_id)
            generation_ref.update({
                'checked': True,
                'status': 'completed',
                'result_id': generation_id,
                'matches': result_data.get('matches', 0),
                'prize_amount': result_data.get('prize_amount', 0)
            })
            
            logger.info(f"Result saved for generation {generation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving result: {e}")
            return False
    
    def get_roi_stats(self) -> Dict:
        """Get ROI statistics"""
        if not self.initialized:
            return self._default_roi_stats()
        
        try:
            doc_ref = self.db.collection('stats').document('roi')
            doc = doc_ref.get()
            if doc.exists:
                return doc.to_dict()
            return self._default_roi_stats()
            
        except Exception as e:
            logger.error(f"Error getting ROI stats: {e}")
            return self._default_roi_stats()
    
    def update_roi_stats(self, stats: Dict) -> bool:
        """Update ROI statistics"""
        if not self.initialized:
            return False
        
        try:
            stats['last_updated'] = firestore.SERVER_TIMESTAMP
            doc_ref = self.db.collection('stats').document('roi')
            doc_ref.set(stats, merge=True)
            return True
            
        except Exception as e:
            logger.error(f"Error updating ROI stats: {e}")
            return False
    
    def _default_roi_stats(self) -> Dict:
        return {
            'total_spent': 0,
            'total_return': 0,
            'roi': 0,
            'games_played': 0,
            'net_profit': 0,
            'wins': 0
        }