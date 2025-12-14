from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from typing import List
from datetime import datetime
from bson import ObjectId

from app.utils.auth import get_current_user
from app.utils.database import get_collection
from app.services.file_processor import BettingFormProcessor
from app.services.sports_api import SportsAPIClient
from app.services.prediction_engine import PredictionEngine
from app.services.live_updater import start_monitoring

router = APIRouter(prefix="/betting-forms", tags=["Betting Forms"])

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_betting_form(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload and analyze a betting form PDF
    """
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported"
        )
    
    try:
        # Read file content
        content = await file.read()
        
        # Process the PDF
        processor = BettingFormProcessor()
        processed_data = await processor.process_betting_form(content, file.filename)
        
        # Initialize API client
        api_client = SportsAPIClient()
        
        # Enhance each game with API data and predictions
        enhanced_games = []
        for game in processed_data["games"]:
            # Find fixture in API
            fixture = await api_client.find_fixture(
                game["home_team"],
                game["away_team"]
            )
            
            if fixture:
                game["game_id"] = fixture["fixture_id"]
                game["kickoff_time"] = fixture["kickoff"]
                game["league"] = fixture.get("league", "Unknown")
                
                # Get additional data (simplified - in real app, you'd fetch team IDs first)
                # For demo purposes, using placeholder data
                home_form = ["W", "W", "D", "W", "L"]  # Would come from API
                away_form = ["L", "D", "W", "L", "L"]  # Would come from API
                h2h_results = []  # Would come from API
                
                # Calculate initial prediction
                bet_type = game["bet_classification"]["specific"]
                prediction = PredictionEngine.calculate_win_probability(
                    home_form=home_form,
                    away_form=away_form,
                    h2h_results=h2h_results,
                    home_team=game["home_team"],
                    bet_type=bet_type
                )
                
                # Calculate expected value
                ev_analysis = PredictionEngine.calculate_expected_value(
                    probability=prediction["win_probability"] / 100,
                    odds=game["odds"],
                    stake=game["stake"]
                )
                
                game["initial_prediction"] = {
                    **prediction,
                    **ev_analysis
                }
            
            enhanced_games.append(game)
        
        # Calculate overall analysis
        total_stake = sum(game.get("stake", 0) for game in enhanced_games)
        total_expected_return = sum(
            game["stake"] * game["odds"] if game.get("initial_prediction", {}).get("win_probability", 0) > 50 else 0
            for game in enhanced_games
        )
        
        overall_win_prob = statistics.mean([
            game.get("initial_prediction", {}).get("win_probability", 50)
            for game in enhanced_games
        ]) if enhanced_games else 50
        
        overall_analysis = {
            "total_stake": total_stake,
            "expected_return": total_expected_return,
            "expected_profit": total_expected_return - total_stake,
            "overall_win_probability": round(overall_win_prob, 2),
            "risk_score": 5.0,  # Placeholder calculation
            "recommendation": "Proceed with caution" if overall_win_prob > 55 else "High risk bets",
            "total_games": len(enhanced_games)
        }
        
        # Store in database
        betting_forms_collection = get_collection("betting_forms")
        
        form_document = {
            "user_id": current_user["user_id"],
            "upload_date": datetime.utcnow(),
            "status": "analyzed",  # "pending", "analyzing", "analyzed", "live", "completed"
            "original_file_name": file.filename,
            "games": enhanced_games,
            "overall_analysis": overall_analysis
        }
        
        result = await betting_forms_collection.insert_one(form_document)
        
        # Auto-start live monitoring for this form
        await start_monitoring(str(result.inserted_id))
        
        return {
            "message": "Betting form uploaded and analyzed successfully",
            "form_id": str(result.inserted_id),
            "total_games": len(enhanced_games),
            "overall_analysis": overall_analysis
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing betting form: {str(e)}"
        )

@router.get("/")
async def get_user_betting_forms(current_user: dict = Depends(get_current_user)):
    """Get all betting forms for current user"""
    betting_forms_collection = get_collection("betting_forms")
    
    cursor = betting_forms_collection.find(
        {"user_id": current_user["user_id"]}
    ).sort("upload_date", -1)
    
    forms = []
    async for document in cursor:
        forms.append({
            "id": str(document["_id"]),
            "upload_date": document["upload_date"],
            "status": document["status"],
            "original_file_name": document["original_file_name"],
            "total_games": len(document.get("games", [])),
            "overall_analysis": document.get("overall_analysis", {})
        })
    
    return {"forms": forms, "total": len(forms)}

@router.get("/{form_id}")
async def get_betting_form(
    form_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get detailed betting form by ID"""
    betting_forms_collection = get_collection("betting_forms")
    
    try:
        document = await betting_forms_collection.find_one({
            "_id": ObjectId(form_id),
            "user_id": current_user["user_id"]
        })
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Betting form not found"
            )
        
        document["_id"] = str(document["_id"])
        return document
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid form ID: {str(e)}"
        )

@router.delete("/{form_id}")
async def delete_betting_form(
    form_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a betting form"""
    betting_forms_collection = get_collection("betting_forms")
    
    try:
        result = await betting_forms_collection.delete_one({
            "_id": ObjectId(form_id),
            "user_id": current_user["user_id"]
        })
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Betting form not found"
            )
        
        return {"message": "Betting form deleted successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error deleting form: {str(e)}"
        )

import statistics  # Add this import at the top