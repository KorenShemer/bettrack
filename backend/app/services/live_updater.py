import asyncio
from datetime import datetime
from typing import Dict, Any, List
from bson import ObjectId

from app.utils.database import get_collection
from app.services.sports_api import SportsAPIClient
from app.services.prediction_engine import PredictionEngine
from app.services.pusher_service import broadcast_update

class LiveUpdater:
    """Background service to poll API and broadcast updates via Pusher"""
    
    def __init__(self):
        self.api_client = SportsAPIClient()
        self.active_forms = set()  # Track which forms are being monitored
        self.tasks = {}  # Track running tasks
    
    async def start_monitoring(self, form_id: str):
        """Start monitoring a betting form for live updates"""
        if form_id in self.active_forms:
            print(f"Already monitoring form {form_id}")
            return
        
        self.active_forms.add(form_id)
        print(f"🎬 Started monitoring form {form_id}")
        
        # Create background task
        task = asyncio.create_task(self._monitor_form(form_id))
        self.tasks[form_id] = task
    
    async def stop_monitoring(self, form_id: str):
        """Stop monitoring a betting form"""
        if form_id in self.active_forms:
            self.active_forms.remove(form_id)
            
            # Cancel task
            if form_id in self.tasks:
                self.tasks[form_id].cancel()
                del self.tasks[form_id]
            
            print(f"🛑 Stopped monitoring form {form_id}")
    
    async def _monitor_form(self, form_id: str):
        """Monitor a form and broadcast updates every 30 seconds"""
        betting_forms = get_collection("betting_forms")
        
        while form_id in self.active_forms:
            try:
                # Get form from database
                form = await betting_forms.find_one({"_id": ObjectId(form_id)})
                
                if not form:
                    print(f"Form {form_id} not found, stopping monitor")
                    break
                
                # Check each game for updates
                updates = []
                
                for game in form.get("games", []):
                    game_id = game.get("game_id")
                    
                    if not game_id:
                        continue
                    
                    # Fetch live data from API
                    live_data = await self.api_client.get_live_fixture_data(game_id)
                    
                    if not live_data:
                        continue
                    
                    # Check if match is live
                    status = live_data.get("status", "")
                    
                    # Only process live matches
                    if status in ["IN_PLAY", "PAUSED"]:  # Football-Data.org statuses
                        current_score = live_data.get("score", {})
                        minute = live_data.get("elapsed", 0)
                        
                        # Recalculate prediction with live data
                        bet_type = game.get("bet_classification", {}).get("specific", "home_win")
                        
                        # Get form data (you'd cache this)
                        home_form = ["W", "W", "D", "W", "L"]
                        away_form = ["L", "D", "W", "L", "L"]
                        h2h_results = []
                        
                        updated_prediction = PredictionEngine.calculate_win_probability(
                            home_form=home_form,
                            away_form=away_form,
                            h2h_results=h2h_results,
                            home_team=game["home_team"],
                            bet_type=bet_type,
                            current_score=current_score,
                            minute=minute
                        )
                        
                        # Calculate EV
                        ev_analysis = PredictionEngine.calculate_expected_value(
                            probability=updated_prediction["win_probability"] / 100,
                            odds=game["odds"],
                            stake=game["stake"]
                        )
                        
                        # Create update object
                        update = {
                            "game_id": game_id,
                            "home_team": game["home_team"],
                            "away_team": game["away_team"],
                            "current_score": f"{current_score.get('home', 0)}-{current_score.get('away', 0)}",
                            "minute": minute,
                            "status": status,
                            "updated_prediction": {
                                **updated_prediction,
                                **ev_analysis
                            },
                            "initial_probability": game.get("initial_prediction", {}).get("win_probability", 50),
                            "change": round(
                                updated_prediction["win_probability"] - 
                                game.get("initial_prediction", {}).get("win_probability", 50),
                                2
                            ),
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        
                        updates.append(update)
                        
                        # Update database
                        await betting_forms.update_one(
                            {
                                "_id": ObjectId(form_id),
                                "games.game_id": game_id
                            },
                            {
                                "$set": {
                                    "games.$.current_prediction": updated_prediction,
                                    "games.$.live_score": current_score,
                                    "games.$.minute": minute,
                                    "games.$.status": status,
                                    "games.$.last_updated": datetime.utcnow()
                                }
                            }
                        )
                
                # Broadcast updates via Pusher if any
                if updates:
                    broadcast_update(form_id, {
                        "type": "live_update",
                        "updates": updates,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    print(f"📡 Broadcasted {len(updates)} update(s) for form {form_id}")
                
                # Wait 30 seconds before next check
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                print(f"Monitoring cancelled for form {form_id}")
                break
            except Exception as e:
                print(f"Error monitoring form {form_id}: {e}")
                await asyncio.sleep(30)
        
        # Cleanup
        if form_id in self.active_forms:
            self.active_forms.remove(form_id)

# Global instance
live_updater = LiveUpdater()

# Convenience functions
async def start_monitoring(form_id: str):
    """Start monitoring a form"""
    await live_updater.start_monitoring(form_id)

async def stop_monitoring(form_id: str):
    """Stop monitoring a form"""
    await live_updater.stop_monitoring(form_id)