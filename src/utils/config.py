"""Configuration management"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv


class Config:
    """Configuration manager for the trading bot"""
    
    def __init__(self, config_dir: str = "config", env_file: str = ".env"):
        """
        Initialize configuration manager.
        
        Args:
            config_dir: Directory containing YAML config files
            env_file: Path to .env file
        """
        self.config_dir = Path(config_dir)
        self.env_file = Path(env_file)
        
        # Load environment variables
        if self.env_file.exists():
            load_dotenv(self.env_file)
        
        # Load YAML configs
        self.strategy_config = self._load_yaml("strategy.yaml")
        self.exchange_config = self._load_yaml("exchanges.yaml")
        
        # Trading mode (paper or live)
        self.trading_mode = os.getenv("TRADING_MODE", "paper").lower()
        
        # Database path
        self.database_path = os.getenv("DATABASE_PATH", "data/trades.db")
        
        # Logging
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.log_dir = os.getenv("LOG_DIR", "logs")
    
    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        """Load YAML configuration file"""
        filepath = self.config_dir / filename
        if filepath.exists():
            with open(filepath, 'r') as f:
                return yaml.safe_load(f) or {}
        return {}
    
    def get_exchange_api_key(self, exchange: str) -> Optional[str]:
        """Get API key for exchange"""
        key_name = f"{exchange.upper()}_API_KEY"
        return os.getenv(key_name)
    
    def get_exchange_api_secret(self, exchange: str) -> Optional[str]:
        """Get API secret for exchange"""
        secret_name = f"{exchange.upper()}_API_SECRET"
        return os.getenv(secret_name)
    
    def is_paper_trading(self) -> bool:
        """Check if bot is in paper trading mode"""
        return self.trading_mode == "paper"
    
    def get_strategy_config(self) -> Dict[str, Any]:
        """Get strategy configuration"""
        return self.strategy_config.get("trend_following", {})
    
    def get_risk_config(self) -> Dict[str, Any]:
        """Get risk management configuration"""
        return self.strategy_config.get("risk_management", {})
    
    def get_exchange_settings(self, exchange: str) -> Dict[str, Any]:
        """Get exchange-specific settings"""
        exchanges = self.exchange_config.get("exchanges", {})
        return exchanges.get(exchange, {})

