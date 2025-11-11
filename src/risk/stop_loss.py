"""Stop loss implementation"""

from decimal import Decimal
from typing import Dict, Optional
from src.utils.logger import setup_logger


class StopLoss:
    """Fixed stop loss management"""
    
    def __init__(self, stop_loss_percent: float = 0.03):
        """
        Initialize stop loss.
        
        Args:
            stop_loss_percent: Stop loss percentage (e.g., 0.03 for 3%)
        """
        self.stop_loss_percent = Decimal(str(stop_loss_percent))
        self.logger = setup_logger(f"{__name__}.StopLoss")
    
    def calculate_stop_price(self, entry_price: Decimal, side: str = "long") -> Decimal:
        """
        Calculate stop loss price.
        
        Args:
            entry_price: Entry price of the position
            side: 'long' or 'short'
            
        Returns:
            Stop loss price
        """
        if side.lower() == "long":
            # For long positions, stop loss is below entry price
            stop_price = entry_price * (Decimal('1') - self.stop_loss_percent)
        else:
            # For short positions, stop loss is above entry price
            stop_price = entry_price * (Decimal('1') + self.stop_loss_percent)
        
        return stop_price
    
    def should_trigger(self, current_price: Decimal, entry_price: Decimal, side: str = "long") -> bool:
        """
        Check if stop loss should be triggered.
        
        Args:
            current_price: Current market price
            entry_price: Entry price of the position
            side: 'long' or 'short'
            
        Returns:
            True if stop loss should be triggered
        """
        stop_price = self.calculate_stop_price(entry_price, side)
        
        if side.lower() == "long":
            # For long positions, trigger if price drops below stop price
            return current_price <= stop_price
        else:
            # For short positions, trigger if price rises above stop price
            return current_price >= stop_price
    
    def get_stop_loss_info(self, entry_price: Decimal, side: str = "long") -> Dict:
        """
        Get stop loss information.
        
        Args:
            entry_price: Entry price
            side: 'long' or 'short'
            
        Returns:
            Dictionary with stop loss details
        """
        stop_price = self.calculate_stop_price(entry_price, side)
        loss_amount = abs(entry_price - stop_price)
        loss_percent = (loss_amount / entry_price) * Decimal('100')
        
        return {
            'stop_price': stop_price,
            'entry_price': entry_price,
            'loss_percent': float(loss_percent),
            'side': side
        }
    
    def update_percent(self, new_percent: float):
        """Update stop loss percentage"""
        self.stop_loss_percent = Decimal(str(new_percent))
        self.logger.info(f"Stop loss percentage updated to {new_percent * 100}%")

