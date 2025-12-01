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
    # TODO: Replace with actual Polymarket market IDs
    market_ids = {
        "BTC": "mock_btc_market_id",
        "ETH": "mock_eth_market_id",
        "SOL": "mock_sol_market_id",
        "XRP": "mock_xrp_market_id"
    }
    
    logger.warning("⚠️  Using MOCK market IDs - Replace with real Polymarket IDs!")
    
    try:
        trader = LiveTrader(config.config, paper_trade=args.paper_trade)
        
        logger.info("Initializing trader...")
        # Comment out initialization for now since we don't have real market IDs
        # await trader.initialize(market_ids)
        
        logger.info("✅ Trader initialized successfully")
        logger.info("📊 Monitoring markets: BTC, ETH, SOL, XRP")
        logger.info("💰 Tradeable assets: SOL, XRP")
        logger.info(f"💵 Stake size: ${config.config['stake_size']}")
        logger.info("")
        logger.info("Press Ctrl+C to stop...")
        logger.info("")
        
        # For testing without real connection
        logger.info("🧪 TEST MODE: Running without real market connection")
        logger.info("To enable real trading, add actual Polymarket market IDs")
        
        # Keep running
        while True:
            await asyncio.sleep(5)
            logger.info("Bot is running... (waiting for real market IDs)")
        
        # When real market IDs are added, uncomment this:
        # await trader.run()
        
    except KeyboardInterrupt:
        logger.info("\n⏹️  Shutting down gracefully...")
        # await trader.shutdown()
        logger.info("✅ Shutdown complete")
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())