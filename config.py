"""
Enhanced Configuration System for Polymarket Trading Bot
Supports both Python dict and JSON file configuration
"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    # API Configuration
    "polymarket_api_url": "https://gamma-api.polymarket.com",
    "polymarket_clob_url": "https://clob.polymarket.com",
    "polymarket_rtds_url": "wss://ws-subscriptions-clob.polymarket.com/ws/market",
    
    # Market Configuration
    "market_interval": "15m",  # 15-minute markets
    "reference_assets": ["BTC", "ETH"],
    "tradeable_assets": ["SOL", "XRP"],
    "all_assets": ["BTC", "ETH", "SOL", "XRP"],
    
    # Strategy Parameters - Zone Thresholds
    "zone_high_min": 0.75,
    "zone_high_max": 1.00,
    "zone_low_min": 0.00,
    "zone_low_max": 0.25,
    "laggard_up_entry_min": 0.00,
    "laggard_up_entry_max": 0.50,
    "laggard_down_entry_min": 0.50,
    "laggard_down_entry_max": 1.00,
    
    # Exit Thresholds
    "exit_up_threshold": 0.90,
    "exit_down_threshold": 0.10,
    
    # Stop Loss (Risk Management)
    "stop_loss_pct": 0.05,  # 5% stop loss from entry
    
    # Time Window Settings
    "window_duration_minutes": 15,
    "entry_window_max_remaining_seconds": 300,  # 5:00 minutes
    "entry_window_min_remaining_seconds": 90,   # 1:30 minutes
    "max_trades_per_window": 1,
    
    # Trading Parameters
    "stake_size_usd": 1.0,
    "entry_check_interval_seconds": 5,
    
    # Backtesting
    "backtest_start_date": "2024-09-01",
    "backtest_end_date": "2024-12-31",
    "backtest_data_dir": "./data/historical",
    
    # Logging
    "log_dir": "./logs",
    "trade_log_file": "trades.csv",
    "system_log_file": "bot.log",
    "log_level": "INFO",
    
    # Features
    "enable_paper_trading": True,
    "enable_backtesting": True,
    "enable_live_trading": False,  # Requires wallet setup
    
    # API Rate Limiting
    "api_request_delay": 0.5,
    "reconnect_delay_seconds": 5,
    "max_reconnect_attempts": 10,
    
    # Wallet Configuration (for live trading)
    "wallet_private_key": "",  # Set via environment variable or config.json
    "wallet_address": "",      # Will be derived from private key
    "chain_id": 137,           # Polygon Mainnet for Polymarket
    
    # CLOB Configuration
    "clob_timeout": 30,
    "clob_order_type": "limit",  # limit or market
    "clob_slippage_percent": 0.5  # Max slippage tolerance
}


class Config:
    """Enhanced configuration manager"""
    
    def __init__(self, config_dict: Optional[dict] = None, config_file: Optional[str] = None):
        """
        Initialize config from dict or JSON file
        
        Args:
            config_dict: Configuration dictionary
            config_file: Path to JSON config file
        """
        self.config = DEFAULT_CONFIG.copy()
        
        # Load from file if provided
        if config_file:
            self.load_from_file(config_file)
        
        # Override with dict if provided
        if config_dict:
            self.config.update(config_dict)
        
        self._validate()
        self._setup_paths()
    
    def _validate(self):
        """Validate configuration parameters"""
        assert 0 < self.config["exit_up_threshold"] <= 1.0, "Invalid exit_up_threshold"
        assert 0 <= self.config["exit_down_threshold"] < 1.0, "Invalid exit_down_threshold"
        assert self.config["entry_window_max_remaining_seconds"] > \
               self.config["entry_window_min_remaining_seconds"], "Invalid time window"
        assert self.config["zone_high_min"] < self.config["zone_high_max"], "Invalid high zone"
        assert self.config["zone_low_min"] < self.config["zone_low_max"], "Invalid low zone"
        assert len(self.config["reference_assets"]) >= 2, "Need at least 2 reference assets"
        assert len(self.config["tradeable_assets"]) >= 1, "Need at least 1 tradeable asset"
    
    def _setup_paths(self):
        """Create necessary directories"""
        Path(self.config["log_dir"]).mkdir(exist_ok=True, parents=True)
        Path(self.config["backtest_data_dir"]).mkdir(exist_ok=True, parents=True)
    
    def get(self, key: str, default=None):
        """Get config value"""
        return self.config.get(key, default)
    
    def __getitem__(self, key: str):
        """Dict-like access"""
        return self.config[key]
    
    def update(self, updates: dict):
        """Update configuration"""
        self.config.update(updates)
        self._validate()
    
    def save_to_file(self, file_path: str):
        """Save configuration to JSON file"""
        with open(file_path, 'w') as f:
            json.dump(self.config, f, indent=2)
        logger.info(f"Configuration saved to {file_path}")
    
    def load_from_file(self, file_path: str):
        """Load configuration from JSON file"""
        try:
            with open(file_path, 'r') as f:
                loaded = json.load(f)
            self.config.update(loaded)
            logger.info(f"Configuration loaded from {file_path}")
        except FileNotFoundError:
            logger.warning(f"Config file not found: {file_path}, using defaults")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
    
    def to_dict(self) -> dict:
        """Export as dictionary"""
        return self.config.copy()
    
    def __str__(self) -> str:
        """String representation"""
        return json.dumps(self.config, indent=2)


# Create default config.json on first import
if __name__ == "__main__":
    config = Config()
    config.save_to_file("config.json")
    print("Default config.json created!")
    print(config)