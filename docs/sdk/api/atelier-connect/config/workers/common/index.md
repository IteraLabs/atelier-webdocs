# `atelier_connect::config::workers::common`

Shared configuration types for all worker variants.

`CommonWorkerFields` captures the configuration knobs that every worker
needs regardless of whether it synchronises events or not.

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_connect::config::workers::common`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-connect/latest/atelier_connect/config/workers/common/).

## Structs

| Item | Summary |
| --- | --- |
| [`CommonWorkerFields`](https://docs.rs/atelier-connect/latest/atelier_connect/config/workers/common/struct.CommonWorkerFields.html) | Configuration fields shared by both `DataWorker` and `MarketWorker`. |
| [`ManifestMetadata`](https://docs.rs/atelier-connect/latest/atelier_connect/config/workers/common/struct.ManifestMetadata.html) | Identity metadata injected into a manifest received over the wire (via the Gateway's `CommandChannel`). |
| [`ReconnectSection`](https://docs.rs/atelier-connect/latest/atelier_connect/config/workers/common/struct.ReconnectSection.html) | TOML-exposed reconnection knobs. |

## Enums

| Item | Summary |
| --- | --- |
| [`OutputSinkConfig`](https://docs.rs/atelier-connect/latest/atelier_connect/config/workers/common/enum.OutputSinkConfig.html) | Describes a single output sink, deserializable from TOML. |
