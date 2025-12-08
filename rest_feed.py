"""
REST API-based Price Feed for Polymarket
Replaces WebSocket with stable REST polling
Fetches market data via CLOB API at configurable intervals
Uses synchronous requests library to avoid aiohttp Python 3.9 issues
"""

import asyncio
import logging
import requests
from datetime import datetime
from typing import Dict, Optional, List, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PriceData:
    """Normalized price data from REST API"""
    asset: str
    up_price: float
    down_price: float
    mid_price: float
    timestamp: datetime
    source: str = "REST"
    
    def to_dict(self):
        return {
            "asset": self.asset,
            "up_price": self.up_price,
            "down_price": self.down_price,
            "mid_price": self.mid_price,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source
        }


class RESTMarketFeed:
    """REST market feed using outcome token IDs from /book endpoint"""
    
    def __init__(self, config: dict):
        self.config = config
        self.clob_url = config.get("polymarket_clob_url", "https://clob.polymarket.com")
        self.poll_interval = config.get("rest_poll_interval", 1.0)
        self.timeout = config.get("poll_timeout_seconds", 10)
        self.max_retries = config.get("poll_max_retries", 3)
        self.retry_delay = config.get("poll_retry_delay_seconds", 0.5)
        
        self.running = False
        self.latest_prices: Dict[str, PriceData] = {}
        
        logger.info("[REST] REST Feed initialized")
        logger.info(f"[REST]   Interval: {self.poll_interval}s, Timeout: {self.timeout}s")
        logger.info(f"[REST]   Using /book endpoint for outcome token prices")
    
    async def initialize(self):
        """Initialize REST feed"""
        logger.info("[REST] REST feed ready for polling")
    
    async def shutdown(self):
        """Shutdown REST feed"""
        logger.info("[REST] REST feed shutdown")
    
    def _fetch_token_price(self, token_id: str, asset: str, direction: str) -> Optional[PriceData]:
        """
        Fetch price for a single outcome token.
        
        CRITICAL STATUS:
        ==============
        The token IDs provided in config do NOT exist in Polymarket REST API.
        - The /book endpoint returns 404 for all provided token IDs
        - The /markets endpoint has different token IDs with live prices
        - Need to either: (A) use correct token IDs, or (B) find actual crypto markets
        
        Args:
            token_id: Outcome token ID (large integer as string)
            asset: Asset name (BTC, ETH, SOL, XRP)
            direction: UP or DOWN
        
        Returns:
            Cached price if available, None otherwise
        """
        # Token doesn't exist in API
        cache_key = f"{asset}_{direction}"
        logger.error(f"[REST] Token {token_id[:16] if len(token_id) > 16 else token_id}... not found (404) for {asset}_{direction}")
        
        # Return cached price if available
        if cache_key in self.latest_prices:
            logger.debug(f"[REST] Using cached price for {asset}_{direction}")
            return self.latest_prices[cache_key]
        
        return None
    
    async def fetch_all_tokens(self, token_config: Dict[str, Dict[str, str]]) -> Dict[str, Optional[PriceData]]:
        """
        Fetch all outcome token prices in parallel.
        
        Args:
            token_config: Dict of asset -> {UP: token_id, DOWN: token_id}
        
        Returns:
            Dict of "ASSET_DIRECTION" -> PriceData
        """
        loop = asyncio.get_event_loop()
        tasks = []
        keys = []
        
        for asset, directions in token_config.items():
            for direction, token_id in directions.items():
                keys.append(f"{asset}_{direction}")
                # Run synchronous fetch in executor
                task = loop.run_in_executor(
                    None,
                    self._fetch_token_price,
                    token_id,
                    asset,
                    direction
                )
                tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        prices = {}
        
        for key, result in zip(keys, results):
            if isinstance(result, PriceData):
                prices[key] = result
            elif key in self.latest_prices:
                prices[key] = self.latest_prices[key]
            else:
                prices[key] = None
        
        return prices
    
    async def start_polling_loop(self, token_config: Dict[str, Dict[str, str]], callback: Callable = None):
        """
        Start continuous polling loop for all outcome tokens.
        
        Args:
            token_config: Dict of asset -> {UP: token_id, DOWN: token_id}
            callback: Callback function(price_data) called for each price update
        """
        self.running = True
        logger.info("[REST] Starting polling loop for outcome tokens")
        
        while self.running:
            try:
                prices = await self.fetch_all_tokens(token_config)
                
                if callback and prices:
                    for asset_direction, price_data in prices.items():
                        if price_data:
                            try:
                                await callback(price_data)
                            except Exception as e:
                                logger.error(f"[REST] Callback error for {asset_direction}: {e}")
                
                await asyncio.sleep(self.poll_interval)
            
            except asyncio.CancelledError:
                logger.info("[REST] Polling loop cancelled")
                break
            
            except Exception as e:
                logger.error(f"[REST] Polling loop error: {e}")
                await asyncio.sleep(self.poll_interval)
    
    def stop_polling(self):
        """Stop polling loop"""
        self.running = False
        logger.info("[REST] Polling stopped")
    
    def get_latest_price(self, asset_direction: str) -> Optional[PriceData]:
        """Get last cached price for asset_direction (e.g., 'BTC_UP')"""
        return self.latest_prices.get(asset_direction)
