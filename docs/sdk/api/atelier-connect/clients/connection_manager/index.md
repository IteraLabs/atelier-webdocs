# `atelier_connect::clients::connection_manager`

Connection lifecycle manager with state tracking and reconnection.
Connection lifecycle manager with state tracking and reconnection.

`ConnectionManager` is a lightweight state-machine wrapper that sits
between the `DataWorker` and
the exchange-specific WSS clients.  It does **not** own the WebSocket
connection itself — instead, it:

1. Tracks the current `ConnectionState` and logs every transition with
   a timestamp and reason via structured `tracing` events.
2. Delegates reconnection decisions to `ReconnectPolicy` (jittered
   exponential backoff + circuit breaker).
3. Exposes a small diagnostic API (`state()`, `transitions()`,
   `consecutive_failures()`) for health reporting.

# Usage

The caller (typically `DataWorker`)
drives the state machine by calling `transition()` at each lifecycle
boundary:

```rust,ignore
manager.transition(ConnectionState::Connecting, "initial connect");
// … spawn exchange client …
manager.transition(ConnectionState::Subscribing, "client spawned");
// … first event arrives …
manager.transition(ConnectionState::Streaming, "first event received");
// … channel closes …
let action = manager.on_disconnect(&reason);
```

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_connect::clients::connection_manager`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-connect/0.0.10/atelier_connect/clients/connection_manager/).

## Structs

| Item | Summary |
| --- | --- |
| [`ConnectionManager`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/clients/connection_manager/struct.ConnectionManager.html) | Stateful connection lifecycle manager. |
| [`ConnectionManagerConfig`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/clients/connection_manager/struct.ConnectionManagerConfig.html) | Configuration for building a `ConnectionManager`. |
