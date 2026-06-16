# atelier-sdk — Normative Compliance Report (txy + fsm) v0.1-beta-2

Audit of `atelier-sdk` against the normative duo: Taxonomy (`../txy/`) and FSM Atlas (`../fsm/`).
Date: 2026-06-15. Gaps-and-violations first, severity-ranked, bidirectional.

## 1. Scope & method

- Subject: `atelier-sdk` workspace. 7 member crates + excluded `atelier-agent`.
- Members: `atelier-types`, `atelier-data`, `atelier-io`, `atelier-quant`, `atelier-sdk`, `atelier-telemetry`, `atelier-connect`. Plus `atelier-agent` (binary; pulls `../atelier-proto`).
- Normative inputs read in full: `txy-main.md`, `txy-review.md`, `use-case-1.md`; `fsm` `agent.md`, `task.md`, `channel.md`, `sink.md`, `manifest.md`, `proto-catalog.md`, `errors.md`, `fsm-main.md`.
- Checks: `txy-review.md §5` seven checks (C1–C7) + violation classes (A–H).
- Wire SSoT: `proto-catalog.md`. SDK consumes `atelier-proto v0.1-beta-2` (codegen).

## 2. Ownership lens (load-bearing)

Per `fsm-main.md §2.4.1`. A real FSM gap exists only where the SDK owns/co-owns the FSM.

| FSM | § | SDK role | On the hook |
|---|---|---|---|
| Agent (RemoteAgent) | 2.1 | co-owner | yes |
| Task (RemoteAgent) | 2.2 | co-owner | yes |
| Channel (agent end) | 2.10 | co-owner (seam) | yes |
| Sink (ObjectSink) | 2.11 | co-owner (producer-local) | yes |
| Overseer / Session / Service / Binding / ComputeSlot / Gateway | 1, 2.7, 2.5, 2.3, 2.8, 2.9 | non-owner | no — absence expected |

SDK carries non-owned IDs (`binding_id`, `service_id`, `session_id`) but executes no transitions for them. Correct.

## 3. Verdict

- Manifest contract (INV-M1/M5/M8): strong. Well-tested.
- Wire enums (Skill, AgentType, SinkType, CommandKind, ErrorKind, ArtifactKind, Activation): consumed correctly from `atelier-proto`.
- Taxonomy nouns, ID newtype discipline, Agent/Task FSM state-machine surface, restart lineage, command scoping: substantial gaps.
- Net: SDK is wire-shape-correct and manifest-correct, but does not yet implement the entity ontology (Task) or the owned FSMs as state machines. Most gaps are self-documented as deferred ("Wave 3.4").

## 4. Severity-ranked gaps & violations

| ID | Finding | Check / Class | Severity | Wave |
|---|---|---|---|---|
| G1 | `Worker` is the pervasive pseudonym for `Task` | C1 / A | High | 3 |
| G2 | ID newtype discipline absent (only `WorkerId`, `OrderId`) | C2 / H | High | lang |
| G3 | Telemetry task-id ≠ artifact-lineage task-id | INV-M1 spirit | High | 3.4 |
| G4 | `restart_epoch` hardcoded `0`; §2.1.5 restart lineage unimplemented | INV-A1/T4/T9/P4 | High | 3.4 |
| G5 | Command `target` scoping ignored — dispatched to all workers | INV-T3 | High | 3.4 |
| G6 | Agent FSM (§2.1) / Task FSM (§2.2) not implemented as state machines | §2.1 / §2.2 | Medium | 3.4 |
| G7 | SDK emits no transition `Event` variants | INV-P3 | Medium | 3.4 |
| G8 | Per-Task `ManifestAck` accept/reject not implemented (stub `Accepted`, empty tasks) | T-T1 / T-T2 | Medium | 3.4 |
| G9 | Sink `Ready`/provisioning handshake absent; sink typology drift | C5 / §2.11 | Medium | 3 |
| G10 | Market/quant vocabulary at shared crate root | C1 / D | Medium | 3 |
| G11 | `_legacy_toml` smuggling; typed `TaskSpec` fields ignored | C3 wire-debt | Medium | 3.2 |
| O1 | `atelier-data` ⇄ `atelier-connect` duplicated worker/sink/connection surface | systems-design | Medium | — |

## 5. Findings — detail

### G1 — `Worker` pseudonym for `Task` (High, C1 / Class A)

