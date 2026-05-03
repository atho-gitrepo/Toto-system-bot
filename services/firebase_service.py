import firebase_admin
from firebase_admin import credentials, firestore
from typing import Dict, List, Optional
from datetime import datetime
import json
import os

class FirebaseService:
    def __init__(self, credentials_json: str = None, project_id: str = None):
        self.db = None
        self.initialized = False
        
        try:
            if not firebase_admin._apps:
                # Try different credential sources
                cred = None
                
                if credentials_json:
                    # From environment variable
                    cred_dict = json.loads(credentials_json)
                    cred = credentials.Certificate(cred_dict)
                elif os.path.exists('firebase-credentials.json'):
                    # From file
                    cred = credentials.Certificate('firebase-credentials.json')
                elif os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
                    # From Google Cloud default credentials
                    cred = credentials.ApplicationDefault()
                else:
                    raise Exception("No Firebase credentials found")
                
                # Initialize Firebase with Project ID (for Firestore)
                app_options = {}
                if project_id:
                    app_options['projectId'] = project_id
                elif cred_dict and 'project_id' in cred_dict:
                    app_options['projectId'] = cred_dict['project_id']
                
                firebase_admin.initialize_app(cred, app_options)
                print("Firebase initialized successfully")
            
            # Get Firestore client (no URL needed)
            self.db = firestore.client()
            self.initialized = True
            print("Firestore client connected")
            
        except Exception as e:
            print(f"Firebase initialization error: {e}")
            self.initialized = False
    
    def save_generation(self, numbers: List[int], metadata: Dict = None) -> str:
        """Save generated numbers to Firestore, returns document ID"""
        if not self.initialized:
            print("Firebase not initialized")
            return None
        
        try:
            doc_data = {
                'numbers': numbers,
                'timestamp': firestore.SERVER_TIMESTAMP,
                'date': datetime.now().isoformat(),
                'type': 'system8',
                'metadata': metadata or {}
            }
            
            # Add document to 'generations' collection
            doc_ref = self.db.collection('generations').document()
            doc_ref.set(doc_data)
            print(f"Generation saved with ID: {doc_ref.id}")
            return doc_ref.id
            
        except Exception as e:
            print(f"Error saving generation: {e}")
            return None
    
    def save_result(self, generation_id: str, result_data: Dict) -> bool:
        """Save result checking data"""
        if not self.initialized:
            return False
        
        try:
            result_data['checked_at'] = firestore.SERVER_TIMESTAMP
            
            # Save to 'results' collection
            doc_ref = self.db.collection('results').document(generation_id)
            doc_ref.set(result_data)
            
            # Update generation with result reference
            generation_ref = self.db.collection('generations').document(generation_id)
            generation_ref.update({'result_checked': True, 'result_id': generation_id})
            
            print(f"Result saved for generation: {generation_id}")
            return True
            
        except Exception as e:
            print(f"Error saving result: {e}")
            return False
    
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
            print(f"Error getting last generation: {e}")
            return None
    
    def get_generation_by_id(self, doc_id: str) -> Optional[Dict]:
        """Get specific generation by ID"""
        if not self.initialized:
            return None
        
        try:
            doc_ref = self.db.collection('generations').document(doc_id)
            doc = doc_ref.get()
            if doc.exists:
                data = doc.to_dict()
                data['id'] = doc.id
                return data
            return None
            
        except Exception as e:
            print(f"Error getting generation: {e}")
            return None
    
    def get_history(self, limit: int = 5) -> List[Dict]:
        """Get generation history"""
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
                # Convert timestamp to readable format
                if 'timestamp' in data and data['timestamp']:
                    data['date_readable'] = data['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if hasattr(data['timestamp'], 'strftime') else str(data['timestamp'])
                history.append(data)
            return history
            
        except Exception as e:
            print(f"Error getting history: {e}")
            return []
    
    def update_roi_stats(self, stats: Dict) -> bool:
        """Update ROI statistics"""
        if not self.initialized:
            return False
        
        try:
            # Add last updated timestamp
            stats['last_updated'] = firestore.SERVER_TIMESTAMP
            stats['last_updated_iso'] = datetime.now().isoformat()
            
            doc_ref = self.db.collection('stats').document('roi')
            doc_ref.set(stats, merge=True)
            print("ROI stats updated")
            return True
            
        except Exception as e:
            print(f"Error updating ROI stats: {e}")
            return False
    
    def get_roi_stats(self) -> Dict:
        """Get ROI statistics"""
        if not self.initialized:
            return {
                'total_spent': 0, 
                'total_return': 0, 
                'roi': 0, 
                'games_played': 0,
                'net_profit': 0
            }
        
        try:
            doc_ref = self.db.collection('stats').document('roi')
            doc = doc_ref.get()
            if doc.exists:
                stats = doc.to_dict()
                # Remove server timestamp for JSON serialization
                stats.pop('last_updated', None)
                return stats
            return {
                'total_spent': 0, 
                'total_return': 0, 
                'roi': 0, 
                'games_played': 0,
                'net_profit': 0
            }
            
        except Exception as e:
            print(f"Error getting ROI stats: {e}")
            return {
                'total_spent': 0, 
                'total_return': 0, 
                'roi': 0, 
                'games_played': 0,
                'net_profit': 0
            }
    
    def get_all_generations(self, limit: int = 50) -> List[Dict]:
        """Get all generations with results"""
        if not self.initialized:
            return []
        
        try:
            docs = self.db.collection('generations')\
                .order_by('timestamp', direction=firestore.Query.DESCENDING)\
                .limit(limit)\
                .stream()
            
            generations = []
            for doc in docs:
                gen_data = doc.to_dict()
                gen_data['id'] = doc.id
                
                # Fetch result if exists
                result_doc = self.db.collection('results').document(doc.id).get()
                if result_doc.exists:
                    gen_data['result'] = result_doc.to_dict()
                
                generations.append(gen_data)
            return generations
            
        except Exception as e:
            print(f"Error getting all generations: {e}")
            return []
    
    def delete_generation(self, doc_id: str) -> bool:
        """Delete a generation (for testing/cleanup)"""
        if not self.initialized:
            return False
        
        try:
            self.db.collection('generations').document(doc_id).delete()
            # Also delete associated result if exists
            self.db.collection('results').document(doc_id).delete()
            print(f"Deleted generation: {doc_id}")
            return True
            
        except Exception as e:
            print(f"Error deleting generation: {e}")
            return False
    
    def get_statistics(self) -> Dict:
        """Get overall statistics"""
        if not self.initialized:
            return {}
        
        try:
            # Get count of generations
            generations_count = self.db.collection('generations').count().get()[0][0].value
            
            # Get count of results with prizes
            results_with_prizes = self.db.collection('results')\
                .where('prize_amount', '>', 0)\
                .count().get()[0][0].value
            
            # Get ROI stats
            roi_stats = self.get_roi_stats()
            
            return {
                'total_generations': generations_count,
                'wins_count': results_with_prizes,
                'win_rate': (results_with_prizes / generations_count * 100) if generations_count > 0 else 0,
                'total_spent': roi_stats.get('total_spent', 0),
                'total_return': roi_stats.get('total_return', 0),
                'roi': roi_stats.get('roi', 0),
                'net_profit': roi_stats.get('net_profit', 0)
            }
            
        except Exception as e:
            print(f"Error getting statistics: {e}")
            return {}