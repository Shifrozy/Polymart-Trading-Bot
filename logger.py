"""
Enhanced logging system with better formatting and file handling
"""

import csv
import os
import logging
from datetime import datetime
from pathlib import Path
import sys


class TradeLogger:
    """Enhanced CSV trade logger with better error handling"""
    
    def __init__(self, config):
        self.log_dir = Path(config["log_dir"])
        self.log_dir.mkdir(exist_ok=True, parents=True)
        
        self.trade_log_file = self.log_dir / config["trade_log_file"]
        self._init_csv()
    
    def _init_csv(self):
        """Initialize CSV with headers if file doesn't exist"""
        if not self.trade_log_file.exists():
            headers = [
                "timestamp_entry", "timestamp_exit", "window_id",
                "asset", "side", "group_config", "group_assets", "group_prices_entry",
                "entry_price", "exit_price", "exit_reason",
                "pnl_pct", "pnl_usd", "stake_size", "outcome",
                "market_id", "cumulative_pnl", "trade_number"
            ]
            
            with open(self.trade_log_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
    
    def log_trade(self, trade_data: dict):
        """Log trade to CSV"""
        try:
            # Ensure all expected fields exist
            expected_fields = [
                "timestamp_entry", "timestamp_exit", "window_id",
                "asset", "side", "group_config", "group_assets", "group_prices_entry",
                "entry_price", "exit_price", "exit_reason",
                "pnl_pct", "pnl_usd", "stake_size", "outcome",
                "market_id", "cumulative_pnl", "trade_number"
            ]
            
            # Fill missing fields with defaults
            for field in expected_fields:
                if field not in trade_data:
                    trade_data[field] = ""
            
            with open(self.trade_log_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=expected_fields)
                writer.writerow(trade_data)
                
        except Exception as e:
            logging.error(f"Failed to log trade: {e}")


def setup_logging(config):
    """Setup enhanced logging system"""
    
    log_dir = Path(config["log_dir"])
    log_dir.mkdir(exist_ok=True, parents=True)
    
    log_file = log_dir / config["system_log_file"]
    log_level = getattr(logging, config.get("log_level", "INFO"))
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # File handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(log_level)
    file_handler.setFormatter(file_formatter)
    
    # Console handler with UTF-8 encoding fix for Windows
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(console_formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Reduce noise from some libraries
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    logging.info("="*60)
    logging.info("Logging system initialized")
    logging.info(f"Log file: {log_file}")
    logging.info(f"Log level: {config.get('log_level', 'INFO')}")
    logging.info("="*60)