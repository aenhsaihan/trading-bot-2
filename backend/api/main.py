"""FastAPI application main file"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from .routes import notifications, websocket, trading

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
app.include_router(trading.router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed messages"""
    errors = exc.errors()
    error_details = []
    for error in errors:
        error_details.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    return JSONResponse(
        status_code=422,
        content={"detail": error_details, "message": "Validation error"}
    )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Trading Bot Notification API",
        "version": "1.0.0",
        "endpoints": {
            "notifications": "/notifications",
            "trading": "/trading",
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

