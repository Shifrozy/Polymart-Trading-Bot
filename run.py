"""
Polymarket Trading Bot - Single Entry Point
Unified interface for Backtesting and Live Trading
"""

import asyncio
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import logging

from config import Config
from logger import setup_logging


async def run_backtest(config, start_date, end_date):
    """Run backtesting mode"""
    import subprocess
    from pathlib import Path
    
    print("\n" + "="*70)
    print("BACKTESTING MODE")
    print("="*70)
    print(f"Date Range: {start_date} to {end_date}")
    print("="*70 + "\n")
    
    logger = logging.getLogger(__name__)
    logger.info(f"[BACKTEST] Starting backtest from {start_date} to {end_date}")
    
    # Check if data file exists
    data_file = Path("data/historical_prices.csv")
    if not data_file.exists():
        print("⚠️  Data file not found: data/historical_prices.csv")
        print("\n📝 FIRST TIME SETUP: Generate sample data")
        print("─" * 70)
        print("\nRun this command to generate historical data:")
        print("  python main_backtest.py --generate-data")
        print("\nThen run this program again to backtest!")
        print("─" * 70 + "\n")
        logger.warning("[BACKTEST] Data file not found")
        return False
    
    try:
        # Run backtest in subprocess (it's synchronous)
        result = subprocess.run(
            [
                sys.executable, 
                "main_backtest.py",
                "--start", start_date,
                "--end", end_date
            ],
            capture_output=False,
            text=True
        )
        
        if result.returncode == 0:
            logger.info("[BACKTEST] Backtest completed successfully")
            print("\n✅ Backtest completed!")
            return True
        else:
            logger.error(f"[BACKTEST] Backtest failed with code {result.returncode}")
            print(f"\n❌ Backtest failed")
            return False
            
    except Exception as e:
        logger.error(f"[BACKTEST ERROR] {e}", exc_info=True)
        print(f"\n❌ Backtest error: {e}")
        return False


async def run_live_trading(config):
    """Run live paper trading mode"""
    from trader import EnhancedLiveTrader
    
    print("\n" + "="*70)
    print("LIVE TRADING MODE (PAPER TRADING - NO REAL MONEY)")
    print("="*70)
    print("Real-time prices from Polymarket")
    print("Orders will be SIMULATED only")
    print("="*70 + "\n")
    
    logger = logging.getLogger(__name__)
    logger.info("[LIVE] Starting live trading session")
    
    try:
        trader = EnhancedLiveTrader(config.config, paper_trade=True)
        await trader.initialize()
        await trader.run()
        
    except KeyboardInterrupt:
        logger.info("\n[INTERRUPT] Received shutdown signal")
        print("\n\n[STOPPED] Live trading stopped by user")
        
    except Exception as e:
        logger.error(f"[LIVE ERROR] {e}", exc_info=True)
        print(f"\n❌ Live trading error: {e}")
        return False
    
    finally:
        if 'trader' in locals():
            await trader.shutdown()
    
    return True


def get_date_range():
    """Get date range from user"""
    print("\n" + "="*70)
    print("SELECT DATE RANGE FOR BACKTESTING")
    print("="*70)
    
    today = datetime.now().date()
    
    # Default range - last 30 days
    default_end = today
    default_start = today - timedelta(days=30)
    
    print(f"\nDefault range: {default_start} to {default_end}")
    print("\nOptions:")
    print("  1. Use default (last 30 days)")
    print("  2. Enter custom dates")
    print("  3. Last 7 days")
    print("  4. Last 90 days")
    print("  5. Go back to main menu")
    
    choice = input("\nSelect option (1-5): ").strip()
    
    if choice == "1":
        return str(default_start), str(default_end)
    elif choice == "2":
        try:
            start_str = input("Start date (YYYY-MM-DD): ").strip()
            end_str = input("End date (YYYY-MM-DD): ").strip()
            
            # Validate dates
            start = datetime.strptime(start_str, "%Y-%m-%d").date()
            end = datetime.strptime(end_str, "%Y-%m-%d").date()
            
            if start > end:
                print("❌ Start date must be before end date")
                return None, None
            
            if end > today:
                print("❌ End date cannot be in the future")
                return None, None
            
            return str(start), str(end)
        except ValueError:
            print("❌ Invalid date format. Use YYYY-MM-DD")
            return None, None
    elif choice == "3":
        end = today
        start = today - timedelta(days=7)
        return str(start), str(end)
    elif choice == "4":
        end = today
        start = today - timedelta(days=90)
        return str(start), str(end)
    elif choice == "5":
        return None, None
    else:
        print("❌ Invalid option")
        return None, None


