# `atelier-types` — API reference

Skeleton API reference for crate
[`atelier-types`](https://docs.rs/atelier-types/0.0.10/atelier_types/) at
version `0.0.10`. Every public item links out to docs.rs for full
signatures, source, and trait implementations.

!!! info "Preliminary skeleton"
    The tables below were hand-derived from a survey of the SDK
    source. Before cutover, regenerate authoritatively with:

    ```bash
    make sdk-api SDK_PATH=../atelier-sdk
    ```

    That populates per-module sub-pages and refreshes this index from
    rustdoc JSON. See [Cutover runbook](../../../operations/cutover-runbook.md).

## Modules

| Module                                                                              | Public items                                                                  |
|-------------------------------------------------------------------------------------|-------------------------------------------------------------------------------|
| [`config`](https://docs.rs/atelier-types/0.0.10/atelier_types/config/)               | `MarketSnapshotConfig`, `MarketConfig`, `WorkerManifest`                       |
| [`errors`](https://docs.rs/atelier-types/0.0.10/atelier_types/errors/)               | `OrderError`, `OrderbookError`, `PersistError`, `TemporalError`, `ConfigError`, plus 2 more |
| [`exchanges`](https://docs.rs/atelier-types/0.0.10/atelier_types/exchanges/)         | `Exchange`, `MarketType`                                                       |
| [`funding`](https://docs.rs/atelier-types/0.0.10/atelier_types/funding/)             | `FundingRate`                                                                  |
| [`levels`](https://docs.rs/atelier-types/0.0.10/atelier_types/levels/)               | `Level`                                                                         |
| [`liquidations`](https://docs.rs/atelier-types/0.0.10/atelier_types/liquidations/)   | `Liquidation`                                                                  |
| [`open_interest`](https://docs.rs/atelier-types/0.0.10/atelier_types/open_interest/) | `OpenInterest`                                                                 |
| [`orderbooks`](https://docs.rs/atelier-types/0.0.10/atelier_types/orderbooks/)       | `Orderbook`, `OrderbookDelta`, `NormalizedDelta`                              |
| [`orders`](https://docs.rs/atelier-types/0.0.10/atelier_types/orders/)               | `Order`, `OrderSide`, `OrderType`                                              |
| [`snapshots`](https://docs.rs/atelier-types/0.0.10/atelier_types/snapshots/)         | `MarketSnapshot`, `MarketAggregate`                                            |
| [`subscriptions`](https://docs.rs/atelier-types/0.0.10/atelier_types/subscriptions/) | `SubscriptionStatus`                                                           |
| [`synchronizers`](https://docs.rs/atelier-types/0.0.10/atelier_types/synchronizers/) | `EventSynchronizer`, `MarketSynchronizer`, `ClockMode`, plus 2 more            |
| [`temporal`](https://docs.rs/atelier-types/0.0.10/atelier_types/temporal/)           | `TimeResolution`, validation helpers, `from_nanos`                             |
| [`trades`](https://docs.rs/atelier-types/0.0.10/atelier_types/trades/)               | `Trade`, `TradeSide`                                                           |
| [`trading_pair`](https://docs.rs/atelier-types/0.0.10/atelier_types/trading_pair/)   | `TradingPair`                                                                  |
| [`workers`](https://docs.rs/atelier-types/0.0.10/atelier_types/workers/)             | `WorkerId`                                                                     |
| `templates`                                                                          | _internal templates; surface intentionally undocumented_                       |
| `utils`                                                                              | _utility helpers; mostly private_                                              |

## Quick links to high-traffic items

| Item                 | What it is                                                | docs.rs                                                                                                                              |
|----------------------|-----------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------|
| `Orderbook`          | BTreeMap-backed limit order book                          | [link](https://docs.rs/atelier-types/0.0.10/atelier_types/orderbooks/struct.Orderbook.html)                                          |
| `OrderbookDelta`     | Incremental order book update                             | [link](https://docs.rs/atelier-types/0.0.10/atelier_types/orderbooks/struct.OrderbookDelta.html)                                      |
| `Trade`              | Public trade execution                                    | [link](https://docs.rs/atelier-types/0.0.10/atelier_types/trades/struct.Trade.html)                                                   |
| `TradeSide`          | Buy / sell taker side                                     | [link](https://docs.rs/atelier-types/0.0.10/atelier_types/trades/enum.TradeSide.html)                                                 |
| `MarketSnapshot`     | Multi-source time-aligned bundle                          | [link](https://docs.rs/atelier-types/0.0.10/atelier_types/snapshots/struct.MarketSnapshot.html)                                       |
| `MarketAggregate`    | 15-scalar feature vector from a snapshot                  | [link](https://docs.rs/atelier-types/0.0.10/atelier_types/snapshots/struct.MarketAggregate.html)                                      |
| `EventSynchronizer`  | Timestamp-based event ordering                             | [link](https://docs.rs/atelier-types/0.0.10/atelier_types/synchronizers/struct.EventSynchronizer.html)                                |
| `MarketSynchronizer` | Multi-source synchronized snapshot aggregation             | [link](https://docs.rs/atelier-types/0.0.10/atelier_types/synchronizers/struct.MarketSynchronizer.html)                               |
| `ClockMode`          | OrderbookDriven / TradeDriven / LiquidationDriven / External | [link](https://docs.rs/atelier-types/0.0.10/atelier_types/synchronizers/enum.ClockMode.html)                                       |
| `Exchange`           | Bybit / Binance / Coinbase / Kraken                       | [link](https://docs.rs/atelier-types/0.0.10/atelier_types/exchanges/enum.Exchange.html)                                               |
| `WorkerManifest`     | TOML-driven multi-worker config                           | [link](https://docs.rs/atelier-types/0.0.10/atelier_types/config/struct.WorkerManifest.html)                                          |

Full reference (docs.rs): <https://docs.rs/atelier-types/0.0.10/atelier_types/>
