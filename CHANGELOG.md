# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Balance detection bug causing all trades to be skipped with "$0.00 calculated amount":
  - `get_balance()` now uses on-chain query as primary method (more reliable)
  - Added debug logging to show balance detection in logs
  - Fixed indentation error in `copy_trader_pct` mode protections
  - Added fallback when balance is 0 or cannot be retrieved

## [1.1.0] - 2026-03-26

### Added
- Safety limits for `copy_trader_pct` trading mode:
  - Maximum investment capped at 95% of available balance (leaves 5% for fees/gas)
  - Automatic adjustment when trader invests >100% (leverage/edge cases)
  - Automatic adjustment when calculated amount exceeds available balance
  - Informative logging for all adjustment scenarios
- Documentation for safety protections in README

### Changed
- Improved wallet setup instructions in README with official Polymarket methods:
  - Funder Address: Copy from profile page next to username
  - Private Key: Export from official settings page (https://polymarket.com/settings?tab=export-private-key)

## [1.0.0] - 2026-03-26

### Added
- Initial release of Polymarket Copy Trader
- Three trading modes:
  - `fixed`: Fixed amount per trade
  - `portfolio_pct`: Percentage of your portfolio
  - `copy_trader_pct`: Copy the same percentage the trader invests
- On-chain USDC balance queries via Polygon RPC for accurate portfolio calculation
- Tkinter GUI with 4 tabs:
  - Control Panel: Start/stop bot and view status
  - Traders: Add/remove traders to follow
  - Configuration: Edit all parameters
  - History: View executed trades and calculate P&L
- Safety protections:
  - Minimum win rate filter per trader
  - Daily loss limit
  - Active trading hours
  - Minimum trade amount ($1)
- Telegram notifications for executed, skipped, and failed trades
- SQLite database for trade history and position snapshots
- P&L tracking with real-time price updates
- CSV import from Polymarket export for closed positions

### Security
- `.gitignore` configured to exclude sensitive files:
  - `config.json` (private keys, API tokens)
  - `copytrade.db` (local database)
  - Python cache files
- `config.example.json` provided as template

[Unreleased]: https://github.com/elcucut/polymarket-copytrade/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/elcucut/polymarket-copytrade/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/elcucut/polymarket-copytrade/releases/tag/v1.0.0
