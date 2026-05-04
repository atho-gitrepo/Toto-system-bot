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
        
        try:
            if not firebase_admin._apps:
                cred = None
                cred_dict = None
                
                if credentials_json:
                    cred_dict = json.loads(credentials_json)
                    cred = credentials.Certificate(cred_dict)
                elif os.path.exists('firebase-credentials.json'):
                    with open('firebase-credentials.json') as f:
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
                logger.info("Firebase initialized successfully")
            
            self.db = firestore.client()
            self.initialized = True
            logger.info("Firestore client connected")
            
        except Exception as e:
            logger.error(f"Firebase initialization error: {e}")
            self.initialized = False
    
    def save_generation(self, numbers: List[int], draw_info: Dict = None) -> Optional[str]:
        """Save generated numbers with draw information"""
        if not self.initialized:
            logger.error("Firebase not initialized")
            return None
        
        try:
            doc_data = {
                'numbers': numbers,
                'timestamp': firestore.SERVER_TIMESTAMP,
                'date': datetime.now().isoformat(),
                'type': 'system8',
                'draw_no': draw_info.get('draw_no') if draw_info else None,
                'draw_date': draw_info.get('draw_date') if draw_info else None,
                'status': 'pending',
                'checked': False
            }
            
            doc_ref = self.db.collection('generations').document()
            doc_ref.set(doc_data)
            logger.info(f"Generation saved with ID: {doc_ref.id} for draw {draw_info.get('draw_no')}")
            return doc_ref.id
            
        except Exception as e:
            logger.error(f"Error saving generation: {e}")
            return None
    
    def save_result(self, generation_id: str, result_data: Dict) -> bool:
        """Save result checking data"""
        if not self.initialized:
            return False
        
        try:
            result_data['checked_at'] = firestore.SERVER_TIMESTAMP
            result_data['checked_at_iso'] = datetime.now().isoformat()
            
            # Save to results collection
            doc_ref = self.db.collection('results').document(generation_id)
            doc_ref.set(result_data)
            
            # Update generation status
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
    
    def get_pending_generations(self) -> List[Dict]:
        """Get generations that haven't been checked yet"""
        if not self.initialized:
            return []
        
        try:
            docs = self.db.collection('generations')\
                .where('checked', '==', False)\
                .where('status', '==', 'pending')\
                .stream()
            
            pending = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                pending.append(data)
            return pending
            
        except Exception as e:
            logger.error(f"Error getting pending generations: {e}")
            return []
    
    def get_last_generation(self) -> Optional[Dict]:
        """Get the most recent generation"""
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
    
    def get_generation_by_draw(self, draw_no: str) -> Optional[Dict]:
        """Get generation for specific draw number"""
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
            logger.error(f"Error getting generation by draw: {e}")
            return None
    
    def get_history(self, limit: int = 5) -> List[Dict]:
        """Get generation history with results"""
        if not self.initialized:
            return []
        
        try:
            docs = self.db.collection('generations')\
                .order_by('timestamp', direction=firestore.Query.DESCENDING)\
                .limit(limit)\
                .stream()
            
            history = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                
                # Fetch result if exists
                result_doc = self.db.collection('results').document(doc.id).get()
                if result_doc.exists:
                    data['result'] = result_doc.to_dict()
                
                history.append(data)
            return history
            
        except Exception as e:
            logger.error(f"Error getting history: {e}")
            return []
    
    def update_roi_stats(self, stats: Dict) -> bool:
        """Update ROI statistics"""
        if not self.initialized:
            return False
        
        try:
            stats['last_updated'] = firestore.SERVER_TIMESTAMP
            stats['last_updated_iso'] = datetime.now().isoformat()
            
            doc_ref = self.db.collection('stats').document('roi')
            doc_ref.set(stats, merge=True)
            logger.info("ROI stats updated")
            return True
            
        except Exception as e:
            logger.error(f"Error updating ROI stats: {e}")
            return False
    
    def get_roi_stats(self) -> Dict:
        """Get ROI statistics"""
        if not self.initialized:
            return self._default_roi_stats()
        
        try:
            doc_ref = self.db.collection('stats').document('roi')
            doc = doc_ref.get()
            if doc.exists:
                stats = doc.to_dict()
                stats.pop('last_updated', None)
                return stats
            return self._default_roi_stats()
            
        except Exception as e:
            logger.error(f"Error getting ROI stats: {e}")
            return self._default_roi_stats()
    
    def _default_roi_stats(self) -> Dict:
        return {
            'total_spent': 0,
            'total_return': 0,
            'roi': 0,
            'games_played': 0,
            'net_profit': 0,
            'wins': 0
        }
    
    def record_draw_result(self, draw_no: str, winning_numbers: List[int], additional: int) -> bool:
        """Record official draw results"""
        if not self.initialized:
            return False
        
        try:
            draw_data = {
                'draw_no': draw_no,
                'draw_date': datetime.now().isoformat(),
                'winning_numbers': winning_numbers,
                'additional_number': additional,
                'recorded_at': firestore.SERVER_TIMESTAMP
            }
            
            doc_ref = self.db.collection('draws').document(draw_no)
            doc_ref.set(draw_data)
            logger.info(f"Draw {draw_no} results recorded")
            return True
            
        except Exception as e:
            logger.error(f"Error recording draw result: {e}")
            return False
    
    def get_draw_result(self, draw_no: str) -> Optional[Dict]:
        """Get official draw results"""
        if not self.initialized:
            return None
        
        try:
            doc_ref = self.db.collection('draws').document(draw_no)
            doc = doc_ref.get()
            if doc.exists:
                return doc.to_dict()
            return None
            
        except Exception as e:
            logger.error(f"Error getting draw result: {e}")
            return None
