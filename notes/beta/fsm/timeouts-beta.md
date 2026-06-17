# FSM Atlas v0.1-beta-2 - Timeout / Config Catalog

The single catalog of time-bounded decisions and configurable tunables referenced by the FSM Atlas. Each entry names the reader (FSM transition or invariant), the default, and the rationale.

**Units.** All durations are in milliseconds unless otherwise stated.

**Overrides.** Every value is a default. An org- or Session-scoped override may replace a default. Overrides live in `SessionEnvelope.config` (org overrides baked at Session creation) or in service runtime config (platform-side).

**Authority.** Defaults in this document are the SSoT. Any other doc in the Atlas that cites a default must link here; changes happen here first.

---

## §T.1 Transport

### `gateway.handshake_timeout_ms` - **2000** (2s)
- **Reader**: CH-T1 (Opening -> Open) handshake watcher.
- **Why**: Short enough to surface misconfigured clients quickly; long enough for a cold gRPC connection through a cluster network.
- **Side effect on expiry**: `CHANNEL_OPEN_FAILED` (61); no Channel row lands.

### `gateway.command_ack_window_ms` - **5000** (5s)
- **Reader**: Command timeout watcher (raises `DISPATCH_TIMEOUT` (44)).
- **Why**: Commands are idempotent at the dispatcher via `command_id`; an occasional retry is cheap. 5s accommodates slow FSM transitions under load.
- **Side effect on expiry**: issuer receives `DISPATCH_TIMEOUT`; re-read the target to decide whether to retry.

### `gateway.channel_idle_timeout_ms` - **60000** (60s)
- **Reader**: Channel keepalive enforcement (deferred CH-T3 Draining decision).
- **Why**: Longer than the longest heartbeat window; protects against idle connections hanging on Gateway resources.
- **v0.1-beta-2 scope**: Gateway may close idle channels via GW-T5; the resulting cascade is spec'd later.

---

## §T.2 Agent lifecycle

### `agent.registration_window_ms` - **30000** (30s)
- **Reader**: A-T17 Registering -> Terminated (registration window expiry).
- **Why**: An Agent that registers and never reaches Ready is broken or was terminated client-side; 30s allows a well-behaved SDK to complete Skill advertisement.
- **Side effect on expiry**: A-T17 fires; `terminated_reason = 'registration_expired'`; `REGISTRATION_EXPIRED` (21).

### `agent.heartbeat_interval_ms` - **5000** (5s)
- **Reader**: Heartbeat producer (SDK); Heartbeat consumer (Gateway -> Overseer).
- **Why**: Responsive liveness without flooding TelemetryChannel. At 5s, the lost detector fires at 3 missed beats = 15s.

### `agent.heartbeat_miss_threshold_ms` - **15000** (15s = 3× interval)
- **Reader**: A-T11 (Ready/Bound -> Lost) guard.
- **Why**: "Three missed beats" posture. Conservative enough that a single network blip does not flap Agents.
- **Side effect on expiry**: A-T11 fires; Overseer may cascade Binding drain (B-T4) and, on grace expiry, A-T15 terminate.

### `agent.drain_budget_ms` - **60000** (60s)
- **Reader**: A-T7 (Draining -> Terminated) transition.
- **Why**: Drain should finish outstanding Tasks. 60s is the default ceiling; longer Tasks should use explicit cancellation.
- **Side effect on expiry**: A-T7 forced terminate; `terminated_reason = 'drain_timeout'`.

