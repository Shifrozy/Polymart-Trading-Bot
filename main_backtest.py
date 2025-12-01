"""
Backtesting script
"""

import argparse
import logging
import os
from config import Config
from backtester import Backtester
from logger import setup_logging


def main():
    parser = argparse.ArgumentParser(description='Polymarket Strategy Backtester')
    parser.add_argument('--start-date', required=True, help='Start date YYYY-MM-DD')
    parser.add_argument('--end-date', required=True, help='End date YYYY-MM-DD')
    parser.add_argument('--data-file', default='data/historical_prices.csv', help='Historical data CSV')
    args = parser.parse_args()
    
    # Initialize config
    config = Config()
    setup_logging(config.config)
    
    logger = logging.getLogger(__name__)
    
    logger.info("="*60)
    logger.info("POLYMARKET BACKTESTING ENGINE")
    logger.info("="*60)
    logger.info(f"Start Date: {args.start_date}")
    logger.info(f"End Date:   {args.end_date}")
    logger.info(f"Data File:  {args.data_file}")
    logger.info("="*60)
    
    # Check if data file exists
    if not os.path.exists(args.data_file):
        logger.error(f"❌ Data file not found: {args.data_file}")
        logger.info("")
        logger.info("📝 To generate sample data, run:")
        logger.info("   python sample_data.py")
        logger.info("")
        return
    
    try:
        # Initialize backtester
        backtester = Backtester(config.config)
        
        # Load data
        logger.info("📊 Loading historical data...")
        data = backtester.load_historical_data(args.data_file)
        logger.info(f"✅ Loaded {len(data)} price records")
        
        # Run backtest
        logger.info("")
        logger.info("🚀 Starting backtest...")
        logger.info("")
        
        backtester.run(data, args.start_date, args.end_date)
        
        logger.info("")
        logger.info("✅ Backtest complete!")
        
    except Exception as e:
        logger.error(f"❌ Backtest failed: {e}", exc_info=True)


if __name__ == "__main__":
    main()