- Canonical unit of work = `Task` (`txy-main.md §Tasks`). `txy-review.md §5 C1` lists `Worker`-as-Task for sdk explicitly.
- SDK runtime unit = `Worker`. 294 occurrences / 59 files.
- Types: `WorkerCommand` (`atelier-connect/src/workers/registry.rs:55`), `WorkerStatus` (`registry.rs:80`), `WorkerRegistry` (`registry.rs:207`), `WorkerId` (`atelier-types/src/workers.rs:26`), `WorkerMode` (`atelier-types/src/synchronizers.rs:31`), `MarketWorker`/`DataWorker`.
- Edge maps Worker→Task only at telemetry build: `worker_to_task_phase` (`atelier-connect/src/remote_agent/telemetry_reporter.rs:255`).
- `WorkerId` doc claims canonical identity "across the SDK, backend, and webapp" (`workers.rs:1-4`) — entrenches the pseudonym cross-repo.
- Note: `txy-main.md §Skills` line 81 itself maps Sync presence to `MarketWorker` vs `DataWorker` — taxonomy already concedes current SDK vocab while flagging it for reconciliation. Decision needed: rename to Task, or ratify `Worker` as the RemoteAgent-local realization of Task in `txy-main.md`.

### G2 — ID newtype discipline absent (High, C2 / Class H)

- `proto-catalog.md §common.proto` (normative) + `txy-review.md §5 C2`: each ID domain SHOULD be a distinct Rust newtype (`AgentId(Uuid)`, `BindingId(Uuid)`, `TaskId(Uuid)`, …) "implemented in `atelier-sdk/atelier-types`". Wire stays flat strings; Rust wraps on decode.
- Actual: only `WorkerId(pub Uuid)` (`atelier-types/src/workers.rs:26`) and `OrderId(u64)` (`atelier-types/src/orders.rs:130`). No `AgentId`/`TaskId`/`BindingId`/`ServiceId`/`SessionId`/`WorkspaceId`/`ComputeSlotId`/`ChannelId`/`SinkId`/`ManifestId`.
- Identifiers carried as raw `String`: `UpstreamSinkConfig{agent_id, binding_id, session_id, service_id, task_id}` (`atelier-connect/src/remote_agent/upstream_sink.rs:51-67`); `HandshakeResult` (`gateway.rs:170-186`); `RemoteAgentConfig`/`GatewayConnectionConfig` (`gateway.rs:69-87`).
- Consequence: cross-domain ID misuse is not a compile error — the exact failure mode the spec's newtype rule prevents.
- Cheap, high-value, language-layer only (no wire impact). Assigned to this crate by name.

### G3 — Telemetry task-id ≠ artifact-lineage task-id (High)

- Artifacts: `ArtifactLineage.task_id` = canonical manifest `task_id` via `UpstreamSinkConfig.task_id` (`upstream_sink.rs:140`), hydrated from `[[metadata.tasks]]` (`orchestrator.rs:538-561,588-590,636-638`). Correct (INV-M1).
- Telemetry: `TaskTelemetry.TaskProgress.task_id` = `ws.id.0` = `WorkerId` (`telemetry_reporter.rs:193`). `AgentStatus.active_task_ids` = `WorkerId` (`telemetry_reporter.rs:227`).
- Same logical Task emits two different IDs upstream. Platform joins `artifacts.task_id` on canonical id but receives `WorkerId` in telemetry → no telemetry↔artifact correlation, no `active_task_ids`↔`tasks` row match.
- Root cause: `TelemetryReporter` reads `WorkerRegistry` (`WorkerStatus.id` only); canonical id never threaded into the registry. Self-flagged TODO (`orchestrator.rs:933-941`).

### G4 — `restart_epoch` hardcoded; restart lineage unimplemented (High)

- `§2.1.5` + INV-A1/INV-T4/INV-T9/INV-P4: `restart_epoch` increments on each successful restart and is the sole lineage discriminator across soft-restart.
- Actual: `restart_epoch: 0` hardcoded at every emission — `ArtifactLineage` + Envelope (`upstream_sink.rs:143,179`), `Heartbeat`/`AgentStatus`/Envelope (`telemetry_reporter.rs:169,224,240`). Comments: "Wave 3.4 threads the actual epoch".
- Post-restart artifacts indistinguishable from pre-restart. INV-T9 monotonicity not observable.
- Semantic mismatch: A-T8 is a soft in-place re-init preserving identity. `WorkerCommand::Restart` = "Tear down and re-create the worker" (`registry.rs:65-67`) — teardown/respawn shape, no epoch bump.

### G5 — Command target scoping ignored (High, INV-T3)

