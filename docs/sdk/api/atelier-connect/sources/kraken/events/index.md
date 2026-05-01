# `atelier_connect::sources::kraken::events`

Kraken WebSocket v2 event types.

For Kraken spot, the public `book` and `trade` channels are available
without authentication.  Liquidations, funding rates, and open interest
are only available on Kraken Futures (separate endpoint + auth model).

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_connect::sources::kraken::events`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-connect/0.0.10/atelier_connect/sources/kraken/events/).

## Enums

| Item | Summary |
| --- | --- |
| [`KrakenWssEvent`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/sources/kraken/events/enum.KrakenWssEvent.html) | Events produced by `KrakenDecoder` from the WebSocket v2 feed. |
