# `atelier_connect::workers::topic_publisher`

Topic-keyed broadcast channels for raw event publishing.
Topic-keyed broadcast channels for raw event publishing.

The `TopicPublisher` is the output interface of the
`DataWorker` (see `super::data_worker::DataWorker`).  Each exchange
subscription maps to exactly one topic, and the `DataWorker`
publishes raw (un-normalised) events through the matching publisher.

# Topic naming convention

```text
{datatype}.{qualifier}.{symbol}
```

Examples:
- `orderbook.50.BTCUSDT`
- `trade.all.BTCUSDT`
- `liquidation.all.BTCUSDT`
- `funding.all.BTCUSDT`
- `open_interest.all.BTCUSDT`

# Back-pressure

The underlying `tokio::sync::broadcast` channel has a bounded
capacity.  If **all** receivers lag behind, the oldest messages are
silently dropped — this is acceptable because the `data_worker`'s
contract is *best-effort ingestion*, not guaranteed delivery.
Guaranteed delivery is the downstream consumer's responsibility.

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_connect::workers::topic_publisher`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-connect/latest/atelier_connect/workers/topic_publisher/).

## Structs

| Item | Summary |
| --- | --- |
| [`TopicMessage`](https://docs.rs/atelier-connect/latest/atelier_connect/workers/topic_publisher/struct.TopicMessage.html) | Envelope wrapping a raw exchange event with ingestion metadata. |
| [`TopicPublisher`](https://docs.rs/atelier-connect/latest/atelier_connect/workers/topic_publisher/struct.TopicPublisher.html) | A single named broadcast channel. |
| [`TopicRegistry`](https://docs.rs/atelier-connect/latest/atelier_connect/workers/topic_publisher/struct.TopicRegistry.html) | Collection of `TopicPublisher`s keyed by topic name. |

## Enums

| Item | Summary |
| --- | --- |
| [`PublishError`](https://docs.rs/atelier-connect/latest/atelier_connect/workers/topic_publisher/enum.PublishError.html) | Error from `TopicRegistry::publish()`. |

## Constants

| Item | Summary |
| --- | --- |
| [`DEFAULT_CHANNEL_CAPACITY`](https://docs.rs/atelier-connect/latest/atelier_connect/workers/topic_publisher/constant.DEFAULT_CHANNEL_CAPACITY.html) | Default broadcast channel capacity per topic. |