- `txy-main.md §Command` + INV-T3: Command carries a `target` (Task-scoped vs Agent/Binding-scoped); Task-scoped Command applies to the named Task only; wrong target → ack `REJECTED`.
- Actual: command loop dispatches every accepted `CommandKind` to ALL workers, ignoring `Command.target` oneof (`orchestrator.rs:732-768`; log line "dispatching command to all workers").
- `map_command_kind` (`orchestrator.rs:884-895`) is kind→action only; no target resolution.
- Effect: per-Task Pause/Resume from the webapp pauses/resumes every Task on the agent. Breaks `use-case-1.md §5` (Task-scoped Pause of one pair while another keeps running).

### G6 — Agent/Task FSMs not implemented as state machines (Medium)

- No `AgentState`/`TaskState` type (confirmed: no such enum in workspace). No S-A*/S-T* states, no A-T*/T-T* transitions, no INV-A*/INV-T* enforcement.
- Lifecycle is linear: connect → handshake → spawn workers → command loop → teardown (`orchestrator.rs:482-849`).
- Phase is approximated at telemetry time from `ConnectionState`: `worker_to_task_phase` (`telemetry_reporter.rs:255-270`) emits only `{Accepted, Running, Paused, Failed}`; `AgentStatus.phase` only `{Ready, Bound}` (`telemetry_reporter.rs:216-220`); `Heartbeat.phase` hardcoded `Bound` (`telemetry_reporter.rs:170`).
- Unreachable agent phases: `Registering, Registered, Restarting, Lost, Draining, Terminated`. Unreachable task phases: `Submitted, Pausing, Resuming, Completing, Completed, Canceled`.
- `AGENT_TERMINATE`/`BINDING_RELEASE` map to `WorkerCommand::Stop` (`orchestrator.rs:890-892`) — workers stop, but no A-T16 terminate / deregister / `AgentTerminated`. Self-flagged "Wave 3.4 handles agent-process exit".
- Mitigation: co-ownership — platform `agents`/`tasks` rows are authoritative mirror (`fsm-main.md §2.4.1`). BYO-infra reduces SDK-side FSM need. Still incomplete for owned FSMs.

### G7 — No transition `Event` emission (Medium, INV-P3)

- Ownership matrix: an owner "emits the corresponding `Event` variants on the wire per INV-P3".
- Actual: SDK emits zero `Event` payload variants (no `EnvelopePayload::Event` anywhere). Only `Heartbeat`, `TaskTelemetry`, `AgentStatus`, `ArtifactFrame`, `TerminalEvent`, `CommandAck`, `Registration`, `ManifestAck`.
- `AgentRegistered`/`AgentReady`/`TaskRunning`/… never emitted by the SDK.
- Ambiguity: spec may intend the Overseer to synthesize Events from agent telemetry for co-owned RemoteAgent FSMs. See D-spec note in §7. Flag for clarification, not just code.

### G8 — Per-Task ManifestAck accept/reject not implemented (Medium, T-T1/T-T2)

- Handshake always sends `ManifestAck.Accepted { binding_id, tasks: vec![] }` (`gateway.rs:391-398`) — "Wave 3.4 populates per-Task AssignedTask records".
- No per-Task acceptance decision. No self-rejection path (`SKILL_MISMATCH`/`SPEC_INVALID`/`INTERNAL_ERROR`). A malformed manifest exits the process (INV-M8) instead of acking `SPEC_INVALID`.
- Partial mitigation: `manifest.md §7` defers the `ManifestAck` round-trip post-beta under BYO-infra. But the SDK is on the gRPC `Manifest`→`ManifestAck` path here (see G11/D1), so the stub is on a path the SDK actually exercises.

### G9 — Sink provisioning Ready absent; sink typology drift (Medium, C5 / §2.11)

- `§2.11` normative states: `Idle → Ready` (SK-T1/SK-T2 handshake; `SinkReady` event). Runtime states deferred.
- SDK `SinkState` = `{Idle, Streaming, Writing, Backpressured, Error}` (`atelier-connect/src/workers/output/mod.rs:38`). Has `Idle`, lacks the normative `Ready`; implements the deferred runtime states instead. No SK-T1/SK-T2 handshake, no `SinkReady` emission.
- Typology (C5): canonical SinkType = `{Object, DB, Terminal}`. SDK `OutputSinkConfig` = `{channel, terminal, parquet{dir}}` (`atelier-connect/src/config/workers/common.rs:182`). `ObjectSink` surfaced as `parquet` (format-specific); non-canonical `channel`; no `object`/`db`.
- ObjectSink impl = `ParquetSnapshotFlusher` (`atelier-io/src/sink.rs:30`), `ParquetSink`/`BufferedSink`/`TerminalSink`(stub) (`output/mod.rs`). `DBSink` absent — expected (backend-owned per matrix).
- Net SDK obligation: name the file sink `Object`-aligned; add `Ready`/handshake if §2.11 is enforced for the producer-local seam.

