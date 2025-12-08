"""
Enhanced Data Feed Manager with REST API polling
Replaces WebSocket with stable REST polling
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable

from market_loader import PolymarketLoader, MarketInfo
from rest_feed import RESTMarketFeed, PriceData

logger = logging.getLogger(__name__)


class PriceData:
    """Normalized price data model"""
    
    def __init__(self, timestamp: datetime, asset: str, price: float, source: str = "mock", contract_type: str = "SPOT"):
        self.timestamp = timestamp
        self.asset = asset
        self.price = price
        self.source = source
        self.contract_type = contract_type  # "SPOT", "UP", or "DOWN"
    
    def to_dict(self):
        return {
            "timestamp": self.timestamp.isoformat(),
            "asset": self.asset,
            "price": self.price,
            "source": self.source,
            "contract_type": self.contract_type
        }



class EnhancedDataFeedManager:
    """Enhanced data feed with REST-based polling using outcome token IDs"""
    
    def __init__(self, config):
        self.config = config
        self.market_loader = PolymarketLoader(config)
        self.rest_feed = RESTMarketFeed(config)  # REST polling for outcome tokens
        self.markets: Dict[str, MarketInfo] = {}
        self.latest_prices: Dict[str, PriceData] = {}
        self.token_config: Dict[str, Dict[str, str]] = {}  # Asset -> {UP: token_id, DOWN: token_id}
        self.polling_task = None
    
    async def initialize(self, assets: List[str]):
        """Initialize with token IDs for REST polling"""
        logger.info("[INIT] Initializing enhanced data feed...")
        
        # Load token IDs directly from config
        token_ids = self.config.get("token_ids", {})
        
        # Build token config for REST polling
        for asset in assets:
            if asset in token_ids:
                self.token_config[asset] = token_ids[asset]
                logger.info(f"[REST] Loaded token IDs for {asset}")
            else:
                logger.warning(f"[REST] No token IDs for {asset}")
        
        # Initialize REST feed
        await self.rest_feed.initialize()
        logger.info("[REST] REST feed initialized for polling")
        logger.info("[OK] Enhanced data feed initialized")
    
    async def _on_price_update(self, price_data: PriceData):
        """Handle price updates from REST polling"""
        self.latest_prices[price_data.asset] = price_data
    
    async def start_stream(self, callback=None):
        """Start REST polling for outcome token prices"""
        logger.info("[STREAM] Starting REST price polling...")
        
        if not self.rest_feed:
            raise RuntimeError("REST feed not initialized")
        
        if not self.token_config:
            raise RuntimeError("No token IDs configured")
        
        # Use internal price update handler if no callback provided
        cb = callback or self._on_price_update
        
        # Start REST polling loop with token config
        await self.rest_feed.start_polling_loop(self.token_config, cb)
    
    async def get_latest_prices(self, assets: List[str]) -> Dict[str, PriceData]:
        """Get latest prices for assets from REST polling"""
        # REST polling continuously updates latest_prices
        result = {}
        for asset in assets:
            if asset in self.latest_prices:
                result[asset] = self.latest_prices[asset]
            else:
                # Fallback - create default price if asset not yet updated
                result[asset] = PriceData(datetime.utcnow(), asset, 0.5, "default")
        
        return result
    
    def get_market_info(self, asset: str) -> Optional[MarketInfo]:
        """Get market info for asset"""
        return self.markets.get(asset)
    
    async def refresh_markets(self):
        """Refresh market data if needed"""
        # Refresh market loader data periodically
        if self.market_loader.should_update():
            logger.info("[REFRESH] Updating market information...")
            assets = list(self.markets.keys())
            self.markets = await self.market_loader.fetch_markets(assets)
            
            # Update market config for REST polling
            for asset in assets:
                if asset in self.markets:
                    market = self.markets[asset]
                    self.market_config[asset] = market.market_id
    
    async def shutdown(self):
        """Shutdown data feed"""
        logger.info("[SHUTDOWN] Shutting down data feed...")
        if self.rest_feed:
            await self.rest_feed.shutdown()
        logger.info("[OK] Data feed shutdown complete")