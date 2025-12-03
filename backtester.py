"""
Enhanced Backtesting Engine
Event-driven historical simulation with full strategy logic
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import csv

from window_manager import WindowManager
from strategy import EnhancedPolymarketStrategy

logger = logging.getLogger(__name__)


@dataclass
class BacktestTrade:
    """Backtest trade record"""
    trade_id: int
    window_id: str
    asset: str
    side: str
    group_config: str
    group_assets: List[str]
    entry_time: datetime
    entry_price: float
    group_prices_entry: Dict[str, float]
    exit_time: datetime
    exit_price: float
    exit_reason: str
    pnl_pct: float
    pnl_usd: float
    stake_size: float
    outcome: str
    
    def to_dict(self):
        d = asdict(self)
        d['entry_time'] = self.entry_time.isoformat()
        d['exit_time'] = self.exit_time.isoformat()
        d['group_assets'] = str(self.group_assets)
        d['group_prices_entry'] = str(self.group_prices_entry)
        return d


class EnhancedBacktester:
    """Enhanced backtesting engine with full strategy simulation"""
    
    def __init__(self, config):
        self.config = config
        self.window_manager = WindowManager(config["window_duration_minutes"])
        self.strategy = EnhancedPolymarketStrategy(config)
        
        self.trades: List[BacktestTrade] = []
        self.equity_curve: List[float] = []
        self.current_position = None
        self.trades_this_window = 0
        self.trade_counter = 0
    
    def load_historical_data(self, file_path: str) -> pd.DataFrame:
        """Load historical price data from CSV"""
        logger.info(f"[LOAD] Loading data from {file_path}")
        
        try:
            df = pd.read_csv(file_path)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')
            
            logger.info(f"[OK] Loaded {len(df)} records")
            logger.info(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
            logger.info(f"Assets: {df['asset'].unique()}")
            
            return df
        except Exception as e:
            logger.error(f"[ERROR] Failed to load data: {e}")
            raise
    
    def run(self, data: pd.DataFrame, start_date: str, end_date: str):
        """Run backtest on historical data"""
        logger.info("")
        logger.info("="*60)
        logger.info("STARTING BACKTEST")
        logger.info("="*60)
        logger.info(f"Period: {start_date} to {end_date}")
        logger.info(f"Strategy: Group + Laggard")
        logger.info(f"Stake: ${self.config['stake_size_usd']} per trade")
        logger.info("="*60)
        logger.info("")
        
        # Filter date range
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        data = data[(data['timestamp'] >= start) & (data['timestamp'] <= end)]
        
        if len(data) == 0:
            logger.error("[ERROR] No data in specified date range")
            return
        
        # Group by timestamp to get all asset prices at once
        timestamps = data['timestamp'].unique()
        timestamps.sort()
        
        logger.info(f"[INFO] Processing {len(timestamps)} timestamps...")
        
        current_window_id = None
        processed = 0
        
        for ts in timestamps:
            processed += 1
            
            if processed % 1000 == 0:
                logger.info(f"[PROGRESS] Processed {processed}/{len(timestamps)} timestamps")
            
            # Get prices at this timestamp
            snapshot = data[data['timestamp'] == ts]
            prices = dict(zip(snapshot['asset'], snapshot['price']))
            
            # Check if we have all required assets
            required_assets = set(self.config['all_assets'])
            if not required_assets.issubset(set(prices.keys())):
                continue
            
            # Get window info
            window_id = self.window_manager.get_window_id(ts)
            
            # Check for new window
            if window_id != current_window_id:
                # Settle any open position from previous window
                if self.current_position:
                    self._settle_position(ts, prices, "WINDOW_EXPIRY")
                
                current_window_id = window_id
                self.trades_this_window = 0
            
            # Process timestamp
            if self.current_position is None:
                self._check_entry(ts, prices)
            else:
                self._check_exit(ts, prices)
        
        # Final settlement
        if self.current_position:
            final_ts = timestamps[-1]
            final_prices = dict(zip(
                data[data['timestamp'] == final_ts]['asset'],
                data[data['timestamp'] == final_ts]['price']
            ))
            self._settle_position(final_ts, final_prices, "BACKTEST_END")
        
        logger.info("")
        logger.info("[OK] Backtest complete")
        logger.info("")
        
        self._generate_report()
        self._export_results()
    
    def _check_entry(self, timestamp: datetime, prices: Dict[str, float]):
        """Check for entry signal"""
        
        # Check trade limit
        if self.trades_this_window >= self.config["max_trades_per_window"]:
            return
        
        # Check time eligibility
        is_eligible = self.window_manager.is_entry_eligible(
            timestamp,
            self.config["entry_window_max_remaining_seconds"],
            self.config["entry_window_min_remaining_seconds"]
        )
        
        if not is_eligible:
            return
        
        # Evaluate signal
        signal = self.strategy.evaluate_signal(prices)
        
        if signal.signal:
            self.current_position = {
                'window_id': self.window_manager.get_window_id(timestamp),
                'asset': signal.asset,
                'side': signal.signal,
                'group_config': signal.group_config,
                'group_assets': signal.group_assets,
                'entry_time': timestamp,
                'entry_price': signal.laggard_price,
                'group_prices': signal.group_prices,
                'stake_size': self.config['stake_size_usd']
            }
            
            self.trades_this_window += 1
            
            logger.debug(
                f"[ENTRY] {signal.signal} {signal.asset} @ {signal.laggard_price:.3f} "
                f"({signal.group_config}) | {timestamp}"
            )
    
    def _check_exit(self, timestamp: datetime, prices: Dict[str, float]):
        """Check exit conditions"""
        if not self.current_position:
            return
        
        asset = self.current_position['asset']
        current_price = prices.get(asset)
        
        if current_price is None:
            return
        
        # Check strategy exit
        should_exit, reason = self.strategy.check_exit(
            self.current_position['side'],
            current_price
        )
        
        if should_exit:
            self._close_position(timestamp, current_price, reason)
    
    def _close_position(self, exit_time: datetime, exit_price: float, reason: str):
        """Close position and record trade"""
        if not self.current_position:
            return
        
        # Calculate P&L
        if self.current_position['side'] == "UP":
            pnl_pct = exit_price - self.current_position['entry_price']
        else:
            pnl_pct = self.current_position['entry_price'] - exit_price
        
        pnl_usd = pnl_pct * self.current_position['stake_size']
        
        # Create trade record
        self.trade_counter += 1
        trade = BacktestTrade(
            trade_id=self.trade_counter,
            window_id=self.current_position['window_id'],
            asset=self.current_position['asset'],
            side=self.current_position['side'],
            group_config=self.current_position['group_config'],
            group_assets=self.current_position['group_assets'],
            entry_time=self.current_position['entry_time'],
            entry_price=self.current_position['entry_price'],
            group_prices_entry=self.current_position['group_prices'],
            exit_time=exit_time,
            exit_price=exit_price,
            exit_reason=reason,
            pnl_pct=pnl_pct,
            pnl_usd=pnl_usd,
            stake_size=self.current_position['stake_size'],
            outcome="WIN" if pnl_usd > 0 else "LOSS"
        )
        
        self.trades.append(trade)
        self.equity_curve.append(pnl_usd)
        
        logger.debug(
            f"[EXIT] {self.current_position['side']} {self.current_position['asset']} "
            f"@ {exit_price:.3f} | P&L: ${pnl_usd:.2f} | {reason}"
        )
        
        self.current_position = None
    
    def _settle_position(self, timestamp: datetime, prices: Dict[str, float], reason: str):
        """Settle position at window expiry"""
        if not self.current_position:
            return
        
        asset = self.current_position['asset']
        settlement_price = prices.get(asset, 0.5)
        
        self._close_position(timestamp, settlement_price, reason)
    
    def _generate_report(self):
        """Generate comprehensive backtest report"""
        if not self.trades:
            logger.warning("[WARNING] No trades executed in backtest")
            return
        
        df = pd.DataFrame([t.to_dict() for t in self.trades])
        
        # Basic statistics
        total_trades = len(df)
        winning_trades = len(df[df['pnl_usd'] > 0])
        losing_trades = len(df[df['pnl_usd'] <= 0])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # P&L statistics
        total_pnl = df['pnl_usd'].sum()
        avg_win = df[df['pnl_usd'] > 0]['pnl_usd'].mean() if winning_trades > 0 else 0
        avg_loss = df[df['pnl_usd'] <= 0]['pnl_usd'].mean() if losing_trades > 0 else 0
        max_win = df['pnl_usd'].max()
        max_loss = df['pnl_usd'].min()
        
        # Equity curve analysis
        cumulative_pnl = df['pnl_usd'].cumsum()
        df['cumulative_pnl'] = cumulative_pnl
        
        peak = cumulative_pnl.cummax()
        drawdown = cumulative_pnl - peak
        max_drawdown = drawdown.min()
        
        # Trade distribution
        up_trades = len(df[df['side'] == 'UP'])
        down_trades = len(df[df['side'] == 'DOWN'])
        
        # Group analysis
        g1_trades = len(df[df['group_config'] == 'G1'])
        g2_trades = len(df[df['group_config'] == 'G2'])
        
        # Asset analysis
        asset_stats = df.groupby('asset')['pnl_usd'].agg(['count', 'sum', 'mean'])
        
        # Display report
        print("\n" + "="*60)
        print("BACKTEST RESULTS")
        print("="*60)
        print(f"\nTRADE STATISTICS")
        print(f"  Total Trades:        {total_trades}")
        print(f"  Winning Trades:      {winning_trades} ({win_rate:.1f}%)")
        print(f"  Losing Trades:       {losing_trades} ({100-win_rate:.1f}%)")
        print(f"  UP Trades:           {up_trades}")
        print(f"  DOWN Trades:         {down_trades}")
        print(f"  Group G1:            {g1_trades}")
        print(f"  Group G2:            {g2_trades}")
        
        print(f"\nP&L STATISTICS")
        print(f"  Total P&L:           ${total_pnl:.2f}")
        print(f"  Average Win:         ${avg_win:.2f}")
        print(f"  Average Loss:        ${avg_loss:.2f}")
        print(f"  Max Win:             ${max_win:.2f}")
        print(f"  Max Loss:            ${max_loss:.2f}")
        print(f"  Max Drawdown:        ${max_drawdown:.2f}")
        
        if winning_trades > 0 and abs(avg_loss) > 0:
            profit_factor = (winning_trades * avg_win) / abs(losing_trades * avg_loss)
            print(f"  Profit Factor:       {profit_factor:.2f}")
        
        print(f"\nPER-ASSET PERFORMANCE")
        for asset in asset_stats.index:
            count = asset_stats.loc[asset, 'count']
            total = asset_stats.loc[asset, 'sum']
            avg = asset_stats.loc[asset, 'mean']
            print(f"  {asset}:  {count} trades | Total: ${total:.2f} | Avg: ${avg:.2f}")
        
        print("\n" + "="*60)
    
    def _export_results(self):
        """Export results to CSV"""
        if not self.trades:
            return
        
        output_file = f"backtest_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        with open(output_file, 'w', newline='') as f:
            if self.trades:
                fieldnames = self.trades[0].to_dict().keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for trade in self.trades:
                    writer.writerow(trade.to_dict())
        
        logger.info(f"[EXPORT] Results saved to {output_file}")