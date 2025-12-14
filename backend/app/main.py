from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from app.utils.database import Database
from app.utils.redis_client import RedisClient

# Import routers
from app.routes import auth, betting_forms
from app.websocket import websocket_endpoint

app = FastAPI(
    title="Soccer Betting Analyzer",
    description="Real-time soccer betting form analyzer with live match updates",
    version="1.0.0"
)

# CORS configuration for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite and CRA
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize database and Redis connections on startup"""
    await Database.connect_db()
    RedisClient.connect()
    print("🚀 Application started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Close database and Redis connections on shutdown"""
    await Database.close_db()
    RedisClient.disconnect()
    print("👋 Application shutdown complete")

# Include routers
app.include_router(auth.router)
app.include_router(betting_forms.router)

# Import live updater
from app.services.live_updater import start_monitoring, stop_monitoring

@app.post("/monitoring/start/{form_id}")
async def start_form_monitoring(form_id: str):
    """Start live monitoring for a betting form"""
    await start_monitoring(form_id)
    return {"message": f"Started monitoring form {form_id}", "form_id": form_id}

@app.post("/monitoring/stop/{form_id}")
async def stop_form_monitoring(form_id: str):
    """Stop live monitoring for a betting form"""
    await stop_monitoring(form_id)
    return {"message": f"Stopped monitoring form {form_id}", "form_id": form_id}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Soccer Betting Analyzer API",
        "version": "1.0.0",
        "status": "online",
        "docs": "/docs",
        "websocket": "/ws/{form_id}"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    db = Database.get_database()
    redis = RedisClient.client
    
    return {
        "status": "healthy",
        "database": "connected" if db else "disconnected",
        "redis": "connected" if redis else "disconnected",
        "service": "betting-analyzer"
    }