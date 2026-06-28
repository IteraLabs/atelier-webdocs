# FSM Atlas v0.1-beta-2 - Error Catalog

Semantic dispatch guide for the `ErrorKind` enum declared in `proto-catalog-beta.md §common.proto`. Every error kind raised on the wire or on the internal bus is listed here with:

- **Raised by**: which FSM transition (or subsystem) produces it
- **Raised at**: the transition boundary where the error lands
- **Observed by**: the peer or internal consumer that must handle it
- **Semantics**: what it means and what the receiver should do
- **Retryable**: `yes` (client may retry without change) / `after-mutate` (retry only after the inputs are corrected) / `no` (terminal)

The `Error.retryable` and `Error.retry_after_ms` fields on the wire are **advisory**. The authoritative retry semantics are in the table below. Senders MAY fill advisory hints consistent with this table; receivers SHOULD NOT rely on them as a contract.

All errors carry `correlation_id` set to the `envelope_id` of the offending request where applicable.

**Scope: `ErrorKind` vs. `TaskRejectionReason`.** This catalog enumerates `ErrorKind` only - the wire-level, cross-cutting error enum declared in `proto-catalog-beta.md §common.proto` and carried by the `Error` message on every boundary (`CommandAck.rejected`, `ManifestAck.rejected`, `RegistrationResponse.rejected`, and the `Error` variant of the Envelope `payload` oneof). Distinct from `ErrorKind` is **`TaskRejectionReason`** (`proto-catalog-beta.md §control.proto`, declared adjacent to `ManifestAck`) - a narrow, Task-FSM-local catalog naming *why a single Task was rejected* during ManifestAck dispatch, with members `TASK_REJECTION_SKILL_MISMATCH`, `TASK_REJECTION_SPEC_INVALID`, `TASK_REJECTION_INTERNAL_ERROR`, and `TASK_REJECTION_PEER_REJECTED` (the last dormant under the v0.1-beta-2 single-Task Manifest restriction per taxonomy §Tasks / beta scope and `binding-beta.md §2.3.2 B-T1`). The first three overlap semantically with `ErrorKind` values of the same base name (`SKILL_MISMATCH = 31`, `SPEC_INVALID = 32`, `INTERNAL = 90`) but live in a separate enum so that the multi-Task (later) `ManifestAck` shape can carry per-Task rejection reasons without bloating `ErrorKind` with Task-local variants. `TaskRejectionReason` is **not** listed in §E.1-§E.10 below; it is documented at its declaration site in `proto-catalog-beta.md` and cross-referenced from `task-beta.md §2.2.2 T-T2`, `binding-beta.md §2.3.2 B-T10`, and `binding-beta.md §2.3.4 IR-BT2`.

---

## §E.1 Auth / identity

### `UNAUTHENTICATED` (1)
- **Raised by**: Gateway (registration handshake, `session_id` check on post-Registration Envelopes).
- **Raised at**: Gateway boundary, before any FSM transition fires.
- **Observed by**: Remote SDK.
- **Semantics**: Missing, malformed, or rejected auth claims. Includes missing `session_id` on non-Registration Envelopes (INV-P2).
- **Retryable**: `after-mutate` - re-authenticate and reconnect.

### `SESSION_EXPIRED` (2)
- **Raised by**: SN-T4 (Session Expiring -> Expired) fan-out; also raised when a post-SN-T4 Envelope lands on the Gateway.
- **Raised at**: any FSM transition that reads the Session row and finds `status = 'expired'`.
- **Observed by**: SDK, Overseer consumers.
- **Semantics**: Session TTL elapsed. All dependent Services have been stopped by cascade. Agents should treat this as terminal and rely on the SDK renewal flow (SN-T5) at a higher layer.
- **Retryable**: `no` in the current Session. `after-mutate` after a new Session is issued.

### `SESSION_REVOKED` (3)
- **Raised by**: SN-T6 (emergency close).
- **Raised at**: Session row transitions to Expired with `expire_reason IN ('auth_revoked', 'compliance_kill', 'plan_revoked')`.
- **Observed by**: SDK, Overseer cascades.
- **Semantics**: An external authority revoked the Session mid-flight. Treat as `SESSION_EXPIRED` but with no renewal path.
- **Retryable**: `no`.

