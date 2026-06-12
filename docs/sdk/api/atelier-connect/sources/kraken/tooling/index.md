# `atelier_connect::sources::kraken::tooling`

Kraken subscription helpers.

Kraken WebSocket v2 uses `{"method": "subscribe", "params": {"channel": ..., "symbol": [...]}}`
for subscription.  This module helps build the channel list from config flags.

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_connect::sources::kraken::tooling`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-connect/latest/atelier_connect/sources/kraken/tooling/).

## Functions

| Item | Summary |
| --- | --- |
| [`channels_for_config`](https://docs.rs/atelier-connect/latest/atelier_connect/sources/kraken/tooling/fn.channels_for_config.html) | Build the list of Kraken channels to subscribe to based on enabled data types. |
