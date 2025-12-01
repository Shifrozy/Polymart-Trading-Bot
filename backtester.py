"""
Event-driven backtesting engine
"""

import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import List, Dict
from dataclasses import dataclass, asdict

from window_manager import WindowManager
from strategy import PolymarketStrategy
from logger import TradeLogger


logger = logging.getLogger(__name__)


@dataclass
class BacktestTrade:
    """Backtest trade record"""
    window_id: str
    asset: str
    side: str
    entry_time: datetime
    entry_price: float
    group_config: str
    group_prices: dict
    exit_time: datetime
    exit_price: float
    exit_reason: str
    pnl: float
    stake_size: float


class Backtester:
    """Event-driven backtesting engine"""
    
    def __init__(self, config):
        self.config = config
        self.window_manager = WindowManager(config["window_duration_minutes"])
        self.strategy = PolymarketStrategy(config)
        self.trades: List[BacktestTrade] = []
    
    def load_historical_data(self, file_path: str) -> pd.DataFrame:
        """Load historical price data"""
        # Expected format: timestamp, asset, price
        df = pd.read_csv(file_path)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        return df
    
    def run(self, price_data: pd.DataFrame, start_date: str, end_date: str):
        """Run backtest on historical data"""
        logger.info(f"Starting backtest: {start_date} to {end_date}")
        
        # Filter date range
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        data = price_data[(price_data['timestamp'] >= start) & (price_data['timestamp'] <= end)]
        
        # Group by timestamp to get all assets at once
        grouped = data.groupby('timestamp')
        
        current_position = None
        current_window_id = None
        
        for timestamp, group in grouped:
            # Get prices dict
            prices = dict(zip(group['asset'], group['price']))
            
            # Check window
            window_id = self.window_manager.get_window_id(timestamp)
            
            # New window - settle previous position
            if window_id != current_window_id:
                if current_position:
                    current_position = self._settle_position(current_position, timestamp, prices)
                current_window_id = window_id
            
            # Check entry if no position
            if not current_position:
                current_position = self._check_entry(timestamp, window_id, prices)
            
            # Check exit if position exists
            elif current_position:
                current_position = self._check_exit(current_position, timestamp, prices)
        
        # Final settlement
        if current_position:
            self._settle_position(current_position, data['timestamp'].max(), {})
        
        self._generate_report()
    
    def _check_entry(self, timestamp, window_id, prices):
        """Check for entry signal"""
        # Check time eligibility
        if not self.window_manager.is_entry_eligible(
            timestamp,
            self.config["entry_window_max_remaining"],
            self.config["entry_window_min_remaining"]
        ):
            return None
        
        # Evaluate signal
        signal = self.strategy.evaluate_signal(prices)
        
        if signal.signal:
            logger.debug(f"{timestamp}: ENTRY {signal.signal} on {signal.asset}")
            
            return {
                'window_id': window_id,
                'asset': signal.asset,
                'side': signal.signal,
                'entry_time': timestamp,
                'entry_price': signal.laggard_price,
                'group_config': signal.group_config,
                'group_prices': signal.group_prices,
                'stake_size': self.config['stake_size']
            }
        
        return None
    
    def _check_exit(self, position, timestamp, prices):
        """Check if position should exit"""
        current_price = prices.get(position['asset'])
        
        if current_price is None:
            return position
        
        should_exit, reason = self.strategy.check_exit(position['side'], current_price)
        
        if should_exit:
            return self._close_position(position, timestamp, current_price, reason)
        
        return position
    
    def _close_position(self, position, exit_time, exit_price, reason):
        """Close position and record trade"""
        # Calculate P&L
        if position['side'] == "UP":
            pnl = exit_price - position['entry_price']
        else:
            pnl = position['entry_price'] - exit_price
        
        trade = BacktestTrade(
            window_id=position['window_id'],
            asset=position['asset'],
            side=position['side'],
            entry_time=position['entry_time'],
            entry_price=position['entry_price'],
            group_config=position['group_config'],
            group_prices=position['group_prices'],
            exit_time=exit_time,
            exit_price=exit_price,
            exit_reason=reason,
            pnl=pnl * position['stake_size'],
            stake_size=position['stake_size']
        )
        
        self.trades.append(trade)
        logger.debug(f"{exit_time}: CLOSED {position['side']} {position['asset']} | P&L: ${trade.pnl:.2f}")
        
        return None
    
    def _settle_position(self, position, timestamp, prices):
        """Settle at window expiry"""
        # Simplified: assume settlement at current price or 1/0
        settlement_price = prices.get(position['asset'], 0.5)
        return self._close_position(position, timestamp, settlement_price, "SETTLEMENT")
    
    def _generate_report(self):
        """Generate backtest performance report"""
        if not self.trades:
            logger.warning("No trades executed in backtest")
            return
        
        df = pd.DataFrame([asdict(t) for t in self.trades])
        
        total_trades = len(df)
        winning_trades = len(df[df['pnl'] > 0])
        losing_trades = len(df[df['pnl'] <= 0])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        total_pnl = df['pnl'].sum()
        avg_win = df[df['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
        avg_loss = df[df['pnl'] <= 0]['pnl'].mean() if losing_trades > 0 else 0
        
        cumulative_pnl = df['pnl'].cumsum()
        max_drawdown = (cumulative_pnl - cumulative_pnl.cummax()).min()
        
        print("\n" + "="*60)
        print("BACKTEST RESULTS")
        print("="*60)
        print(f"Total Trades:     {total_trades}")
        print(f"Winning Trades:   {winning_trades} ({win_rate*100:.1f}%)")
        print(f"Losing Trades:    {losing_trades}")
        print(f"Total P&L:        ${total_pnl:.2f}")
        print(f"Average Win:      ${avg_win:.2f}")
        print(f"Average Loss:     ${avg_loss:.2f}")
        print(f"Max Drawdown:     ${max_drawdown:.2f}")
        print("="*60 + "\n")
        
        # Save to CSV
        output_file = f"backtest_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(output_file, index=False)
        logger.info(f"Results saved to {output_file}")