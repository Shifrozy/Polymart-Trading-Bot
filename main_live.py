"""
Live trading script - Paper trading mode
"""

import asyncio
import argparse
import logging
from config import Config
from trader import LiveTrader
from logger import setup_logging


async def main():
    parser = argparse.ArgumentParser(description='Polymarket Live Trading Bot')
    parser.add_argument('--paper-trade', action='store_true', help='Run in paper trading mode')
    args = parser.parse_args()
    
    # Initialize config
    config = Config()
    setup_logging(config.config)
    
    logger = logging.getLogger(__name__)
    logger.info("="*60)
    logger.info("POLYMARKET TRADING BOT - STARTING")
    logger.info(f"Mode: {'PAPER TRADING' if args.paper_trade else 'LIVE TRADING'}")
    logger.info("="*60)
    
    # TEMPORARY: Mock market IDs for testing
    market_ids = {
        "BTC": "235",
        "ETH": "785268",
        "SOL": "785267",
        "XRP": "785266"
    }
    
    logger.warning("[WARNING] Using MOCK market IDs - Replace with real Polymarket IDs!")
    
    try:
        trader = LiveTrader(config.config, paper_trade=args.paper_trade)
        
        logger.info("Initializing trader...")
        await trader.initialize(market_ids)
        
        logger.info("[OK] Trader initialized successfully")
        logger.info("[INFO] Monitoring markets: BTC, ETH, SOL, XRP")
        logger.info("[INFO] Tradeable assets: SOL, XRP")
        logger.info(f"[INFO] Stake size: ${config.config['stake_size']}")
        logger.info("")
        logger.info("Press Ctrl+C to stop...")
        logger.info("")
        
        logger.info("[TEST MODE] Running with MOCK data stream")
        logger.info("To enable real trading, add actual Polymarket market IDs")
        logger.info("")
        
        # Start the trader
        await trader.run()
        
    except KeyboardInterrupt:
        logger.info("\n[STOP] Shutting down gracefully...")
        await trader.shutdown()
        logger.info("[OK] Shutdown complete")
    except Exception as e:
        logger.error(f"[ERROR] {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())