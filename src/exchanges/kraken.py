"""Kraken exchange implementation"""

import ccxt
import certifi
import os
import urllib3
from decimal import Decimal
from typing import Dict, List, Optional, Any
from .base import ExchangeBase
from src.utils.logger import setup_logger

# Set SSL certificate path for macOS compatibility
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

# Suppress urllib3 SSL warnings when verification is disabled (we handle it ourselves)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class KrakenExchange(ExchangeBase):
    """Kraken exchange implementation using ccxt"""
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None, sandbox: bool = False):
        super().__init__("kraken", api_key, api_secret, sandbox)
        self.logger = setup_logger(f"{__name__}.{self.name}")
        self.exchange = None
    
    def connect(self) -> bool:
        """Connect to Kraken"""
        # For paper trading, API keys are optional (public data access)
        base_config = {
            'enableRateLimit': True,
            'rateLimit': 1000  # 1 second between requests (Kraken allows 1 req/sec for public endpoints)
        }
        
        # Only add API keys if provided
        if self.api_key:
            base_config['apiKey'] = self.api_key
        if self.api_secret:
            base_config['secret'] = self.api_secret
        
        if self.sandbox:
            base_config['urls'] = {
                'api': {
                    'public': 'https://demo-futures.kraken.com',
                    'private': 'https://demo-futures.kraken.com',
                }
            }
        
        # Try connecting with SSL verification first
        # Note: Python 3.14 on macOS may have SSL certificate issues
        # If SSL verification fails, retry with verification disabled
        for verify_ssl in [certifi.where(), False]:
            try:
                config = base_config.copy()
                config['verify'] = verify_ssl
                
                self.exchange = ccxt.kraken(config)
                self.exchange.load_markets()
                self._connected = True
                mode = 'sandbox' if self.sandbox else 'live'
                key_status = 'with API keys' if self.api_key else 'public data only'
                ssl_status = 'SSL verified' if verify_ssl else 'SSL verification disabled (dev)'
                self.logger.info(f"Connected to Kraken ({mode}, {key_status}, {ssl_status})")
                if not verify_ssl:
                    self.logger.warning("SSL verification is disabled - FOR DEVELOPMENT ONLY!")
                return True
            except Exception as e:
                # If SSL verification failed, try without verification
                if verify_ssl and ('SSL' in str(e) or 'certificate' in str(e).lower()):
                    self.logger.warning(f"SSL verification failed, retrying without verification: {e}")
                    continue
                # If it's not an SSL error or we've already tried without verification, fail
                if not verify_ssl:
                    self.logger.error(f"Failed to connect to Kraken: {e}")
                    self._connected = False
                    return False
        
        self._connected = False
        return False
    
    def get_balance(self, currency: str = "USDT") -> Decimal:
        """Get account balance"""
        try:
            balance = self.exchange.fetch_balance()
            # Kraken uses ZUSD or USD instead of USDT
            if currency == "USDT":
                for alt in ["ZUSD", "USD", "USDT"]:
                    if alt in balance:
                        currency = alt
                        break
            
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
    
    def get_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 100, since: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get OHLCV data"""
        try:
            params = {}
            if since:
                params['since'] = since
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit, **params)
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

