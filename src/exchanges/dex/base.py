"""Base DEX interface"""

from abc import ABC, abstractmethod
from typing import Dict, Optional
from decimal import Decimal
from ..base import ExchangeBase


class DEXBase(ExchangeBase):
    """Abstract base class for DEX implementations"""
    
    def __init__(self, name: str, chain_id: int, rpc_url: Optional[str] = None):
        """
        Initialize DEX.
        
        Args:
            name: DEX name (e.g., 'uniswap', 'pancakeswap')
            chain_id: Blockchain chain ID (1 for Ethereum, 56 for BSC, etc.)
            rpc_url: RPC endpoint URL
        """
        super().__init__(name, None, None, False)
        self.chain_id = chain_id
        self.rpc_url = rpc_url
        self.wallet_address = None
        self.private_key = None
    
    @abstractmethod
    def connect_wallet(self, address: str, private_key: Optional[str] = None) -> bool:
        """
        Connect wallet to DEX.
        
        Args:
            address: Wallet address
            private_key: Private key (optional, can use wallet connect instead)
            
        Returns:
            True if connection successful
        """
        pass
    
    @abstractmethod
    def get_token_balance(self, token_address: str) -> Decimal:
        """
        Get token balance for connected wallet.
        
        Args:
            token_address: ERC20 token contract address
            
        Returns:
            Token balance
        """
        pass
    
    @abstractmethod
    def get_token_price(self, token_address: str, quote_token: str = "USDT") -> Decimal:
        """
        Get token price from DEX.
        
        Args:
            token_address: Token contract address
            quote_token: Quote token (USDT, USDC, etc.)
            
        Returns:
            Token price in quote token
        """
        pass
    
    @abstractmethod
    def swap_tokens(self, token_in: str, token_out: str, amount_in: Decimal, slippage: float = 0.01) -> Dict:
        """
        Execute token swap.
        
        Args:
            token_in: Input token address
            token_out: Output token address
            amount_in: Amount to swap
            slippage: Maximum slippage tolerance (e.g., 0.01 = 1%)
            
        Returns:
            Transaction hash and details
        """
        pass
    
    def disconnect_wallet(self):
        """Disconnect wallet"""
        self.wallet_address = None
        self.private_key = None
        self._connected = False