### G10 — Domain vocabulary at shared crate root (Medium, C1 / Class D)

- `txy-review.md §7 Class D`: Orderbook / Trade / MarketSnapshot / Hawkes must sit in a Service-specific namespace; nothing at platform/shared scope should name them.
- `atelier-types` root modules: `orderbooks, trades, snapshots, funding, liquidations, open_interest, levels, orders` (`atelier-types/src/lib.rs:26-54`) — market-microstructure at the foundational shared crate's root.
- `atelier-quant`: `hawkes/`, `poisson/`, `arrivals/`, `forecast.rs`.
- `WorkerId` doc asserts atelier-types is shared "across the SDK, backend, and webapp" — so the leak radiates to platform scope.
- Partial mitigation exists: `config/markets/` namespace is present. Core data types are not under a `markets/` namespace. Pull market types under `markets/` (or assert SDK = Remote-domain Service scope and exempt).

### G11 — `_legacy_toml` smuggling (Medium, wire-debt)

- Manifest body extracted from `Manifest.tasks[0].params._legacy_toml` Struct field (`gateway.rs:636-647`), not typed `TaskSpec` fields (`skill`, `params`, `datatypes`, `sink_ids` per `proto-catalog.md §control.proto`).
- Self-flagged: "Wave 3.2 replaces this with typed TaskSpec fields" (`gateway.rs:629-635`).
- Works (the `[[metadata.tasks]]` block rides inside the TOML), but the typed wire contract is bypassed.

### O1 — Crate duplication (Medium, systems-design observation)

- `atelier-data` and `atelier-connect` each independently define: `trait OutputSink` (`*/src/workers/output/mod.rs`), `enum ConnectionState` (`*/src/clients/connection_state.rs`), `enum OutputSinkConfig` (`*/src/config/workers/common.rs`), `workers/`, `clients/`, `config/workers/`.
- Doubles the surface where taxonomy terms can drift; two copies to keep conformant.
- Confirm intent: is `atelier-data` legacy, superseded by `atelier-connect`? If so, schedule consolidation before reconciling C1/C5 (fix once, not twice).

## 6. Conformant (brief — credit where due)

- C4 Skill: declares canonical `Skill::{Ingest, Sync, Emit, Report}` from `atelier-proto`; `Transform` correctly excluded as PlatformAgent territory (`gateway.rs:286-297`, test `gateway.rs:707-721`). Enum names + tags match `proto-catalog.md`.
- AgentType: `AgentType::Remote` used; `AgentLocation` not present. `txy-review.md` legacy `AgentLocation`/`AgentCapability` drifts are NOT in current SDK (clean).
- C6 Activation: only `Activation::ServiceId` emitted; `ExperimentId` never produced (`upstream_sink.rs:144`). Matches beta scope (Service-only).
- C3 verbs: no invented `CommandKind`; `RECONFIGURE` removed (`orchestrator.rs:28-33`); unknown kind → `CommandUnsupported` ack (`orchestrator.rs:770-783`). Matches `errors.md UPDATE_NOT_SUPPORTED`.
- Manifest INV-M1/M5/M8: `parse_metadata_tasks` + typed `ManifestParseError` (6 classes) + canonical hydration strictly before worker spawn + fail-loud non-zero exit; 9 unit tests (`orchestrator.rs:222-432,538-561`). Strong.
- ArtifactKind/data.proto: `ARTIFACT_KIND_DATA`; lineage-only vs payload-bearing emission per Iteration 4.5.4; `ManifestArtifact` kept off `ArtifactFrame` (`upstream_sink.rs:154-171`).
- INV-P2: pre-registration Envelope `session_id` empty; post-registration pinned (`gateway.rs:301`, `upstream_sink.rs`, `telemetry_reporter.rs`).
- W1-1: `agent_id` Gateway-allocated, never sent inbound; `Registration` carries `agent_alias` only (`gateway.rs:9-14,286-297`).

## 7. Doc-update candidates (code ahead of / inconsistent with spec)

Flagged per the bidirectional brief. These are spec edits, not (only) SDK fixes.

