# `atelier_connect::workers::registry`

Worker registry for fleet-level state aggregation and control.
Worker registry for fleet-level state aggregation and control.

The `WorkerRegistry` is the single source of truth for "which workers
exist, what state are they in, and how do I talk to them."  It backs the
Data Collector Workers sidebar in the dashboard.

# Architecture

```text
                     ┌──────────────┐
                     │   Registry   │
                     │ DashMap<id,  │
                     │  WorkerHandle│
                     └──────┬───────┘
                            │
           ┌────────────────┼────────────────┐
           ▼                ▼                 ▼
    ┌─────────────┐ ┌─────────────┐   ┌─────────────┐
    │ WorkerHandle│ │ WorkerHandle│   │ WorkerHandle│
    │  cmd_tx ────│ │  cmd_tx ────│   │  cmd_tx ────│
    │  status ◄───│ │  status ◄───│   │  status ◄───│
    └─────────────┘ └─────────────┘   └─────────────┘
           │                │                 │
           ▼                ▼                 ▼
       DataWorker      MarketWorker      DataWorker
```

Each worker holds the receiving end of a command channel and periodically
publishes its `WorkerStatus` through a `watch` channel.  The registry
owns the sending halves and the `watch` receivers.

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_connect::workers::registry`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/registry/).

## Structs

| Item | Summary |
| --- | --- |
| [`RegistryCounts`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/registry/struct.RegistryCounts.html) | Summary counts for the dashboard's filter tabs: ALL / LIVE / ERR / PAUSED. |
| [`WorkerChannels`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/registry/struct.WorkerChannels.html) | Channel halves that the worker keeps to receive commands and publish status. |
| [`WorkerHandle`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/registry/struct.WorkerHandle.html) | Control surface for a single registered worker. |
| [`WorkerRegistry`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/registry/struct.WorkerRegistry.html) | Central registry of all active workers. |
| [`WorkerStatus`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/registry/struct.WorkerStatus.html) | Snapshot of a worker's current state, designed to be rendered directly by the dashboard sidebar. |

## Enums

| Item | Summary |
| --- | --- |
| [`WorkerCommand`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/registry/enum.WorkerCommand.html) | Commands that can be sent to a running worker via the registry. |
