import pusher
import os
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

class PusherService:
    """Pusher service for real-time broadcasting"""
    
    def __init__(self):
        self.client = pusher.Pusher(
            app_id=os.getenv('PUSHER_APP_ID'),
            key=os.getenv('PUSHER_KEY'),
            secret=os.getenv('PUSHER_SECRET'),
            cluster=os.getenv('PUSHER_CLUSTER'),
            ssl=True
        )
    
    def broadcast_live_update(self, form_id: str, data: Dict[str, Any]):
        """
        Broadcast live match update to all clients watching this form
        
        Args:
            form_id: Betting form ID
            data: Update data (game updates, scores, predictions)
        """
        try:
            self.client.trigger(
                f'form-{form_id}',  # Channel name
                'live-update',       # Event name
                data
            )
            print(f"✅ Broadcasted update to form-{form_id}")
        except Exception as e:
            print(f"❌ Pusher broadcast error: {e}")
    
    def broadcast_prediction_update(self, form_id: str, game_id: str, prediction: Dict[str, Any]):
        """Broadcast updated prediction for a specific game"""
        try:
            self.client.trigger(
                f'form-{form_id}',
                'prediction-update',
                {
                    'game_id': game_id,
                    'prediction': prediction
                }
            )
            print(f"✅ Broadcasted prediction update for game {game_id}")
        except Exception as e:
            print(f"❌ Pusher broadcast error: {e}")
    
    def notify_connection(self, form_id: str, message: str):
        """Send connection notification"""
        try:
            self.client.trigger(
                f'form-{form_id}',
                'notification',
                {'message': message}
            )
        except Exception as e:
            print(f"❌ Pusher notification error: {e}")

# Create singleton instance
pusher_service = PusherService()

# Convenience functions
def broadcast_update(form_id: str, data: Dict[str, Any]):
    """Broadcast live update"""
    pusher_service.broadcast_live_update(form_id, data)

def broadcast_prediction(form_id: str, game_id: str, prediction: Dict[str, Any]):
    """Broadcast prediction update"""
    pusher_service.broadcast_prediction_update(form_id, game_id, prediction)