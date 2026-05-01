# `atelier_connect::sources::binance::rest`

Binance spot public REST client for orderbook snapshots.

`BinanceRestClient` fetches a single depth snapshot from the
Binance REST API. It is a thin wrapper over `reqwest::Client`
with no rate-limiting (single-call usage).

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_connect::sources::binance::rest`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-connect/0.0.10/atelier_connect/sources/binance/rest/).

## Structs

| Item | Summary |
| --- | --- |
| [`BinanceRestClient`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/sources/binance/rest/struct.BinanceRestClient.html) | Binance REST API client for public market data. |
