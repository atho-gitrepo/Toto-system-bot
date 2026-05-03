import firebase_admin
from firebase_admin import credentials, firestore
from typing import Dict, List, Optional
from datetime import datetime
import json
import os

class FirebaseService:
    def __init__(self, credentials_json: str = None, db_url: str = None):
        self.db = None
        self.initialized = False
        
        try:
            if not firebase_admin._apps:
                if credentials_json:
                    cred_dict = json.loads(credentials_json)
                    cred = credentials.Certificate(cred_dict)
                elif os.path.exists('firebase-credentials.json'):
                    cred = credentials.Certificate('firebase-credentials.json')
                else:
                    raise Exception("Firebase credentials not found")
                
                if db_url:
                    firebase_admin.initialize_app(cred, {'databaseURL': db_url})
                else:
                    firebase_admin.initialize_app(cred)
            
            self.db = firestore.client()
            self.initialized = True
        except Exception as e:
            print(f"Firebase error: {e}")
    
    def save_generation(self, numbers: List[int], metadata: Dict = None) -> bool:
        if not self.initialized:
            return False
        try:
            self.db.collection('generations').add({
                'numbers': numbers,
                'timestamp': firestore.SERVER_TIMESTAMP,
                'date': datetime.now().isoformat(),
                'metadata': metadata or {}
            })
            return True
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    def get_last_generation(self) -> Optional[Dict]:
        if not self.initialized:
            return None
        try:
            docs = self.db.collection('generations').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(1).stream()
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                return data
            return None
        except Exception as e:
            print(f"Error: {e}")
            return None
    
    def get_history(self, limit: int = 5) -> List[Dict]:
        if not self.initialized:
            return []
        try:
            docs = self.db.collection('generations').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(limit).stream()
            return [{'id': doc.id, **doc.to_dict()} for doc in docs]
        except Exception as e:
            print(f"Error: {e}")
            return []
    
    def update_roi_stats(self, stats: Dict) -> bool:
        if not self.initialized:
            return False
        try:
            self.db.collection('stats').document('roi').set(stats, merge=True)
            return True
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    def get_roi_stats(self) -> Dict:
        if not self.initialized:
            return {'total_spent': 0, 'total_return': 0, 'roi': 0, 'games_played': 0}
        try:
            doc = self.db.collection('stats').document('roi').get()
            return doc.to_dict() if doc.exists else {'total_spent': 0, 'total_return': 0, 'roi': 0, 'games_played': 0}
        except Exception as e:
            print(f"Error: {e}")
            return {'total_spent': 0, 'total_return': 0, 'roi': 0, 'games_played': 0}
