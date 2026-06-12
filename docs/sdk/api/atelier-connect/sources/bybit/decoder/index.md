# `atelier_connect::sources::bybit::decoder`

Bybit WebSocket v5 decoder.

Routes incoming JSON frames from the Bybit unified v5 stream to
`BybitWssEvent` variants.  Control frames (subscription acks,
`pong` heartbeats) are silently consumed and produce `Ok(None)`.

# Topic dispatch

Bybit data messages carry a `"topic"` field whose prefix selects the
channel:

| Prefix              | Event variant                       |
|---------------------|-------------------------------------|
| `allLiquidation.*`  | `BybitWssEvent::LiquidationData`  |
| `publicTrade.*`     | `BybitWssEvent::TradeData`         |
| `orderbook.*`       | `BybitWssEvent::OrderbookData`     |
| `tickers*`          | `BybitWssEvent::TickerData`        |

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_connect::sources::bybit::decoder`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-connect/latest/atelier_connect/sources/bybit/decoder/).

## Structs

| Item | Summary |
| --- | --- |
| [`BybitDecoder`](https://docs.rs/atelier-connect/latest/atelier_connect/sources/bybit/decoder/struct.BybitDecoder.html) | `WssDecoder` implementation for the Bybit unified v5 WebSocket API. |
