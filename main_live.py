"""
Main script for live/paper trading
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

from config import Config
from trader import EnhancedLiveTrader
from logger import setup_logging


async def main():
    """Main entry point for live trading"""
    
    parser = argparse.ArgumentParser(
        description='Polymarket 15-Minute Trading Bot',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main_live.py --paper-trade
  python main_live.py --config custom_config.json --paper-trade
  python main_live.py --live  # Real trading (requires setup)
        """
    )
    
    parser.add_argument(
        '--paper-trade',
        action='store_true',
        help='Run in paper trading mode (simulated, no real money)'
    )
    
    parser.add_argument(
        '--live',
        action='store_true',
        help='Run in LIVE trading mode (REAL MONEY - use with caution)'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='config.json',
        help='Path to configuration file'
    )
    
    args = parser.parse_args()
    
    # Validate mode
    if not args.paper_trade and not args.live:
        parser.error("Must specify either --paper-trade or --live")
    
    if args.live and args.paper_trade:
        parser.error("Cannot specify both --paper-trade and --live")
    
    # Load configuration
    if Path(args.config).exists():
        config = Config(config_file=args.config)
        print(f"[CONFIG] Loaded from {args.config}")
    else:
        config = Config()
        print(f"[CONFIG] Using default configuration")
        if args.config != 'config.json':
            print(f"[WARNING] Config file not found: {args.config}")
    
    # Setup logging
    setup_logging(config.config)
    logger = logging.getLogger(__name__)
    
    # Display header
    print("\n" + "="*60)
    print("POLYMARKET 15-MINUTE TRADING BOT")
    print("="*60)
    print(f"Mode: {'PAPER TRADING (Simulated)' if args.paper_trade else 'LIVE TRADING (REAL MONEY)'}")
    print(f"Version: 2.0 Enhanced")
    print("="*60)
    
    # Safety check for live trading
    if args.live:
        print("\n" + "!"*60)
        print("WARNING: LIVE TRADING MODE")
        print("!"*60)
        print("This will execute REAL trades with REAL money!")
        print("")
        print("REQUIREMENTS FOR LIVE TRADING:")
        print("  1. ✓ Configure your wallet (private key setup)")
        print("  2. ✓ Fund your account on Polymarket")
        print("  3. ✓ Implement order execution in _execute_order()")
        print("  4. ✓ Test thoroughly in PAPER MODE first")
        print("  5. ✓ Understand the RISKS")
        print("")
        print("STATUS: Order execution NOT yet implemented!")
        print("  → Currently: _execute_order() is a stub function")
        print("  → Need: CLOB API implementation + wallet integration")
        print("")
        
        response = input("Type 'I UNDERSTAND THE RISKS' to continue: ")
        if response != "I UNDERSTAND THE RISKS":
            print("[ABORTED] Live trading cancelled")
            return
        
        print("\nProceeding with live trading...")
        print("[WARNING] Orders will NOT actually execute until _execute_order() is implemented")
        print("")
    
    print("")
    
    # Initialize trader
    trader = EnhancedLiveTrader(config.config, paper_trade=args.paper_trade)
    
    try:
        # Initialize
        await trader.initialize()
        
        # Run trading loop
        await trader.run()
        
    except KeyboardInterrupt:
        logger.info("\n[INTERRUPT] Received shutdown signal")
        
    except Exception as e:
        logger.error(f"\n[ERROR] Fatal error: {e}", exc_info=True)
        
    finally:
        # Graceful shutdown
        await trader.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[STOPPED] Bot stopped by user")
        sys.exit(0)