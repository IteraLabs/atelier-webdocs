# `atelier_connect::sources::binance::client`

Binance spot public WebSocket client.

`BinanceWssClient` handles Binance-specific connection, subscription
framing, and heartbeat protocol. Message decoding is delegated to
`BinanceDecoder` via the `WssDecoder` trait.

Public market data streams do **not** require authentication.

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_connect::sources::binance::client`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-connect/0.0.10/atelier_connect/sources/binance/client/).

## Structs

| Item | Summary |
| --- | --- |
| [`BinanceWssClient`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/sources/binance/client/struct.BinanceWssClient.html) | Binance spot public WebSocket client. |
