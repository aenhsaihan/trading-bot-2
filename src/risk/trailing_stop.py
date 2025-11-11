"""Trailing stop loss implementation"""

from decimal import Decimal
from typing import Dict, Optional
from src.utils.logger import setup_logger


class TrailingStopLoss:
    """Trailing stop loss that adjusts with favorable price movement"""
    
    def __init__(self, trailing_percent: float = 0.025):
        """
        Initialize trailing stop loss.
        
        Args:
            trailing_percent: Trailing stop percentage (e.g., 0.025 for 2.5%)
        """
        self.trailing_percent = Decimal(str(trailing_percent))
        self.logger = setup_logger(f"{__name__}.TrailingStopLoss")
        self.positions = {}  # Track positions: {position_id: {'peak_price': ..., 'stop_price': ...}}
    
    def initialize_position(self, position_id: str, entry_price: Decimal, side: str = "long"):
        """
        Initialize trailing stop for a new position.
        
        Args:
            position_id: Unique position identifier
            entry_price: Entry price
            side: 'long' or 'short'
        """
        if side.lower() == "long":
            stop_price = entry_price * (Decimal('1') - self.trailing_percent)
        else:
            stop_price = entry_price * (Decimal('1') + self.trailing_percent)
        
        self.positions[position_id] = {
            'entry_price': entry_price,
            'peak_price': entry_price,
            'stop_price': stop_price,
            'side': side.lower()
        }
        
        self.logger.info(f"Trailing stop initialized for position {position_id}: entry={entry_price}, stop={stop_price}")
    
    def update(self, position_id: str, current_price: Decimal) -> Optional[Decimal]:
        """
        Update trailing stop based on current price.
        
        Args:
            position_id: Position identifier
            current_price: Current market price
            
        Returns:
            Updated stop price, or None if position not found
        """
        if position_id not in self.positions:
            return None
        
        position = self.positions[position_id]
        side = position['side']
        peak_price = position['peak_price']
        
        # Update peak price for long positions (price going up)
        # or for short positions (price going down)
        if side == "long":
            if current_price > peak_price:
                position['peak_price'] = current_price
                # Update stop price to trail below peak
                position['stop_price'] = current_price * (Decimal('1') - self.trailing_percent)
                self.logger.debug(f"Updated trailing stop for {position_id}: peak={current_price}, stop={position['stop_price']}")
        else:  # short
            if current_price < peak_price:
                position['peak_price'] = current_price
                # Update stop price to trail above peak
                position['stop_price'] = current_price * (Decimal('1') + self.trailing_percent)
                self.logger.debug(f"Updated trailing stop for {position_id}: peak={current_price}, stop={position['stop_price']}")
        
        return position['stop_price']
    
    def should_trigger(self, position_id: str, current_price: Decimal) -> bool:
        """
        Check if trailing stop should be triggered.
        
        Args:
            position_id: Position identifier
            current_price: Current market price
            
        Returns:
            True if trailing stop should be triggered
        """
        if position_id not in self.positions:
            return False
        
        position = self.positions[position_id]
        stop_price = position['stop_price']
        side = position['side']
        
        if side == "long":
            # For long positions, trigger if price drops below stop price
            return current_price <= stop_price
        else:
            # For short positions, trigger if price rises above stop price
            return current_price >= stop_price
    
    def get_stop_price(self, position_id: str) -> Optional[Decimal]:
        """Get current stop price for a position"""
        if position_id in self.positions:
            return self.positions[position_id]['stop_price']
        return None
    
    def get_position_info(self, position_id: str) -> Optional[Dict]:
        """Get trailing stop information for a position"""
        if position_id in self.positions:
            pos = self.positions[position_id].copy()
            # Convert Decimal to float for JSON serialization
            for key in ['entry_price', 'peak_price', 'stop_price']:
                pos[key] = float(pos[key])
            return pos
        return None
    
    def remove_position(self, position_id: str):
        """Remove position from tracking"""
        if position_id in self.positions:
            del self.positions[position_id]
            self.logger.info(f"Removed trailing stop for position {position_id}")
    
    def update_percent(self, new_percent: float):
        """Update trailing stop percentage for all positions"""
        self.trailing_percent = Decimal(str(new_percent))
        
        # Recalculate stop prices for all positions
        for position_id, position in self.positions.items():
            peak_price = position['peak_price']
            side = position['side']
            
            if side == "long":
                position['stop_price'] = peak_price * (Decimal('1') - self.trailing_percent)
            else:
                position['stop_price'] = peak_price * (Decimal('1') + self.trailing_percent)
        
        self.logger.info(f"Trailing stop percentage updated to {new_percent * 100}% for all positions")

