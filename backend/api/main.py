"""FastAPI application main file"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import notifications, websocket

# Create FastAPI app
app = FastAPI(
    title="Trading Bot Notification API",
    description="REST API and WebSocket server for trading bot notifications",
    version="1.0.0"
)

# CORS middleware - allow all origins (adjust for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(notifications.router)
app.include_router(websocket.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Trading Bot Notification API",
        "version": "1.0.0",
        "endpoints": {
            "notifications": "/notifications",
            "websocket": "/ws/notifications",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

