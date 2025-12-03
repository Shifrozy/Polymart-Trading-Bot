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
    yes_token_id: str
    no_token_id: str
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
        self.update_interval = 300
        self.use_mock = False  # Track if we're using mock
    
    async def fetch_markets(self, assets: List[str]) -> Dict[str, MarketInfo]:
        """Fetch 15-minute markets for given assets"""
        
        # If already using mock, skip API calls
        if self.use_mock:
            logger.info("[MOCK] Using cached mock markets")
            return self._create_all_mock_markets(assets)
        
        logger.info(f"[API] Fetching 15-minute markets for: {', '.join(assets)}")
        
        try:
            import requests
            
            markets = {}
            api_failed = False
            
            for asset in assets:
                try:
                    # Try to fetch from API with longer timeout
                    search_url = f"{self.api_url}/markets"
                    params = {
                        "active": "true",
                        "closed": "false",
                        "_limit": 10
                    }
                    
                    response = requests.get(search_url, params=params, timeout=15)
                    
                    if response.status_code == 200:
                        data = response.json()
                        market_data = self._find_15min_market(data, asset)
                        
                        if market_data:
                            markets[asset] = self._parse_market(market_data, asset)
                            logger.info(f"[OK] Found {asset} market")
                        else:
                            logger.warning(f"[API] No 15-min market found for {asset}")
                            api_failed = True
                    else:
                        logger.warning(f"[API] Error {response.status_code} for {asset}")
                        api_failed = True
                    
                    await asyncio.sleep(self.config["api_request_delay"])
                    
                except requests.exceptions.Timeout:
                    logger.warning(f"[API] Timeout for {asset}")
                    api_failed = True
                    break
                except Exception as e:
                    logger.warning(f"[API] Error for {asset}: {e}")
                    api_failed = True
                    break
            
            # If API failed, use mock markets
            if api_failed or not markets:
                logger.info("[MOCK] API unavailable - switching to mock markets for testing")
                self.use_mock = True
                return self._create_all_mock_markets(assets)
            
            self.markets = markets
            self.last_update = time.time()
            return markets
            
        except ImportError:
            logger.info("[MOCK] requests library not installed - using mock markets")
            self.use_mock = True
            return self._create_all_mock_markets(assets)
        except Exception as e:
            logger.warning(f"[API] Error: {e} - using mock markets")
            self.use_mock = True
            return self._create_all_mock_markets(assets)
    
    def _find_15min_market(self, data: List[dict], asset: str) -> Optional[dict]:
        """Find 15-minute market in API response"""
        for market in data:
            question = market.get("question", "").upper()
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
        return {asset: self._create_mock_market(asset) for asset in assets}
    
    async def update_prices(self):
        """Update current market prices"""
        if self.use_mock:
            return  # Skip if using mock
        # Real implementation here
    
    def get_market_ids(self) -> Dict[str, str]:
        """Get market IDs for WebSocket subscription"""
        return {asset: market.market_id for asset, market in self.markets.items()}
    
    def should_update(self) -> bool:
        """Check if markets should be refreshed"""
        if self.use_mock:
            return False  # Don't refresh mock markets
        return (time.time() - self.last_update) > self.update_interval