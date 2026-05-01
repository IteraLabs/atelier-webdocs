# `atelier_connect::sources::coinbase::tooling`

Coinbase subscription helpers.

Coinbase Advanced Trade uses a different subscription model from Bybit:
channels and product_ids are specified separately in the subscribe message.
This module helps build the channel list from a `MarketSnapshotConfig`.

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_connect::sources::coinbase::tooling`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-connect/0.0.10/atelier_connect/sources/coinbase/tooling/).

## Functions

| Item | Summary |
| --- | --- |
| [`channels_for_config`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/sources/coinbase/tooling/fn.channels_for_config.html) | Build the list of Coinbase channels to subscribe to based on enabled data types. |
