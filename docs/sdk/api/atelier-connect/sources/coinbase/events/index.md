# `atelier_connect::sources::coinbase::events`

Coinbase WebSocket event types.

For Coinbase Advanced Trade (spot), only orderbook and trade channels
are available. Liquidations, funding rates, and open interest require
Coinbase INTX (perpetual futures).

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_connect::sources::coinbase::events`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-connect/0.0.10/atelier_connect/sources/coinbase/events/).

## Enums

| Item | Summary |
| --- | --- |
| [`CoinbaseWssEvent`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/sources/coinbase/events/enum.CoinbaseWssEvent.html) | Events produced by `CoinbaseDecoder` from the Advanced Trade WSS feed. |
