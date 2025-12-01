"""
Utility functions for Polymarket Trading Bot
"""

import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging


logger = logging.getLogger(__name__)


def load_config_from_json(file_path: str) -> dict:
    """
    Load configuration from JSON file
    
    Args:
        file_path: Path to config JSON file
    
    Returns:
        Configuration dictionary
    """
    try:
        with open(file_path, 'r') as f:
            config = json.load(f)
        logger.info(f"Configuration loaded from {file_path}")
        return config
    except FileNotFoundError:
        logger.error(f"Config file not found: {file_path}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file: {e}")
        return {}


def save_config_to_json(config: dict, file_path: str):
    """Save configuration to JSON file"""
    try:
        with open(file_path, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info(f"Configuration saved to {file_path}")
    except Exception as e:
        logger.error(f"Failed to save config: {e}")


def validate_price(price: float) -> bool:
    """
    Validate if price is in valid range [0, 1]
    
    Args:
        price: Price value to validate
    
    Returns:
        True if valid, False otherwise
    """
    return 0.0 <= price <= 1.0


def calculate_pnl(entry_price: float, exit_price: float, side: str, stake_size: float) -> float:
    """
    Calculate profit/loss for a trade
    
    Args:
        entry_price: Entry price (0-1 range)
        exit_price: Exit price (0-1 range)
        side: "UP" or "DOWN"
        stake_size: Position size in USD
    
    Returns:
        P&L in USD
    """
    if side == "UP":
        pnl = exit_price - entry_price
    elif side == "DOWN":
        pnl = entry_price - exit_price
    else:
        logger.error(f"Invalid side: {side}")
        return 0.0
    
    return pnl * stake_size


def format_timestamp(dt: datetime) -> str:
    """Format datetime to ISO string"""
    return dt.isoformat()


def parse_timestamp(timestamp_str: str) -> datetime:
    """Parse ISO timestamp string to datetime"""
    try:
        return datetime.fromisoformat(timestamp_str)
    except ValueError:
        logger.error(f"Invalid timestamp format: {timestamp_str}")
        return datetime.utcnow()


def get_window_id_from_timestamp(timestamp: datetime, window_minutes: int = 15) -> str:
    """
    Generate window ID from timestamp
    
    Args:
        timestamp: Datetime object
        window_minutes: Window duration in minutes
    
    Returns:
        Window ID string (e.g., "20241201_1200")
    """
    minutes = (timestamp.minute // window_minutes) * window_minutes
    window_start = timestamp.replace(minute=minutes, second=0, microsecond=0)
    return window_start.strftime("%Y%m%d_%H%M")


def calculate_win_rate(trades: List[Dict]) -> float:
    """
    Calculate win rate from trade history
    
    Args:
        trades: List of trade dictionaries
    
    Returns:
        Win rate as percentage (0-100)
    """
    if not trades:
        return 0.0
    
    winning_trades = sum(1 for t in trades if t.get('pnl', 0) > 0)
    return (winning_trades / len(trades)) * 100


def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.0) -> float:
    """
    Calculate Sharpe ratio
    
    Args:
        returns: List of returns
        risk_free_rate: Risk-free rate (default 0)
    
    Returns:
        Sharpe ratio
    """
    if not returns or len(returns) < 2:
        return 0.0
    
    import numpy as np
    
    returns_array = np.array(returns)
    excess_returns = returns_array - risk_free_rate
    
    if np.std(excess_returns) == 0:
        return 0.0
    
    return np.mean(excess_returns) / np.std(excess_returns)


def calculate_max_drawdown(cumulative_pnl: List[float]) -> float:
    """
    Calculate maximum drawdown
    
    Args:
        cumulative_pnl: List of cumulative P&L values
    
    Returns:
        Max drawdown (negative value)
    """
    if not cumulative_pnl:
        return 0.0
    
    import numpy as np
    
    arr = np.array(cumulative_pnl)
    running_max = np.maximum.accumulate(arr)
    drawdown = arr - running_max
    
    return np.min(drawdown)


def export_trades_to_csv(trades: List[Dict], file_path: str):
    """
    Export trades to CSV file
    
    Args:
        trades: List of trade dictionaries
        file_path: Output CSV file path
    """
    try:
        df = pd.DataFrame(trades)
        df.to_csv(file_path, index=False)
        logger.info(f"Trades exported to {file_path}")
    except Exception as e:
        logger.error(f"Failed to export trades: {e}")


def load_trades_from_csv(file_path: str) -> List[Dict]:
    """
    Load trades from CSV file
    
    Args:
        file_path: CSV file path
    
    Returns:
        List of trade dictionaries
    """
    try:
        df = pd.read_csv(file_path)
        trades = df.to_dict('records')
        logger.info(f"Loaded {len(trades)} trades from {file_path}")
        return trades
    except Exception as e:
        logger.error(f"Failed to load trades: {e}")
        return []


def create_price_dataframe(price_data: List[Dict]) -> pd.DataFrame:
    """
    Convert price data list to pandas DataFrame
    
    Args:
        price_data: List of price dictionaries
    
    Returns:
        DataFrame with timestamp, asset, price columns
    """
    df = pd.DataFrame(price_data)
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
    return df


def get_market_summary(prices: Dict[str, float]) -> str:
    """
    Generate human-readable market summary
    
    Args:
        prices: Dictionary of asset prices
    
    Returns:
        Formatted summary string
    """
    summary = "Market Summary:\n"
    for asset, price in sorted(prices.items()):
        percentage = price * 100
        summary += f"  {asset}: {percentage:.1f}%\n"
    return summary


def is_market_hours() -> bool:
    """
    Check if current time is within market hours
    (Polymarket is 24/7, so always returns True)
    
    Returns:
        True (always, since crypto markets are 24/7)
    """
    return True


def retry_on_failure(func, max_retries: int = 3, delay: float = 1.0):
    """
    Retry decorator for network requests
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retries
        delay: Delay between retries in seconds
    
    Returns:
        Function result or None on failure
    """
    import time
    
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(delay)
            else:
                logger.error(f"All {max_retries} attempts failed")
                return None


def format_pnl(pnl: float) -> str:
    """
    Format P&L with color indicators
    
    Args:
        pnl: P&L value
    
    Returns:
        Formatted string
    """
    sign = "+" if pnl >= 0 else ""
    return f"{sign}${pnl:.2f}"


def seconds_to_time_str(seconds: float) -> str:
    """
    Convert seconds to readable time string
    
    Args:
        seconds: Time in seconds
    
    Returns:
        Formatted time string (e.g., "5:30")
    """
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"