### `agent.reconnect_grace_ms` - **60000** (60s) / `agent.reconnect_grace_draining_ms` - **120000** (120s)
- **Reader**: A-T11 / A-T12 start the reconciliation grace timer on entry to `Lost`; A-T15 (`Lost -> Terminated`) fires on expiry; A-T14 (`Lost -> {Ready,Bound,Draining,Restarting}`) clears it on reconnection. SEQ-4 Crash Recovery reads the same window when reconciling a `Lost` Agent at boot.
- **Why**: The window an Agent may stay `Lost` (transport dropped, heartbeat missed past `agent.heartbeat_miss_threshold_ms`) before its Bindings are force-released. 60s from {`Ready`, `Bound`} (A-T11) covers a process relaunch / network blip without holding ComputeSlots indefinitely; 120s from `Draining` (A-T12) is longer because in-flight Tasks are still settling and a premature terminate would discard partially-drained work. From `Restarting` (A-T13) the per-Task `task.stop_drain_timeout_ms` is repurposed as the grace window - no separate timer (per `agent-beta.md §2.1.5` IR-AO4 / note on A-T13).
- **Side effect on expiry**: A-T15 fires; `terminated_reason = 'reconnect_grace_timeout'`; IR-AB4 force-releases all non-Released Bindings with `release_reason = 'agent_lost'`; any Channel still in `draining`/`open` for the Agent's Bindings is force-closed to `failed` (CH-T10).

---

## §T.3 Session lifecycle

### `session.default_ttl_ms` - **3_600_000** (60 min)
- **Reader**: SN-T1 Session creation (`ttl_at = issued_at + default_ttl`).
- **Why**: Typical research session scale. Overridable per Session.

### `session.expiry_warning_window_ms` - **300_000** (5 min)
- **Reader**: SN-T3 (Active -> Expiring).
- **Why**: Gives the SDK time to call SN-T5 Renew or cleanly checkpoint.

### `session.renew_window_max_ms` - **600_000** (10 min)
- **Reader**: SN-T5 Renew guard.
- **Why**: Upper bound on how far `ttl_at` may be pushed in a single renewal. Prevents a bug from zombifying a Session.
- **Side effect on violation**: `QUOTA_DENIED` (11) or a dedicated rejection.

### `session.expired_sweep_interval_ms` - **60000** (60s)
- **Reader**: Session TTL sweeper - background worker that fires SN-T3 and SN-T4.
- **Why**: Granularity of the timer; finer than `expiry_warning_window_ms` so the warning fires on the correct tick.

---

## §T.4 Service / Deploy

### `service.deploy_dispatch_timeout_ms` - **10000** (10s)
- **Reader**: SV-T2 Deploy Manifest dispatch to Agent (ManifestAck watch).
- **Why**: RemoteAgent may take longer than the generic 5s Command ack to process a large Manifest.
- **Side effect on expiry**: SV-T2 falls back to Stopped with `stopped_reason = 'dispatch_timeout'`.

### `service.spawn_budget_ms` - **30000** (30s)
- **Reader**: SV-T2 PlatformAgent spawn watcher.
- **Why**: Budget for process launch + Skill advertisement + Workspace attach.
- **Side effect on expiry**: SV-T2 -> Stopped with `stopped_reason = 'spawn_failed'`; `SPAWN_FAILED` (52) on internal bus.

### `service.stop_drain_budget_ms` - **120_000** (2 min)
- **Reader**: SV-T6 (Active -> Stopping) drain watcher.
- **Why**: Generous enough to finish in-flight Tasks without forcing. Explicit force-stop bypasses this.

---

## §T.5 Binding / Task

### `binding.pending_ack_ms` - **5000** (5s)
- **Reader**: B-T1 -> B-T3 watcher (Binding Pending -> Active).
- **Why**: Same as generic Command ack. Binding activation should be nearly immediate once Channels are Open.

### `binding.pending_grace_ms` - **60000** (60s)
- **Reader**: B-T2 (Pending -> Released) live grace ticker (`overseer-beta.md §1.7`).
- **Why**: BYO-infra path. After SEQ-1 Phase A returns (`gateway_url`, `token`) to the researcher (`sequences-beta.md §3.1.1`), the Binding sits at `pending` until the researcher's RemoteAgent connects and Gateway forwards Registration to fire A-T1 / A-T2 / A-T3. 60s allows realistic human-driven `docker run` lead time without holding a ComputeSlot reservation indefinitely. Boot reconciler (`overseer-beta.md §1.7` Step 1) handles the post-restart sweep; this tunable governs steady-state.
- **Side effect on expiry**: B-T2 fires; `release_reason = 'registration_grace_timeout'`; ComputeSlot reservation released (reset to Vacant).

