"""WebSocket connection manager for managing client connections and health monitoring"""

import sys
import asyncio
from pathlib import Path
from typing import Dict, Set, Optional, Any
from datetime import datetime, timedelta
from fastapi import WebSocket

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger


class WebSocketManager:
    """Manages WebSocket connections with health monitoring and subscription support"""
    
    def __init__(self, max_clients: int = 1000):
        """
        Initialize WebSocket manager.
        
        Args:
            max_clients: Maximum number of concurrent clients (safety limit)
        """
        self.clients: Dict[WebSocket, Dict[str, Any]] = {}
        self.logger = setup_logger(f"{__name__}.WebSocketManager")
        self._health_check_task: Optional[asyncio.Task] = None
        self._is_running = False
        self.max_clients = max_clients
    
    def add_client(self, websocket: WebSocket, client_type: str = "market_data") -> str:
        """
        Add a WebSocket client to the manager.
        
        Args:
            websocket: WebSocket connection
            client_type: Type of client (e.g., 'market_data', 'notifications')
            
        Returns:
            Client ID string
        """
        # Check if this WebSocket is already registered (prevent duplicates)
        if websocket in self.clients:
            existing_id = self.clients[websocket]["id"]
            self.logger.warning(f"WebSocket already registered: {existing_id}. Skipping duplicate add.")
            return existing_id
        
        # Safety check: prevent runaway connection growth
        if len(self.clients) >= self.max_clients:
            self.logger.warning(f"Maximum client limit reached ({self.max_clients}). Attempting cleanup...")
            # Quick cleanup: remove connections that haven't pinged in 2 minutes
            now = datetime.now()
            timeout = timedelta(seconds=120)
            stale = [ws for ws, info in list(self.clients.items()) if (now - info["last_ping"]) > timeout]
            for ws in stale:
                if ws in self.clients:
                    self.remove_client(ws)
            
            if len(self.clients) >= self.max_clients:
                self.logger.error(f"Maximum client limit ({self.max_clients}) reached even after cleanup. Rejecting connection.")
                raise Exception(f"Maximum client limit ({self.max_clients}) reached")
        
        client_id = f"{client_type}_{id(websocket)}_{datetime.now().timestamp()}"
        self.clients[websocket] = {
            "id": client_id,
            "type": client_type,
            "connected_at": datetime.now(),
            "last_ping": datetime.now(),
            "subscriptions": set(),  # Set of subscribed symbols
            "is_alive": True
        }
        self.logger.info(f"Added WebSocket client {client_id} (type: {client_type}). Total clients: {len(self.clients)}")
        
        # Start health check if not running
        if not self._is_running:
            self.start_health_check()
        
        return client_id
    
    def remove_client(self, websocket: WebSocket):
        """Remove a WebSocket client from the manager"""
        if websocket in self.clients:
            client_info = self.clients[websocket]
            client_id = client_info["id"]
            del self.clients[websocket]
            self.logger.info(f"Removed WebSocket client {client_id}. Total clients: {len(self.clients)}")
            
            # Stop health check if no clients
            if len(self.clients) == 0:
                self.stop_health_check()
    
    def get_client_info(self, websocket: WebSocket) -> Optional[Dict[str, Any]]:
        """Get client information"""
        return self.clients.get(websocket)
    
    def subscribe(self, websocket: WebSocket, symbol: str):
        """Subscribe client to a symbol"""
        if websocket in self.clients:
            self.clients[websocket]["subscriptions"].add(symbol)
            self.logger.info(f"Client {self.clients[websocket]['id']} subscribed to {symbol}. Total subscriptions: {len(self.get_all_subscriptions())}")
    
    def unsubscribe(self, websocket: WebSocket, symbol: str):
        """Unsubscribe client from a symbol"""
        if websocket in self.clients:
            self.clients[websocket]["subscriptions"].discard(symbol)
            self.logger.info(f"Client {self.clients[websocket]['id']} unsubscribed from {symbol}. Total subscriptions: {len(self.get_all_subscriptions())}")
    
    def get_subscriptions(self, websocket: WebSocket) -> Set[str]:
        """Get all subscriptions for a client"""
        if websocket in self.clients:
            return self.clients[websocket]["subscriptions"].copy()
        return set()
    
    def get_all_subscriptions(self) -> Set[str]:
        """Get all unique symbols that any client is subscribed to"""
        all_subs = set()
        for client_info in self.clients.values():
            all_subs.update(client_info["subscriptions"])
        return all_subs
    
    def update_ping(self, websocket: WebSocket):
        """Update last ping time for a client"""
        if websocket in self.clients:
            self.clients[websocket]["last_ping"] = datetime.now()
            self.clients[websocket]["is_alive"] = True
    
    async def broadcast(self, message: Dict[str, Any], client_type: Optional[str] = None, symbols: Optional[Set[str]] = None):
        """
        Broadcast message to all clients (optionally filtered by type and subscriptions).
        
        Args:
            message: Message to broadcast
            client_type: Only send to clients of this type (None = all types)
            symbols: Only send to clients subscribed to these symbols (None = all clients)
        """
        if not self.clients:
            return
        
        disconnected = []
        sent_count = 0
        
        # Create a list copy to avoid modification during iteration
        clients_to_check = list(self.clients.items())
        
        for websocket, client_info in clients_to_check:
            # Skip if already removed
            if websocket not in self.clients:
                continue
            
            # Filter by client type if specified
            if client_type and client_info["type"] != client_type:
                continue
            
            # Filter by subscriptions if specified
            if symbols:
                client_subs = client_info["subscriptions"]
                if not client_subs.intersection(symbols):
                    continue
            
            try:
                # Check WebSocket state before sending
                try:
                    ws_state = getattr(websocket, 'client_state', None)
                    if ws_state is not None:
                        state_name = getattr(ws_state, 'name', None)
                        if state_name == 'DISCONNECTED':
                            disconnected.append(websocket)
                            continue
                except (AttributeError, Exception):
                    pass  # Can't check state, try to send anyway
                
                await websocket.send_json(message)
                sent_count += 1
            except Exception as e:
                error_str = str(e).lower()
                self.logger.debug(f"Error sending message to client {client_info['id']}: {e}")
                # Mark as disconnected if it's a connection error
                if "disconnect" in error_str or "closed" in error_str or "connection" in error_str:
                    disconnected.append(websocket)
        
        # Remove disconnected clients
        for ws in disconnected:
            if ws in self.clients:
                self.remove_client(ws)
        
        if sent_count > 0:
            self.logger.debug(f"Broadcast message to {sent_count} client(s)")
        elif client_type or symbols:
            self.logger.debug(f"No clients matched filters (type={client_type}, symbols={symbols})")
    
    def start_health_check(self):
        """Start health check task"""
        if self._is_running:
            return
        
        self._is_running = True
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        self.logger.info("Started WebSocket health check")
    
    def stop_health_check(self):
        """Stop health check task"""
        self._is_running = False
        if self._health_check_task:
            self._health_check_task.cancel()
            self._health_check_task = None
        self.logger.info("Stopped WebSocket health check")
    
    async def _health_check_loop(self):
        """Health check loop - monitors client connections"""
        while self._is_running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                now = datetime.now()
                timeout = timedelta(seconds=60)  # 60 second timeout
                disconnected = []
                
                # Create a copy of items to iterate over (since we'll be modifying the dict)
                clients_to_check = list(self.clients.items())
                
                for websocket, client_info in clients_to_check:
                    time_since_ping = now - client_info["last_ping"]
                    
                    # Check if WebSocket is actually still connected
                    try:
                        # Try to check WebSocket state (if available)
                        ws_state = getattr(websocket, 'client_state', None)
                        if ws_state is not None and ws_state.name == 'DISCONNECTED':
                            # Already disconnected, remove it
                            disconnected.append(websocket)
                            continue
                    except (AttributeError, Exception):
                        # Can't check state, rely on ping timeout
                        pass
                    
                    # Mark as dead if no ping in timeout period
                    if time_since_ping > timeout:
                        if client_info["is_alive"]:
                            self.logger.debug(
                                f"Client {client_info['id']} timed out (no ping for {time_since_ping.total_seconds():.1f}s)"
                            )
                            client_info["is_alive"] = False
                            disconnected.append(websocket)
                
                # Remove disconnected clients
                for ws in disconnected:
                    try:
                        # Check if WebSocket is actually disconnected before removing
                        try:
                            ws_state = getattr(ws, 'client_state', None)
                            if ws_state is not None:
                                state_name = getattr(ws_state, 'name', None)
                                if state_name != 'DISCONNECTED':
                                    # Not actually disconnected, skip
                                    continue
                        except (AttributeError, Exception):
                            # Can't check state, proceed with removal
                            pass
                        
                        self.remove_client(ws)
                    except Exception as e:
                        # Client might already be removed or WebSocket is invalid
                        self.logger.debug(f"Error removing client during health check: {e}")
                        # Force remove from dict if it still exists
                        if ws in self.clients:
                            try:
                                del self.clients[ws]
                            except Exception:
                                pass
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in health check loop: {e}", exc_info=True)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket manager statistics"""
        stats = {
            "total_clients": len(self.clients),
            "clients_by_type": {},
            "total_subscriptions": len(self.get_all_subscriptions()),
            "unique_symbols": list(self.get_all_subscriptions())
        }
        
        for client_info in self.clients.values():
            client_type = client_info["type"]
            stats["clients_by_type"][client_type] = stats["clients_by_type"].get(client_type, 0) + 1
        
        return stats


# Global WebSocket manager instance (singleton)
_websocket_manager: Optional[WebSocketManager] = None


def get_websocket_manager() -> WebSocketManager:
    """Get or create WebSocket manager instance"""
    global _websocket_manager
    if _websocket_manager is None:
        _websocket_manager = WebSocketManager()
    return _websocket_manager