- D1 — `Gateway.Handshake` RPC does not exist in the proto SSoT. `manifest.md §2.3`, `agent.md §2.1.2`, and `proto-catalog.md` source lines cite `Gateway.Handshake → HandshakeResult.toml_config`. `proto-catalog.md §services.proto` defines only `CommandChannel`, `TelemetryChannel`, `EventSubscribe` — no `Handshake`. SDK implements the CommandChannel `Registration→RegistrationResponse→Manifest→ManifestAck` flow (`gateway.rs:256-445`) and synthesizes its own `HandshakeResult`. Reconcile: either add `Handshake` to `services.proto`, or rewrite `manifest.md`/`agent.md` delivery prose to the CommandChannel flow the SDK and `services.proto` actually use.
- D2 — RemoteAgent connection sub-FSM is unmodeled by the Atlas. `ConnectionState` (`Disconnected/Connecting/Authenticating/Subscribing/Streaming/Paused/Reconnecting`) is a mature state machine with a diagram and transition records (`atelier-connect/src/clients/connection_state.rs:49-123`). `txy-main.md` "Ingest" skill is "stateful … handles reconnection" but the Atlas specs no connection FSM. Candidate: Atlas acknowledges/owns an Ingest connection sub-FSM in v0.1-beta-3.
- D3 — SDK `SinkState` implements the §2.11 deferred runtime states (`Streaming/Writing/Backpressured/Error`) the Atlas has not yet specified. When §2.11 lifts the deferral, lift the SDK enum as the reference shape.
- D4 — INV-P3 reach for co-owned RemoteAgent FSMs is ambiguous. Spec does not state whether the RemoteAgent must emit `Event` variants or whether the Overseer synthesizes them from agent telemetry (`AgentStatus`/`Heartbeat`). Clarify in `fsm-main.md §2.4.1` before scoring G7 as a code defect.

## 8. Not applicable (non-owned FSMs — absence is expected)

Overseer §1, Session §2.7, Service §2.5, Binding §2.3, ComputeSlot §2.8, Gateway §2.9.
SDK references their IDs only. No transition/persistence/Event obligation. No findings.

## 9. Remediation waves (maps to `txy-review.md §8`)

- Wave 1 (spec edits): resolve D1, D4. No SDK code until settled.
- Wave 2 (wire cut): G11 — switch `_legacy_toml` to typed `TaskSpec`. Bundle with `atelier-proto` cut.
- Wave 3.4 (FSM driver layer): G3, G4, G5, G6, G7, G8 — Task identity, restart_epoch, command targeting, Agent/Task states, Events, ManifestAck per-Task. Largest block; mostly self-flagged.
- Wave 3 (code-only moves): G1 (Worker→Task or ratify), G9 (Sink naming + Ready), G10 (markets namespace), O1 (de-dup atelier-data/atelier-connect).
- Language-layer (independent): G2 — ID newtypes in `atelier-types`. Do early; unblocks compile-time safety for all later waves.

## 10. Evidence index (primary file:line)

- `atelier-types/src/workers.rs:26` — `WorkerId(pub Uuid)` (sole id newtype).
- `atelier-types/src/lib.rs:26-54` — market types at crate root (G10).
- `atelier-connect/src/remote_agent/gateway.rs:286-297` — Skill set declared (C4 ✓); `:391-398` ManifestAck stub (G8); `:636-647` `_legacy_toml` (G11).
- `atelier-connect/src/remote_agent/orchestrator.rs:222-263` — `parse_metadata_tasks` (INV-M8 ✓); `:732-768` dispatch-to-all (G5); `:884-895` `map_command_kind`.
- `atelier-connect/src/remote_agent/upstream_sink.rs:51-67` — string IDs (G2); `:140-144` lineage incl. `restart_epoch:0` (G4) + `Activation::ServiceId` (C6 ✓).
- `atelier-connect/src/remote_agent/telemetry_reporter.rs:169-170,193,216-227,255-270` — hardcoded phase/epoch, WorkerId-as-task_id (G3/G4/G6).
- `atelier-connect/src/workers/registry.rs:55-68` — `WorkerCommand`; `:80-106` `WorkerStatus` (G1).
- `atelier-connect/src/workers/output/mod.rs:38` — `SinkState` (G9); `atelier-connect/src/config/workers/common.rs:182` — `OutputSinkConfig` (G9).
- `atelier-io/src/sink.rs:30` — `ParquetSnapshotFlusher` (ObjectSink impl, G9).
- `atelier-quant/src/hawkes/`, `poisson/` — quant vocabulary (G10).
