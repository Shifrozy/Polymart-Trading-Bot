# Polymarket 15-Minute Trading Bot - Production Version 2.0

A professional algorithmic trading bot for Polymarket 15-minute UP/DOWN prediction markets with full backtesting capabilities.

## Features

✅ **Real Polymarket API Integration**
- Dynamic market loading from Polymarket API
- Real-time WebSocket (RTDS) price streaming
- Automatic market refresh and reconnection

✅ **Advanced Strategy**
- Group + Laggard momentum detection
- Configurable zone thresholds
- Time-window based entry/exit rules
- Multiple group configurations (G1, G2)

✅ **Full Backtesting Engine**
- Event-driven historical simulation
- Comprehensive performance metrics
- Trade-by-trade analysis
- Equity curve tracking

✅ **Paper Trading Mode**
- Risk-free testing with real market data
- Full strategy execution simulation
- Real-time P&L tracking

✅ **Production-Ready**
- Modular, clean codebase
- Comprehensive error handling
- Detailed logging system
- JSON configuration

---

## Quick Start

### Installation
```bash
# Clone or download the project
cd polymarket_bot

# Install dependencies
pip install pandas numpy requests websockets aiohttp
```

### Generate Sample Data
```bash
python main_backtest.py --generate-data
```

### Run Backtest
```bash
python main_backtest.py --start 2024-09-01 --end 2024-12-31
```

### Run Paper Trading
```bash
python main_live.py --paper-trade
```

---

## Project Structure
```
polymarket_bot/
├── config.py              # Configuration system
├── config.json            # User configuration file
├── market_loader.py       # Polymarket API market loader
├── data_feed.py           # Real-time data feed (RTDS + REST)
├── window_manager.py      # 15-minute window management
├── strategy.py            # Group + Laggard strategy
├── trader.py              # Live trading engine
├── backtester.py          # Backtesting engine
├── logger.py              # Logging utilities
├── utils.py               # Helper functions
├── sample_data.py         # Sample data generator
├── main_live.py           # Live/paper trading entry point
├── main_backtest.py       # Backtesting entry point
├── README.md              # This file
├── data/                  # Historical data directory
└── logs/                  # Log files directory
    ├── bot.log           # System logs
    └── trades.csv        # Trade history
```

---

## Strategy Overview

### Assets
- **Reference Group**: BTC, ETH (always monitored)
- **Tradeable**: SOL, XRP (we trade these)

### Group Configurations

**Group G1**: BTC + ETH + SOL → Trade XRP
**Group G2**: BTC + ETH + XRP → Trade SOL

### Entry Signals

**UP Entry**:
- Group (3 assets) ALL in HIGH zone [0.75 - 1.00]
- Laggard in LOW zone [0.00 - 0.50]
- → BUY UP on laggard

**DOWN Entry**:
- Group (3 assets) ALL in LOW zone [0.00 - 0.25]
- Laggard in HIGH zone [0.50 - 1.00]
- → BUY DOWN on laggard

### Exit Rules

- **UP Trade**: Exit when laggard >= 0.90
- **DOWN Trade**: Exit when laggard <= 0.10
- **Otherwise**: Hold until settlement

### Time Windows

- Markets are 15-minute intervals
- Entry only when 1:30 to 5:00 minutes remain
- Maximum 1 trade per window

---

## Configuration

Edit `config.json` to customize:
```json
{
  "zone_high_min": 0.75,
  "zone_high_max": 1.00,
  "zone_low_min": 0.00,
  "zone_low_max": 0.25,
  "exit_up_threshold": 0.90,
  "exit_down_threshold": 0.10,
  "stake_size_usd": 1.0
}
```

### Key Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `zone_high_min/max` | High zone thresholds | 0.75 - 1.00 |
| `zone_low_min/max` | Low zone thresholds | 0.00 - 0.25 |
| `exit_up_threshold` | UP trade exit target | 0.90 |
| `exit_down_threshold` | DOWN trade exit target | 0.10 |
| `stake_size_usd` | Position size | 1.0 USD |
| `window_duration_minutes` | Market window length | 15 min |
| `entry_window_max_remaining_seconds` | Latest entry time | 300s (5:00) |
| `entry_window_min_remaining_seconds` | Earliest entry time | 90s (1:30) |

---

## Usage Examples

