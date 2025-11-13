"""WebSocket routes for real-time notifications and price updates"""

import sys
from pathlib import Path
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.services.notification_service import NotificationService
from backend.services.price_update_service import get_price_update_service
from backend.services.trading_service import TradingService
from backend.services.websocket_manager import get_websocket_manager
from backend.services.market_data_streamer import get_market_data_streamer
from src.utils.logger import setup_logger
import json

router = APIRouter()
logger = setup_logger(f"{__name__}.websocket")

# Global service instances
notification_service = NotificationService()
price_update_service = get_price_update_service()
ws_manager = get_websocket_manager()
market_data_streamer = get_market_data_streamer()
# Use same instance pattern as trading routes
trading_service = TradingService()


@router.websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket):
    """WebSocket endpoint for real-time notification updates"""
    await websocket.accept()
    
    # Add client to service
    notification_service.add_websocket_client(websocket)
    
    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to notification stream"
        })
        
        # Keep connection alive and handle messages
        while True:
            # Wait for any message from client (ping/pong, etc.)
            data = await websocket.receive_text()
            
            # Handle ping/pong
            if data == "ping":
                await websocket.send_text("pong")
            
    except WebSocketDisconnect:
        # Client disconnected
        notification_service.remove_websocket_client(websocket)
    except Exception as e:
        # Error occurred, remove client
        notification_service.remove_websocket_client(websocket)
        raise


@router.websocket("/ws/market-data")
async def websocket_market_data(websocket: WebSocket):
    """WebSocket endpoint for real-time market data streaming (price ticks, OHLCV updates)"""
    await websocket.accept()
    
    # Add client to WebSocket manager
    client_id = ws_manager.add_client(websocket, client_type="market_data")
    print(f"[WEBSOCKET] New market data client connected: {client_id}")
    logger.info(f"New market data client connected: {client_id}")
    
    # Start streaming if not already running
    if not market_data_streamer.is_running:
        market_data_streamer.start_streaming()
        print(f"[WEBSOCKET] Started market data streamer")
    
    try:
        # Send initial connection message
        print(f"[WEBSOCKET] Sending connection message to client {client_id}")
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to market data stream",
            "client_id": client_id
        })
        
        # Keep connection alive and handle messages
        while True:
            # Wait for any message from client
            try:
                data = await websocket.receive_text()
                print(f"[WEBSOCKET] Received message from client {client_id}: {data[:100]}")
                logger.info(f"Received message from client {client_id}: {data[:100]}")
                
                # Handle ping/pong
                if data == "ping":
                    ws_manager.update_ping(websocket)
                    await websocket.send_text("pong")
                else:
                    # Try to parse as JSON for subscription commands
                    try:
                        message = json.loads(data)
                        message_type = message.get("type")
                        print(f"[WEBSOCKET] Parsed message type: {message_type}, full message: {message}")
                        logger.info(f"Parsed message type: {message_type}, full message: {message}")
                        
                        if message_type == "subscribe":
                            # Subscribe to symbol(s)
                            symbols = message.get("symbols", [])
                            if isinstance(symbols, str):
                                symbols = [symbols]
                            print(f"[WEBSOCKET] Received subscribe request for symbols: {symbols}")
                            logger.info(f"Received subscribe request for symbols: {symbols}")
                            for symbol in symbols:
                                ws_manager.subscribe(websocket, symbol)
                            subscribed = list(ws_manager.get_subscriptions(websocket))
                            print(f"[WEBSOCKET] Client {ws_manager.get_client_info(websocket)['id']} now subscribed to: {subscribed}")
                            logger.info(f"Client {ws_manager.get_client_info(websocket)['id']} now subscribed to: {subscribed}")
                            await websocket.send_json({
                                "type": "subscribed",
                                "symbols": subscribed
                            })
                        
                        elif message_type == "unsubscribe":
                            # Unsubscribe from symbol(s)
                            symbols = message.get("symbols", [])
                            if isinstance(symbols, str):
                                symbols = [symbols]
                            for symbol in symbols:
                                ws_manager.unsubscribe(websocket, symbol)
                            await websocket.send_json({
                                "type": "unsubscribed",
                                "symbols": list(ws_manager.get_subscriptions(websocket))
                            })
                        
                        elif message_type == "get_subscriptions":
                            # Get current subscriptions
                            await websocket.send_json({
                                "type": "subscriptions",
                                "symbols": list(ws_manager.get_subscriptions(websocket))
                            })
                        
                        else:
                            logger.warning(f"Unknown message type: {message_type}")
                    
                    except json.JSONDecodeError as e:
                        logger.warning(f"Received non-JSON message from client {client_id}: {data[:200]}. Error: {e}")
            
            except WebSocketDisconnect:
                # Break out of loop immediately on disconnect
                print(f"[WEBSOCKET] Client {client_id} disconnected (WebSocketDisconnect)")
                logger.info(f"Client {client_id} disconnected (WebSocketDisconnect)")
                break
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}", exc_info=True)
                # Check if it's a connection error
                error_str = str(e).lower()
                if "disconnect" in error_str or "closed" in error_str or "connection" in error_str:
                    print(f"[WEBSOCKET] Client {client_id} disconnected (error: {e})")
                    break
                # Continue loop for non-disconnect errors
    
    except WebSocketDisconnect:
        # Client disconnected
        print(f"[WEBSOCKET] Client {client_id} disconnected (outer WebSocketDisconnect)")
        logger.info(f"Market data WebSocket client {client_id} disconnected")
        ws_manager.remove_client(websocket)
    except Exception as e:
        # Error occurred, remove client
        error_str = str(e).lower()
        print(f"[WEBSOCKET] Client {client_id} error/disconnect: {e}")
        logger.error(f"Error in market data WebSocket: {e}", exc_info=True)
        ws_manager.remove_client(websocket)
        # Don't raise - just log and clean up


@router.websocket("/ws/prices")
async def websocket_prices(websocket: WebSocket):
    """WebSocket endpoint for real-time price updates for positions"""
    await websocket.accept()
    
    # Add client to price update service
    price_update_service.add_websocket_client(websocket)
    
    try:
        # Get current position symbols and start monitoring
        position_symbols = trading_service.get_position_symbols()
        if position_symbols:
            price_update_service.update_monitored_symbols(position_symbols)
        
        # Send initial connection message
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to price update stream",
            "monitored_symbols": position_symbols
        })
        
        # Keep connection alive and handle messages
        while True:
            # Wait for any message from client
            try:
                data = await websocket.receive_text()
                
                # Handle ping/pong
                if data == "ping":
                    await websocket.send_text("pong")
                # Handle symbol subscription updates
                elif data.startswith("subscribe:"):
                    # Format: "subscribe:['BTC/USDT','ETH/USDT']"
                    import json
                    symbols_str = data.replace("subscribe:", "")
                    symbols = json.loads(symbols_str)
                    price_update_service.update_monitored_symbols(symbols)
                    await websocket.send_json({
                        "type": "subscribed",
                        "symbols": symbols
                    })
            except WebSocketDisconnect:
                # Break out of loop immediately on disconnect
                break
            except Exception as e:
                # Log error but keep connection alive for non-disconnect errors
                logger.error(f"Error handling WebSocket message: {e}", exc_info=True)
            
    except WebSocketDisconnect:
        # Client disconnected
        price_update_service.remove_websocket_client(websocket)
    except Exception as e:
        # Error occurred, remove client
        price_update_service.remove_websocket_client(websocket)
        raise

