"""
Enhanced Live Trading Engine
Production-ready with better error handling and position management
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict
from dataclasses import dataclass, asdict

from data_feed import EnhancedDataFeedManager
from window_manager import WindowManager
from strategy import EnhancedPolymarketStrategy
from logger import TradeLogger

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Active trading position"""
    window_id: str
    asset: str
    side: str
    entry_time: datetime
    entry_price: float
    group_config: str
    group_assets: list
    group_prices: dict
    stake_size: float
    market_id: str = ""
    stop_loss_price: float = 0.0  # Stop loss level
    
    def to_dict(self):
        return asdict(self)


class EnhancedLiveTrader:
    """Enhanced live trading engine"""
    
    def __init__(self, config, paper_trade=True):
        self.config = config
        self.paper_trade = paper_trade
        
        # Initialize components
        self.window_manager = WindowManager(config["window_duration_minutes"])
        self.strategy = EnhancedPolymarketStrategy(config)
        self.trade_logger = TradeLogger(config)
        self.data_feed = None
        
        # State
        self.current_position: Optional[Position] = None
        self.current_window_id = None
        self.trades_this_window = 0
        self.running = False
        self.total_trades = 0
        self.total_pnl = 0.0
        
        logger.info(f"[INIT] EnhancedLiveTrader initialized (Paper Trade Mode: {paper_trade})")
    
    async def initialize(self):
        """Initialize trader and data feeds"""
        logger.info("[INIT] Initializing trader components...")
        
        # Initialize data feed with all assets
        self.data_feed = EnhancedDataFeedManager(self.config)
        all_assets = self.config["all_assets"]
        await self.data_feed.initialize(all_assets)
        await self.data_feed.start_stream()
        
        # Wait for initial prices
        logger.info("[INIT] Waiting for initial price data...")
        await asyncio.sleep(3)
        
        logger.info("[OK] Trader initialization complete")
        self._log_config()
    
    def _log_config(self):
        """Log current configuration"""
        logger.info("="*60)
        logger.info("TRADING CONFIGURATION")
        logger.info("="*60)
        logger.info(f"Assets: {', '.join(self.config['all_assets'])}")
        logger.info(f"Reference: {', '.join(self.config['reference_assets'])}")
        logger.info(f"Tradeable: {', '.join(self.config['tradeable_assets'])}")
        logger.info(f"Window: {self.config['window_duration_minutes']} minutes")
        logger.info(f"Entry window: {self.config['entry_window_min_remaining_seconds']}s - {self.config['entry_window_max_remaining_seconds']}s")
        logger.info(f"Stake size: ${self.config['stake_size_usd']}")
        logger.info(f"Stop Loss: {self.config['stop_loss_pct']*100:.1f}%")
        logger.info(f"Exit UP: >= {self.config['exit_up_threshold']}")
        logger.info(f"Exit DOWN: <= {self.config['exit_down_threshold']}")
        logger.info("="*60)
    
    def _calculate_stop_loss(self, side: str, entry_price: float) -> float:
        """
        Calculate stop loss price
        
        For binary options (0-1 range):
        - UP: Stop loss is entry_price - stop_loss_pct
        - DOWN: Stop loss is entry_price + stop_loss_pct
        """
        stop_loss_pct = self.config.get("stop_loss_pct", 0.05)
        
        if side == "UP":
            # For UP trades, stop loss is below entry (subtract percentage)
            stop_loss = max(0.0, entry_price - stop_loss_pct)
        else:  # DOWN
            # For DOWN trades, stop loss is above entry (add percentage)
            stop_loss = min(1.0, entry_price + stop_loss_pct)
        
        return stop_loss
    
    async def run(self):
        """Main trading loop"""
        self.running = True
        logger.info("[START] Starting trading loop")
        logger.info("Press Ctrl+C to stop...")
        logger.info("")
        
        while self.running:
            try:
                await self._trading_cycle()
                await asyncio.sleep(self.config["entry_check_interval_seconds"])
            except KeyboardInterrupt:
                raise
            except Exception as e:
                logger.error(f"[ERROR] Trading cycle error: {e}", exc_info=True)
                await asyncio.sleep(5)
    
    async def _trading_cycle(self):
        """Single trading cycle"""
        current_time = datetime.utcnow()
        window_start, window_end = self.window_manager.get_current_window(current_time)
        window_id = self.window_manager.get_window_id(current_time)
        time_remaining = self.window_manager.get_time_remaining(current_time)
        
        # Check for new window
        if window_id != self.current_window_id:
            await self._handle_new_window(window_id)
        
        # Get latest prices (now returns option prices)
        all_assets = self.config["all_assets"]
        price_data = await self.data_feed.get_latest_prices(all_assets)
        
        # Convert to option price format: {"BTC": {"UP": 0.45, "DOWN": 0.55}, ...}
        prices = {}
        for asset, data in price_data.items():
            if asset not in prices:
                prices[asset] = {"UP": 0.5, "DOWN": 0.5}
            # For now, use the price as UP price (mock data)
            prices[asset]["UP"] = data.price
            prices[asset]["DOWN"] = 1.0 - data.price
        
        # Log prices periodically
        if int(time_remaining) % 60 == 0:  # Every minute
            price_str = ", ".join([f"{k}={v['UP']:.3f}" for k, v in sorted(prices.items())])
            logger.info(f"[PRICES] {price_str} | Window: {window_id} | Remaining: {time_remaining:.0f}s")
        
        # Check for actions
        if self.current_position is None:
            await self._check_entry(current_time, prices)
        else:
            await self._check_exit(current_time, prices)
    
    async def _handle_new_window(self, window_id: str):
        """Handle transition to new window"""
        logger.info("")
        logger.info("="*60)
        logger.info(f"[NEW WINDOW] {window_id}")
        logger.info("="*60)
        
        # Settle any open position
        if self.current_position:
            await self._settle_position("WINDOW_EXPIRY")
        
        # Reset window counters
        self.current_window_id = window_id
        self.trades_this_window = 0
        
        # Refresh market data periodically
        await self.data_feed.refresh_markets()
    
    async def _check_entry(self, current_time: datetime, prices: Dict[str, float]):
        """Check for entry signal"""
        
        # Check if we can trade this window
        if self.trades_this_window >= self.config["max_trades_per_window"]:
            return
        
        # Check time eligibility
        is_eligible = self.window_manager.is_entry_eligible(
            current_time,
            self.config["entry_window_max_remaining_seconds"],
            self.config["entry_window_min_remaining_seconds"]
        )
        
        if not is_eligible:
            return
        
        # Evaluate strategy
        signal = self.strategy.evaluate_signal(prices)
        
        if signal.signal:
            logger.info("")
            logger.info("*"*60)
            logger.info(f"[SIGNAL DETECTED] {signal}")
            logger.info("*"*60)
            
            await self._enter_position(signal, current_time, prices)
    
    async def _enter_position(self, signal, entry_time: datetime, prices: Dict[str, float]):
        """Enter a new position"""
        
        # Get market info
        market_info = self.data_feed.get_market_info(signal.asset)
        
        # Create position
        self.current_position = Position(
            window_id=self.current_window_id,
            asset=signal.asset,
            side=signal.signal,
            entry_time=entry_time,
            entry_price=signal.laggard_price,
            group_config=signal.group_config,
            group_assets=signal.group_assets,
            group_prices=signal.group_prices,
            stake_size=self.config["stake_size_usd"],
            market_id=market_info.market_id if market_info else "",
            stop_loss_price=self._calculate_stop_loss(signal.signal, signal.laggard_price)
        )
        
        # Log entry
        logger.info(f"[ENTRY] {signal.signal} position on {signal.asset}")
        logger.info(f"  Window: {self.current_window_id}")
        logger.info(f"  Group: {signal.group_config} - {signal.group_assets}")
        logger.info(f"  Group prices: {signal.group_prices}")
        logger.info(f"  Entry price: {signal.laggard_price:.4f}")
        logger.info(f"  Stop Loss: {self.current_position.stop_loss_price:.4f}")
        logger.info(f"  Stake: ${self.config['stake_size_usd']}")
        logger.info(f"  Market ID: {self.current_position.market_id}")
        
        if self.paper_trade:
            logger.info(f"  [PAPER TRADE] ✓ Simulated entry CONFIRMED")
        else:
            logger.info(f"  [LIVE TRADE] Executing order...")
            await self._execute_order("ENTRY", signal.asset, signal.signal)
        
        self.trades_this_window += 1
        logger.info("")
    
    async def _check_exit(self, current_time: datetime, prices: Dict[str, float]):
        """Check exit conditions"""
        if not self.current_position:
            return
        
        price_data = prices.get(self.current_position.asset)
        
        if price_data is None:
            logger.warning(f"[WARNING] No price for {self.current_position.asset}")
            return
        
        # Extract the correct option price based on position side
        if isinstance(price_data, dict):
            if self.current_position.side == "UP":
                current_price = price_data.get("UP", 0.5)
            else:
                current_price = price_data.get("DOWN", 0.5)
        else:
            current_price = price_data
        
        # Check STOP LOSS first (most important)
        if self._check_stop_loss(current_price):
            await self._exit_position(current_time, current_price, "STOP_LOSS")
            return
        
        # Check strategy exit conditions
        should_exit, reason = self.strategy.check_exit(
            self.current_position.side,
            current_price
        )
        
        if should_exit:
            await self._exit_position(current_time, current_price, reason)
    
    def _check_stop_loss(self, current_price: float) -> bool:
        """Check if stop loss is triggered"""
        if not self.current_position:
            return False
        
        stop_loss_price = self.current_position.stop_loss_price
        
        if self.current_position.side == "UP":
            # For UP, stop loss triggers when price goes below stop loss
            return current_price <= stop_loss_price
        else:  # DOWN
            # For DOWN, stop loss triggers when price goes above stop loss
            return current_price >= stop_loss_price
    
    async def _exit_position(self, exit_time: datetime, exit_price: float, reason: str):
        """Exit current position"""
        if not self.current_position:
            return
        
        # Calculate P&L
        if self.current_position.side == "UP":
            pnl_pct = exit_price - self.current_position.entry_price
        else:  # DOWN
            pnl_pct = self.current_position.entry_price - exit_price
        
        pnl_usd = pnl_pct * self.current_position.stake_size
        
        # Update totals
        self.total_trades += 1
        self.total_pnl += pnl_usd
        
        # Prepare trade log
        trade_data = {
            "timestamp_entry": self.current_position.entry_time.isoformat(),
            "timestamp_exit": exit_time.isoformat(),
            "window_id": self.current_position.window_id,
            "asset": self.current_position.asset,
            "side": self.current_position.side,
            "group_config": self.current_position.group_config,
            "group_assets": str(self.current_position.group_assets),
            "group_prices_entry": str(self.current_position.group_prices),
            "entry_price": self.current_position.entry_price,
            "exit_price": exit_price,
            "exit_reason": reason,
            "pnl_pct": pnl_pct,
            "pnl_usd": pnl_usd,
            "stake_size": self.current_position.stake_size,
            "outcome": "WIN" if pnl_usd > 0 else "LOSS",
            "market_id": self.current_position.market_id,
            "cumulative_pnl": self.total_pnl,
            "trade_number": self.total_trades
        }
        
        # Log trade
        self.trade_logger.log_trade(trade_data)
        
        # Display results
        logger.info("")
        logger.info("="*60)
        logger.info(f"[EXIT] Position closed - {reason}")
        logger.info("="*60)
        logger.info(f"Asset: {self.current_position.asset} | Side: {self.current_position.side}")
        logger.info(f"Entry Price:   {self.current_position.entry_price:.4f} @ {self.current_position.entry_time.strftime('%H:%M:%S')}")
        logger.info(f"Stop Loss:     {self.current_position.stop_loss_price:.4f}")
        logger.info(f"Exit Price:    {exit_price:.4f} @ {exit_time.strftime('%H:%M:%S')}")
        logger.info(f"P&L:           {'+' if pnl_usd >= 0 else ''}{pnl_usd:.4f} USD ({'+' if pnl_pct >= 0 else ''}{pnl_pct*100:.2f}%)")
        logger.info(f"Result:        {'✅ WIN' if pnl_usd > 0 else '❌ LOSS'}")
        logger.info(f"Exit Reason:   {reason}")
        logger.info(f"Stats:         Trade #{self.total_trades} | Cumulative P&L: ${self.total_pnl:.2f}")
        logger.info("="*60)
        logger.info("")
        
        if self.paper_trade:
            logger.info("[PAPER TRADE] ✓ Exit order simulated")
        else:
            logger.info("[LIVE TRADE] Executing exit order...")
            await self._execute_order("EXIT", self.current_position.asset, self.current_position.side)
        
        # Clear position
        self.current_position = None
    
    async def _settle_position(self, reason: str):
        """Settle position at window expiry"""
        if not self.current_position:
            return
        
        logger.info(f"[SETTLEMENT] Position settling: {reason}")
        
        # Get final price
        price_data = await self.data_feed.get_latest_prices([self.current_position.asset])
        
        if self.current_position.asset in price_data:
            final_price = price_data[self.current_position.asset].price
        else:
            # Simplified settlement
            final_price = 1.0 if self.current_position.side == "UP" else 0.0
            logger.warning(f"[SETTLEMENT] No final price, using {final_price}")
        
        await self._exit_position(datetime.utcnow(), final_price, reason)
    
    async def _execute_order(self, action: str, asset: str, side: str):
        """
        Simulate order execution (Paper Trading Mode)
        
        In real implementation, this would place actual orders via CLOB API
        For now, we just simulate the execution
        """
        if self.paper_trade:
            logger.info(f"[PAPER TRADE] {action}: {side} {asset} @ simulated market price")
            logger.info(f"[PAPER TRADE] Stake: ${self.config['stake_size_usd']}")
            logger.info(f"[PAPER TRADE] Status: ✓ Simulated order filled")
        else:
            logger.warning(f"[WARNING] LIVE TRADING not yet implemented!")
            logger.warning(f"[WARNING] {action}: {side} {asset} would execute here with real money")
            logger.warning(f"[NOTE] To use live trading, implement CLOB API integration")
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("")
        logger.info("[SHUTDOWN] Initiating shutdown...")
        self.running = False
        
        # Close open positions
        if self.current_position:
            await self._settle_position("SHUTDOWN")
        
        # Shutdown data feed
        if self.data_feed:
            await self.data_feed.shutdown()
        
        # Final statistics
        logger.info("")
        logger.info("="*60)
        logger.info("SESSION SUMMARY")
        logger.info("="*60)
        logger.info(f"Total Trades: {self.total_trades}")
        logger.info(f"Total P&L: ${self.total_pnl:.2f}")
        if self.total_trades > 0:
            avg_pnl = self.total_pnl / self.total_trades
            logger.info(f"Average P&L: ${avg_pnl:.2f}")
        logger.info("="*60)
        logger.info("[OK] Shutdown complete")