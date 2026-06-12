# `atelier_connect::workers::pipeline::book_initializer`

Binance orderbook initialisation pipeline stage.

`BookInitializer` intercepts orderbook events from the WSS stream,
buffers them while fetching a REST depth snapshot, reconciles the
two according to Binance's documented protocol, and then forwards
a synthesised snapshot followed by validated deltas.

Trade events are forwarded immediately regardless of book state.

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_connect::workers::pipeline::book_initializer`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-connect/latest/atelier_connect/workers/pipeline/book_initializer/).

## Structs

| Item | Summary |
| --- | --- |
| [`BookInitializer`](https://docs.rs/atelier-connect/latest/atelier_connect/workers/pipeline/book_initializer/struct.BookInitializer.html) | Pipeline stage that coordinates REST snapshot + WSS delta reconciliation for Binance orderbooks. |
