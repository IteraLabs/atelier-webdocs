# `atelier_connect::sources::coinbase::client`

Coinbase Advanced Trade WebSocket client.

`CoinbaseWssClient` handles Coinbase-specific connection, subscription
framing, and heartbeat protocol. Message decoding is delegated to
`CoinbaseDecoder` via the `WssDecoder` trait.

Public market data channels (`level2`, `market_trades`) do **not**
require authentication on Coinbase Advanced Trade (beta).

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_connect::sources::coinbase::client`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-connect/latest/atelier_connect/sources/coinbase/client/).

## Structs

| Item | Summary |
| --- | --- |
| [`CoinbaseWssClient`](https://docs.rs/atelier-connect/latest/atelier_connect/sources/coinbase/client/struct.CoinbaseWssClient.html) | Coinbase Advanced Trade WebSocket client. |