### `PLAN_REVOKED` (4)
- **Raised by**: plan-service callback -> Overseer reconciliation.
- **Raised at**: A-T15 (forced terminate), SN-T6 (`expire_reason = 'plan_revoked'`).
- **Observed by**: SDK, Overseer.
- **Semantics**: The Session's parent Plan was revoked. Entire Session is torn down.
- **Retryable**: `no`.

---

## §E.2 Envelope / quota

### `ENVELOPE_EXCEEDED` (10)
- **Raised by**: IR-O4 atomicity check at SV-T1 (Service Provisioning), A-T1 (Agent Register), or any envelope-consuming transition.
- **Raised at**: FSM driver transaction - `SELECT ... FOR UPDATE` on `sessions` row detects the addition would exceed `envelope`.
- **Observed by**: SDK or Overseer-originated command issuer.
- **Semantics**: The Session envelope has no room for this addition. The proposed child row is not created.
- **Retryable**: `after-mutate` - wait for an existing consumer to release (Service Stopped, Agent Terminated) or renew the envelope.

### `QUOTA_DENIED` (11)
- **Raised by**: platform-level quota subsystem (distinct from Session envelope).
- **Raised at**: Gateway / Overseer admission path.
- **Observed by**: SDK.
- **Semantics**: Platform-scoped rate or burst quota exceeded.
- **Retryable**: `yes` with backoff.

---

## §E.3 Agent / registration

### `REGISTRATION_INVALID` (20)
- **Raised by**: A-T1 guard failure.
- **Raised at**: Registration parse / validation, before any row lands.
- **Observed by**: SDK.
- **Semantics**: `Registration.skills` lists an unknown Skill, `agent_type` is `UNSPECIFIED`, or `host_identity` fails validation.
- **Retryable**: `after-mutate` - correct the Registration body.

### `REGISTRATION_EXPIRED` (21)
- **Raised by**: Overseer reconciliation (Stage 2) or registration TTL sweep.
- **Raised at**: A-T17 (Registering -> Terminated, registration window expiry).
- **Observed by**: SDK.
- **Semantics**: Registration was never promoted to Ready within the registration window.
- **Retryable**: `after-mutate` - re-register.

### `AGENT_NOT_FOUND` (22)
- **Raised by**: Command dispatch.
- **Raised at**: Command target resolution pre-transition.
- **Observed by**: Command issuer.
- **Semantics**: `AgentTarget.agent_id` does not resolve in the current Session.
- **Retryable**: `no`.

### `AGENT_LOST` (23)
- **Raised by**: A-T11 (Ready/Bound -> Lost), commands dispatched after A-T11.
- **Raised at**: heartbeat-gap detector fires A-T11; later Commands reject.
- **Observed by**: SDK, Binding FSM driver (B-T4 drain decision).
- **Semantics**: Agent missed the heartbeat deadline. See §2.1.5 for restart reconcile.
- **Retryable**: `after-mutate` after A-T8 Restart completes or A-T9/A-T10 terminates.

### `DUPLICATE_AGENT_ID` (24)
- **Raised by**: A-T1 guard - `agent_id` uniqueness.
- **Raised at**: Registration admission.
- **Observed by**: SDK.
- **Semantics**: UUIDv4 collision (should not occur) or SDK-replay of a successful Registration.
- **Retryable**: `no` - returns the already-registered Agent row for idempotency.

---

## §E.4 Manifest

### `MANIFEST_REJECTED` (30)
- **Raised by**: B-T10 (Manifest rejection cascade) - Agent ManifestAck rejected.
- **Raised at**: Binding Pending -> Releasing (B-T10) on Agent self-rejection.
- **Observed by**: SDK.
- **Semantics**: Umbrella rejection. Usually specialized into `SKILL_MISMATCH` or `SPEC_INVALID`.
- **Retryable**: `after-mutate`.

### `SKILL_MISMATCH` (31)
- **Raised by**: A-T2 guard (Agent skill-subset check) or B-T10 (Agent ManifestAck self-rejection) - Agent's declared Skills do not cover the Manifest's Task requirements.
- **Raised at**: A-T2 (Registered -> Ready) guard, or B-T10 Manifest rejection.
- **Observed by**: SDK.
- **Semantics**: Manifest requires a Skill the Agent does not declare.
- **Retryable**: `after-mutate`.

