"""
Real-time and historical data feed manager for Polymarket
Simplified version without aiohttp dependency issues
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable
import random

logger = logging.getLogger(__name__)


class PriceData:
    """Normalized price data model"""
    
    def __init__(self, timestamp: datetime, asset: str, price: float):
        self.timestamp = timestamp
        self.asset = asset
        self.price = price
    
    def to_dict(self):
        return {
            "timestamp": self.timestamp.isoformat(),
            "asset": self.asset,
            "price": self.price
        }


class PolymarketRESTClient:
    """REST API client - Simplified version"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
    
    async def __aenter__(self):
        logger.info("REST client initialized (mock mode)")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    
    async def get_market_prices(self, market_ids: List[str]) -> Dict[str, float]:
        """Fetch current prices - returns mock data"""
        logger.debug("Using mock prices (REST client)")
        return {mid: 0.5 for mid in market_ids}
    
    async def get_historical_data(self, market_id: str, start_date: str, end_date: str):
        """Fetch historical price data"""
        return []


class PolymarketRTDSClient:
    """Real-time data stream - Mock implementation"""
    
    def __init__(self, ws_url: str, market_ids: Dict[str, str], reconnect_delay: int = 5):
        self.ws_url = ws_url
        self.market_ids = market_ids
        self.reconnect_delay = reconnect_delay
        self.running = False
        self.callbacks: List[Callable] = []
    
    def subscribe(self, callback: Callable):
        """Register callback for price updates"""
        self.callbacks.append(callback)
    
    async def connect(self):
        """Generate mock price stream"""
        logger.info("[MOCK] Starting mock price stream for testing")
        await self._mock_price_stream()
    
    async def _mock_price_stream(self):
        """Generate realistic mock price updates"""
        # Initialize prices with some variety
        prices = {
            "BTC": random.uniform(0.45, 0.55),
            "ETH": random.uniform(0.45, 0.55),
            "SOL": random.uniform(0.45, 0.55),
            "XRP": random.uniform(0.45, 0.55)
        }
        
        self.running = True
        iteration = 0
        
        while self.running:
            iteration += 1
            
            # Every 20 iterations, create potential signal conditions
            if iteration % 20 == 0:
                scenario = random.choice(['up_signal', 'down_signal', 'neutral'])
                
                if scenario == 'up_signal':
                    # Group high, laggard low
                    prices["BTC"] = random.uniform(0.75, 0.95)
                    prices["ETH"] = random.uniform(0.75, 0.95)
                    prices["SOL"] = random.uniform(0.75, 0.95)
                    prices["XRP"] = random.uniform(0.10, 0.45)
                    logger.info("[MOCK] Creating UP signal scenario")
                    
                elif scenario == 'down_signal':
                    # Group low, laggard high
                    prices["BTC"] = random.uniform(0.05, 0.25)
                    prices["ETH"] = random.uniform(0.05, 0.25)
                    prices["SOL"] = random.uniform(0.05, 0.25)
                    prices["XRP"] = random.uniform(0.55, 0.90)
                    logger.info("[MOCK] Creating DOWN signal scenario")
                    
                else:
                    # Random neutral prices
                    for asset in prices:
                        prices[asset] = random.uniform(0.30, 0.70)
            else:
                # Small random changes
                for asset in prices:
                    change = random.uniform(-0.02, 0.02)
                    prices[asset] = max(0.01, min(0.99, prices[asset] + change))
            
            # Send price updates
            for asset in self.market_ids.keys():
                price_data = PriceData(datetime.utcnow(), asset, prices[asset])
                
                for callback in self.callbacks:
                    try:
                        await callback(price_data)
                    except Exception as e:
                        logger.error(f"Callback error: {e}")
            
            await asyncio.sleep(2)  # Update every 2 seconds
    
    async def disconnect(self):
        """Gracefully disconnect"""
        self.running = False
        logger.info("[MOCK] Price stream stopped")


class DataFeedManager:
    """Manages both REST and RTDS feeds"""
    
    def __init__(self, config):
        self.config = config
        self.rest_client = None
        self.rtds_client = None
        self.latest_prices: Dict[str, PriceData] = {}
        self.use_rtds = True
    
    async def initialize(self, market_ids: Dict[str, str]):
        """Initialize both REST and RTDS clients"""
        logger.info("Initializing data feed manager...")
        
        self.rest_client = PolymarketRESTClient(self.config["polymarket_rest_url"])
        await self.rest_client.__aenter__()
        
        self.rtds_client = PolymarketRTDSClient(
            self.config["polymarket_rtds_url"],
            market_ids,
            self.config["reconnect_delay"]
        )
        
        # Subscribe to price updates
        self.rtds_client.subscribe(self._on_price_update)
        
        logger.info("[OK] Data feed manager initialized")
    
    async def _on_price_update(self, price_data: PriceData):
        """Handle incoming price updates from RTDS"""
        self.latest_prices[price_data.asset] = price_data
        self.use_rtds = True
    
    async def start_rtds(self):
        """Start RTDS connection in background"""
        logger.info("Starting RTDS connection...")
        asyncio.create_task(self.rtds_client.connect())
    
    async def get_latest_prices(self, assets: List[str]) -> Dict[str, PriceData]:
        """Get latest prices"""
        # Wait a moment if prices not ready
        if not all(asset in self.latest_prices for asset in assets):
            await asyncio.sleep(0.5)
        
        if self.use_rtds and all(asset in self.latest_prices for asset in assets):
            return {asset: self.latest_prices[asset] for asset in assets}
        
        # Fallback
        result = {}
        for asset in assets:
            if asset in self.latest_prices:
                result[asset] = self.latest_prices[asset]
            else:
                result[asset] = PriceData(datetime.utcnow(), asset, 0.5)
        
        return result
    
    async def shutdown(self):
        """Clean shutdown"""
        logger.info("Shutting down data feed manager...")
        await self.rtds_client.disconnect()
        await self.rest_client.__aexit__(None, None, None)
        logger.info("[OK] Data feed shutdown complete")