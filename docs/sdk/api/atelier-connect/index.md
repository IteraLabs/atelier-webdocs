# `atelier-connect` — API reference

Skeleton API reference for crate
[`atelier-connect`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/) at
version `0.0.10`.

!!! info "Preliminary skeleton"
    Hand-derived from the Phase-1 survey. Run
    `make sdk-api SDK_PATH=../atelier-sdk` before cutover to refresh
    from rustdoc JSON.

## Modules

| Module                                                                                     | Public items                                                                                              |
|--------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------|
| [`clients`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/clients/)                | `WssClient<D>`, `WssClientBuilder`, `HttpClient`, `ConnectionManager`, `ReconnectPolicy`, `DisconnectReason`, `HealthMonitor`, plus more |
| [`sources`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/sources/)                | `BinanceWssClient`, `BybitWssClient`, `CoinbaseWssClient`, `KrakenWssClient`, `ExchangeEvent`              |
| [`config`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/config/)                  | `DataWorkerConfig`, `MarketWorkerConfig`, plus nested sub-tables                                          |
| [`synchronizers`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/synchronizers/)    | `EventSynchronizer`, `MarketSynchronizer`, `ClockMode`                                                    |
| [`workers`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/)                | `DataWorker`, `MarketWorker`, `OutputSinkSet`, `TopicRegistry`, `IngestionCore`, `GapDetector`, `GapDetectorSet`, plus more |
| [`errors`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/errors/)                  | Connection / parse / worker-specific error enums                                                          |
| `remote_agent` *(feature: `gateway`)*                                                       | `GatewayConnection`, `RemoteAgent`, `TelemetryReporter`, `UpstreamSink`                                   |

## Quick links to high-traffic items

| Item                  | What it is                                                                            | docs.rs                                                                                                                |
|-----------------------|---------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------|
| `BybitWssClient`      | Bybit WebSocket client (perpetuals + spot)                                            | [link](https://docs.rs/atelier-connect/0.0.10/atelier_connect/sources/bybit/struct.BybitWssClient.html)                |
| `BinanceWssClient`    | Binance WebSocket + REST client                                                       | [link](https://docs.rs/atelier-connect/0.0.10/atelier_connect/sources/binance/struct.BinanceWssClient.html)            |
| `CoinbaseWssClient`   | Coinbase Advanced Trade WebSocket client                                              | [link](https://docs.rs/atelier-connect/0.0.10/atelier_connect/sources/coinbase/struct.CoinbaseWssClient.html)          |
| `KrakenWssClient`     | Kraken v2 WebSocket client                                                            | [link](https://docs.rs/atelier-connect/0.0.10/atelier_connect/sources/kraken/struct.KrakenWssClient.html)              |
| `ExchangeEvent`       | Unified enum across exchange-native event types                                       | [link](https://docs.rs/atelier-connect/0.0.10/atelier_connect/sources/enum.ExchangeEvent.html)                         |
| `DataWorker`          | Raw event passthrough worker                                                          | [link](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/data_worker/struct.DataWorker.html)              |
| `MarketWorker`        | Synchronized snapshot worker                                                          | [link](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/market_worker/struct.MarketWorker.html)          |
| `OutputSinkSet`       | Fan-out container: channel + terminal + parquet sinks                                  | [link](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/sinks/struct.OutputSinkSet.html)                 |
| `ConnectionManager`   | Multi-exchange connection lifecycle tracker                                            | [link](https://docs.rs/atelier-connect/0.0.10/atelier_connect/clients/struct.ConnectionManager.html)                   |
| `ReconnectPolicy`     | Jittered exponential backoff with circuit breaker                                     | [link](https://docs.rs/atelier-connect/0.0.10/atelier_connect/clients/struct.ReconnectPolicy.html)                     |
| `MarketWorkerManifest`| TOML-driven manifest parser, returns N `MarketWorkerConfig`s                          | [link](https://docs.rs/atelier-connect/0.0.10/atelier_connect/config/workers/struct.MarketWorkerManifest.html)          |

Full reference (docs.rs): <https://docs.rs/atelier-connect/0.0.10/atelier_connect/>
