"""
Configuration module for Polymarket Trading Bot
All strategy parameters are configurable here
"""

DEFAULT_CONFIG = {
    # Trading Parameters
    "entry_check_interval": 5,  # seconds
    "stake_size": 1.0,  # USD per trade
    
    # Group Band Thresholds
    "band_high_group": [0.75, 1.00],  # Group must be in this range for UP entry
    "band_low_group": [0.00, 0.25],   # Group must be in this range for DOWN entry
    
    # Laggard Zone Thresholds
    "laggard_low_zone": [0.00, 0.50],   # Laggard range for UP entry
    "laggard_high_zone": [0.50, 1.00],  # Laggard range for DOWN entry
    
    # Exit Thresholds
    "exit_up_threshold": 0.90,   # Close UP trade when laggard reaches this
    "exit_down_threshold": 0.10, # Close DOWN trade when laggard reaches this
    
    # Asset Configuration
    "reference_assets": ["BTC", "ETH"],  # Always in reference group
    "tradeable_assets": ["SOL", "XRP"],  # Assets we can trade
    
    # Time Window Configuration
    "window_duration_minutes": 15,
    "entry_window_max_remaining": 300,  # 5:00 minutes in seconds
    "entry_window_min_remaining": 90,   # 1:30 minutes in seconds
    
    # API Configuration
    "polymarket_rest_url": "https://clob.polymarket.com",
    "polymarket_rtds_url": "wss://ws-subscriptions-clob.polymarket.com/ws/market",
    "reconnect_delay": 5,  # seconds
    
    # Backtesting
    "backtest_start_date": "2024-09-01",
    "backtest_data_path": "./data/historical/",
    
    # Logging
    "log_dir": "./logs/",
    "trade_log_file": "trades.csv",
    "system_log_file": "system.log"
}


class Config:
    """Configuration manager with validation"""
    
    def __init__(self, config_dict=None):
        self.config = DEFAULT_CONFIG.copy()
        if config_dict:
            self.config.update(config_dict)
        self._validate()
    
    def _validate(self):
        """Validate configuration parameters"""
        assert 0 < self.config["exit_up_threshold"] <= 1.0, "exit_up_threshold must be in (0, 1]"
        assert 0 <= self.config["exit_down_threshold"] < 1.0, "exit_down_threshold must be in [0, 1)"
        assert self.config["entry_window_max_remaining"] > self.config["entry_window_min_remaining"], \
            "entry_window_max_remaining must be greater than entry_window_min_remaining"
        assert len(self.config["reference_assets"]) >= 2, "Need at least 2 reference assets"
        assert len(self.config["tradeable_assets"]) >= 1, "Need at least 1 tradeable asset"
    
    def get(self, key, default=None):
        """Get config value by key"""
        return self.config.get(key, default)
    
    def __getitem__(self, key):
        """Allow dict-like access"""
        return self.config[key]
    
    def update(self, updates: dict):
        """Update configuration"""
        self.config.update(updates)
        self._validate()
    
    def save_to_json(self, file_path: str):
        """Save configuration to JSON file"""
        import json
        with open(file_path, 'w') as f:
            json.dump(self.config, f, indent=2)
        print(f"✅ Configuration saved to {file_path}")
    
    @classmethod
    def load_from_json(cls, file_path: str):
        """Load configuration from JSON file"""
        import json
        with open(file_path, 'r') as f:
            config_dict = json.load(f)
        print(f"✅ Configuration loaded from {file_path}")
        return cls(config_dict)
    
    def __str__(self):
        """String representation"""
        import json
        return json.dumps(self.config, indent=2)


# Example usage
if __name__ == "__main__":
    # Create default config
    config = Config()
    print("Default Configuration:")
    print(config)
    
    # Save to JSON
    config.save_to_json("config.json")
    
    # Load from JSON
    loaded_config = Config.load_from_json("config.json")
    print("\nLoaded Configuration:")
    print(loaded_config)