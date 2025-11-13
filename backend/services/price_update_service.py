"""Price update service for real-time position price updates"""

import sys
import asyncio
from pathlib import Path
from typing import Dict, Set, List, Optional
from decimal import Decimal
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from fastapi import WebSocket
from backend.services.price_service import get_price_service
from src.utils.logger import setup_logger


class PriceUpdateService:
    """Service for managing real-time price updates for positions"""
    
    def __init__(self, update_interval: float = 5.0):  # Increased from 3.0 to 5.0 to reduce API calls
        """
        Initialize price update service.
        
        Args:
            update_interval: How often to poll for price updates (in seconds)
        """
        self.update_interval = update_interval
        self.price_service = get_price_service("binance")
        self.websocket_clients: Set[WebSocket] = set()
        self.monitored_symbols: Set[str] = set()
        self.current_prices: Dict[str, Decimal] = {}
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        self.logger = setup_logger(f"{__name__}.PriceUpdateService")
    
    def add_websocket_client(self, websocket: WebSocket):
        """Add a WebSocket client to receive price updates"""
        self.websocket_clients.add(websocket)
        self.logger.info(f"Added WebSocket client. Total clients: {len(self.websocket_clients)}")
        
        # Start polling if not already running
        if not self.is_running:
            self.start_polling()
    
    def remove_websocket_client(self, websocket: WebSocket):
        """Remove a WebSocket client"""
        self.websocket_clients.discard(websocket)
        self.logger.info(f"Removed WebSocket client. Total clients: {len(self.websocket_clients)}")
        
        # Stop polling if no clients
        if len(self.websocket_clients) == 0:
            self.stop_polling()
    
    def add_symbol(self, symbol: str):
        """Add a symbol to monitor"""
        self.monitored_symbols.add(symbol)
        self.logger.debug(f"Added symbol to monitor: {symbol}")
    
    def remove_symbol(self, symbol: str):
        """Remove a symbol from monitoring"""
        self.monitored_symbols.discard(symbol)
        self.logger.debug(f"Removed symbol from monitor: {symbol}")
    
    def update_monitored_symbols(self, symbols: List[str]):
        """Update the list of monitored symbols"""
        self.monitored_symbols = set(symbols)
        self.logger.debug(f"Updated monitored symbols: {len(self.monitored_symbols)} symbols")
    
    def start_polling(self):
        """Start the price polling task"""
        if self.is_running:
            return
        
        self.is_running = True
        self._task = asyncio.create_task(self._poll_prices())
        self.logger.info("Started price polling service")
    
    def stop_polling(self):
        """Stop the price polling task"""
        if not self.is_running:
            return
        
        self.is_running = False
        if self._task:
            self._task.cancel()
        self.logger.info("Stopped price polling service")
    
    async def _poll_prices(self):
        """Poll for price updates and broadcast to WebSocket clients"""
        while self.is_running:
            try:
                if not self.monitored_symbols:
                    # No symbols to monitor, wait and check again
                    await asyncio.sleep(self.update_interval)
                    continue
                
                # Fetch prices for all monitored symbols
                price_updates: Dict[str, float] = {}
                for symbol in self.monitored_symbols:
                    try:
                        price = self.price_service.get_current_price(symbol)
                        if price and price > 0:
                            # Check if price changed
                            old_price = self.current_prices.get(symbol)
                            if old_price != price:
                                price_updates[symbol] = float(price)
                                self.current_prices[symbol] = price
                    except Exception as e:
                        self.logger.warning(f"Error fetching price for {symbol}: {e}")
                
                # Broadcast price updates to all connected clients
                if price_updates and self.websocket_clients:
                    message = {
                        "type": "price_update",
                        "timestamp": datetime.utcnow().isoformat(),
                        "prices": price_updates
                    }
                    
                    # Send to all clients (remove disconnected ones)
                    disconnected_clients = set()
                    # Create a copy of the set to iterate over (since we'll be modifying it)
                    clients_to_check = list(self.websocket_clients)
                    
                    for client in clients_to_check:
                        # Check if client is still in the set (might have been removed)
                        if client not in self.websocket_clients:
                            continue
                        
                        # Check WebSocket state before sending
                        try:
                            # Check if WebSocket is still open
                            client_state = getattr(client, 'client_state', None)
                            if client_state is not None:
                                state_name = getattr(client_state, 'name', None)
                                if state_name == 'DISCONNECTED':
                                    disconnected_clients.add(client)
                                    continue
                            
                            # Try to send
                            await client.send_json(message)
                        except Exception as e:
                            # Client disconnected or error sending
                            self.logger.debug(f"Error sending price update to client: {e}")
                            disconnected_clients.add(client)
                    
                    # Remove disconnected clients
                    for client in disconnected_clients:
                        self.remove_websocket_client(client)
                
                # Wait before next poll
                await asyncio.sleep(self.update_interval)
                
            except asyncio.CancelledError:
                self.logger.info("Price polling task cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in price polling: {e}", exc_info=True)
                await asyncio.sleep(self.update_interval)
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get the most recent price for a symbol"""
        price = self.current_prices.get(symbol)
        return float(price) if price else None


# Global singleton instance
_price_update_service: Optional[PriceUpdateService] = None


def get_price_update_service() -> PriceUpdateService:
    """Get the global price update service instance"""
    global _price_update_service
    if _price_update_service is None:
        _price_update_service = PriceUpdateService()
    return _price_update_service


