# `atelier_connect::clients::connection_state`

Formal connection state machine for the data worker WSS lifecycle.
Formal connection state machine for the data worker WSS lifecycle.

`ConnectionState` models the discrete phases a WebSocket connection
passes through.  The `ConnectionManager`
drives transitions and emits structured tracing events at each boundary.

# State diagram

```text
┌──────────────┐
│ Disconnected │─────────────────────────────┐
└──────┬───────┘                             │
       │ start()                             │
       ▼                                     │
┌──────────────┐                             │
│  Connecting  │                             │
└──────┬───────┘                             │
       │ ws_stream opened                    │
       ▼                                     │
┌──────────────┐                             │
│Authenticating│  (skipped for public feeds) │
└──────┬───────┘                             │
       │ auth_ack / no-op                    │
       ▼                                     │
┌──────────────┐                             │
│  Subscribing │                             │
└──────┬───────┘                             │
       │ sub_ack / first event               │
       ▼                                     │
┌──────────────┐   disconnect   ┌───────────────┐
│  Streaming   │──────────────▶│  Reconnecting  │
└──────────────┘               └───────┬───────┘
       ▲                               │
       └───────────────────────────────┘
                backoff elapsed
```

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_connect::clients::connection_state`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-connect/latest/atelier_connect/clients/connection_state/).

## Structs

| Item | Summary |
| --- | --- |
| [`StateTransition`](https://docs.rs/atelier-connect/latest/atelier_connect/clients/connection_state/struct.StateTransition.html) | Timestamped record of a single state transition. |

## Enums

| Item | Summary |
| --- | --- |
| [`ConnectionState`](https://docs.rs/atelier-connect/latest/atelier_connect/clients/connection_state/enum.ConnectionState.html) | Discrete connection lifecycle phase. |
