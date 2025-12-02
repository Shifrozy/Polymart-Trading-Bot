"""
Live trading engine with paper trading support
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

from data_feed import DataFeedManager
from window_manager import WindowManager
from strategy import PolymarketStrategy
from logger import TradeLogger

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Active trading position"""
    window_id: str
    asset: str
    side: str  # "UP" or "DOWN"
    entry_time: datetime
    entry_price: float
    group_config: str
    group_prices: dict
    stake_size: float


class LiveTrader:
    """Live trading engine with paper trading mode"""
    
    def __init__(self, config, paper_trade=True):
        self.config = config
        self.paper_trade = paper_trade
        
        self.window_manager = WindowManager(config["window_duration_minutes"])
        self.strategy = PolymarketStrategy(config)
        self.trade_logger = TradeLogger(config)
        
        self.data_feed = None
        self.current_position: Optional[Position] = None
        self.current_window_id = None
        self.running = False
        
        logger.info(f"LiveTrader initialized (Paper: {paper_trade})")
    
    async def initialize(self, market_ids: dict):
        """Initialize data feeds"""
        self.data_feed = DataFeedManager(self.config)
        await self.data_feed.initialize(market_ids)
        await self.data_feed.start_rtds()
        logger.info("✅ Data feed initialized")
    
    async def run(self):
        """Main trading loop"""
        self.running = True
        logger.info(f"🚀 Starting trading loop")
        
        while self.running:
            try:
                await self._trading_cycle()
                await asyncio.sleep(self.config["entry_check_interval"])
            except Exception as e:
                logger.error(f"Trading cycle error: {e}", exc_info=True)
                await asyncio.sleep(5)
    
    async def _trading_cycle(self):
        """Single trading cycle"""
        current_time = datetime.utcnow()
        window_start, window_end = self.window_manager.get_current_window(current_time)
        window_id = self.window_manager.get_window_id(current_time)
        
        # Check if new window
        if window_id != self.current_window_id:
            logger.info(f"📅 New window: {window_id}")
            self.current_window_id = window_id
            
            # Close any position from previous window
            if self.current_position:
                await self._settle_position("SETTLEMENT")
        
        # Get latest prices
        all_assets = self.config["reference_assets"] + self.config["tradeable_assets"]
        price_data = await self.data_feed.get_latest_prices(all_assets)
        prices = {asset: data.price for asset, data in price_data.items()}
        
        # Log current prices
        price_str = ", ".join([f"{k}={v:.3f}" for k, v in prices.items()])
        logger.debug(f"Prices: {price_str}")
        
        # If no position, check for entry
        if self.current_position is None:
            await self._check_entry(current_time, window_start, window_end, prices)
        
        # If position exists, check for exit
        else:
            await self._check_exit(current_time, prices)
    
    async def _check_entry(self, current_time, window_start, window_end, prices):
        """Check for entry signal"""
        
        # Check time eligibility
        if not self.window_manager.is_entry_eligible(
            current_time,
            self.config["entry_window_max_remaining"],
            self.config["entry_window_min_remaining"]
        ):
            return
        
        # Evaluate strategy signal
        signal = self.strategy.evaluate_signal(prices)
        
        if signal.signal:
            logger.info(f"🎯 ENTRY SIGNAL: {signal.signal} on {signal.asset} ({signal.group_config})")
            logger.info(f"   Entry price: {signal.laggard_price:.3f}")
            logger.info(f"   Group prices: {signal.group_prices}")
            
            # Create position
            self.current_position = Position(
                window_id=self.current_window_id,
                asset=signal.asset,
                side=signal.signal,
                entry_time=current_time,
                entry_price=signal.laggard_price,
                group_config=signal.group_config,
                group_prices=signal.group_prices,
                stake_size=self.config["stake_size"]
            )
            
            # Execute order (paper trade or real)
            if self.paper_trade:
                logger.info(f"📝 [PAPER] Entered {signal.signal} on {signal.asset} @ {signal.laggard_price:.3f}")
            else:
                await self._execute_order("BUY", signal.asset, signal.signal, self.config["stake_size"])
    
    async def _check_exit(self, current_time, prices):
        """Check if position should be exited"""
        if not self.current_position:
            return
        
        current_price = prices.get(self.current_position.asset)
        if current_price is None:
            logger.warning(f"⚠️  Missing price for {self.current_position.asset}")
            return
        
        # Check exit conditions
        should_exit, reason = self.strategy.check_exit(
            self.current_position.side,
            current_price
        )
        
        if should_exit:
            await self._close_position(current_time, current_price, reason)
    
    async def _close_position(self, exit_time, exit_price, reason):
        """Close current position"""
        if not self.current_position:
            return
        
        # Calculate P&L
        if self.current_position.side == "UP":
            pnl = exit_price - self.current_position.entry_price
        else:  # DOWN
            pnl = self.current_position.entry_price - exit_price
        
        pnl_usd = pnl * self.current_position.stake_size
        
        # Log trade
        trade_data = {
            "timestamp_entry": self.current_position.entry_time.isoformat(),
            "window_id": self.current_position.window_id,
            "asset": self.current_position.asset,
            "side": self.current_position.side,
            "entry_price": self.current_position.entry_price,
            "group_config": self.current_position.group_config,
            "group_prices_entry": str(self.current_position.group_prices),
            "timestamp_exit": exit_time.isoformat(),
            "exit_price": exit_price,
            "exit_reason": reason,
            "pnl_contract": pnl,
            "pnl_usd": pnl_usd,
            "stake_size": self.current_position.stake_size,
            "settlement_outcome": "WIN" if pnl > 0 else "LOSS",
            "fees": 0.0
        }
        
        self.trade_logger.log_trade(trade_data)
        
        pnl_sign = "+" if pnl_usd >= 0 else ""
        logger.info(f"🏁 CLOSED: {self.current_position.side} {self.current_position.asset}")
        logger.info(f"   Entry: {self.current_position.entry_price:.3f} → Exit: {exit_price:.3f}")
        logger.info(f"   P&L: {pnl_sign}${pnl_usd:.2f} | {reason}")
        
        if self.paper_trade:
            logger.info(f"📝 [PAPER] Position closed")
        else:
            await self._execute_order("SELL", self.current_position.asset, 
                                     self.current_position.side, self.current_position.stake_size)
        
        self.current_position = None
    
    async def _settle_position(self, reason):
        """Settle position at window expiry"""
        if self.current_position:
            logger.info(f"⏰ Settling position at window expiry")
            # Simplified: assume final price based on direction
            settlement_price = 1.0 if self.current_position.side == "UP" else 0.0
            await self._close_position(datetime.utcnow(), settlement_price, reason)
    
    async def _execute_order(self, action, asset, side, amount):
        """Execute real order on Polymarket"""
        logger.info(f"💼 Executing {action} order: {asset} {side} ${amount}")
        # TODO: Implement actual Polymarket order execution
        pass
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("🛑 Shutting down trader...")
        self.running = False
        if self.current_position:
            await self._settle_position("SHUTDOWN")
        if self.data_feed:
            await self.data_feed.shutdown()
        logger.info("✅ Trader shutdown complete")