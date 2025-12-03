"""
Quick Start Guide for Polymarket Trading Bot
"""

print("""
╔════════════════════════════════════════════════════════════════════╗
║         POLYMARKET 15-MINUTE TRADING BOT - QUICK START             ║
╚════════════════════════════════════════════════════════════════════╝

🚀 GETTING STARTED
─────────────────────────────────────────────────────────────────────

1. Install dependencies:
   pip install pandas numpy requests websockets aiohttp

2. Run the bot:
   python run.py

   This will show you a menu to choose between:
   ├─ 📊 BACKTEST   (Test on historical data)
   ├─ 🔴 LIVE TRADE (Real-time paper trading)
   ├─ ⚙️  CONFIG    (View settings)
   └─ ❌ EXIT       (Quit)


📊 BACKTESTING MODE
─────────────────────────────────────────────────────────────────────

What it does:
  ✅ Tests strategy on historical price data
  ✅ No real money involved (100% safe)
  ✅ Runs from start to end date
  ✅ Shows complete trade history
  ✅ Calculates P&L and statistics

How to run:
  python run.py → Select "1" → Choose date range

Output includes:
  • All trades with entry/exit times
  • P&L for each trade
  • Total trades and win rate
  • Cumulative profit/loss


🔴 LIVE TRADING MODE
─────────────────────────────────────────────────────────────────────

What it does:
  ✅ Connects to real Polymarket API
  ✅ Gets live market prices (15-minute markets)
  ✅ Executes strategy in real-time
  ✅ Simulates trades (NO real money)
  ✅ Tracks positions with stop loss

How to run:
  python run.py → Select "2"

Safety features:
  🛡️  PAPER TRADING (all orders are simulated)
  🛡️  STOP LOSS (5% by default - can be changed in config.py)
  🛡️  NO real money at risk
  🛡️  Can stop anytime with Ctrl+C

Live data sources:
  • Polymarket API (real market data)
  • Falls back to mock data if API unavailable
  • Shows clear entry/exit signals


📊 UNDERSTANDING THE SIGNALS
─────────────────────────────────────────────────────────────────────

ENTRY SIGNAL Example:
  [SIGNAL DETECTED] UP on XRP (G1): Group HIGH, Laggard LOW
  
  Meaning:
    • GO UP on XRP
    • BTC, ETH, SOL prices are HIGH (0.75-1.0)
    • XRP is LOW (0.0-0.25)
    • Good time to buy

EXIT SIGNAL - Strategy Exit:
  Exit when price reaches 0.90 (for UP) or 0.10 (for DOWN)

EXIT SIGNAL - Stop Loss:
  Automatic exit at -5% to protect against losses


🔧 CONFIGURATION
─────────────────────────────────────────────────────────────────────

Edit config.py to change:

  stake_size_usd: 1.0        # Amount per trade
  stop_loss_pct: 0.05        # 5% stop loss level
  
  exit_up_threshold: 0.90    # Exit UP at this price
  exit_down_threshold: 0.10  # Exit DOWN at this price
  
  window_duration_minutes: 15            # 15-min markets
  entry_window_min_remaining_seconds: 90 # Enter only in last 90s
  entry_window_max_remaining_seconds: 300 # Enter in last 300s


📁 FILE STRUCTURE
─────────────────────────────────────────────────────────────────────

run.py                 ← START HERE (main entry point)
config.py              ← Configuration settings
trader.py              ← Live trading logic (with stop loss)
strategy.py            ← Entry/exit signals
data_feed.py           ← Real-time price data
main_backtest.py       ← Historical backtesting
main_live.py           ← Legacy live trading
logs/
  ├─ bot.log          ← System logs
  └─ trades.csv       ← Trade history
data/
  └─ historical/      ← Backtest data


❓ COMMON QUESTIONS
─────────────────────────────────────────────────────────────────────

Q: Is my money safe?
A: Yes! Paper trading mode simulates all trades. No real money is used.

Q: Can I see what trades were made?
A: Yes! Check logs/trades.csv for complete trade history.

Q: How do I change the stake size?
A: Edit config.py, change "stake_size_usd": 1.0 to your amount.

Q: What if API fails?
A: Bot automatically switches to mock mode for testing.

Q: How do I stop the bot?
A: Press Ctrl+C anytime.

Q: Can I test on different dates?
A: Yes! In backtest mode, choose custom date range.


🎯 RECOMMENDED WORKFLOW
─────────────────────────────────────────────────────────────────────

1. START with backtesting (safe, fast)
   ├─ Test last 30 days
   ├─ Check results
   └─ Understand strategy behavior

2. THEN run live trading (real prices, simulated trades)
   ├─ Run for 1-2 hours
   ├─ Watch signal quality
   └─ Verify entries/exits

3. TWEAK settings in config.py if needed
   └─ Different stop loss? Entry window? Stake size?

4. REPEAT with new config


💡 TIPS
─────────────────────────────────────────────────────────────────────

✓ Always backtest first before going live
✓ Monitor logs/bot.log for any issues
✓ Stop loss protects you from big losses
✓ Each trade is logged in logs/trades.csv
✓ Real Polymarket data is used for signals


🚀 QUICK COMMANDS
─────────────────────────────────────────────────────────────────────

# Run the bot (recommended)
python run.py

# Run paper trading directly
python main_live.py --paper-trade

# Run backtesting directly
python main_backtest.py

# View the code
cat strategy.py      # Strategy logic
cat config.py        # Settings
cat trader.py        # Trading engine


═════════════════════════════════════════════════════════════════════

Got it? Run: python run.py

Good luck! 🎯

═════════════════════════════════════════════════════════════════════
""")
