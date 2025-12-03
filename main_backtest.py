"""
Main script for backtesting
"""

import argparse
import logging
import sys
from pathlib import Path

from config import Config
from backtester import EnhancedBacktester
from logger import setup_logging
from sample_data import generate_sample_data


def main():
    """Main entry point for backtesting"""
    
    parser = argparse.ArgumentParser(
        description='Polymarket Trading Bot - Backtesting Engine',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main_backtest.py --start 2024-09-01 --end 2024-12-31
  python main_backtest.py --start 2024-09-01 --end 2024-12-31 --config custom_config.json
  python main_backtest.py --generate-data  # Generate sample data first
        """
    )
    
    parser.add_argument(
        '--start',
        type=str,
        required='--generate-data' not in sys.argv,
        help='Backtest start date (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--end',
        type=str,
        required='--generate-data' not in sys.argv,
        help='Backtest end date (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--data-file',
        type=str,
        default='data/historical_prices.csv',
        help='Path to historical data CSV'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='config.json',
        help='Path to configuration file'
    )
    
    parser.add_argument(
        '--generate-data',
        action='store_true',
        help='Generate sample data for testing'
    )
    
    args = parser.parse_args()
    
    # Generate sample data if requested
    if args.generate_data:
        print("\n[GENERATE] Creating sample historical data...")
        start = input("Start date (YYYY-MM-DD) [2024-09-01]: ") or "2024-09-01"
        end = input("End date (YYYY-MM-DD) [2024-12-31]: ") or "2024-12-31"
        
        output_file = generate_sample_data(start, end)
        print(f"\n[OK] Sample data generated: {output_file}")
        print("You can now run backtest with:")
        print(f"  python main_backtest.py --start {start} --end {end}")
        return
    
    # Load configuration
    if Path(args.config).exists():
        config = Config(config_file=args.config)
        print(f"[CONFIG] Loaded from {args.config}")
    else:
        config = Config()
        print(f"[CONFIG] Using default configuration")
    
    # Setup logging
    setup_logging(config.config)
    logger = logging.getLogger(__name__)
    
    # Check if data file exists
    if not Path(args.data_file).exists():
        print(f"\n[ERROR] Data file not found: {args.data_file}")
        print("\nTo generate sample data, run:")
        print("  python main_backtest.py --generate-data")
        print("\nOr specify a different data file with --data-file")
        return
    
    print("\n" + "="*60)
    print("POLYMARKET TRADING BOT - BACKTESTING")
    print("="*60)
    print(f"Data file:    {args.data_file}")
    print(f"Date range:   {args.start} to {args.end}")
    print(f"Strategy:     Group + Laggard (Enhanced)")
    print("="*60)
    print("")
    
    try:
        # Initialize backtester
        backtester = EnhancedBacktester(config.config)
        
        # Load historical data
        data = backtester.load_historical_data(args.data_file)
        
        # Run backtest
        backtester.run(data, args.start, args.end)
        
        print("\n[OK] Backtest completed successfully")
        
    except FileNotFoundError as e:
        logger.error(f"[ERROR] File not found: {e}")
        print("\nMake sure the data file exists or generate sample data with:")
        print("  python main_backtest.py --generate-data")
        
    except Exception as e:
        logger.error(f"[ERROR] Backtest failed: {e}", exc_info=True)


if __name__ == "__main__":
    main()