### `SPEC_INVALID` (32)
- **Raised by**: B-T1 guard - Manifest schema / referential validation.
- **Raised at**: Binding Pending transition.
- **Observed by**: SDK.
- **Semantics**: Manifest references a missing `workspace_ref`, declares an impossible sink mapping, or has malformed `TaskSpec.params`.
- **Retryable**: `after-mutate`.

### `MANIFEST_IDEMPOTENCY_COLLISION` (33)
- **Raised by**: ManifestChannel exactly-once guard.
- **Raised at**: CH-T1 rejected or Manifest admission.
- **Observed by**: SDK.
- **Semantics**: Two Manifests submitted with the same `idempotency_key` but different bodies. First wins; second is rejected. (Same body, same key -> returns the original ack, no error.)
- **Retryable**: `no` without a fresh key.

---

## §E.5 Command / target

### `COMMAND_TARGET_NOT_FOUND` (40)
- **Raised by**: CommandAck dispatcher.
- **Raised at**: Command target resolution before firing the transition.
- **Observed by**: Command issuer.
- **Semantics**: Target ID does not resolve in the Session scope.
- **Retryable**: `no`.

### `COMMAND_TARGET_WRONG_STATE` (41)
- **Raised by**: any FSM transition guard that reads target state.
- **Raised at**: the transition the Command was intended to fire.
- **Observed by**: Command issuer.
- **Semantics**: Target exists but is in a state that does not allow the requested transition.
- **Retryable**: `no` without state change; `after-mutate` if the client waits.

### `COMMAND_UNSUPPORTED` (42)
- **Raised by**: CommandKind dispatcher.
- **Raised at**: pre-transition.
- **Observed by**: Command issuer.
- **Semantics**: `CommandKind` is recognized but not implemented in this build.
- **Retryable**: `no`.

### `UPDATE_NOT_SUPPORTED` (43)
- **Raised by**: Service FSM - any Command that would transition an Active Service into Updating.
- **Raised at**: SV-T attempted (absent in v0.1-beta-2; see `service-beta.md §2.5`).
- **Observed by**: SDK.
- **Semantics**: Service update is explicitly deferred in v0.1-beta-2. The remediation is SV-T3/SV-T4 (stop) followed by SV-T1/SV-T2 (re-provision + re-deploy).
- **Retryable**: `no` in v0.1-beta-2.

### `DISPATCH_TIMEOUT` (44)
- **Raised by**: Command timeout watcher.
- **Raised at**: `command_id` ack window elapsed without CommandAck.
- **Observed by**: Command issuer.
- **Semantics**: No ack within the dispatch window. The underlying transition MAY still have fired (at-least-once). The issuer should re-read the target state before retrying.
- **Retryable**: `yes` with idempotency-aware re-read.

---

## §E.6 Binding / Task

### `BINDING_ALREADY_RELEASED` (50)
- **Raised by**: B-T4 / B-T5 / B-T6 guards.
- **Raised at**: a Command arriving against a Binding in `released`.
- **Observed by**: Command issuer.
- **Semantics**: Terminal Binding state; no further transitions possible.
- **Retryable**: `no`.

### `TASK_ALREADY_TERMINAL` (51)
- **Raised by**: T-T7 / T-T8 / T-T9 guards.
- **Raised at**: a Task-targeted Command against a Task in `{completed, failed, canceled}`.
- **Observed by**: Command issuer.
- **Semantics**: Task has reached a terminal state.
- **Retryable**: `no`.

### `SPAWN_FAILED` (52)
- **Raised by**: SV-T2 deploy path (PlatformAgent spawn failure) or T-T2 (platform-side Task launch).
- **Raised at**: SV-T2 fallback -> `stopped` with `stopped_reason = 'spawn_failed'`; T-T2 fallback -> T-T8 Failed.
- **Observed by**: Overseer internal recovery; surfaced to SDK if RemoteAgent-observable.
- **Semantics**: Platform process-spawning subsystem declined or failed the spawn.
- **Retryable**: `after-mutate` once the subsystem recovers.

---

## §E.7 Transport

### `GATEWAY_UNAVAILABLE` (60)
- **Raised by**: SDK-side connect path; or platform routing when Gateway is in `Stopping` / `Stopped` (GW-T5 / GW-T6).
- **Raised at**: pre-CommandChannel open.
- **Observed by**: SDK.
- **Semantics**: Gateway is not admitting new connections. RemoteAgents cannot register or re-register. For already-connected Channels, INV-GW1 (connection persistence through A-T8 soft-restart) governs continuity.
- **Retryable**: `yes` with backoff.

