"""
Real-time and historical data feed manager for Polymarket
Supports both REST API and RTDS WebSocket
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable

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
    """REST API client for historical data and fallback"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        try:
            import aiohttp
            self.session = aiohttp.ClientSession()
        except ImportError:
            logger.warning("aiohttp not installed - REST client disabled")
            self.session = None
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_market_prices(self, market_ids: List[str]) -> Dict[str, float]:
        """Fetch current prices for given market IDs"""
        if not self.session:
            logger.warning("No session available - returning mock prices")
            return {mid: 0.5 for mid in market_ids}
        
        try:
            prices = {}
            for market_id in market_ids:
                url = f"{self.base_url}/markets/{market_id}"
                async with self.session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        prices[market_id] = float(data.get('price', 0.5))
                    else:
                        logger.warning(f"Failed to fetch {market_id}: {response.status}")
                        prices[market_id] = 0.5
            return prices
        except Exception as e:
            logger.error(f"REST API error: {e}")
            return {mid: 0.5 for mid in market_ids}
    
    async def get_historical_data(self, market_id: str, start_date: str, end_date: str):
        """Fetch historical price data"""
        if not self.session:
            return []
        
        url = f"{self.base_url}/markets/{market_id}/history"
        params = {"start": start_date, "end": end_date}
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                return []
        except Exception as e:
            logger.error(f"Historical data error: {e}")
            return []


class PolymarketRTDSClient:
    """Real-time data stream WebSocket client with auto-reconnect"""
    
    def __init__(self, ws_url: str, market_ids: Dict[str, str], reconnect_delay: int = 5):
        self.ws_url = ws_url
        self.market_ids = market_ids  # {"BTC": "market_id_123", ...}
        self.reconnect_delay = reconnect_delay
        self.ws = None
        self.running = False
        self.callbacks: List[Callable] = []
        self.websockets_available = False
        
        try:
            import websockets
            self.websockets_available = True
        except ImportError:
            logger.warning("websockets not installed - RTDS disabled")
    
    def subscribe(self, callback: Callable):
        """Register callback for price updates"""
        self.callbacks.append(callback)
    
    async def connect(self):
        """Connect to WebSocket with auto-reconnect"""
        if not self.websockets_available:
            logger.warning("WebSocket not available - running in mock mode")
            await self._mock_price_stream()
            return
        
        import websockets
        self.running = True
        
        while self.running:
            try:
                async with websockets.connect(self.ws_url) as ws:
                    self.ws = ws
                    logger.info("RTDS WebSocket connected")
                    
                    # Subscribe to markets
                    subscribe_msg = {
                        "type": "subscribe",
                        "markets": list(self.market_ids.values())
                    }
                    await ws.send(json.dumps(subscribe_msg))
                    
                    # Listen for updates
                    async for message in ws:
                        await self._handle_message(message)
                        
            except websockets.exceptions.ConnectionClosed:
                logger.warning(f"WebSocket disconnected, reconnecting in {self.reconnect_delay}s")
                await asyncio.sleep(self.reconnect_delay)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                await asyncio.sleep(self.reconnect_delay)
    
    async def _mock_price_stream(self):
        """Generate mock price updates for testing"""
        import random
        logger.info("🧪 Starting mock price stream")
        
        prices = {asset: 0.5 for asset in self.market_ids.keys()}
        
        while self.running:
            for asset in self.market_ids.keys():
                # Random walk
                change = random.uniform(-0.05, 0.05)
                prices[asset] = max(0.0, min(1.0, prices[asset] + change))
                
                price_data = PriceData(datetime.utcnow(), asset, prices[asset])
                
                for callback in self.callbacks:
                    await callback(price_data)
            
            await asyncio.sleep(2)  # Update every 2 seconds
    
    async def _handle_message(self, message: str):
        """Parse and distribute price updates"""
        try:
            data = json.loads(message)
            
            if data.get("type") == "price_update":
                market_id = data.get("market_id")
                price = float(data.get("price", 0.5))
                timestamp = datetime.fromisoformat(data.get("timestamp", datetime.utcnow().isoformat()))
                
                # Find asset name from market_id
                asset = None
                for asset_name, mid in self.market_ids.items():
                    if mid == market_id:
                        asset = asset_name
                        break
                
                if asset:
                    price_data = PriceData(timestamp, asset, price)
                    
                    # Notify all callbacks
                    for callback in self.callbacks:
                        await callback(price_data)
                        
        except Exception as e:
            logger.error(f"Message parsing error: {e}")
    
    async def disconnect(self):
        """Gracefully disconnect"""
        self.running = False
        if self.ws:
            await self.ws.close()


class DataFeedManager:
    """Manages both REST and RTDS feeds with automatic fallback"""
    
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
        
        logger.info("✅ Data feed manager initialized")
    
    async def _on_price_update(self, price_data: PriceData):
        """Handle incoming price updates from RTDS"""
        self.latest_prices[price_data.asset] = price_data
        self.use_rtds = True  # RTDS is working
        logger.debug(f"Price update: {price_data.asset} = {price_data.price:.4f}")
    
    async def start_rtds(self):
        """Start RTDS connection in background"""
        logger.info("Starting RTDS connection...")
        asyncio.create_task(self.rtds_client.connect())
    
    async def get_latest_prices(self, assets: List[str]) -> Dict[str, PriceData]:
        """Get latest prices, fallback to REST if RTDS fails"""
        if self.use_rtds and all(asset in self.latest_prices for asset in assets):
            return {asset: self.latest_prices[asset] for asset in assets}
        
        # Fallback to REST
        logger.debug("Using REST API for prices")
        market_ids = [self.rtds_client.market_ids.get(asset) for asset in assets if asset in self.rtds_client.market_ids]
        prices = await self.rest_client.get_market_prices(market_ids)
        
        result = {}
        for asset in assets:
            market_id = self.rtds_client.market_ids.get(asset)
            if market_id and market_id in prices:
                result[asset] = PriceData(datetime.utcnow(), asset, prices[market_id])
        
        return result
    
    async def shutdown(self):
        """Clean shutdown"""
        logger.info("Shutting down data feed manager...")
        await self.rtds_client.disconnect()
        await self.rest_client.__aexit__(None, None, None)
        logger.info("✅ Data feed shutdown complete")