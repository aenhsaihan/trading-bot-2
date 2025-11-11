"""Paper trading simulation"""

from decimal import Decimal
from datetime import datetime
from typing import Dict, Optional
from src.utils.logger import setup_logger


class PaperTrading:
    """Simulates trading without real money"""
    
    def __init__(self, initial_balance: Decimal = Decimal('10000')):
        """
        Initialize paper trading account.
        
        Args:
            initial_balance: Starting balance in quote currency (e.g., USDT)
        """
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.positions = {}  # {symbol: {'amount': ..., 'entry_price': ..., 'side': ...}}
        self.trade_history = []
        self.logger = setup_logger(f"{__name__}.PaperTrading")
    
    def get_balance(self, currency: str = "USDT") -> Decimal:
        """Get available balance"""
        return self.balance
    
    def can_afford(self, amount: Decimal, price: Decimal) -> bool:
        """Check if account can afford the trade"""
        cost = amount * price
        return cost <= self.balance
    
    def buy(self, symbol: str, amount: Decimal, price: Decimal) -> Dict:
        """
        Simulate a buy order.
        
        Args:
            symbol: Trading pair symbol
            amount: Amount to buy
            price: Buy price
            
        Returns:
            Trade result dictionary
        """
        cost = amount * price
        
        if cost > self.balance:
            self.logger.warning(f"Insufficient balance: need {cost}, have {self.balance}")
            return {'success': False, 'error': 'Insufficient balance'}
        
        self.balance -= cost
        
        # Update position
        if symbol in self.positions:
            pos = self.positions[symbol]
            if pos['side'] == 'long':
                # Add to existing long position
                total_cost = (pos['entry_price'] * pos['amount']) + cost
                pos['amount'] += amount
                pos['entry_price'] = total_cost / pos['amount']
            else:
                # Close short position
                if pos['amount'] <= amount:
                    # Fully close short
                    profit = (pos['entry_price'] - price) * pos['amount']
                    self.balance += profit
                    del self.positions[symbol]
                else:
                    # Partially close short
                    profit = (pos['entry_price'] - price) * amount
                    self.balance += profit
                    pos['amount'] -= amount
        else:
            # New long position
            self.positions[symbol] = {
                'amount': amount,
                'entry_price': price,
                'side': 'long',
                'entry_time': datetime.utcnow().isoformat()
            }
        
        trade = {
            'symbol': symbol,
            'side': 'buy',
            'amount': amount,
            'price': price,
            'cost': cost,
            'timestamp': datetime.utcnow().isoformat(),
            'balance_after': self.balance
        }
        
        self.trade_history.append(trade)
        self.logger.info(f"Paper buy: {amount} {symbol} @ {price}, balance: {self.balance}")
        
        return {'success': True, 'trade': trade}
    
    def sell(self, symbol: str, amount: Decimal, price: Decimal) -> Dict:
        """
        Simulate a sell order.
        
        Args:
            symbol: Trading pair symbol
            amount: Amount to sell
            price: Sell price
            
        Returns:
            Trade result dictionary
        """
        if symbol not in self.positions or self.positions[symbol]['side'] != 'long':
            self.logger.warning(f"No long position found for {symbol}")
            return {'success': False, 'error': 'No position to sell'}
        
        pos = self.positions[symbol]
        
        if amount > pos['amount']:
            amount = pos['amount']  # Can't sell more than owned
        
        revenue = amount * price
        profit = (price - pos['entry_price']) * amount
        
        self.balance += revenue
        
        # Update position
        pos['amount'] -= amount
        if pos['amount'] <= 0:
            del self.positions[symbol]
        
        trade = {
            'symbol': symbol,
            'side': 'sell',
            'amount': amount,
            'price': price,
            'revenue': revenue,
            'profit': profit,
            'timestamp': datetime.utcnow().isoformat(),
            'balance_after': self.balance
        }
        
        self.trade_history.append(trade)
        self.logger.info(f"Paper sell: {amount} {symbol} @ {price}, profit: {profit}, balance: {self.balance}")
        
        return {'success': True, 'trade': trade}
    
    def get_positions(self) -> Dict:
        """Get all open positions"""
        return self.positions.copy()
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """Get position for a symbol"""
        return self.positions.get(symbol)
    
    def get_total_value(self, current_prices: Dict[str, Decimal]) -> Decimal:
        """
        Calculate total portfolio value.
        
        Args:
            current_prices: Dictionary of {symbol: current_price}
            
        Returns:
            Total portfolio value
        """
        total = self.balance
        
        for symbol, position in self.positions.items():
            if symbol in current_prices:
                current_price = current_prices[symbol]
                position_value = position['amount'] * current_price
                total += position_value
        
        return total
    
    def get_pnl(self, current_prices: Dict[str, Decimal]) -> Decimal:
        """
        Calculate profit and loss.
        
        Args:
            current_prices: Dictionary of {symbol: current_price}
            
        Returns:
            Total P&L
        """
        total_value = self.get_total_value(current_prices)
        return total_value - self.initial_balance
    
    def get_trade_history(self) -> list:
        """Get trade history"""
        return self.trade_history.copy()

