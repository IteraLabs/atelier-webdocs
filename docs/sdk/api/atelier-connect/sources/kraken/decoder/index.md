# `atelier_connect::sources::kraken::decoder`

Kraken WebSocket v2 decoder.

Routes incoming JSON messages by the `"channel"` field to produce
[`KrakenWssEvent`] variants.  Heartbeats and subscription
confirmations are silently consumed.

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_connect::sources::kraken::decoder`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-connect/0.0.10/atelier_connect/sources/kraken/decoder/).

## Structs

| Item | Summary |
| --- | --- |
| [`KrakenDecoder`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/sources/kraken/decoder/struct.KrakenDecoder.html) | [`WssDecoder`] implementation for the Kraken WebSocket v2 API. |