### `binding.drain_budget_ms` - **60000** (60s)
- **Reader**: B-T4 (Active -> Draining) watcher.
- **Why**: Drain should finish Tasks or the Binding releases forcibly (B-T5).

### `task.stop_drain_timeout_ms` - **60000** (60s)
- **Reader**: T-T8 (Stopping) drain watcher AND A-T8 / T-T12 soft-Restart completion watcher - the single bound on both a Task's Stop-drain and its Restart re-initialization. This is the taxonomy's `stop_drain_timeout` (`agent-beta.md` INV-A6, `task-beta.md` INV-T8); Restart shares it rather than carrying a separate budget.
- **Why**: A Task draining on Stop, or re-initializing in place on Restart, must finish within one bound. 60s covers a final Artifact flush or an in-process re-init that reloads from the persistent workspace.
- **Side effect on expiry**: T-T10 (Stopping -> Failed, `reason=drain_timeout`, Ack `PARTIAL`) on the Stop path; T-T14 (Restarting -> Failed, `reason=restart_failed`) on the Restart path; in-flight Artifacts are marked `partial`.

### `task.accept_ack_ms` - **5000** (5s)
- **Reader**: T-T1 (Pending -> Accepted) watcher.
- **Why**: Agent should accept or reject immediately after Binding is Active.

### `task.pause_resume_ack_ms` - **5000** (5s)
- **Reader**: T-T4 / T-T5 (Running -> Paused / Paused -> Running) watchers.
- **Why**: Symmetric with pause/resume Commands.

### `task.complete_ack_ms` - **10000** (10s)
- **Reader**: T-T9 (Stopping -> Completed) watcher.
- **Why**: Slightly higher to accommodate final artifact flushes to Sinks.

---

## §T.6 Sink / Channel provisioning

### `sink.open_budget_ms` - **5000** (5s)
- **Reader**: SK-T1 -> SK-T2 (Idle -> Ready) watcher.
- **Why**: Sink handshake (credential probe, schema negotiation) should be fast; auth / target missing fails out.
- **Side effect on expiry**: `SINK_OPEN_FAILED` (62).

### `channel.open_budget_ms` - **2000** (2s)
- **Reader**: CH-T1 -> CH-T2 watcher.
- **Why**: Duplicate of `gateway.handshake_timeout_ms`; referenced from the Channel FSM side.

---

## §T.7 Overseer recovery

### `overseer.reconcile_stage1_budget_ms` - **30000** (30s)
- **Reader**: Overseer Recovery Stage 1 (§1.7).
- **Why**: Stage 1 re-probes Channels and Bindings. Should complete quickly post-restart.
- **Side effect on expiry**: Overseer stays in `degraded`; subsystem-loss flags remain raised.

### `overseer.reconcile_stage2_budget_ms` - **120_000** (2 min)
- **Reader**: Overseer Recovery Stage 2 - orphan Agent sweep, Binding cleanup.
- **Why**: Tolerates a large Session with many Agents.

### `overseer.degraded_refresh_ms` - **5000** (5s)
- **Reader**: subsystem-probe loop in `degraded` state.
- **Why**: Fast enough to catch recovery; slow enough to avoid hammering a flapping subsystem.

### `overseer.retry_after_secs` - **5** (5s)
- **Reader**: Overseer `GET /health/ready` response while `Draining` (§1.2.1) — the `Retry-After` header value.
- **Why**: Matches `degraded_refresh_ms` — the soonest the state could next change, so a client poll loop backs off exactly one probe cycle. v0.1-beta-2 ships this as a fixed constant in the readiness handler (`RETRY_AFTER_SECS`); env-tunable-ization is deferred.

### `overseer.event_flush_ms` - **100** (100ms)
- **Reader**: Event bus batcher.
- **Why**: Caps event emission latency; ~100ms is imperceptible to observability consumers while amortizing writes.

---

## §T.8 Config surface

Keys live in a single namespaced config table, structurally:

```
atelier.timeouts.<section>.<key>
```

Examples:

```
atelier.timeouts.transport.gateway.handshake_timeout_ms = 2000
atelier.timeouts.agent.heartbeat_interval_ms             = 5000
atelier.timeouts.session.default_ttl_ms                  = 3_600_000
```

