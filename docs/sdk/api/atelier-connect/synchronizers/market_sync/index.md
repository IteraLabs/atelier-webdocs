# `atelier_connect::synchronizers::market_sync`

Multi-source time synchronizer with configurable clock modes.

Aligns orderbook snapshots, trades, liquidations, funding rates, and open
interest to a uniform time grid. Produces `MarketSnapshot` at each period.

# Clock Modes

The synchronizer supports four clock modes via `ClockMode`:

- **OrderbookDriven** (default): Grid periods are triggered by orderbook
  timestamp crossings, matching the original `MarketSynchronizer` behavior.
- **TradeDriven**: Grid periods are triggered by trade timestamps.
- **LiquidationDriven**: Grid periods are triggered by liquidation timestamps.
- **ExternalClock**: Grid periods are driven by explicit `on_time()` calls
  with an external nanosecond timestamp.

# Semantics

- **Orderbook, funding rate, OI** are *state-based*: the latest value is
  carried forward into each period.
- **Trades, liquidations** are *event-based*: all events within a period
  are collected into a single bucket.

# Usage

```ignore
use atelier_connect::synchronizers::{MarketSynchronizer, ClockMode};

// Orderbook-driven (default, backward compatible)
let mut sync = MarketSynchronizer::new(100_000_000);

// External clock
let mut sync = MarketSynchronizer::external_clock(100_000_000);
sync.on_orderbook("BTCUSDT", ts_ms, orderbook); // updates state only
sync.on_trade(trade);                            // accumulates only
sync.on_time(ts_ns);                             // drives the grid

// Trade-driven
let mut sync = MarketSynchronizer::trade_driven(100_000_000);
sync.on_orderbook("BTCUSDT", ts_ms, orderbook); // updates state only
sync.on_trade(trade);                            // accumulates + drives grid

// Liquidation-driven
let mut sync = MarketSynchronizer::liquidation_driven(100_000_000);
sync.on_liquidation(liq);                        // accumulates + drives grid

// At end of stream:
sync.finalize();
let snapshots: Vec<MarketSnapshot> = sync.drain();
```

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_connect::synchronizers::market_sync`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-connect/latest/atelier_connect/synchronizers/market_sync/).

## Structs

| Item | Summary |
| --- | --- |
| [`MarketSynchronizer`](https://docs.rs/atelier-connect/latest/atelier_connect/synchronizers/market_sync/struct.MarketSynchronizer.html) | Multi-source time synchronizer that produces `MarketSnapshot` at each grid period, combining all data sources. |

## Enums

| Item | Summary |
| --- | --- |
| [`ClockMode`](https://docs.rs/atelier-connect/latest/atelier_connect/synchronizers/market_sync/enum.ClockMode.html) | Determines which data feed drives the grid clock. |
