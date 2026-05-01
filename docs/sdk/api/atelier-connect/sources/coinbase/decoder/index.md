# `atelier_connect::sources::coinbase::decoder`

Coinbase Advanced Trade WSS decoder.

Routes incoming JSON messages by the `"channel"` field to produce
[`CoinbaseWssEvent`] variants.

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_connect::sources::coinbase::decoder`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-connect/0.0.10/atelier_connect/sources/coinbase/decoder/).

## Structs

| Item | Summary |
| --- | --- |
| [`CoinbaseDecoder`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/sources/coinbase/decoder/struct.CoinbaseDecoder.html) | [`WssDecoder`] implementation for the Coinbase Advanced Trade WebSocket API. |