Resolution order (SDK, Overseer, Gateway share the same client):

1. `SessionEnvelope.config` overrides (per-Session)
2. Org-level overrides (per-tenant)
3. Build-time defaults (from this document)

Missing keys resolve to the default; an unknown override key logs a warning and is ignored.

---

## §T.9 Governance

- **Changing a default.** Edit this document and any Rust `const` that references it. A CI check verifies no other doc in the Atlas cites a hard-coded millisecond value for a timer named here.
- **Adding a timer.** Add an entry with Reader, Why, Side effect, and reference the FSM transition or invariant that reads it. Add a Rust `const` in the appropriate crate.
- **Removing a timer.** Only if no FSM transition or invariant refers to it and no production config override targets it. A version bump is required.

---

## §T.10 Cross-reference summary

| Timer | Default | Used by |
|---|---|---|
| `gateway.handshake_timeout_ms` | 2000 | CH-T1 |
| `gateway.command_ack_window_ms` | 5000 | Command dispatcher |
| `gateway.channel_idle_timeout_ms` | 60000 | deferred GW-T5 path |
| `agent.registration_window_ms` | 30000 | A-T17 |
| `agent.heartbeat_interval_ms` | 5000 | Heartbeat producer |
| `agent.heartbeat_miss_threshold_ms` | 15000 | A-T11 |
| `agent.drain_budget_ms` | 60000 | A-T7 |
| `agent.reconnect_grace_ms` | 60000 | A-T11 start / A-T15 expiry |
| `agent.reconnect_grace_draining_ms` | 120000 | A-T12 start / A-T15 expiry |
| `session.default_ttl_ms` | 3_600_000 | SN-T1 |
| `session.expiry_warning_window_ms` | 300_000 | SN-T3 |
| `session.renew_window_max_ms` | 600_000 | SN-T5 guard |
| `session.expired_sweep_interval_ms` | 60000 | Session TTL sweeper |
| `service.deploy_dispatch_timeout_ms` | 10000 | SV-T2 |
| `service.spawn_budget_ms` | 30000 | SV-T2 PlatformAgent |
| `service.stop_drain_budget_ms` | 120_000 | SV-T6 |
| `binding.pending_ack_ms` | 5000 | B-T3 |
| `binding.pending_grace_ms` | 60000 | B-T2 |
| `binding.drain_budget_ms` | 60000 | B-T4 |
| `task.accept_ack_ms` | 5000 | T-T1 |
| `task.pause_resume_ack_ms` | 5000 | T-T4 / T-T5 |
| `task.complete_ack_ms` | 10000 | T-T9 |
| `task.stop_drain_timeout_ms` | 60000 | T-T8 / T-T10, A-T8 |
| `sink.open_budget_ms` | 5000 | SK-T1 -> SK-T2 |
| `channel.open_budget_ms` | 2000 | CH-T1 -> CH-T2 |
| `overseer.reconcile_stage1_budget_ms` | 30000 | Recovery Stage 1 |
| `overseer.reconcile_stage2_budget_ms` | 120_000 | Recovery Stage 2 |
| `overseer.degraded_refresh_ms` | 5000 | subsystem probe |
| `overseer.retry_after_secs` | 5 | /health/ready Draining `Retry-After` |
| `overseer.event_flush_ms` | 100 | Event batcher |

---

## Sources

- [overseer-beta.md - §1.6 IR-O1..O6, §1.7 Recovery](overseer-beta.md)
- [agent-beta.md - §2.1 Agent](agent-beta.md)
- [task-beta.md - §2.2 Task](task-beta.md)
- [binding-beta.md - §2.3 Binding](binding-beta.md)
- [service-beta.md - §2.5 Service](service-beta.md)
- [session-beta.md - §2.7 Session](session-beta.md)
- [gateway-beta.md - §2.9 Gateway](gateway-beta.md)
- [channel-beta.md - §2.10 Channel](channel-beta.md)
- [sink-beta.md - §2.11 Sink](sink-beta.md)
- [proto-catalog-beta.md - Ack / timeout-related messages](proto-catalog-beta.md)
