"""Order management system"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from enum import Enum
from src.utils.logger import setup_logger


class OrderStatus(Enum):
    """Order status enumeration"""
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    FAILED = "failed"


class OrderManager:
    """Manages order placement, tracking, and execution"""
    
    def __init__(self, is_paper_trading: bool = True):
        """
        Initialize order manager.
        
        Args:
            is_paper_trading: If True, simulate trades; if False, execute real trades
        """
        self.is_paper_trading = is_paper_trading
        self.orders = {}  # {order_id: order_dict}
        self.positions = {}  # {position_id: position_dict}
        self.logger = setup_logger(f"{__name__}.OrderManager")
    
    def create_order(
        self,
        symbol: str,
        side: str,
        amount: Decimal,
        price: Decimal,
        order_type: str = "market",
        exchange: Optional[str] = None
    ) -> Dict:
        """
        Create a new order.
        
        Args:
            symbol: Trading pair symbol
            side: 'buy' or 'sell'
            amount: Order amount
            price: Order price (for limit orders) or current price (for market orders)
            order_type: 'market' or 'limit'
            exchange: Exchange name
            
        Returns:
            Order dictionary
        """
        order_id = str(uuid.uuid4())
        
        order = {
            'id': order_id,
            'symbol': symbol,
            'side': side,
            'type': order_type,
            'amount': amount,
            'price': price,
            'status': OrderStatus.PENDING.value,
            'filled': Decimal('0'),
            'exchange': exchange,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        self.orders[order_id] = order
        self.logger.info(f"Created {order_type} {side} order {order_id} for {amount} {symbol} @ {price}")
        
        return order
    
    def execute_order(self, order_id: str, exchange_api, fill_price: Optional[Decimal] = None) -> bool:
        """
        Execute an order (paper or live).
        
        Args:
            order_id: Order ID
            exchange_api: Exchange API instance
            fill_price: Fill price (for paper trading)
            
        Returns:
            True if execution successful
        """
        if order_id not in self.orders:
            self.logger.error(f"Order {order_id} not found")
            return False
        
        order = self.orders[order_id]
        
        if self.is_paper_trading:
            return self._execute_paper_order(order, fill_price)
        else:
            return self._execute_live_order(order, exchange_api)
    
    def _execute_paper_order(self, order: Dict, fill_price: Optional[Decimal]) -> bool:
        """Execute order in paper trading mode"""
        try:
            if not fill_price:
                fill_price = order['price']
            
            order['status'] = OrderStatus.FILLED.value
            order['filled'] = order['amount']
            order['fill_price'] = fill_price
            order['updated_at'] = datetime.utcnow().isoformat()
            
            # Create or update position
            self._update_position_from_order(order)
            
            self.logger.info(f"Paper trade executed: {order['side']} {order['filled']} {order['symbol']} @ {fill_price}")
            return True
        except Exception as e:
            self.logger.error(f"Error executing paper order: {e}")
            order['status'] = OrderStatus.FAILED.value
            return False
    
    def _execute_live_order(self, order: Dict, exchange_api) -> bool:
        """Execute order on live exchange"""
        try:
            result = exchange_api.place_order(
                symbol=order['symbol'],
                side=order['side'],
                amount=order['amount'],
                order_type=order['type'],
                price=order['price'] if order['type'] == 'limit' else None
            )
            
            order['status'] = result['status']
            order['filled'] = result['filled']
            order['exchange_order_id'] = result['id']
            order['updated_at'] = datetime.utcnow().isoformat()
            
            if result['status'] == 'filled':
                self._update_position_from_order(order)
            
            self.logger.info(f"Live trade executed: {order['side']} {order['filled']} {order['symbol']}")
            return True
        except Exception as e:
            self.logger.error(f"Error executing live order: {e}")
            order['status'] = OrderStatus.FAILED.value
            return False
    
    def _update_position_from_order(self, order: Dict):
        """Update position from executed order"""
        symbol = order['symbol']
        side = order['side']
        amount = order['filled']
        price = order.get('fill_price', order['price'])
        
        position_id = f"{symbol}_{side}"
        
        if position_id in self.positions:
            # Update existing position
            position = self.positions[position_id]
            if side == 'buy':
                # Add to long position
                total_cost = (position['avg_price'] * position['amount']) + (price * amount)
                position['amount'] += amount
                position['avg_price'] = total_cost / position['amount']
            else:
                # Reduce position
                position['amount'] -= amount
                if position['amount'] <= 0:
                    del self.positions[position_id]
        else:
            # Create new position
            if side == 'buy':
                self.positions[position_id] = {
                    'symbol': symbol,
                    'side': 'long',
                    'amount': amount,
                    'avg_price': price,
                    'entry_time': datetime.utcnow().isoformat()
                }
    
    def cancel_order(self, order_id: str, exchange_api=None) -> bool:
        """Cancel an order"""
        if order_id not in self.orders:
            return False
        
        order = self.orders[order_id]
        
        if self.is_paper_trading:
            order['status'] = OrderStatus.CANCELLED.value
            order['updated_at'] = datetime.utcnow().isoformat()
            return True
        else:
            if exchange_api and order.get('exchange_order_id'):
                try:
                    exchange_api.cancel_order(order['exchange_order_id'], order['symbol'])
                    order['status'] = OrderStatus.CANCELLED.value
                    order['updated_at'] = datetime.utcnow().isoformat()
                    return True
                except Exception as e:
                    self.logger.error(f"Error canceling order: {e}")
                    return False
        
        return False
    
    def get_order(self, order_id: str) -> Optional[Dict]:
        """Get order by ID"""
        return self.orders.get(order_id)
    
    def get_open_orders(self) -> List[Dict]:
        """Get all open orders"""
        return [
            order for order in self.orders.values()
            if order['status'] in [OrderStatus.PENDING.value, OrderStatus.OPEN.value, OrderStatus.PARTIALLY_FILLED.value]
        ]
    
    def get_positions(self) -> List[Dict]:
        """Get all open positions"""
        return list(self.positions.values())
    
    def get_position(self, symbol: str, side: str = "long") -> Optional[Dict]:
        """Get position for a symbol"""
        position_id = f"{symbol}_{side}"
        return self.positions.get(position_id)
    
    def close_position(self, symbol: str, side: str, amount: Decimal, price: Decimal) -> Dict:
        """Close a position"""
        position_id = f"{symbol}_{side}"
        
        if position_id not in self.positions:
            return {}
        
        position = self.positions[position_id]
        close_amount = min(amount, position['amount'])
        
        # Create sell order
        order = self.create_order(
            symbol=symbol,
            side='sell' if side == 'long' else 'buy',
            amount=close_amount,
            price=price,
            order_type='market'
        )
        
        # Update position
        position['amount'] -= close_amount
        if position['amount'] <= 0:
            del self.positions[position_id]
        
        return order

