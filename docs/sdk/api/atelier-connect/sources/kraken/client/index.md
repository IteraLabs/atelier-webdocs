# `atelier_connect::sources::kraken::client`

Kraken WebSocket v2 client.

[`KrakenWssClient`] handles Kraken-specific connection, subscription
framing, and heartbeat handling.  Message decoding is delegated to
[`KrakenDecoder`] via the [`WssDecoder`] trait.

Public market data channels (`book`, `trade`) do **not** require
authentication on Kraken WebSocket v2.

Kraken sends automatic heartbeats (~1/s) so no explicit heartbeat
subscription is needed (unlike Coinbase).

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_connect::sources::kraken::client`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-connect/0.0.10/atelier_connect/sources/kraken/client/).

## Structs

| Item | Summary |
| --- | --- |
| [`KrakenWssClient`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/sources/kraken/client/struct.KrakenWssClient.html) | Kraken WebSocket v2 client. |
