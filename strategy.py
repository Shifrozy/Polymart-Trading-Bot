"""
Core trading strategy: Group + Laggard logic
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
    group_prices: Optional[Dict[str, float]]
    laggard_price: Optional[float]
    reason: str


class PolymarketStrategy:
    """
    Group + Laggard trading strategy
    
    Group G1: BTC, ETH, SOL → Laggard = XRP
    Group G2: BTC, ETH, XRP → Laggard = SOL
    """
    
    def __init__(self, config):
        self.config = config
        self.reference_assets = config["reference_assets"]  # ["BTC", "ETH"]
        self.tradeable_assets = config["tradeable_assets"]  # ["SOL", "XRP"]
        
        # Thresholds
        self.band_high = config["band_high_group"]
        self.band_low = config["band_low_group"]
        self.laggard_low = config["laggard_low_zone"]
        self.laggard_high = config["laggard_high_zone"]
    
    def _in_range(self, value: float, range_tuple: List[float]) -> bool:
        """Check if value is within range [min, max]"""
        return range_tuple[0] <= value <= range_tuple[1]
    
    def _all_in_range(self, prices: Dict[str, float], range_tuple: List[float]) -> bool:
        """Check if all prices are within range"""
        return all(self._in_range(p, range_tuple) for p in prices.values())
    
    def evaluate_signal(self, prices: Dict[str, float]) -> SignalResult:
        """
        Evaluate entry signal based on current prices
        
        Args:
            prices: Dict of {"BTC": 0.8, "ETH": 0.75, "SOL": 0.4, "XRP": 0.9}
        
        Returns:
            SignalResult with signal type and details
        """
        
        # Try Group G1: BTC, ETH, SOL → Laggard = XRP
        g1_assets = self.reference_assets + [self.tradeable_assets[0]]  # BTC, ETH, SOL
        g1_laggard = self.tradeable_assets[1]  # XRP
        
        g1_result = self._evaluate_group(
            prices, 
            g1_assets, 
            g1_laggard, 
            "G1"
        )
        
        if g1_result.signal:
            return g1_result
        
        # Try Group G2: BTC, ETH, XRP → Laggard = SOL
        g2_assets = self.reference_assets + [self.tradeable_assets[1]]  # BTC, ETH, XRP
        g2_laggard = self.tradeable_assets[0]  # SOL
        
        g2_result = self._evaluate_group(
            prices,
            g2_assets,
            g2_laggard,
            "G2"
        )
        
        if g2_result.signal:
            return g2_result
        
        return SignalResult(
            signal=None,
            asset=None,
            group_config=None,
            group_prices=None,
            laggard_price=None,
            reason="No signal condition met"
        )
    
    def _evaluate_group(
        self, 
        prices: Dict[str, float], 
        group_assets: List[str], 
        laggard_asset: str,
        group_name: str
    ) -> SignalResult:
        """Evaluate a specific group configuration"""
        
        # Extract prices
        group_prices = {asset: prices.get(asset) for asset in group_assets}
        laggard_price = prices.get(laggard_asset)
        
        # Check if all prices available
        if None in group_prices.values() or laggard_price is None:
            return SignalResult(
                signal=None,
                asset=None,
                group_config=None,
                group_prices=None,
                laggard_price=None,
                reason=f"{group_name}: Missing price data"
            )
        
        # UP Signal: Group in [0.75, 1.00] AND Laggard in [0.00, 0.50]
        if self._all_in_range(group_prices, self.band_high) and \
           self._in_range(laggard_price, self.laggard_low):
            
            logger.info(f"{group_name} UP signal: Group={group_prices}, Laggard {laggard_asset}={laggard_price}")
            return SignalResult(
                signal="UP",
                asset=laggard_asset,
                group_config=group_name,
                group_prices=group_prices,
                laggard_price=laggard_price,
                reason=f"{group_name}: Group high, laggard low"
            )
        
        # DOWN Signal: Group in [0.00, 0.25] AND Laggard in [0.50, 1.00]
        if self._all_in_range(group_prices, self.band_low) and \
           self._in_range(laggard_price, self.laggard_high):
            
            logger.info(f"{group_name} DOWN signal: Group={group_prices}, Laggard {laggard_asset}={laggard_price}")
            return SignalResult(
                signal="DOWN",
                asset=laggard_asset,
                group_config=group_name,
                group_prices=group_prices,
                laggard_price=laggard_price,
                reason=f"{group_name}: Group low, laggard high"
            )
        
        return SignalResult(
            signal=None,
            asset=None,
            group_config=None,
            group_prices=None,
            laggard_price=None,
            reason=f"{group_name}: Conditions not met"
        )
    
    def check_exit(self, signal_type: str, current_price: float) -> Tuple[bool, str]:
        """
        Check if position should be exited
        
        Args:
            signal_type: "UP" or "DOWN"
            current_price: Current laggard price
        
        Returns:
            (should_exit, reason)
        """
        if signal_type == "UP":
            if current_price >= self.config["exit_up_threshold"]:
                return True, f"TARGET_REACHED (>= {self.config['exit_up_threshold']})"
        
        elif signal_type == "DOWN":
            if current_price <= self.config["exit_down_threshold"]:
                return True, f"TARGET_REACHED (<= {self.config['exit_down_threshold']})"
        
        return False, "HOLDING"


# Test the strategy
if __name__ == "__main__":
    from config import Config
    
    config = Config()
    strategy = PolymarketStrategy(config.config)
    
    print("Testing PolymarketStrategy:")
    print("=" * 50)
    
    # Test case 1: UP signal
    prices = {
        "BTC": 0.85,
        "ETH": 0.80,
        "SOL": 0.78,
        "XRP": 0.35
    }
    
    print("\nTest 1 - UP Signal Expected:")
    print(f"Prices: {prices}")
    signal = strategy.evaluate_signal(prices)
    print(f"Signal: {signal.signal}")
    print(f"Asset: {signal.asset}")
    print(f"Group: {signal.group_config}")
    print(f"Reason: {signal.reason}")
    
    # Test case 2: DOWN signal
    prices2 = {
        "BTC": 0.15,
        "ETH": 0.20,
        "SOL": 0.18,
        "XRP": 0.75
    }
    
    print("\n\nTest 2 - DOWN Signal Expected:")
    print(f"Prices: {prices2}")
    signal2 = strategy.evaluate_signal(prices2)
    print(f"Signal: {signal2.signal}")
    print(f"Asset: {signal2.asset}")
    print(f"Group: {signal2.group_config}")
    print(f"Reason: {signal2.reason}")
    
    # Test case 3: No signal
    prices3 = {
        "BTC": 0.50,
        "ETH": 0.55,
        "SOL": 0.52,
        "XRP": 0.48
    }
    
    print("\n\nTest 3 - No Signal Expected:")
    print(f"Prices: {prices3}")
    signal3 = strategy.evaluate_signal(prices3)
    print(f"Signal: {signal3.signal}")
    print(f"Reason: {signal3.reason}")
    
    print("\n" + "=" * 50)