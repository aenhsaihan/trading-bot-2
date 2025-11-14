"""Symbol normalization utility - converts bare symbols to exchange format"""

from typing import Optional


def normalize_symbol(symbol: str, quote_currency: str = "USDT") -> str:
    """
    Normalize a symbol to exchange format (BASE/QUOTE).
    
    If symbol is already in BASE/QUOTE format, returns as-is.
    If symbol is just BASE (e.g., "BTC"), converts to "BTC/USDT".
    
    Args:
        symbol: Symbol to normalize (e.g., "BTC" or "BTC/USDT")
        quote_currency: Quote currency to use if not present (default: "USDT")
        
    Returns:
        Normalized symbol in BASE/QUOTE format
    """
    if not symbol:
        return symbol
    
    # If already in BASE/QUOTE format, return as-is
    if '/' in symbol:
        return symbol
    
    # Convert bare symbol to BASE/QUOTE format
    return f"{symbol}/{quote_currency}"


def normalize_symbols(symbols: list[str], quote_currency: str = "USDT") -> list[str]:
    """
    Normalize a list of symbols to exchange format.
    
    Args:
        symbols: List of symbols to normalize
        quote_currency: Quote currency to use if not present (default: "USDT")
        
    Returns:
        List of normalized symbols
    """
    return [normalize_symbol(s, quote_currency) for s in symbols]

