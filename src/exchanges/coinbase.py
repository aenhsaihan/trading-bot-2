"""Coinbase Pro exchange implementation"""

import ccxt
from decimal import Decimal
from typing import Dict, List, Optional, Any
from .base import ExchangeBase
from src.utils.logger import setup_logger


class CoinbaseExchange(ExchangeBase):
    """Coinbase Pro exchange implementation using ccxt"""
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None, sandbox: bool = False):
        super().__init__("coinbase", api_key, api_secret, sandbox)
        self.logger = setup_logger(f"{__name__}.{self.name}")
        self.exchange = None
    
    def connect(self) -> bool:
        """Connect to Coinbase Pro"""
        try:
            config = {
                'apiKey': self.api_key,
                'secret': self.api_secret,
                'enableRateLimit': True,
            }
            
            if self.sandbox:
                # Coinbase Pro uses different endpoint for sandbox
                config['urls'] = {
                    'api': {
                        'public': 'https://public.sandbox.pro.coinbase.com',
                        'private': 'https://public.sandbox.pro.coinbase.com',
                    }
                }
            
            self.exchange = ccxt.coinbasepro(config)
            self.exchange.load_markets()
            self._connected = True
            self.logger.info(f"Connected to Coinbase Pro ({'sandbox' if self.sandbox else 'live'})")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to Coinbase Pro: {e}")
            self._connected = False
            return False
    
    def get_balance(self, currency: str = "USDT") -> Decimal:
        """Get account balance"""
        try:
            balance = self.exchange.fetch_balance()
            # Coinbase uses USD instead of USDT
            if currency == "USDT":
                currency = "USD"
            
            if currency in balance:
                return Decimal(str(balance[currency]['free']))
            return Decimal('0')
        except Exception as e:
            self.logger.error(f"Error fetching balance: {e}")
            return Decimal('0')
    
    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get ticker data"""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return {
                'last': Decimal(str(ticker['last'])),
                'bid': Decimal(str(ticker['bid'])),
                'ask': Decimal(str(ticker['ask'])),
                'volume': Decimal(str(ticker['quoteVolume'])),
                'timestamp': ticker['timestamp']
            }
        except Exception as e:
            self.logger.error(f"Error fetching ticker for {symbol}: {e}")
            raise
    
    def get_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 100) -> List[Dict[str, Any]]:
        """Get OHLCV data"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            return [
                {
                    'timestamp': candle[0],
                    'open': Decimal(str(candle[1])),
                    'high': Decimal(str(candle[2])),
                    'low': Decimal(str(candle[3])),
                    'close': Decimal(str(candle[4])),
                    'volume': Decimal(str(candle[5]))
                }
                for candle in ohlcv
            ]
        except Exception as e:
            self.logger.error(f"Error fetching OHLCV for {symbol}: {e}")
            raise
    
    def place_order(self, symbol: str, side: str, amount: Decimal, order_type: str = "market", price: Optional[Decimal] = None) -> Dict[str, Any]:
        """Place an order"""
        try:
            params = {}
            if order_type == "limit" and price:
                params['price'] = float(price)
            
            order = self.exchange.create_order(
                symbol=symbol,
                type=order_type,
                side=side,
                amount=float(amount),
                **params
            )
            
            return {
                'id': order['id'],
                'symbol': order['symbol'],
                'side': order['side'],
                'type': order['type'],
                'amount': Decimal(str(order['amount'])),
                'price': Decimal(str(order.get('price', '0'))),
                'status': order['status'],
                'filled': Decimal(str(order.get('filled', '0')))
            }
        except Exception as e:
            self.logger.error(f"Error placing order: {e}")
            raise
    
    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an order"""
        try:
            self.exchange.cancel_order(order_id, symbol)
            return True
        except Exception as e:
            self.logger.error(f"Error canceling order {order_id}: {e}")
            return False
    
    def get_order_status(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Get order status"""
        try:
            order = self.exchange.fetch_order(order_id, symbol)
            return {
                'id': order['id'],
                'symbol': order['symbol'],
                'side': order['side'],
                'type': order['type'],
                'amount': Decimal(str(order['amount'])),
                'filled': Decimal(str(order.get('filled', '0'))),
                'price': Decimal(str(order.get('price', '0'))),
                'status': order['status']
            }
        except Exception as e:
            self.logger.error(f"Error fetching order status: {e}")
            raise
    
    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Get open positions"""
        try:
            balances = self.exchange.fetch_balance()
            positions = []
            
            for currency, balance_info in balances.items():
                if currency in ['free', 'used', 'total', 'info']:
                    continue
                if isinstance(balance_info, dict) and balance_info.get('total', 0) > 0:
                    positions.append({
                        'symbol': currency,
                        'amount': Decimal(str(balance_info['total'])),
                        'free': Decimal(str(balance_info.get('free', 0))),
                        'used': Decimal(str(balance_info.get('used', 0)))
                    })
            
            return positions
        except Exception as e:
            self.logger.error(f"Error fetching open positions: {e}")
            return []