def show_main_menu():
    """Show main menu"""
    print("\n" + "="*70)
    print("POLYMARKET 15-MINUTE TRADING BOT")
    print("="*70)
    print("\nSelect Mode:")
    print("  1. 📊 BACKTEST   - Test strategy on historical data")
    print("  2. 🔴 LIVE TRADE - Real-time paper trading (no money)")
    print("  3. ⚙️  CONFIG    - View configuration")
    print("  4. 📋 SETUP     - First time setup (generate sample data)")
    print("  5. ❌ EXIT       - Exit the program")
    print("="*70)
    
    choice = input("\nSelect option (1-5): ").strip()
    return choice


async def show_config(config):
    """Show current configuration"""
    print("\n" + "="*70)
    print("CURRENT CONFIGURATION")
    print("="*70)
    
    cfg = config.config
    
    print("\n📍 ASSETS:")
    print(f"  Reference: {', '.join(cfg['reference_assets'])}")
    print(f"  Tradeable: {', '.join(cfg['tradeable_assets'])}")
    print(f"  All: {', '.join(cfg['all_assets'])}")
    
    print("\n⏱️  TIME SETTINGS:")
    print(f"  Window Duration: {cfg['window_duration_minutes']} minutes")
    print(f"  Entry Window: {cfg['entry_window_min_remaining_seconds']}s - {cfg['entry_window_max_remaining_seconds']}s")
    
    print("\n💰 TRADING PARAMETERS:")
    print(f"  Stake Size: ${cfg['stake_size_usd']}")
    print(f"  Max Trades Per Window: {cfg['max_trades_per_window']}")
    
    print("\n📈 STRATEGY ZONES:")
    print(f"  High Zone: {cfg['zone_high_min']} - {cfg['zone_high_max']}")
    print(f"  Low Zone: {cfg['zone_low_min']} - {cfg['zone_low_max']}")
    
    print("\n🎯 EXIT THRESHOLDS:")
    print(f"  Exit UP: >= {cfg['exit_up_threshold']}")
    print(f"  Exit DOWN: <= {cfg['exit_down_threshold']}")
    
    print("\n" + "="*70)
    input("Press Enter to continue...")


async def main():
    """Main entry point"""
    
    # Load configuration
    if Path("config.json").exists():
        config = Config(config_file="config.json")
        print("[CONFIG] Loaded from config.json")
    else:
        config = Config()
        print("[CONFIG] Using default configuration")
    
    # Setup logging
    setup_logging(config.config)
    logger = logging.getLogger(__name__)
    
    # Main loop
    while True:
        choice = show_main_menu()
        
        if choice == "1":
            # Backtest
            start_date, end_date = get_date_range()
            
            if start_date and end_date:
                success = await run_backtest(config, start_date, end_date)
                if success:
                    input("\nPress Enter to continue...")
            else:
                if start_date is None:  # User cancelled
                    continue
                else:  # Error in date parsing
                    input("\nPress Enter to try again...")
        
        elif choice == "2":
            # Live trading
            success = await run_live_trading(config)
            input("\nPress Enter to continue...")
        
        elif choice == "3":
            # Show config
            await show_config(config)
        
        elif choice == "4":
            # Setup - generate sample data
            print("\n" + "="*70)
            print("FIRST TIME SETUP - GENERATE SAMPLE DATA")
            print("="*70)
            print("\nThis will generate historical price data for backtesting")
            print("\nRunning: python main_backtest.py --generate-data\n")
            
            import subprocess
            subprocess.run([sys.executable, "main_backtest.py", "--generate-data"])
            
            print("\n" + "="*70)
            print("✅ Setup complete! You can now run backtests.")
            print("="*70)
            input("\nPress Enter to continue...")
        
        elif choice == "5":
            # Exit
            print("\n✅ Thank you for using Polymarket Trading Bot!")
            sys.exit(0)
        
        else:
            print("❌ Invalid option. Please try again.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Program stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
