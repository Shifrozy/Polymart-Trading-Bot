"""
Enhanced Group + Laggard Strategy
Cleaner implementation with better logging
"""

import logging
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SignalResult:
    """Trading signal result"""
    signal: Optional[str]  # "UP", "DOWN", or None
    asset: Optional[str]   # "SOL" or "XRP"
    group_config: Optional[str]  # "G1" or "G2"
    group_assets: Optional[List[str]]
    group_prices: Optional[Dict[str, float]]
    laggard_price: Optional[float]
    reason: str
    
    def __str__(self):
        if self.signal:
            return f"{self.signal} on {self.asset} ({self.group_config}): {self.reason}"
        return self.reason


class EnhancedPolymarketStrategy:
    """
    Enhanced Group + Laggard Strategy
    
    Group G1: BTC + ETH + SOL → Laggard = XRP
    Group G2: BTC + ETH + XRP → Laggard = SOL
    """
    
    def __init__(self, config):
        self.config = config
        self.reference_assets = config["reference_assets"]
        self.tradeable_assets = config["tradeable_assets"]
        
        # Zone thresholds from config
        self.zone_high = (config["zone_high_min"], config["zone_high_max"])
        self.zone_low = (config["zone_low_min"], config["zone_low_max"])
        self.laggard_up = (config["laggard_up_entry_min"], config["laggard_up_entry_max"])
        self.laggard_down = (config["laggard_down_entry_min"], config["laggard_down_entry_max"])
        
        self.exit_up = config["exit_up_threshold"]
        self.exit_down = config["exit_down_threshold"]
        
        logger.info(f"Strategy initialized: High={self.zone_high}, Low={self.zone_low}")
    
    def _in_zone(self, value: float, zone: Tuple[float, float]) -> bool:
        """Check if value is in zone"""
        return zone[0] <= value <= zone[1]
    
    def _all_in_zone(self, prices: Dict[str, float], zone: Tuple[float, float]) -> bool:
        """Check if all prices in zone"""
        return all(self._in_zone(p, zone) for p in prices.values())
    
    def evaluate_signal(self, prices: Dict[str, float]) -> SignalResult:
        """
        Evaluate trading signal using option prices
        
        Args:
            prices: Current option prices for all assets
                   Format: {"BTC": {"UP": 0.45, "DOWN": 0.55}, ...}
        
        Returns:
            SignalResult with signal details
        """
        # Check if we have all required prices
        required = set(self.reference_assets + self.tradeable_assets)
        available = set(prices.keys())
        
        if not required.issubset(available):
            missing = required - available
            return SignalResult(
                None, None, None, None, None, None,
                f"Missing prices: {missing}"
            )
        
        # Extract UP prices for all assets
        up_prices = {}
        for asset in required:
            if isinstance(prices[asset], dict):
                up_prices[asset] = prices[asset].get("UP", 0.5)
            else:
                up_prices[asset] = prices[asset]
        
        # Try Group G1: BTC + ETH + SOL UP → XRP UP laggard
        g1_result = self._evaluate_group(
            up_prices,
            self.reference_assets + [self.tradeable_assets[0]],  # BTC, ETH, SOL
            self.tradeable_assets[1],  # XRP
            "G1"
        )
        
        if g1_result.signal:
            return g1_result
        
        # Try Group G2: BTC + ETH + XRP UP → SOL UP laggard
        g2_result = self._evaluate_group(
            up_prices,
            self.reference_assets + [self.tradeable_assets[1]],  # BTC, ETH, XRP
            self.tradeable_assets[0],  # SOL
            "G2"
        )
        
        if g2_result.signal:
            return g2_result
        
        return SignalResult(
            None, None, None, None, None, None,
            "No valid signal condition"
        )
    
    def _evaluate_group(
        self,
        prices: Dict[str, float],
        group_assets: List[str],
        laggard_asset: str,
        group_name: str
    ) -> SignalResult:
        """Evaluate specific group configuration"""
        
        group_prices = {a: prices[a] for a in group_assets}
        laggard_price = prices[laggard_asset]
        
        # UP Signal: Group HIGH + Laggard LOW
        if self._all_in_zone(group_prices, self.zone_high) and \
           self._in_zone(laggard_price, self.laggard_up):
            
            logger.info(
                f"[{group_name}] UP SIGNAL DETECTED: "
                f"Group {group_assets} in HIGH zone, "
                f"{laggard_asset}={laggard_price:.3f} in LOW zone"
            )
            
            return SignalResult(
                signal="UP",
                asset=laggard_asset,
                group_config=group_name,
                group_assets=group_assets,
                group_prices=group_prices,
                laggard_price=laggard_price,
                reason=f"Group HIGH ({self.zone_high}), Laggard LOW"
            )
        
        # DOWN Signal: Group LOW + Laggard HIGH
        if self._all_in_zone(group_prices, self.zone_low) and \
           self._in_zone(laggard_price, self.laggard_down):
            
            logger.info(
                f"[{group_name}] DOWN SIGNAL DETECTED: "
                f"Group {group_assets} in LOW zone, "
                f"{laggard_asset}={laggard_price:.3f} in HIGH zone"
            )
            
            return SignalResult(
                signal="DOWN",
                asset=laggard_asset,
                group_config=group_name,
                group_assets=group_assets,
                group_prices=group_prices,
                laggard_price=laggard_price,
                reason=f"Group LOW ({self.zone_low}), Laggard HIGH"
            )
        
        return SignalResult(
            None, None, None, None, None, None,
            f"{group_name}: No signal"
        )
    
    def check_exit(self, side: str, current_price: float) -> Tuple[bool, str]:
        """
        Check if position should exit
        
        Args:
            side: "UP" or "DOWN"
            current_price: Current laggard price
        
        Returns:
            (should_exit, reason)
        """
        if side == "UP":
            if current_price >= self.exit_up:
                return True, f"TARGET_HIT (>= {self.exit_up})"
        
        elif side == "DOWN":
            if current_price <= self.exit_down:
                return True, f"TARGET_HIT (<= {self.exit_down})"
        
        return False, "HOLDING"


# Test strategy
if __name__ == "__main__":
    from config import Config
    
    config = Config()
    strategy = EnhancedPolymarketStrategy(config.config)
    
    print("\n" + "="*60)
    print("STRATEGY TEST")
    print("="*60)
    
    # Test UP signal
    test_prices = {
        "BTC": 0.85,
        "ETH": 0.82,
        "SOL": 0.79,
        "XRP": 0.35
    }
    
    print(f"\nTest 1 - Expected: UP signal on XRP")
    print(f"Prices: {test_prices}")
    signal = strategy.evaluate_signal(test_prices)
    print(f"Result: {signal}")
    
    # Test DOWN signal
    test_prices2 = {
        "BTC": 0.15,
        "ETH": 0.18,
        "XRP": 0.12,
        "SOL": 0.75
    }
    
    print(f"\nTest 2 - Expected: DOWN signal on SOL")
    print(f"Prices: {test_prices2}")
    signal2 = strategy.evaluate_signal(test_prices2)
    print(f"Result: {signal2}")
    
    print("\n" + "="*60)