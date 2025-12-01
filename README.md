# Polymarket Trading Bot - Production Ready

A complete algorithmic trading system for Polymarket 15-minute UP/DOWN markets with backtesting engine.

## Features

- ✅ Real-time WebSocket (RTDS) + REST API fallback
- ✅ Group + Laggard momentum strategy
- ✅ 15-minute window management
- ✅ Full backtesting engine
- ✅ Paper trading mode
- ✅ Comprehensive logging
- ✅ All parameters configurable

## Quick Start

### Installation

```bash
pip install aiohttp websockets pandas numpy
```

### Configuration

Edit `config.py` or create `custom_config.json`:

```json
{
  "entry_check_interval": 5,
  "stake_size": 1.0,
  "band_high_group": [0.75, 1.00],
  "band_low_group": [0.00, 0.25],
  "exit_up_threshold": 0.90,
  "exit_down_threshold": 0.10
}
```

### Run Live Trading (Paper Mode)

```bash
python main_live.py --paper-trade
```

### Run Backtest

```bash
python main_backtest.py --start-date 2024-09-01 --end-date 2024-11-30
```

## Strategy Overview

### Assets
- **Reference Group**: BTC, ETH (always monitored)
- **Tradeable**: SOL, XRP (we trade these)

### Groups
- **G1**: BTC + ETH + SOL → Trade XRP
- **G2**: BTC + ETH + XRP → Trade SOL

### Entry Logic
- **UP**: Group in [0.75-1.00] AND Laggard in [0.00-0.50]
- **DOWN**: Group in [0.00-0.25] AND Laggard in [0.50-1.00]

### Exit Logic
- **UP**: Close when price >= 0.90
- **DOWN**: Close when price <= 0.10
- Otherwise hold to settlement

### Time Windows
- Markets are 15 minutes (e.g., 12:00-12:15)
- Entry only when 1:30 to 5:00 minutes remain
- Max 1 trade per window

## Project Structure

```
polymarket_bot/
├── config.py           # Configuration
├── data_feed.py        # REST + RTDS clients
├── window_manager.py   # Time window logic
├── strategy.py         # Trading strategy
├── trader.py           # Live trading engine
├── backtester.py       # Backtesting engine
├── logger.py           # Logging utilities
├── utils.py            # Helper functions
├── main_live.py        # Live/paper trading
├── main_backtest.py    # Backtesting
└── README.md           # This file
```

## Logs

All trades logged to CSV with:
- Entry/exit timestamps
- Window info
- Asset, side, prices
- Group configuration
- P&L, fees
- Settlement outcome

## Safety

⚠️ **ALWAYS test with paper trading first!**
⚠️ **Never risk more than you can afford to lose**
⚠️ **This is experimental software - use at your own risk**

## License

MIT - Use at your own risk