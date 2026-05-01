# `atelier_types::config::markets::market_config`

Configuration for market snapshot collection pipelines.

`MarketSnapshotConfig` is the top-level struct deserialized from a TOML
file that drives the `bybit_markets` (and future exchange) examples.

# Example TOML

```toml
[exchange]
name = "bybit"

[symbol]
name = "BTCUSDT"
sync_mode = "on_trade"

[update_frequency]
value = 100
unit = "Millis"

[pipeline]
flush_threshold = 36000

[datatypes.orderbook]
enabled = true
depth = 50

[datatypes.trades]
enabled = true

[datatypes.liquidations]
enabled = true

[datatypes.funding_rates]
enabled = true

[datatypes.open_interest]
enabled = true

[logs]
n_orderbooks = 100
n_trades = 10
n_liquidations = 1
n_fundings = 10
n_open_interests = 10

[output]
dir = "datasets/collected/bybit/market_snapshots"
```

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_types::config::markets::market_config`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-types/0.0.10/atelier_types/config/markets/market_config/).

## Structs

| Item | Summary |
| --- | --- |
| [`DataTypesSection`](https://docs.rs/atelier-types/0.0.10/atelier_types/config/markets/market_config/struct.DataTypesSection.html) | `[datatypes]` — selects which data feeds to subscribe to and collect. |
| [`ExchangeSection`](https://docs.rs/atelier-types/0.0.10/atelier_types/config/markets/market_config/struct.ExchangeSection.html) | `[exchange]` — identifies the target exchange. |
| [`FeedToggle`](https://docs.rs/atelier-types/0.0.10/atelier_types/config/markets/market_config/struct.FeedToggle.html) | Generic toggle for a data feed. |
| [`LogsSection`](https://docs.rs/atelier-types/0.0.10/atelier_types/config/markets/market_config/struct.LogsSection.html) | `[logs]` — per-event-type print frequency thresholds. |
| [`MarketSnapshotConfig`](https://docs.rs/atelier-types/0.0.10/atelier_types/config/markets/market_config/struct.MarketSnapshotConfig.html) | Top-level market snapshot configuration. |
| [`OrderbookConfig`](https://docs.rs/atelier-types/0.0.10/atelier_types/config/markets/market_config/struct.OrderbookConfig.html) | Configuration for the orderbook data feed. |
| [`OutputSection`](https://docs.rs/atelier-types/0.0.10/atelier_types/config/markets/market_config/struct.OutputSection.html) | `[output]` — where to write Parquet files. |
| [`PipelineSection`](https://docs.rs/atelier-types/0.0.10/atelier_types/config/markets/market_config/struct.PipelineSection.html) | `[pipeline]` — flush cadence. |
| [`SymbolSection`](https://docs.rs/atelier-types/0.0.10/atelier_types/config/markets/market_config/struct.SymbolSection.html) | `[symbol]` — the instrument to collect and how to synchronize. |
| [`UpdateFrequency`](https://docs.rs/atelier-types/0.0.10/atelier_types/config/markets/market_config/struct.UpdateFrequency.html) | `[update_frequency]` — grid spacing expressed as value + unit. |

## Enums

| Item | Summary |
| --- | --- |
| [`SyncMode`](https://docs.rs/atelier-types/0.0.10/atelier_types/config/markets/market_config/enum.SyncMode.html) | Which event type drives the synchronization grid clock. |
| [`TimeUnit`](https://docs.rs/atelier-types/0.0.10/atelier_types/config/markets/market_config/enum.TimeUnit.html) | Time unit for `UpdateFrequency`. |
