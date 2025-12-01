"""
Trade logging utilities
"""

import csv
import os
import logging
from datetime import datetime
from pathlib import Path


class TradeLogger:
    """CSV trade logger"""
    
    def __init__(self, config):
        self.log_dir = Path(config["log_dir"])
        self.log_dir.mkdir(exist_ok=True)
        
        self.trade_log_file = self.log_dir / config["trade_log_file"]
        self._init_csv()
    
    def _init_csv(self):
        """Initialize CSV with headers"""
        if not self.trade_log_file.exists():
            headers = [
                "timestamp_entry", "window_id", "asset", "side", "entry_price",
                "group_config", "group_prices_entry", "timestamp_exit", "exit_price",
                "exit_reason", "settlement_outcome", "pnl_contract", "pnl_usd",
                "stake_size", "fees"
            ]
            
            with open(self.trade_log_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
    
    def log_trade(self, trade_data: dict):
        """Log trade to CSV"""
        with open(self.trade_log_file, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=trade_data.keys())
            writer.writerow(trade_data)


def setup_logging(config):
    """Setup system logging"""
    log_dir = Path(config["log_dir"])
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / config["system_log_file"]
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )