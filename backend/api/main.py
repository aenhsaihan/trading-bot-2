"""FastAPI application main file"""

import os
import asyncio
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    project_root = Path(__file__).parent.parent.parent.parent
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        print(f"Loaded environment variables from {env_file}")
except ImportError:
    pass  # python-dotenv not installed, skip

from .routes import notifications, websocket, trading, ai, market_data, alerts, signals, system, voice, news
from backend.services.alert_service import get_alert_service
from backend.services.notification_source_service import get_notification_source_service
from backend.services.news_monitor import get_news_monitor

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
app.include_router(ai.router)
app.include_router(market_data.router)
app.include_router(alerts.router)
app.include_router(signals.router)
app.include_router(system.router)
app.include_router(voice.router)
app.include_router(news.router)


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
            "ai": "/ai",
            "alerts": "/alerts",
            "signals": "/signals",
            "news": "/news",
            "websocket": "/ws/notifications",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


async def alert_evaluation_loop():
    """
    Background task that periodically evaluates all enabled alerts.
    Runs every 30 seconds to check if any alerts should trigger.
    """
    alert_service = get_alert_service()
    
    while True:
        try:
            await asyncio.sleep(30)  # Evaluate every 30 seconds
            
            # Evaluate all alerts (run in thread pool to avoid blocking event loop)
            # Using to_thread for Python 3.9+, fallback to run_in_executor for older versions
            try:
                triggered = await asyncio.to_thread(alert_service.evaluate_all_alerts)
            except AttributeError:
                # Fallback for Python < 3.9
                loop = asyncio.get_event_loop()
                triggered = await loop.run_in_executor(None, alert_service.evaluate_all_alerts)
            
            if triggered:
                alert_service.logger.info(
                    f"Alert evaluation: {len(triggered)} alert(s) triggered"
                )
        except asyncio.CancelledError:
            # Task was cancelled, exit gracefully
            alert_service.logger.info("Alert evaluation task cancelled")
            break
        except Exception as e:
            alert_service.logger.error(
                f"Error in alert evaluation loop: {e}",
                exc_info=True
            )
            # Continue running even if there's an error
            await asyncio.sleep(30)


@app.on_event("startup")
async def startup_event():
    """Start background tasks on application startup"""
    # Start alert evaluation background task
    asyncio.create_task(alert_evaluation_loop())
    print("✅ Started alert evaluation background task (evaluates every 30 seconds)")
    
    # Start notification source monitoring service (optional, controlled by env var)
    enable_notification_sources = os.getenv("ENABLE_NOTIFICATION_SOURCES", "false").lower() == "true"
    if enable_notification_sources:
        try:
            notification_source_service = get_notification_source_service()
            if not notification_source_service.is_running():
                notification_source_service.start()
                print("✅ NotificationSourceService started successfully")
            else:
                print("ℹ️  NotificationSourceService is already running")
        except Exception as e:
            print(f"⚠️  Failed to start NotificationSourceService: {e}")
            # Don't fail startup if service fails to start
            pass
    else:
        print("ℹ️  NotificationSourceService disabled (set ENABLE_NOTIFICATION_SOURCES=true to enable)")
    
    # Start news monitor (optional, auto-starts if enabled)
    enable_news_monitoring = os.getenv("ENABLE_NEWS_MONITORING", "true").lower() == "true"
    
    if enable_news_monitoring:
        try:
            news_monitor = get_news_monitor()
            if not news_monitor.is_monitoring():
                news_monitor.start()
                categories = news_monitor.monitored_categories
                categories_str = ", ".join(categories) if categories else "all categories"
                print(f"✅ News Monitor started successfully (monitoring {categories_str})")
            else:
                print("ℹ️  News Monitor is already running")
        except Exception as e:
            print(f"⚠️  Failed to start News Monitor: {e}")
            # Don't fail startup if service fails to start
            pass
    else:
        print("ℹ️  News Monitor disabled (set ENABLE_NEWS_MONITORING=true to enable)")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    # Stop notification source service
    try:
        notification_source_service = get_notification_source_service()
        if notification_source_service.is_running():
            notification_source_service.stop()
            print("✅ NotificationSourceService stopped successfully")
    except Exception as e:
        print(f"⚠️  Error stopping NotificationSourceService: {e}")
    
    # Stop news monitor
    try:
        news_monitor = get_news_monitor()
        if news_monitor.is_monitoring():
            news_monitor.stop()
            print("✅ News Monitor stopped successfully")
    except Exception as e:
        print(f"⚠️  Error stopping News Monitor: {e}")
    
    # Background tasks will be cancelled automatically
    print("Shutting down background tasks...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

