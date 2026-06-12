# `atelier_connect::clients::reconnect`

Policy for reconnecting
Reconnection policy, error classification, and connection health monitoring.

This module provides the building blocks for resilient WebSocket connections:

- `DisconnectReason` — a typed classification of *why* a connection ended,
  derived from WebSocket close frames, transport errors, or application-level
  signals (stale connection, receiver drop).

- `ReconnectPolicy` — a stateful backoff engine with **jittered exponential
  backoff**, a configurable **max-attempts** limit, and a three-state **circuit
  breaker** (`Closed → Open → HalfOpen → Closed`).

- `HealthMonitor` — stale-connection detection based on a per-exchange
  silence timeout.  Designed to slot into a `tokio::select!` loop via its
  `deadline()` method.

# Architecture

Connection ownership is layered:

| Layer | Responsibility |
|-------|---------------|
| `WssClient::run()` | Single connection lifetime; returns a `DisconnectReason` on exit |
| Exchange client (`receive_data`) | Subscription, heartbeat, decode; delegates to `WssClient` |
| `MarketWorker` | Owns a `ReconnectPolicy`; consumes the reason and decides retry / give-up / circuit-open |

# Jitter rationale

Pure exponential backoff (`delay × 2`) causes **thundering-herd** spikes when
many workers disconnect simultaneously (e.g. exchange maintenance window).
Adding uniform random jitter spreads reconnection attempts:

```text
actual_delay = base_delay + rand(0 .. base_delay × jitter_factor)
```

With the default `jitter_factor = 0.5`, a 4 s base delay becomes a uniform
draw from `[4.0, 6.0)` seconds.

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_connect::clients::reconnect`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-connect/latest/atelier_connect/clients/reconnect/).

## Structs

| Item | Summary |
| --- | --- |
| [`HealthMonitor`](https://docs.rs/atelier-connect/latest/atelier_connect/clients/reconnect/struct.HealthMonitor.html) | Stale-connection detector. |
| [`ReconnectPolicy`](https://docs.rs/atelier-connect/latest/atelier_connect/clients/reconnect/struct.ReconnectPolicy.html) | Stateful reconnection policy with jittered exponential backoff and a circuit breaker. |
| [`ReconnectPolicyBuilder`](https://docs.rs/atelier-connect/latest/atelier_connect/clients/reconnect/struct.ReconnectPolicyBuilder.html) | Builder for `ReconnectPolicy`. |

## Enums

| Item | Summary |
| --- | --- |
| [`CircuitState`](https://docs.rs/atelier-connect/latest/atelier_connect/clients/reconnect/enum.CircuitState.html) | The three states of the circuit breaker. |
| [`ReconnectAction`](https://docs.rs/atelier-connect/latest/atelier_connect/clients/reconnect/enum.ReconnectAction.html) | What the caller should do after consulting the `ReconnectPolicy`. |

## Traits

| Item | Summary |
| --- | --- |
| [`ConnectionHealth`](https://docs.rs/atelier-connect/latest/atelier_connect/clients/reconnect/trait.ConnectionHealth.html) | Per-exchange staleness timeout configuration. |