### Backtesting
```bash
# Generate sample data first
python main_backtest.py --generate-data

# Run backtest
python main_backtest.py --start 2024-09-01 --end 2024-12-31

# With custom config
python main_backtest.py --start 2024-09-01 --end 2024-12-31 --config my_config.json

# Custom data file
python main_backtest.py --start 2024-09-01 --end 2024-12-31 --data-file my_data.csv
```

### Paper Trading
```bash
# Basic paper trading
python main_live.py --paper-trade

# With custom config
python main_live.py --paper-trade --config my_config.json
```

### Live Trading (Real Money)
```bash
# ⚠️ WARNING: This uses real money!
python main_live.py --live --config production_config.json
```

---

## Output Files

### Trade Logs (`logs/trades.csv`)

Contains detailed information for each trade:
- Entry/exit timestamps
- Asset, side (UP/DOWN)
- Entry/exit prices
- Group configuration
- P&L (percentage and USD)
- Cumulative P&L
- Settlement outcome

### System Logs (`logs/bot.log`)

Contains system events:
- Initialization
- Price updates
- Signal detection
- Entry/exit execution
- Errors and warnings

---

## Backtest Output
```
============================================================
BACKTEST RESULTS
============================================================

TRADE STATISTICS
  Total Trades:        45
  Winning Trades:      24 (53.3%)
  Losing Trades:       21 (46.7%)
  UP Trades:           23
  DOWN Trades:         22
  Group G1:            22
  Group G2:            23

P&L STATISTICS
  Total P&L:           $12.45
  Average Win:         $2.15
  Average Loss:        -$1.89
  Max Win:             $5.20
  Max Loss:            -$4.30
  Max Drawdown:        -$8.50
  Profit Factor:       1.24

PER-ASSET PERFORMANCE
  SOL:  23 trades | Total: $6.50 | Avg: $0.28
  XRP:  22 trades | Total: $5.95 | Avg: $0.27

============================================================
```

---

## API Integration

### Market Loading

The bot automatically fetches 15-minute markets from Polymarket:
```python
# Markets are loaded dynamically
loader = PolymarketLoader(config)
markets = await loader.fetch_markets(["BTC", "ETH", "SOL", "XRP"])
```

### Real-Time Prices

Prices stream via WebSocket (RTDS):
```python
# Auto-reconnecting WebSocket
rtds_client = EnhancedRTDSClient(url, markets)
await rtds_client.connect()
```

---

## Safety Features

✅ **Paper Trading Default**: No real money by default
✅ **Max 1 Trade Per Window**: Prevents over-trading
✅ **Time Window Restrictions**: Only trade in specific time windows
✅ **Auto Reconnection**: Handles network issues
✅ **Error Handling**: Comprehensive error catching
✅ **Graceful Shutdown**: Properly closes all positions

---

## Development

### Adding New Assets

Edit `config.json`:
```json
{
  "reference_assets": ["BTC", "ETH", "MATIC"],
  "tradeable_assets": ["SOL", "XRP", "DOGE"],
  "all_assets": ["BTC", "ETH", "SOL", "XRP", "MATIC", "DOGE"]
}
```

### Custom Strategy Modifications

Edit `strategy.py` - all strategy logic is in `EnhancedPolymarketStrategy` class.

### Adjusting Thresholds

All thresholds are configurable in `config.json` - no code changes needed!

---

## Troubleshooting

### No trades in backtest?

- Check if data has valid signal conditions
- Review zone thresholds - they might be too strict
- Verify time window settings

### WebSocket connection issues?

- Bot automatically falls back to mock mode
- Check internet connection
- Verify Polymarket API is accessible

### Missing data file?
```bash
python main_backtest.py --generate-data
```

---

## Disclaimer

⚠️ **IMPORTANT**: This bot is for educational purposes. Trading involves risk of loss. Never trade with money you can't afford to lose. Always test thoroughly in paper trading mode before considering live trading.

- This bot does NOT guarantee profits
- Past performance does NOT indicate future results
- You are responsible for your own trading decisions
- The developers are NOT liable for any losses

---

## License

MIT License - Use at your own risk

---

## Support

For issues or questions:
1. Check this README
2. Review the code comments
3. Check log files for errors
4. Test with sample data first

---

## Version History

**v2.0** - Enhanced Production Version
- Real Polymarket API integration
- Dynamic market loading
- Enhanced strategy engine
- Full backtesting capabilities
- Improved logging and error handling

**v1.0** - Initial Release
- Basic strategy implementation
- Mock data support
- Simple backtesting

---

**Happy Trading! 🚀**

Remember: Test extensively before live trading!