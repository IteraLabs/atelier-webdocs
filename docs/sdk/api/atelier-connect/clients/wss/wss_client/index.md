# `atelier_connect::clients::wss::wss_client`

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_connect::clients::wss::wss_client`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-connect/latest/atelier_connect/clients/wss/wss_client/).

## Structs

| Item | Summary |
| --- | --- |
| [`WssClient`](https://docs.rs/atelier-connect/latest/atelier_connect/clients/wss/wss_client/struct.WssClient.html) | Transport-level WebSocket client that pumps decoded events into an `mpsc` channel. |
| [`WssClientBuilder`](https://docs.rs/atelier-connect/latest/atelier_connect/clients/wss/wss_client/struct.WssClientBuilder.html) | Builder for `WssClient<D>`. |

## Traits

| Item | Summary |
| --- | --- |
| [`WssDecoder`](https://docs.rs/atelier-connect/latest/atelier_connect/clients/wss/wss_client/trait.WssDecoder.html) | Stateless decoder that maps raw WebSocket text frames to typed events. |
