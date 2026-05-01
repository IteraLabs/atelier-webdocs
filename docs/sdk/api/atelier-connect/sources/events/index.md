# `atelier_connect::sources::events`

Unified exchange event wrapper.

`ExchangeEvent` is the single event type that flows through the worker
pipeline. Each exchange decoder produces its own native event type, which
is then wrapped in an `ExchangeEvent` variant before being sent to the
`DataWorker` event loop.

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_connect::sources::events`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-connect/0.0.10/atelier_connect/sources/events/).

## Enums

| Item | Summary |
| --- | --- |
| [`ExchangeEvent`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/sources/events/enum.ExchangeEvent.html) | Exchange-agnostic event wrapper. |
