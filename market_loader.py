"""
Dynamic Polymarket Market Loader
Fetches 15-minute UP/DOWN markets from Polymarket API
"""

import asyncio
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
import time

logger = logging.getLogger(__name__)


@dataclass
class MarketInfo:
    """Market information"""
    asset: str
    market_id: str
    condition_id: str
    yes_token_id: str  # UP outcome
    no_token_id: str   # DOWN outcome
    yes_price: float
    no_price: float
    active: bool
    end_date: str


class PolymarketLoader:
    """Load 15-minute markets from Polymarket API"""
    
    def __init__(self, config):
        self.config = config
        self.api_url = config["polymarket_api_url"]
        self.clob_url = config["polymarket_clob_url"]
        self.markets: Dict[str, MarketInfo] = {}
        self.last_update = 0
        self.update_interval = 300  # Update every 5 minutes
    
    async def fetch_markets(self, assets: List[str]) -> Dict[str, MarketInfo]:
        """
        Fetch 15-minute markets for given assets
        
        Args:
            assets: List of asset symbols (e.g., ["BTC", "ETH", "SOL", "XRP"])
        
        Returns:
            Dictionary of {asset: MarketInfo}
        """
        logger.info(f"Fetching 15-minute markets for: {', '.join(assets)}")
        
        try:
            # Try to import requests for API calls
            import requests
            
            markets = {}
            
            for asset in assets:
                # Search for 15-minute markets
                search_url = f"{self.api_url}/markets"
                params = {
                    "active": "true",
                    "closed": "false",
                    "_limit": 10
                }
                
                response = requests.get(search_url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Find 15-min market for this asset
                    market_data = self._find_15min_market(data, asset)
                    
                    if market_data:
                        markets[asset] = self._parse_market(market_data, asset)
                        logger.info(f"[OK] Found {asset} 15-min market: {markets[asset].market_id}")
                    else:
                        logger.warning(f"[WARNING] No 15-min market found for {asset}")
                        # Create mock market for testing
                        markets[asset] = self._create_mock_market(asset)
                else:
                    logger.error(f"API error for {asset}: {response.status_code}")
                    markets[asset] = self._create_mock_market(asset)
                
                # Rate limiting
                await asyncio.sleep(self.config["api_request_delay"])
            
            self.markets = markets
            self.last_update = time.time()
            
            return markets
            
        except ImportError:
            logger.warning("requests library not installed, using mock markets")
            return self._create_all_mock_markets(assets)
        except Exception as e:
            logger.error(f"Error fetching markets: {e}")
            return self._create_all_mock_markets(assets)
    
    def _find_15min_market(self, data: List[dict], asset: str) -> Optional[dict]:
        """Find 15-minute market in API response"""
        for market in data:
            question = market.get("question", "").upper()
            
            # Look for 15-minute markets
            if "15" in question and asset.upper() in question:
                if "MINUTE" in question or "MIN" in question:
                    return market
        
        return None
    
    def _parse_market(self, market_data: dict, asset: str) -> MarketInfo:
        """Parse market data from API response"""
        return MarketInfo(
            asset=asset,
            market_id=market_data.get("id", f"mock_{asset}_market"),
            condition_id=market_data.get("conditionId", f"mock_{asset}_condition"),
            yes_token_id=market_data.get("tokens", [{}])[0].get("token_id", f"mock_{asset}_yes"),
            no_token_id=market_data.get("tokens", [{}])[1].get("token_id", f"mock_{asset}_no") if len(market_data.get("tokens", [])) > 1 else f"mock_{asset}_no",
            yes_price=0.5,
            no_price=0.5,
            active=market_data.get("active", True),
            end_date=market_data.get("endDate", "")
        )
    
    def _create_mock_market(self, asset: str) -> MarketInfo:
        """Create mock market for testing"""
        return MarketInfo(
            asset=asset,
            market_id=f"mock_{asset.lower()}_15min",
            condition_id=f"mock_condition_{asset.lower()}",
            yes_token_id=f"mock_{asset.lower()}_yes_token",
            no_token_id=f"mock_{asset.lower()}_no_token",
            yes_price=0.5,
            no_price=0.5,
            active=True,
            end_date="2025-12-31T23:59:59Z"
        )
    
    def _create_all_mock_markets(self, assets: List[str]) -> Dict[str, MarketInfo]:
        """Create mock markets for all assets"""
        logger.info("[MOCK] Creating mock markets for testing")
        return {asset: self._create_mock_market(asset) for asset in assets}
    
    async def update_prices(self):
        """Update current market prices from CLOB API"""
        try:
            import requests
            
            for asset, market in self.markets.items():
                url = f"{self.clob_url}/price"
                params = {"token_id": market.yes_token_id}
                
                response = requests.get(url, params=params, timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    market.yes_price = float(data.get("price", 0.5))
                    market.no_price = 1.0 - market.yes_price
                
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.debug(f"Price update error: {e}")
    
    def get_market_ids(self) -> Dict[str, str]:
        """Get market IDs for WebSocket subscription"""
        return {asset: market.market_id for asset, market in self.markets.items()}
    
    def should_update(self) -> bool:
        """Check if markets should be refreshed"""
        return (time.time() - self.last_update) > self.update_interval


# Test the loader
if __name__ == "__main__":
    async def test():
        from config import Config
        config = Config()
        
        loader = PolymarketLoader(config.config)
        markets = await loader.fetch_markets(["BTC", "ETH", "SOL", "XRP"])
        
        print("\n" + "="*60)
        print("POLYMARKET 15-MINUTE MARKETS")
        print("="*60)
        
        for asset, market in markets.items():
            print(f"\n{asset}:")
            print(f"  Market ID: {market.market_id}")
            print(f"  YES Token (UP): {market.yes_token_id}")
            print(f"  NO Token (DOWN): {market.no_token_id}")
            print(f"  Active: {market.active}")
        
        print("\n" + "="*60)
    
    asyncio.run(test())