"""
Enhanced Data Feed Manager with Real Polymarket Integration
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable
import random

from market_loader import PolymarketLoader, MarketInfo

logger = logging.getLogger(__name__)


class PriceData:
    """Normalized price data model"""
    
    def __init__(self, timestamp: datetime, asset: str, price: float, source: str = "mock"):
        self.timestamp = timestamp
        self.asset = asset
        self.price = price  # This is YES token price (UP probability)
        self.source = source
    
    def to_dict(self):
        return {
            "timestamp": self.timestamp.isoformat(),
            "asset": self.asset,
            "price": self.price,
            "source": self.source
        }


class EnhancedRTDSClient:
    """Enhanced Real-time data stream with market info"""
    
    def __init__(self, ws_url: str, markets: Dict[str, MarketInfo], reconnect_delay: int = 5):
        self.ws_url = ws_url
        self.markets = markets
        self.reconnect_delay = reconnect_delay
        self.running = False
        self.callbacks: List[Callable] = []
        self.websockets_available = False
        
        try:
            import websockets
            self.websockets_available = True
            logger.info("WebSocket support enabled")
        except ImportError:
            logger.warning("websockets not installed - using mock mode")
    
    def subscribe(self, callback: Callable):
        """Register callback for price updates"""
        self.callbacks.append(callback)
    
    async def connect(self):
        """Connect to WebSocket with auto-reconnect"""
        if not self.websockets_available:
            logger.info("[MOCK MODE] Starting mock price stream")
            await self._mock_price_stream()
            return
        
        import websockets
        self.running = True
        attempts = 0
        
        while self.running and attempts < 10:
            try:
                async with websockets.connect(self.ws_url) as ws:
                    logger.info("[RTDS] WebSocket connected")
                    attempts = 0
                    
                    # Subscribe to all markets
                    subscribe_msg = {
                        "type": "subscribe",
                        "markets": [m.market_id for m in self.markets.values()]
                    }
                    await ws.send(json.dumps(subscribe_msg))
                    logger.info(f"[RTDS] Subscribed to {len(self.markets)} markets")
                    
                    # Listen for updates
                    async for message in ws:
                        await self._handle_message(message)
                        
            except websockets.exceptions.ConnectionClosed:
                attempts += 1
                logger.warning(f"[RTDS] Disconnected, reconnecting... (attempt {attempts})")
                await asyncio.sleep(self.reconnect_delay)
            except Exception as e:
                attempts += 1
                logger.error(f"[RTDS] Error: {e}")
                await asyncio.sleep(self.reconnect_delay)
        
        if attempts >= 10:
            logger.error("[RTDS] Max reconnection attempts reached, falling back to mock mode")
            await self._mock_price_stream()
    
    async def _handle_message(self, message: str):
        """Parse WebSocket message"""
        try:
            data = json.loads(message)
            
            if data.get("type") == "price_update":
                market_id = data.get("market")
                price = float(data.get("price", 0.5))
                
                # Find asset by market_id
                asset = None
                for a, market in self.markets.items():
                    if market.market_id == market_id:
                        asset = a
                        break
                
                if asset:
                    price_data = PriceData(
                        datetime.utcnow(),
                        asset,
                        price,
                        source="rtds"
                    )
                    
                    for callback in self.callbacks:
                        await callback(price_data)
                        
        except Exception as e:
            logger.error(f"Message parsing error: {e}")
    
    async def _mock_price_stream(self):
        """Generate realistic mock price stream with signals"""
        logger.info("[MOCK] Starting enhanced mock price stream")
        
        # Initialize with varied starting prices
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
            
            # Create signal scenarios periodically
            if iteration % 30 == 0:
                scenario = random.choice(['up_signal', 'down_signal', 'neutral', 'neutral'])
                
                if scenario == 'up_signal':
                    # Group G1: BTC, ETH, SOL high → XRP low
                    prices["BTC"] = random.uniform(0.76, 0.92)
                    prices["ETH"] = random.uniform(0.76, 0.92)
                    prices["SOL"] = random.uniform(0.76, 0.92)
                    prices["XRP"] = random.uniform(0.15, 0.45)
                    logger.info("[MOCK SCENARIO] Creating UP signal opportunity (G1)")
                    
                elif scenario == 'down_signal':
                    # Group G2: BTC, ETH, XRP low → SOL high
                    prices["BTC"] = random.uniform(0.08, 0.24)
                    prices["ETH"] = random.uniform(0.08, 0.24)
                    prices["XRP"] = random.uniform(0.08, 0.24)
                    prices["SOL"] = random.uniform(0.55, 0.85)
                    logger.info("[MOCK SCENARIO] Creating DOWN signal opportunity (G2)")
                    
                else:
                    # Random neutral zone
                    for asset in prices:
                        prices[asset] = random.uniform(0.35, 0.65)
            
            # Small random walk
            else:
                for asset in prices:
                    change = random.uniform(-0.03, 0.03)
                    prices[asset] = max(0.01, min(0.99, prices[asset] + change))
            
            # Emit price updates
            for asset in self.markets.keys():
                price_data = PriceData(
                    datetime.utcnow(),
                    asset,
                    prices[asset],
                    source="mock"
                )
                
                for callback in self.callbacks:
                    try:
                        await callback(price_data)
                    except Exception as e:
                        logger.error(f"Callback error: {e}")
            
            await asyncio.sleep(2)
    
    async def disconnect(self):
        """Disconnect WebSocket"""
        self.running = False


class EnhancedDataFeedManager:
    """Enhanced data feed with market loader"""
    
    def __init__(self, config):
        self.config = config
        self.market_loader = PolymarketLoader(config)
        self.rtds_client = None
        self.markets: Dict[str, MarketInfo] = {}
        self.latest_prices: Dict[str, PriceData] = {}
    
    async def initialize(self, assets: List[str]):
        """Initialize with dynamic market loading"""
        logger.info("[INIT] Initializing enhanced data feed...")
        
        # Load markets from Polymarket API
        self.markets = await self.market_loader.fetch_markets(assets)
        
        # Initialize RTDS client
        self.rtds_client = EnhancedRTDSClient(
            self.config["polymarket_rtds_url"],
            self.markets,
            self.config["reconnect_delay_seconds"]
        )
        
        # Subscribe to price updates
        self.rtds_client.subscribe(self._on_price_update)
        
        logger.info("[OK] Enhanced data feed initialized")
    
    async def _on_price_update(self, price_data: PriceData):
        """Handle price updates"""
        self.latest_prices[price_data.asset] = price_data
    
    async def start_stream(self):
        """Start price stream"""
        logger.info("[STREAM] Starting price stream...")
        asyncio.create_task(self.rtds_client.connect())
    
    async def get_latest_prices(self, assets: List[str]) -> Dict[str, PriceData]:
        """Get latest prices for assets"""
        # Wait briefly if prices not ready
        max_wait = 5
        waited = 0
        while not all(asset in self.latest_prices for asset in assets) and waited < max_wait:
            await asyncio.sleep(0.5)
            waited += 0.5
        
        result = {}
        for asset in assets:
            if asset in self.latest_prices:
                result[asset] = self.latest_prices[asset]
            else:
                # Fallback to default
                result[asset] = PriceData(datetime.utcnow(), asset, 0.5, "default")
        
        return result
    
    def get_market_info(self, asset: str) -> Optional[MarketInfo]:
        """Get market info for asset"""
        return self.markets.get(asset)
    
    async def refresh_markets(self):
        """Refresh market data"""
        if self.market_loader.should_update():
            logger.info("[REFRESH] Updating market information...")
            assets = list(self.markets.keys())
            self.markets = await self.market_loader.fetch_markets(assets)
    
    async def shutdown(self):
        """Shutdown data feed"""
        logger.info("[SHUTDOWN] Shutting down data feed...")
        if self.rtds_client:
            await self.rtds_client.disconnect()
        logger.info("[OK] Data feed shutdown complete")