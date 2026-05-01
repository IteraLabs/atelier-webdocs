# `atelier_connect::sources::bybit::client`

Bybit-specific WebSocket client.

[`BybitWssClient`] is a thin, exchange-aware wrapper that handles
Bybit's connection, subscription framing, heartbeat protocol, and
delegates all message decoding to [`BybitDecoder`] via the [`WssDecoder`]
trait.

This is the single entry point for Bybit WSS I/O. All other code
(workers, examples) should use this client — never raw `WssClient<D>`.

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_connect::sources::bybit::client`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-connect/0.0.10/atelier_connect/sources/bybit/client/).

## Structs

| Item | Summary |
| --- | --- |
| [`BybitWssClient`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/sources/bybit/client/struct.BybitWssClient.html) | Bybit WebSocket client. |
