"""
Dynamic Polymarket Market Loader
Fetches 15-minute UP/DOWN markets from Polymarket API
Supports manual configuration of UP/DOWN IDs
"""

import asyncio
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
import time
import json
from pathlib import Path

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
    up_price: float = 0.5  # UP contract price
    down_price: float = 0.5  # DOWN contract price
    up_id: str = ""  # Manual UP market ID
    down_id: str = ""  # Manual DOWN market ID


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
        
        # Check if using manual markets
        if self.config.get("use_manual_markets", False):
            logger.info("[MANUAL] Using manually configured market IDs")
            return self._load_manual_markets(assets)
        
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
                    # Use specific search for 15-minute UP/DOWN markets
                    search_url = f"{self.api_url}/markets"
                    
                    # Build search query for this specific asset
                    # Try multiple search variations
                    search_queries = [
                        f"{asset} 15 MINUTE",           # "BTC 15 MINUTE"
                        f"{asset} 15M",                 # "BTC 15M"
                        f"{asset} UP DOWN 15",          # "BTC UP DOWN 15"
                    ]
                    
                    market_data = None
                    
                    for search_query in search_queries:
                        logger.debug(f"[API] Try: {search_query}")
                        
                        params = {
                            "active": "true",
                            "closed": "false",
                            "q": search_query,
                            "_limit": 100  # Get more results
                        }
                        
                        response = requests.get(search_url, params=params, timeout=15)
                        
                        if response.status_code == 200:
                            data = response.json()
                            logger.info(f"[API] Query '{search_query}' returned {len(data)} results")
                            market_data = self._find_15min_market(data, asset)
                            
                            if market_data:
                                logger.info(f"[OK] ✓ Found {asset} market: {market_data.get('question', '')[:50]}...")
                                markets[asset] = self._parse_market(market_data, asset)
                                break  # Found it, move to next asset
                    
                    if not market_data:
                        logger.warning(f"[API] ✗ No 15-min market found for {asset} after all searches")
                        api_failed = True
                    
                    await asyncio.sleep(self.config["api_request_delay"])
                    
                except requests.exceptions.Timeout:
                    logger.warning(f"[API] Timeout for {asset}")
                    api_failed = True
                except Exception as e:
                    logger.warning(f"[API] Error for {asset}: {e}")
                    api_failed = True
            
            # If API failed for some assets, try backup search
            if api_failed:
                logger.warning("[API] Some markets failed - trying backup search...")
                for asset in assets:
                    if asset not in markets:
                        try:
                            # Backup: search without "15 MINUTE" filter
                            search_url = f"{self.api_url}/markets"
                            params = {
                                "active": "true",
                                "closed": "false",
                                "q": asset,  # Just search for asset name
                                "_limit": 50
                            }
                            response = requests.get(search_url, params=params, timeout=15)
                            
                            if response.status_code == 200:
                                data = response.json()
                                # Find best matching market for this asset
                                for market in data[:5]:  # Check first 5
                                    question = market.get("question", "").upper()
                                    if asset.upper() in question:
                                        logger.info(f"[BACKUP] Using alternative {asset} market")
                                        markets[asset] = self._parse_market(market, asset)
                                        break
                        except Exception as e:
                            logger.debug(f"[BACKUP] Failed for {asset}: {e}")
            
            # If still missing markets, raise error
            if not markets or len(markets) < len(assets):
                missing = [a for a in assets if a not in markets]
                error_msg = f"[API] Failed to fetch markets for: {', '.join(missing)}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            
            self.markets = markets
            self.last_update = time.time()
            return markets
            
        except ImportError:
            logger.error("[ERROR] requests library not installed - cannot fetch markets")
            raise
        except Exception as e:
            logger.error(f"[ERROR] Failed to fetch markets: {e}")
            raise
    
    def _find_15min_market(self, data: List[dict], asset: str) -> Optional[dict]:
        """Find 15-minute market in API response"""
        logger.info(f"[API] Searching {asset} in {len(data)} markets...")
        
        for market in data:
            question = market.get("question", "").upper()
            logger.debug(f"[API]   - {question[:70]}")
            
            # Check if this is a 15-minute market
            if ("15" in question or "15M" in question) and (asset.upper() in question or f"{asset}/" in question):
                if any(x in question for x in ["MINUTE", "MIN", "15M"]):
                    logger.info(f"[API] ✓✓ FOUND 15-min {asset}: {question[:60]}...")
                    return market
        
        logger.warning(f"[API] ✗ No 15-min market found for {asset}")
        
        # Fallback: any market with asset name (but log all options)
        logger.info(f"[API] Trying fallback for {asset}...")
        for market in data:
            question = market.get("question", "").upper()
            if asset.upper() in question or f"{asset}/" in question:
                logger.warning(f"[API] ⚠ FALLBACK {asset}: {question[:60]}...")
                return market
        
        logger.error(f"[API] ✗✗ NO MARKET FOUND for {asset}")
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
    
    def _load_manual_markets(self, assets: List[str]) -> Dict[str, MarketInfo]:
        """Load manually configured market IDs from config"""
        logger.info("[MANUAL] Loading manually configured market IDs...")
        
        manual_markets = self.config.get("manual_markets", {})
        markets = {}
        
        for asset in assets:
            up_key = f"{asset}_UP"
            down_key = f"{asset}_DOWN"
            
            up_id = manual_markets.get(up_key, "")
            down_id = manual_markets.get(down_key, "")
            
            if not up_id or not down_id:
                logger.warning(f"[MANUAL] Missing IDs for {asset} - UP: {bool(up_id)}, DOWN: {bool(down_id)}")
                logger.warning(f"[MANUAL] Please add market IDs in config.py under 'manual_markets'")
                # Fall back to mock
                markets[asset] = self._create_mock_market(asset)
            else:
                logger.info(f"[MANUAL] ✓ {asset}: UP={up_id[:16]}... DOWN={down_id[:16]}...")
                markets[asset] = MarketInfo(
                    asset=asset,
                    market_id=up_id,  # Use UP market ID as primary
                    condition_id=f"manual_{asset.lower()}_condition",
                    yes_token_id=up_id,
                    no_token_id=down_id,
                    yes_price=0.5,
                    no_price=0.5,
                    active=True,
                    end_date="2025-12-31T23:59:59Z",
                    up_id=up_id,
                    down_id=down_id
                )
        
        logger.info("[MANUAL] ✓ Manual markets loaded successfully")
        return markets
    
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
    
    def load_manual_ids(self, manual_config_file: str = "manual_market_ids.json") -> bool:
        """
        Load manually configured UP/DOWN market IDs from JSON file
        
        File format:
        {
            "BTC": {
                "up_id": "0x...",
                "down_id": "0x...",
                "up_price": 0.45,
                "down_price": 0.55
            },
            "ETH": {
                "up_id": "0x...",
                "down_id": "0x...",
                "up_price": 0.50,
                "down_price": 0.50
            }
        }
        """
        config_path = Path(manual_config_file)
        
        if not config_path.exists():
            logger.warning(f"[MANUAL] Config file not found: {manual_config_file}")
            return False
        
        try:
            with open(config_path, 'r') as f:
                manual_config = json.load(f)
            
            logger.info(f"[MANUAL] Loading market IDs from {manual_config_file}")
            
            for asset, ids in manual_config.items():
                if asset in self.markets:
                    market = self.markets[asset]
                    market.up_id = ids.get("up_id", "")
                    market.down_id = ids.get("down_id", "")
                    market.up_price = ids.get("up_price", 0.5)
                    market.down_price = ids.get("down_price", 0.5)
                    
                    logger.info(f"[MANUAL] {asset}: UP={market.up_id[:8]}... DOWN={market.down_id[:8]}...")
                else:
                    logger.warning(f"[MANUAL] Asset {asset} not found in markets")
            
            logger.info("[MANUAL] ✓ Manual market IDs loaded successfully")
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"[MANUAL] Invalid JSON in {manual_config_file}: {e}")
            return False
        except Exception as e:
            logger.error(f"[MANUAL] Error loading manual IDs: {e}")
            return False
    
    def set_manual_ids(self, asset: str, up_id: str, down_id: str, up_price: float = 0.5, down_price: float = 0.5):
        """
        Manually set UP/DOWN IDs for a specific asset
        
        Args:
            asset: Asset name (e.g., 'BTC', 'ETH')
            up_id: Market ID for UP contract
            down_id: Market ID for DOWN contract
            up_price: Current UP contract price (0.0-1.0)
            down_price: Current DOWN contract price (0.0-1.0)
        """
        if asset not in self.markets:
            logger.warning(f"[MANUAL] Asset {asset} not found in markets")
            return False
        
        market = self.markets[asset]
        market.up_id = up_id
        market.down_id = down_id
        market.up_price = up_price
        market.down_price = down_price
        
        logger.info(f"[MANUAL] Set {asset}: UP={up_id[:8]}... DOWN={down_id[:8]}...")
        return True
    
    def save_manual_ids(self, output_file: str = "manual_market_ids.json"):
        """
        Save current market IDs to a JSON file for future use
        
        Args:
            output_file: Path to save the configuration
        """
        manual_config = {}
        
        for asset, market in self.markets.items():
            if market.up_id and market.down_id:
                manual_config[asset] = {
                    "up_id": market.up_id,
                    "down_id": market.down_id,
                    "up_price": market.up_price,
                    "down_price": market.down_price
                }
        
        try:
            with open(output_file, 'w') as f:
                json.dump(manual_config, f, indent=2)
            logger.info(f"[MANUAL] ✓ Market IDs saved to {output_file}")
            return True
        except Exception as e:
            logger.error(f"[MANUAL] Error saving manual IDs: {e}")
            return False
    
    def get_manual_ids(self, asset: str) -> Optional[Dict]:
        """
        Get manually configured IDs for an asset
        
        Returns:
            Dict with up_id, down_id, up_price, down_price or None
        """
        if asset not in self.markets:
            return None
        
        market = self.markets[asset]
        
        if market.up_id and market.down_id:
            return {
                "up_id": market.up_id,
                "down_id": market.down_id,
                "up_price": market.up_price,
                "down_price": market.down_price
            }
        
        return None