### `CHANNEL_OPEN_FAILED` (61)
- **Raised by**: CH-T1 rejected path (no Channel row lands).
- **Raised at**: Channel handshake rejection.
- **Observed by**: the endpoint that initiated CH-T1.
- **Semantics**: Reliability class mismatch, `channel_id` collision, or category rejection.
- **Retryable**: `after-mutate` - correct the handshake parameters.

### `SINK_OPEN_FAILED` (62)
- **Raised by**: SK-T1 rejected or SK-T2 timeout.
- **Raised at**: Sink provisioning in SV-T2 or T-T2.
- **Observed by**: Service FSM driver -> surfaces as SV-T2 fallback.
- **Semantics**: Sink could not be provisioned - auth, target missing, config invalid.
- **Retryable**: `after-mutate`.

### `SINK_UNAVAILABLE` (63)
- **Raised by**: Sink runtime (deferred SK-T states: Writing, Error).
- **Raised at**: mid-Task artifact emit.
- **Observed by**: Task FSM driver -> T-T8 Failed with `failure_reason`.
- **Semantics**: Sink was provisioned successfully but is now rejecting writes.
- **Retryable**: `yes` with backoff for transient; `after-mutate` if permanent.

---

## §E.8 Subsystem degradation

These kinds are the wire representations of the four subsystem loss modes catalogued in `overseer-beta.md §1.4`. They appear in two places:

1. As the `losses` list in an `OverseerDegraded` event.
2. As the `Error.kind` on a specific Command or Manifest that failed because the subsystem was down.

### `SUBSYSTEM_LOSS_PERSISTENT_STORAGE` (70)
- **Raised by**: Postgres connectivity loss or write failure on an FSM driver transaction.
- **Raised at**: any transition whose Effects include a write to the schema.
- **Observed by**: Overseer -> emits `OverseerDegraded`; SDK -> receives on specific Commands.
- **Semantics**: Per the Operation Availability Matrix (§1.4), read-only transitions may continue, but Deploy, Register, etc., reject.
- **Retryable**: `yes` with backoff until `OverseerRecovered` clears.

### `SUBSYSTEM_LOSS_MESSAGE_DELIVERY` (71)
- **Raised by**: gRPC / Channel layer failure.
- **Raised at**: Command dispatch, Manifest transmit, Event emission.
- **Observed by**: Overseer; SDKs detect transport failures.
- **Semantics**: In-cluster message bus is degraded.
- **Retryable**: `yes` with backoff.

### `SUBSYSTEM_LOSS_PROCESS_SPAWNING` (72)
- **Raised by**: PlatformAgent spawn subsystem (OS process launcher / Docker spawner).
- **Raised at**: SV-T2 PlatformAgent deploy, T-T2 on-platform Task launch.
- **Observed by**: Overseer; Services fail deploy with `stopped_reason = 'spawn_failed'`.
- **Semantics**: Platform cannot launch new Agent processes. RemoteAgent-typed Services are unaffected.
- **Retryable**: `after-mutate` once healthy.

### `SUBSYSTEM_LOSS_EVENT_BROADCAST` (73)
- **Raised by**: internal event bus failure.
- **Raised at**: transition effects that fan out Events.
- **Observed by**: Overseer -> emits `OverseerDegraded`.
- **Semantics**: Transitions can persist, but downstream consumers may miss events. Best-effort resync on recovery.
- **Retryable**: `yes` once recovery fires.

---

## §E.9 Generic

### `INTERNAL` (90)
- **Raised by**: any FSM driver on unexpected condition.
- **Semantics**: A bug. File a defect.
- **Retryable**: `no`.

### `NOT_IMPLEMENTED` (91)
- **Raised by**: any stubbed FSM transition.
- **Semantics**: Transition enumerated in v0.1-beta-2 but deferred.
- **Retryable**: `no`.

### `TEMPORARILY_UNAVAILABLE` (92)
- **Raised by**: any admission control path that does not match a more specific kind.
- **Semantics**: Generic transient rejection.
- **Retryable**: `yes` with backoff.

---

## §E.10 Mapping table

