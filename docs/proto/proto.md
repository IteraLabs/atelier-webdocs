# Atelier Wire Protocol

`atelier-proto` is the gRPC / Protocol Buffers contract spoken between a remote
**agent**, the **gateway**, and the **overseer** control plane. It defines
message shapes and a single service. It carries no business logic and no data —
artifact payloads are opaque bytes described by an out-of-band schema reference.

Package: `atelier.v1beta1`.

## Service and channels

A single `Gateway` service exposes three RPCs:

| RPC | Shape | Carries |
| --- | --- | --- |
| `CommandChannel` | bidirectional stream of `Envelope` | `Registration` (first frame), then `Manifest` / `Command` and their acks; downstream `Command`s from the platform |
| `TelemetryChannel` | client stream of `Envelope` returning `Ack` | `Heartbeat`, `AgentStatus`, `TaskTelemetry`, `ArtifactFrame` |
| `EventSubscribe` | `EventSubscribeRequest` returning a server stream of `Envelope` | session-scoped lifecycle `Event`s |

Every cross-boundary message is wrapped in an **`Envelope`** carrying per-frame
metadata — `envelope_id`, `session_id`, `sender_id`, a per-(channel, sender)
monotonic `sequence`, and `restart_epoch` — plus exactly one typed `payload`.

## Handshake

1. The agent opens `CommandChannel` and sends **`Registration`** (`agent_alias`,
   `agent_type`, `skills`, an opaque `host_identity`, and `target_session_id`).
2. The gateway replies with **`RegistrationResponse.Accepted`**, allocating the
   `agent_id` and binding the `session_id`.

`AgentType` is `REMOTE` or `PLATFORM`. `Skill` is a closed set: `INGEST`, `SYNC`,
`TRANSFORM`, `EMIT`, `REPORT`.

## Work: manifests and tasks

- **`Manifest`** describes the work a binding runs: a set of `TaskSpec` (each a
  `Skill` plus opaque `params`, `datatypes`, and `sink_ids`) and
  `SinkAssignment`s (`SinkType` is `OBJECT`, `DB`, or `TERMINAL`). It is delivered
  exactly-once via `idempotency_key`.
- **`ManifestAck.Accepted`** returns the overseer-allocated `binding_id` and, per
  task, the platform `task_id` the agent uses thereafter.

## Commands

**`Command`** is a single control verb against exactly one target (`Session`,
`Service`, `Agent`, `Binding`, or `Task`), delivered at-least-once and acked by
`command_id` via **`CommandAck`**. `CommandKind` covers the session, service,
agent, binding, and task verbs — for example `TASK_START`, `TASK_PAUSE`,
`BINDING_RELEASE`, `AGENT_DRAIN`, `SERVICE_DEPLOY`.

## Telemetry

Upstream on `TelemetryChannel`, best-effort with sequence:

- **`Heartbeat`** — liveness and current phase.
- **`AgentStatus`** — a phase snapshot plus the bindings and tasks the agent
  holds. `Phase`: `REGISTERED`, `READY`, `BOUND`, `RESTARTING`, `LOST`,
  `DRAINING`, `TERMINATED`.
- **`TaskTelemetry`** — a batch of `TaskProgress` (`task_id`, `TaskPhase`,
  artifact counters, opaque `metrics`). `TaskPhase`: `SUBMITTED`, `ACCEPTED`,
  `RUNNING`, `PAUSING`, `PAUSED`, `RESUMING`, `COMPLETING`, `COMPLETED`, `FAILED`,
  `CANCELED`.

## Artifacts

- **`ArtifactFrame`** — agent-emitted output. `ArtifactKind` is `DATA`, `LOGS`, or
  `MODEL`. The `payload` is opaque bytes (Parquet, Arrow IPC, JSON, or log lines)
  named by `payload_schema_ref`. `ArtifactLineage` (artifact and task ids,
  `restart_epoch`, a monotone `sequence`) is a first-class submessage so consumers
  can join on lineage without decoding the payload.
- **`ManifestArtifactFrame`** — platform-emitted archive of a manifest body for
  audit and reproducibility.
- **`TerminalEvent`** — a lightweight topic notification for the live data/logs
  feed.

## Lifecycle events

`EventSubscribe` streams **`Event`**s, one variant per boundary-crossing state
transition, scoped to the subscriber's session. The variant families and their
states:

| Family | States |
| --- | --- |
| Agent | registered, ready, bound, restarting, lost, draining, terminated |
| Task | accepted, running, paused, resumed, completed, failed, canceled, restarted |
| Binding | created, active, draining, releasing, released |
| Service | provisioning, deploying, active, stopping, stopped, archived |
| Session | created, active, renewed, expiring, expired, closed |
| ComputeSlot | reserved, occupied, releasing, vacant, retired |
| Gateway | ready, degraded, stopping, stopped |
| Overseer | ready, degraded, recovered, draining |
| Channel / Sink | opening, open / idle, ready |

`EventSubscribeRequest` may filter to specific transitions; its `session_id` must
match the authenticated session.

## Errors

**`Error`** carries an `ErrorKind` — a stable, cross-cutting catalog spanning
auth/identity, envelope/quota, registration, manifest, command/target,
binding/task, transport, and subsystem-degradation classes — together with a
human-readable `message`, a `correlation_id`, and retry hints (`retryable`,
`retry_after_ms`).

## Reliability summary

| Channel | Delivery |
| --- | --- |
| CommandChannel — `Command` | at-least-once, ack by `command_id` |
| CommandChannel — `Manifest` | exactly-once via `idempotency_key` |
| TelemetryChannel | best-effort, per-sender `sequence` |
| EventSubscribe | session-scoped, filterable by transition |

`restart_epoch` is echoed on agent-originated frames so consumers can fence stale
work across agent restarts.
