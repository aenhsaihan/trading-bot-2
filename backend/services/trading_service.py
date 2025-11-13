"""Trading service for managing positions and orders"""

import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.utils.paper_trading import PaperTrading
from src.risk.stop_loss import StopLoss
from src.risk.trailing_stop import TrailingStopLoss
from src.utils.logger import setup_logger
from .price_service import get_price_service


class TradingService:
    """Service layer for trading operations"""
    
    def __init__(self, initial_balance: Decimal = Decimal('10000'), exchange_name: str = "binance"):
        """
        Initialize trading service.
        
        Args:
            initial_balance: Starting balance for paper trading
            exchange_name: Exchange to use for price data (default: 'binance')
        """
        self.paper_trading = PaperTrading(initial_balance)
        self.stop_loss = StopLoss(stop_loss_percent=0.03)  # 3% default
        self.trailing_stop = TrailingStopLoss(trailing_percent=0.025)  # 2.5% default
        self.positions: Dict[str, Dict] = {}  # {position_id: position_data}
        self.logger = setup_logger(f"{__name__}.TradingService")
        self.price_service = get_price_service(exchange_name)
    
    def get_balance(self) -> Dict:
        """Get account balance and portfolio value"""
        try:
            balance = float(self.paper_trading.get_balance())
            
            # Calculate total portfolio value
            current_prices = self._get_current_prices()
            total_value = float(self.paper_trading.get_total_value(current_prices))
            total_pnl = float(self.paper_trading.get_pnl(current_prices))
            
            # Calculate P&L percentage safely
            initial_balance = float(self.paper_trading.initial_balance)
            total_pnl_percent = (total_pnl / initial_balance * 100) if initial_balance > 0 else 0.0
            
            return {
                'balance': balance,
                'currency': 'USDT',
                'total_value': total_value,
                'total_pnl': total_pnl,
                'total_pnl_percent': total_pnl_percent
            }
        except Exception as e:
            self.logger.error(f"Error in get_balance: {e}", exc_info=True)
            raise
    
    def get_positions(self) -> List[Dict]:
        """Get all open positions with current prices and P&L"""
        paper_positions = self.paper_trading.get_positions()
        current_prices = self._get_current_prices()
        
        positions = []
        for symbol, paper_pos in paper_positions.items():
            position_id = self._get_position_id_for_symbol(symbol)
            # If no position_id found, create one (for positions created before we started tracking IDs)
            if not position_id:
                # Try to find by matching symbol in existing positions
                # If still not found, create a new position_id for this paper position
                # Replace '/' with '-' in symbol to avoid URL path issues
                safe_symbol = symbol.replace('/', '-')
                position_id = f"{safe_symbol}_{uuid4().hex[:8]}_{int(datetime.utcnow().timestamp())}"
                self.positions[position_id] = {
                    'symbol': symbol,
                    'side': paper_pos.get('side', 'long'),
                    'stop_loss_percent': None,
                    'trailing_stop_percent': None,
                    'created_at': paper_pos.get('entry_time', datetime.utcnow().isoformat())
                }
            
            position_data = self.positions.get(position_id, {})
            current_price = current_prices.get(symbol, Decimal(str(paper_pos['entry_price'])))
            
            # Calculate P&L
            entry_price = Decimal(str(paper_pos['entry_price']))
            amount = Decimal(str(paper_pos['amount']))
            side = paper_pos.get('side', 'long')
            
            if side == 'long':
                pnl = (current_price - entry_price) * amount
            else:  # short
                pnl = (entry_price - current_price) * amount
            
            pnl_percent = float((pnl / (entry_price * amount)) * 100) if entry_price * amount > 0 else 0
            
            # Get stop loss and trailing stop
            stop_loss_price = None
            stop_loss_percent = position_data.get('stop_loss_percent')
            if stop_loss_percent is not None and stop_loss_percent > 0:
                stop_loss_price = float(self.stop_loss.calculate_stop_price(entry_price, side))
            
            trailing_stop_price = None
            trailing_stop_percent = position_data.get('trailing_stop_percent')
            if trailing_stop_percent is not None and trailing_stop_percent > 0:
                if position_id in self.trailing_stop.positions:
                    trailing_stop_price = float(self.trailing_stop.get_stop_price(position_id) or entry_price)
            
            positions.append({
                'id': position_id,
                'symbol': symbol,
                'side': side,
                'amount': float(amount),
                'entry_price': float(entry_price),
                'current_price': float(current_price),
                'pnl': float(pnl),
                'pnl_percent': pnl_percent,
                'stop_loss': stop_loss_price,
                'stop_loss_percent': float(stop_loss_percent) if stop_loss_percent and stop_loss_percent > 0 else None,
                'trailing_stop': float(trailing_stop_percent) if trailing_stop_percent and trailing_stop_percent > 0 else None,
                'entry_time': paper_pos.get('entry_time', datetime.utcnow().isoformat()),
                'created_at': position_data.get('created_at', datetime.utcnow().isoformat())
            })
        
        return positions
    
    def get_position_symbols(self) -> List[str]:
        """Get list of symbols from all open positions (for price monitoring)"""
        paper_positions = self.paper_trading.get_positions()
        return list(paper_positions.keys())
    
    def open_position(
        self,
        symbol: str,
        side: str,
        amount: float,
        stop_loss_percent: Optional[float] = None,
        trailing_stop_percent: Optional[float] = None
    ) -> Dict:
        """
        Open a new position.
        
        Args:
            symbol: Trading pair symbol
            side: 'long' or 'short'
            amount: Position amount
            stop_loss_percent: Optional stop loss percentage
            trailing_stop_percent: Optional trailing stop percentage
            
        Returns:
            Created position dictionary
        """
        # Get current price (mock for now, TODO: get from exchange API)
        current_price = self._get_current_price(symbol)
        
        # Execute trade
        if side == 'long':
            result = self.paper_trading.buy(symbol, Decimal(str(amount)), current_price)
        else:  # short
            # For short, we'd need to implement short selling in PaperTrading
            # For now, we'll simulate it
            result = self._simulate_short_sell(symbol, Decimal(str(amount)), current_price)
        
        if not result.get('success'):
            raise ValueError(result.get('error', 'Failed to open position'))
        
        # Create position record
        # Replace '/' with '-' in symbol to avoid URL path issues
        safe_symbol = symbol.replace('/', '-')
        position_id = f"{safe_symbol}_{uuid4().hex[:8]}_{int(datetime.utcnow().timestamp())}"
        
        # Initialize trailing stop if specified
        if trailing_stop_percent:
            self.trailing_stop.trailing_percent = Decimal(str(trailing_stop_percent / 100))
            self.trailing_stop.initialize_position(position_id, current_price, side)
        
        # Store position metadata
        self.positions[position_id] = {
            'symbol': symbol,
            'side': side,
            'stop_loss_percent': stop_loss_percent,
            'trailing_stop_percent': trailing_stop_percent,
            'created_at': datetime.utcnow().isoformat()
        }
        
        # Get the created position - build it directly instead of calling get_positions()
        # to avoid any issues with position lookup
        paper_pos = self.paper_trading.get_position(symbol)
        if not paper_pos:
            raise ValueError("Position was created but not found in paper trading")
        
        entry_price = Decimal(str(paper_pos['entry_price']))
        amount_decimal = Decimal(str(paper_pos['amount']))
        
        # Calculate P&L (should be 0 for new position)
        pnl = Decimal('0')
        pnl_percent = 0.0
        
        # Get stop loss and trailing stop
        stop_loss_price = None
        if stop_loss_percent:
            # Update stop loss percentage before calculating price
            self.stop_loss.update_percent(stop_loss_percent / 100)
            stop_loss_price = float(self.stop_loss.calculate_stop_price(entry_price, side))
        
        trailing_stop_price = None
        if trailing_stop_percent and position_id in self.trailing_stop.positions:
            trailing_stop_price = float(self.trailing_stop.get_stop_price(position_id) or entry_price)
        
        created_position = {
            'id': position_id,
            'symbol': symbol,
            'side': side,
            'amount': float(amount_decimal),
            'entry_price': float(entry_price),
            'current_price': float(current_price),
            'pnl': float(pnl),
            'pnl_percent': pnl_percent,
            'stop_loss': stop_loss_price,
            'stop_loss_percent': float(stop_loss_percent) if stop_loss_percent and stop_loss_percent > 0 else None,
            'trailing_stop': float(trailing_stop_percent) if trailing_stop_percent and trailing_stop_percent > 0 else None,
            'entry_time': paper_pos.get('entry_time', datetime.utcnow().isoformat()),
            'created_at': self.positions[position_id]['created_at']
        }
        
        self.logger.info(f"Opened {side} position: {amount} {symbol} @ {current_price}")
        return created_position
    
    def close_position(self, position_id: str) -> Dict:
        """
        Close a position.
        
        Args:
            position_id: Position identifier (may contain '/' or '-' in symbol part)
            
        Returns:
            Closed position information
        """
        # Try direct lookup first
        position = self.positions.get(position_id)
        
        # If not found, try with '/' replaced by '-' (for old IDs with '/' in them)
        if not position:
            normalized_id = position_id.replace('/', '-')
            position = self.positions.get(normalized_id)
        
        # If still not found, try to find by matching the symbol part
        if not position:
            # Extract symbol from position_id (format: SYMBOL_UUID_TIMESTAMP)
            # Try both with '/' and '-' in the symbol
            for pos_id, pos_data in self.positions.items():
                # Check if the position_id matches when we normalize the symbol
                pos_symbol = pos_data.get('symbol', '')
                # Create normalized versions
                pos_id_normalized = pos_id.replace('/', '-')
                position_id_normalized = position_id.replace('/', '-')
                if pos_id_normalized == position_id_normalized:
                    position = pos_data
                    position_id = pos_id  # Use the actual stored ID
                    break
        
        if not position:
            raise ValueError(f"Position {position_id} not found")
        
        symbol = position['symbol']
        side = position['side']
        
        # Get current position from paper trading
        paper_pos = self.paper_trading.get_position(symbol)
        if not paper_pos:
            raise ValueError(f"No open position found for {symbol}")
        
        # Get current price
        current_price = self._get_current_price(symbol)
        amount = Decimal(str(paper_pos['amount']))
        
        # Execute close trade
        if side == 'long':
            result = self.paper_trading.sell(symbol, amount, current_price)
        else:  # short
            result = self._simulate_short_cover(symbol, amount, current_price)
        
        if not result.get('success'):
            raise ValueError(result.get('error', 'Failed to close position'))
        
        # Remove trailing stop tracking
        self.trailing_stop.remove_position(position_id)
        
        # Remove position record
        del self.positions[position_id]
        
        self.logger.info(f"Closed {side} position: {amount} {symbol} @ {current_price}")
        return {
            'id': position_id,
            'symbol': symbol,
            'closed_at': datetime.utcnow().isoformat(),
            'close_price': float(current_price),
            'profit': float(result.get('trade', {}).get('profit', 0))
        }
    
    def set_stop_loss(self, position_id: str, stop_loss_percent: float) -> Dict:
        """
        Set stop loss for a position.
        
        Args:
            position_id: Position identifier
            stop_loss_percent: Stop loss percentage (0 to remove stop loss)
            
        Returns:
            Updated position
        """
        position = self.positions.get(position_id)
        if not position:
            raise ValueError(f"Position {position_id} not found")
        
        position['stop_loss_percent'] = stop_loss_percent if stop_loss_percent > 0 else None
        if stop_loss_percent > 0:
            self.stop_loss.update_percent(stop_loss_percent / 100)
        
        positions = self.get_positions()
        updated = next((p for p in positions if p['id'] == position_id), None)
        
        if not updated:
            raise ValueError("Failed to retrieve updated position")
        
        self.logger.info(f"Set stop loss for {position_id}: {stop_loss_percent}%")
        return updated
    
    def set_trailing_stop(self, position_id: str, trailing_stop_percent: float) -> Dict:
        """
        Set trailing stop for a position.
        
        Args:
            position_id: Position identifier
            trailing_stop_percent: Trailing stop percentage (0 to remove trailing stop)
            
        Returns:
            Updated position
        """
        position = self.positions.get(position_id)
        if not position:
            raise ValueError(f"Position {position_id} not found")
        
        if trailing_stop_percent > 0:
            position['trailing_stop_percent'] = trailing_stop_percent
            
            # Update trailing stop
            self.trailing_stop.trailing_percent = Decimal(str(trailing_stop_percent / 100))
            
            # Re-initialize if position exists in trailing stop
            if position_id in self.trailing_stop.positions:
                paper_pos = self.paper_trading.get_position(position['symbol'])
                if paper_pos:
                    entry_price = Decimal(str(paper_pos['entry_price']))
                    self.trailing_stop.initialize_position(position_id, entry_price, position['side'])
        else:
            # Remove trailing stop
            position['trailing_stop_percent'] = None
            self.trailing_stop.remove_position(position_id)
        
        positions = self.get_positions()
        updated = next((p for p in positions if p['id'] == position_id), None)
        
        if not updated:
            raise ValueError("Failed to retrieve updated position")
        
        self.logger.info(f"Set trailing stop for {position_id}: {trailing_stop_percent}%")
        return updated
    
    def _get_current_price(self, symbol: str) -> Decimal:
        """
        Get current price for a symbol from exchange.
        
        Falls back to mock prices if exchange is not available.
        """
        if self.price_service and self.price_service.is_connected():
            try:
                price = self.price_service.get_current_price(symbol)
                if price > 0:
                    return price
                else:
                    self.logger.warning(f"Got zero price for {symbol}, falling back to mock")
            except Exception as e:
                self.logger.error(f"Error fetching real price for {symbol}: {e}, falling back to mock")
        
        # Fallback to mock prices if exchange unavailable
        mock_prices = {
            'BTC/USDT': Decimal('46500'),
            'ETH/USDT': Decimal('2500'),
            'BNB/USDT': Decimal('320'),
            'SOL/USDT': Decimal('100'),
            'DOGE/USDT': Decimal('0.08'),
            'ADA/USDT': Decimal('0.5'),
            'MATIC/USDT': Decimal('0.8'),
            'AVAX/USDT': Decimal('35'),
            'XRP/USDT': Decimal('0.6'),
            'DOT/USDT': Decimal('7'),
            'LINK/USDT': Decimal('15'),
            'UNI/USDT': Decimal('6'),
            'ATOM/USDT': Decimal('10'),
            'ALGO/USDT': Decimal('0.2'),
            'LTC/USDT': Decimal('70'),
            'BCH/USDT': Decimal('250'),
            'ETC/USDT': Decimal('20'),
            'XLM/USDT': Decimal('0.12'),
            'FIL/USDT': Decimal('5'),
            'AAVE/USDT': Decimal('90'),
            'SUSHI/USDT': Decimal('1.5'),
            'COMP/USDT': Decimal('50'),
        }
        return mock_prices.get(symbol, Decimal('1000'))
    
    def _get_current_prices(self) -> Dict[str, Decimal]:
        """
        Get current prices for all symbols from exchange.
        
        Falls back to mock prices if exchange is not available.
        """
        paper_positions = self.paper_trading.get_positions()
        symbols = list(paper_positions.keys())
        
        if self.price_service and self.price_service.is_connected() and symbols:
            try:
                prices = self.price_service.get_current_prices(symbols)
                # Filter out zero prices and use fallback
                result = {}
                for symbol in symbols:
                    price = prices.get(symbol, Decimal('0'))
                    if price > 0:
                        result[symbol] = price
                    else:
                        result[symbol] = self._get_current_price(symbol)  # Fallback
                return result
            except Exception as e:
                self.logger.error(f"Error fetching real prices: {e}, falling back to mocks")
        
        # Fallback: fetch individually (which will use mocks if needed)
        prices = {}
        for symbol in symbols:
            prices[symbol] = self._get_current_price(symbol)
        return prices
    
    def _get_position_id_for_symbol(self, symbol: str) -> Optional[str]:
        """Get position ID for a symbol"""
        for pos_id, pos_data in self.positions.items():
            if pos_data.get('symbol') == symbol:
                return pos_id
        return None
    
    def _simulate_short_sell(self, symbol: str, amount: Decimal, price: Decimal) -> Dict:
        """Simulate short selling (for paper trading)"""
        # In real trading, short selling is more complex
        # For paper trading, we'll track it as a negative position
        revenue = amount * price
        self.paper_trading.balance += revenue
        
        # Store short position
        if symbol not in self.paper_trading.positions:
            self.paper_trading.positions[symbol] = {
                'amount': amount,
                'entry_price': price,
                'side': 'short',
                'entry_time': datetime.utcnow().isoformat()
            }
        else:
            pos = self.paper_trading.positions[symbol]
            if pos['side'] == 'short':
                total_revenue = (pos['entry_price'] * pos['amount']) + revenue
                pos['amount'] += amount
                pos['entry_price'] = total_revenue / pos['amount']
        
        return {
            'success': True,
            'trade': {
                'symbol': symbol,
                'side': 'sell',
                'amount': float(amount),
                'price': float(price),
                'revenue': float(revenue),
                'timestamp': datetime.utcnow().isoformat()
            }
        }
    
    def _simulate_short_cover(self, symbol: str, amount: Decimal, price: Decimal) -> Dict:
        """Simulate covering a short position"""
        if symbol not in self.paper_trading.positions:
            return {'success': False, 'error': 'No short position found'}
        
        pos = self.paper_trading.positions[symbol]
        if pos['side'] != 'short':
            return {'success': False, 'error': 'Position is not a short'}
        
        if amount > pos['amount']:
            amount = pos['amount']
        
        cost = amount * price
        profit = (pos['entry_price'] - price) * amount
        
        self.paper_trading.balance -= cost
        
        pos['amount'] -= amount
        if pos['amount'] <= 0:
            del self.paper_trading.positions[symbol]
        
        return {
            'success': True,
            'trade': {
                'symbol': symbol,
                'side': 'buy',
                'amount': float(amount),
                'price': float(price),
                'cost': float(cost),
                'profit': float(profit),
                'timestamp': datetime.utcnow().isoformat()
            }
        }