| Kind | Raised by | Retryable |
|---|---|---|
| UNAUTHENTICATED (1) | Gateway auth / session_id check | after-mutate |
| SESSION_EXPIRED (2) | SN-T4 | no |
| SESSION_REVOKED (3) | SN-T6 | no |
| PLAN_REVOKED (4) | plan-service cascade | no |
| ENVELOPE_EXCEEDED (10) | IR-O4 guard | after-mutate |
| QUOTA_DENIED (11) | org quota admission | yes (backoff) |
| REGISTRATION_INVALID (20) | A-T1 guard | after-mutate |
| REGISTRATION_EXPIRED (21) | A-T17 reconcile | after-mutate |
| AGENT_NOT_FOUND (22) | Command resolution | no |
| AGENT_LOST (23) | A-T11 | after-mutate |
| DUPLICATE_AGENT_ID (24) | A-T1 uniqueness | no (idempotent) |
| MANIFEST_REJECTED (30) | B-T1 | after-mutate |
| SKILL_MISMATCH (31) | B-T1 guard | after-mutate |
| SPEC_INVALID (32) | B-T1 guard | after-mutate |
| MANIFEST_IDEMPOTENCY_COLLISION (33) | ManifestChannel | no |
| COMMAND_TARGET_NOT_FOUND (40) | dispatcher | no |
| COMMAND_TARGET_WRONG_STATE (41) | transition guard | no |
| COMMAND_UNSUPPORTED (42) | dispatcher | no |
| UPDATE_NOT_SUPPORTED (43) | Service FSM | no |
| DISPATCH_TIMEOUT (44) | timeout watcher | yes (idempotent re-read) |
| BINDING_ALREADY_RELEASED (50) | B-T6 guard | no |
| TASK_ALREADY_TERMINAL (51) | Task guard | no |
| SPAWN_FAILED (52) | spawner | after-mutate |
| GATEWAY_UNAVAILABLE (60) | Gateway state | yes (backoff) |
| CHANNEL_OPEN_FAILED (61) | CH-T1 rejected | after-mutate |
| SINK_OPEN_FAILED (62) | SK-T1 rejected | after-mutate |
| SINK_UNAVAILABLE (63) | Sink runtime | varies |
| SUBSYSTEM_LOSS_PERSISTENT_STORAGE (70) | FSM driver write | yes (backoff) |
| SUBSYSTEM_LOSS_MESSAGE_DELIVERY (71) | transport | yes (backoff) |
| SUBSYSTEM_LOSS_PROCESS_SPAWNING (72) | spawner | after-mutate |
| SUBSYSTEM_LOSS_EVENT_BROADCAST (73) | event bus | yes (backoff) |
| INTERNAL (90) | any | no |
| NOT_IMPLEMENTED (91) | stubbed transitions | no |
| TEMPORARILY_UNAVAILABLE (92) | generic | yes (backoff) |

---

## §E.11 Notes

- **Adding an error.** A new `ErrorKind` value requires: (a) addition to `proto-catalog-beta.md §common.proto`; (b) a new `§E.*` entry here with the five required fields; (c) an entry in the §E.10 mapping table; (d) a referenced FSM transition or a justification why no transition is associated. Without all four, the catalog is incomplete.
- **Removal / renumber.** Once an `ErrorKind` value is assigned, its tag number is stable for v0.1-beta-2. Removing or renumbering requires a catalog version bump.
- **Advisory retry fields.** `Error.retryable` and `Error.retry_after_ms` on the wire are advisory. Middleware SHOULD fill them consistently with this catalog. SDKs MAY surface them to users but MUST NOT rely on them as a contract.

---

## Sources

- [proto-catalog-beta.md - §common.proto ErrorKind enum](proto-catalog-beta.md)
- [overseer-beta.md - §1.4 Operation Availability Matrix](overseer-beta.md)
- [agent-beta.md - §2.1 Agent, incl. §2.1.5](agent-beta.md)
- [task-beta.md - §2.2 Task](task-beta.md)
- [binding-beta.md - §2.3 Binding](binding-beta.md)
- [service-beta.md - §2.5 Service](service-beta.md)
- [session-beta.md - §2.7 Session](session-beta.md)
- [compute-slot-beta.md - §2.8 ComputeSlot](compute-slot-beta.md)
- [gateway-beta.md - §2.9 Gateway](gateway-beta.md)
- [channel-beta.md - §2.10 Channel](channel-beta.md)
- [sink-beta.md - §2.11 Sink](sink-beta.md)
