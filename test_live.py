#!/usr/bin/env python3
"""Quick test of live trading with manual markets"""

import asyncio
import sys
from config import DEFAULT_CONFIG
from trader import EnhancedLiveTrader
from strategy import EnhancedPolymarketStrategy

async def main():
    print("Testing Live Trading with Manual Markets...")
    print(f"use_manual_markets: {DEFAULT_CONFIG.get('use_manual_markets')}")
    print(f"BTC_UP: {DEFAULT_CONFIG['manual_markets'].get('BTC_UP')}")
    
    try:
        trader = EnhancedLiveTrader(
            config=DEFAULT_CONFIG,
            paper_trade=True
        )
        
        print("\n[INIT] Initializing trader...")
        await trader.initialize()
        
        print("\n[OK] Trader initialized successfully!")
        print(f"Markets loaded: {list(trader.data_feed.markets.keys())}")
        
        # Get one price update
        print("\n[STREAM] Waiting for initial prices...")
        await asyncio.sleep(2)
        
        print("\n[OK] Live trading ready!")
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
