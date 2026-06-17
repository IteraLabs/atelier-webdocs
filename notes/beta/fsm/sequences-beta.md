# FSM Atlas v0.1-beta-2 - Cross-FSM Sequences

This document traces how multiple FSMs coordinate during the operations that matter for v0.1-beta-2. For each sequence, it enumerates:

- The **participants** - which FSMs and external entities are involved.
- The **preconditions** - the state each participant must be in before the sequence can start.
- The **choreography** - the ordered series of transitions, wire exchanges, and persistence writes.
- The **happy-path diagram** - ASCII swimlane.
- The **failure branches** - the most common failures and which FSM observes them.
- The **invariants asserted** during the sequence.

SEQ-1 Deploy and SEQ-2 Delete are fully specified in v0.1-beta-2 - together they close the Bring-Your-Own-Infra use-case steps 1-6 (`../txy/txy-beta.md`). SEQ-4 Overseer Crash Recovery and SEQ-5 Graceful Shutdown are specified (§3.4, §3.5 below) - together they close use-case step 7 (Platform Drain -> researcher-side resilience -> Recovery). Their prerequisites - the `channels` persistence table (`schema-beta.md` table 12) and the `agent.reconnect_grace_ms` tunable (`timeouts-beta.md §T.2`) - landed in the same iteration. SEQ-3 Agent Disconnect (enumerated in `fsm-beta.md §3`) remains a thin sequence: it is the §3.2.3 "Agent Lost" failure branch generalized, and is folded into SEQ-4 Stage 2 reconciliation rather than given its own section.

---

## SEQ-1: Deploy (RemoteAgent)

The operator (SDK) requests a new Service bound to a RemoteAgent. The sequence ends when a Task is Running in a ComputeSlot, emitting Artifacts to a Sink.

### Participants

| Role | FSM / system |
|---|---|
| Operator | SDK client process |
| Gateway | `gateway-beta.md §2.9` |
| CommandChannel, ManifestChannel, TelemetryChannel | `channel-beta.md §2.10` |
| Overseer | `overseer-beta.md §1` |
| Session | `session-beta.md §2.7` |
| Agent (RemoteAgent) | `agent-beta.md §2.1` |
| Service | `service-beta.md §2.5` |
| Binding | `binding-beta.md §2.3` |
| Workspace | row only (`schema-beta.md`) |
| Pipeline | row only (`schema-beta.md`) |
| ComputeSlot | `compute-slot-beta.md §2.8` |
| Task | `task-beta.md §2.2` |
| Sink | `sink-beta.md §2.11` |
| ArtifactChannel | `channel-beta.md §2.10` |
| Persistence | `schema-beta.md` (Postgres) |

### Preconditions

- Overseer is in `ready` (§1.3). The four subsystems (persistent storage, message delivery, process spawning, event broadcast) are all healthy.
- Gateway is in `ready` (§2.9).
- Session is in `active` with remaining envelope ≥ 1 Service + 1 Agent + per-Task slot capacity + per-Sink capacity.
- Pipeline row exists with a `vacant` ComputeSlot at `slot_ordinal = 0` (single-slot pipeline is the v0.1-beta-2 common path).

### §3.1.1 Choreography - happy path

The choreography splits into two architectural phases by who originates the transitions and where the sequence pauses:

- **Phase A - Overseer-side synchronous.** Run inside `Scheduler::deploy_service` in response to the operator's `POST /api/services`. Touches Service / Workspace / ComputeSlot / Binding / Manifest rows in a single Overseer-side transaction stack. Ends with the Binding at `pending`, the ComputeSlot at `Reserved` (not yet Occupied), and a JWT scoped to (`session_id`, `binding_id`, `service_id`) returned to the webapp. The sequence pauses here.
- **Phase B - Gateway-driven (Agent-side).** Run inside `gateway_consumer` on receipt of `lifecycle.events.AgentRegistered` (delivered when the researcher's RemoteAgent connects to the Gateway carrying the Phase-A-issued JWT). Drives A-T1 / A-T2; resumes Binding activation with B-T3 -> cascades into A-T3 + SV-T3; runs T-T1 / T-T2 -> CS-T2 -> T-T3 to steady state.

The pause window between Phase A return and Phase B start is governed by `binding.pending_grace_ms` (`timeouts-beta.md §T.5`, default 60s). If Phase B does not begin within that window, the live grace ticker (`overseer-beta.md §1.7`) fires B-T2 with `release_reason = 'registration_grace_timeout'` and the Binding is released without ever activating. See §3.1.3 for the failure branch and §3.1.6 for recovery semantics around the pause point.

Steps are numbered. Each step names the triggering transition (or wire frame) and its Effects. Persistence writes are bracketed. Wire frames use proto-catalog message names.

#### Phase A - Overseer-side synchronous

Operator enters Phase A by `POST /api/services` carrying the Manifest TOML. Overseer resolves Session, Pipeline, prepares Service skeleton, mints credentials, returns.

1. **Operator submits Service spec.** Webapp `POST /api/services` with `manifest_toml` body. Overseer admits via `check_availability(SystemOperation::Deploy)` per §1.4 (`overseer-beta.md`).

2. **Overseer fires SV-T1** (creation -> Provisioning).
   - Guard: IR-O4 - `SELECT ... FOR UPDATE sessions`; envelope has room for +1 Service (INV-SV2).
   - Persist (one transaction): `INSERT INTO services ... status='provisioning'`; `INSERT INTO workspaces (service_id deferred FK) ... destroyed_at=NULL`; `UPDATE sessions.envelope_counters`.
   - Emit: Event `ServiceProvisioning`.

3. **Overseer fires SV-T2 start** (Provisioning -> Deploying).
   - Guard: Pipeline row exists; ComputeSlot at `slot_ordinal=0` is `vacant`. The Skill-subset check (Manifest's declared Task Skills against the RemoteAgent's declared Skills) is **deferred to Phase B step 14** because no Agent is registered yet.
   - Effects: begin Manifest composition; `UPDATE services.status='deploying'`.
   - Emit: Event `ServiceDeploying`.

4. **Overseer composes Manifest.** Populates `TaskSpec[]`, `SinkAssignment[]`, fresh `idempotency_key`. Per W1-1 the Manifest body has neither `binding_id` nor `agent_id` - both are platform-allocated.

   *BYO-infra augmentation (v0.1-beta-2):* `manifest_generator::inject_metadata` prepends the `[metadata]` block (composition-time IDs: `manifest_id`, `binding_id`, `service_id`); `accept_task` (T-T1) is fired here per `TaskSpec` to allocate the canonical `tasks.task_id`(s); `manifest_generator::append_metadata_tasks` then appends the `[[metadata.tasks]]` sub-array carrying the allocated `task_id`(s). The fully augmented body is what gets persisted at step 6. See `manifest-beta.md §2.1` and INV-M3 / INV-M4.

5. **Overseer fires CS-T1** (Vacant -> Reserved) for the pipeline's slot.
   - Guard (INV-CS3, via partial unique index `compute_slots_pipeline_single_activation`): no other activation holds the Pipeline.
   - Persist: `UPDATE compute_slots SET state='reserved', current_activation_id=<service_id>, reserved_at=now()` - atomically, so the partial index rejects concurrent Deploys.
   - Emit: Event `ComputeSlotReserved`.

6. **Overseer fires B-T1** (creation -> Pending).
   - Persist (one transaction): `INSERT INTO bindings ... status='pending'`; `INSERT INTO manifests ... body=<FULL augmented body from step 4>, ack_result=NULL`; `UPDATE manifests.binding_id` using the deferred FK.
   - Emit: Event `BindingCreated`.
   - BindingId allocated here per W1-1; returned at step 8 in `DeployServiceResponse`.
   - INV-M4: `manifests.body` is the FULL augmented shape from step 4; never rewritten after this commit.

7. **Overseer mints JWT.** Claims = (`session_id`, `binding_id`, `service_id`). Signed with `GATEWAY_JWT_SECRET`. Lifetime bounded by Session expiry (a token outliving its Session is rejected on Registration).

8. **Overseer returns DeployServiceResponse to webapp.** Body carries (`service_id`, `binding_id`, `gateway_url`, `token`). Webapp's SpawnModal renders `gateway_url` and `token` as the BYO-infra credential pair plus a `docker run -e ATELIER_GATEWAY_URL=… -e ATELIER_TOKEN=… iteralabs/atelier-agent` launch snippet.

9. **Pause point.** Overseer-side state at end of Phase A:
   - `services.status = 'deploying'`
   - `bindings.status = 'pending'`
   - `compute_slots.state = 'reserved'` (not Occupied)
   - `tasks` rows do not exist yet - T-T1 fires in Phase B
   - No Channels open
   - No Agent registered

   The grace timer (`binding.pending_grace_ms`) is now armed. The live ticker (`overseer-beta.md §1.7`) sweeps Pending Bindings older than the grace window and fires B-T2 on expiry. The boot reconciler (`§1.7` Step 1) covers the same B-T2 cascade for the Overseer-restart case.

#### Phase B - Gateway-driven (Agent-side)

Researcher launches the IteraLabs Docker image with `ATELIER_GATEWAY_URL` and `ATELIER_TOKEN` from Phase A. Phase B begins on Gateway-side Registration receipt.

10. **RemoteAgent opens CommandChannel.** Outbound gRPC bidirectional stream against Gateway. Gateway authenticates the JWT against `GATEWAY_JWT_SECRET`, confirms `(session_id, binding_id, service_id)` against the Phase-A-issued claims, binds the Channel to those claims. CH-T1 fires for CommandChannel (category `command`, reliability `at-least-once`).

11. **RemoteAgent sends Envelope{Registration}.** Handshake frame over CommandChannel. `Registration.agent_type = REMOTE`, `Registration.skills` populated, `Registration.target_session_id` matches the JWT claim, `Registration.agent_alias` carried. Per W1-1 the body carries no `agent_id` and no `binding_id`.

12. **Gateway forwards Registration on Kafka `lifecycle.events`.** Event arrives at Overseer's `gateway_consumer` (consumer wiring). The consumer fires **A-T1** (creation -> Registered).
    - Guard: Session in `active` or `expiring` (INV-SV2 analogue); envelope has room for +1 Agent (IR-O4); JWT-implied `(session_id, binding_id, service_id)` matches an existing `bindings` row in `pending`.
    - Persist: `INSERT INTO agents (...) status='registered'` within a `SELECT ... FOR UPDATE sessions` transaction (INV-SN1).
    - Emit: Event `AgentRegistered` (transition_id `A-T1`).
    - AgentId allocated here per W1-1; returned at step 13.

13. **Overseer sends Envelope{RegistrationResponse.Accepted}.** Routed back through Gateway over CommandChannel with assigned `agent_id`.

14. **Overseer fires A-T2** (Registered -> Ready).
    - Guard: Skills non-empty; all recognized; the deferred Skill-subset check from step 3 lands here - Agent's declared Skills must cover the Manifest's declared Task Skills.
    - Persist: `UPDATE agents SET status='ready'`.
    - Emit: Event `AgentReady`.

15. **RemoteAgent opens TelemetryChannel.** Second gRPC stream against Gateway. CH-T1 -> CH-T2 for TelemetryChannel (category `telemetry`, reliability `best-effort-with-sequence`).

16. **RemoteAgent begins heartbeats.** Envelope{Heartbeat} every `agent.heartbeat_interval_ms` (5s default).

17. **Overseer transmits Manifest.** Envelope{Manifest} over CommandChannel (ManifestChannel embedded per INV-CH6). Composed in Phase A step 4; held until A-T2 confirms Skill satisfaction.

    *BYO-infra note (v0.1-beta-2):* Under the BYO-infra delivery path, "transmit Manifest" is **not a separate wire step** - the agent already has the full augmented body. It was returned in the gRPC handshake response (`HandshakeResult.toml_config`, step 12) when the Agent registered. T-T1 fired during Phase A composition (step 4), so the persisted body the Gateway returns at handshake already carries the canonical `[[metadata.tasks]]` block. The `ManifestAck.AssignedTask` round-trip in the canonical wire-spec is reserved for the gRPC `ManifestChannel` path. The Overseer ALSO publishes the augmented body to Kafka `control.manifests` during Phase A - this is server-internal and not load-bearing for v0.1-beta-2 (`manifest-beta.md §2.4` / §6). See INV-M3, INV-M4, and `manifest-beta.md §7` for the wire-spec correspondence.

18. **RemoteAgent validates Manifest locally and opens declared Sinks.** Per declared Sink: SK-T1 fires (handshake against the Sink's transport - credential probe, schema negotiation). Timer per Sink: `sink.open_budget_ms` (5s).

19. **Sink handshakes complete.** SK-T2 fires per Sink (Idle -> Ready). For the BYO-infra use case: ObjectSink (local Parquet) and TerminalSink (live event feed upstream).
    - Emit: Event `SinkReady` per Sink.
    - This gates IR-CHO3 for the ArtifactChannels opened at step 27.

20. **RemoteAgent sends Envelope{ManifestAck.Accepted}.** All declared Tasks accepted.

21. **Overseer fires B-T3** (Pending -> Active).
    - Guard (IR-CHO1 + IR-CHO2): CommandChannel and TelemetryChannel are both Open; ManifestChannel (embedded) is Open. INV-T6 holds.
    - Persist: `UPDATE bindings.status='active'`; `UPDATE manifests.ack_result='accepted'`, `acked_at=now()`.
    - Emit: Event `BindingActive`.

22. **B-T3 cascades drive A-T3 and SV-T3 (atomic with respect to step 21's transaction).**
    - **A-T3** (Ready -> Bound) per IR-BA2. `UPDATE agents.status='bound'`. Emit: Event `AgentBound` (typed `wire::Event::AgentBound` via `gateway_consumer`).
    - **SV-T3** (Deploying -> Active). `UPDATE services.status='active'`, `activated_at=now()`. Emit: Event `ServiceActive`.

23. **Overseer creates each Task** in the Manifest (initial state Pending).
    - Persist: `INSERT INTO tasks ... status='pending', compute_slot_id=<reserved slot>`.

24. **RemoteAgent sends per-Task accept.** SDK runs local Accept logic; sends Envelope{Command{TASK_START, TaskTarget}}.

25. **Overseer fires T-T1** (Pending -> Accepted).
    - Persist: `UPDATE tasks.status='accepted'`, `accepted_at=now()`.
    - Emit: Event `TaskAccepted`.

26. **Overseer fires CS-T2** (Reserved -> Occupied) for the slot the Task will run on.
    - Persist: `UPDATE compute_slots SET state='occupied', current_task_id=<task_id>, current_binding_id=<binding_id>, occupied_at=now()`.
    - The field-fill CHECK on `compute_slots` asserts INV-CS7.
    - Emit: Event `ComputeSlotOccupied`.

27. **RemoteAgent opens ArtifactChannel(s).** One per declared upstream Sink - per use-case §3, ArtifactChannel CH-303 (local to ObjectSink) and ArtifactChannel CH-304 (upstream to TerminalSink). CH-T1 fires per Channel; reliability inherits from Sink (INV-SK4 / `§2.10.3` SinkType -> reliability_class table).

28. **ArtifactChannel handshakes complete.** CH-T2 per Channel.
    - Emit: Event `ChannelOpen` per Channel.

29. **Overseer fires T-T3** (accepted -> running).
    - Guard (IR-CHO3): all declared ArtifactChannels are Open.
    - Persist: `UPDATE tasks.status='running'`, `running_at=now()`.
    - Effects: Agent begins producing Artifacts; frames flow over ArtifactChannel to the Sink.
    - Emit: Event `TaskRunning`.

#### Phase J - Steady state

30. Agent emits `Envelope{ArtifactFrame}` over ArtifactChannel(s) at the application cadence. Each frame carries `restart_epoch` (0 for first run) and per-Channel `sequence` (INV-CH4).
31. Agent emits `Envelope{TaskTelemetry}` periodically over TelemetryChannel.
32. Agent emits `Envelope{Heartbeat}` at `agent.heartbeat_interval_ms`.

**Sequence complete.** Service-stop-and-teardown via operator Delete is covered by SEQ-2 below (§3.2). Overseer crash recovery and platform graceful shutdown are covered by SEQ-4 (§3.4) and SEQ-5 (§3.5); unexpected Agent disconnect (SEQ-3) is folded into SEQ-4 Stage 2 (§3.4.6).

### §3.1.2 Happy-path swimlane

```
Webapp        Researcher        Gateway          Overseer         Persistence        Event bus
  |               |                 |                 |                  |                 |
  |---POST--------|                 |                 |                  |                 |
  |  /api/services|                 |                 |                  |                 |
  |               |                 |                 |--SV-T1---------->|-ServiceProv---->|
  |               |                 |                 |  [INS services,  |                 |
  |               |                 |                 |   INS workspaces,|                 |
  |               |                 |                 |   UPD sessions]  |                 |
  |               |                 |                 |--SV-T2 start---->|-ServiceDeploy-->|
  |               |                 |                 |  [UPD services]  |                 |
  |               |                 |                 |--CS-T1---------->|-CSReserved----->|
  |               |                 |                 |  [UPD slots]     |                 |
  |               |                 |                 |--B-T1----------->|-BindingCreated->|
  |               |                 |                 |  [INS bindings,  |                 |
  |               |                 |                 |   INS manifests] |                 |
  |<-DeployResp---|                 |                 |                  |                 |
  |  (gw_url,tok) |                 |                 |                  |                 |
  |==============================================================================================|
  |                            (PAUSE - Phase A complete; binding=pending; grace timer armed)   |
  |==============================================================================================|
  |               |---docker run--->|                 |                  |                 |
  |               |  -e ATELIER_*   |                 |                  |                 |
  |               |---CmdChan open->|--CH-T1 CH-T2--->|                  |                 |
  |               |---Envelope{Reg}>|---------------->|                  |                 |
  |               |                 |  [Kafka         |                  |                 |
  |               |                 |   lifecycle.    |                  |                 |
  |               |                 |   events]       |--A-T1----------->|-AgentRegistered>|
  |               |                 |                 |  [INS agents]    |                 |
  |               |<--RegResp.OK----|<----------------|                  |                 |
  |               |                 |                 |--A-T2----------->|-AgentReady----->|
  |               |                 |                 |  [UPD agents]    |                 |
  |               |---TelChan open->|--CH-T1 CH-T2--->|                  |                 |
  |               |---Heartbeats--->|                 |                  |                 |
  |               |<-Envelope{Man}--|<----------------|                  |                 |
  |               |---SK-T1 open--->|                 |                  |                 |
  |               |---SK-T2 ready-->|---------------->|                  |-SinkReady------>|
  |               |---ManifestAck-->|---------------->|                  |                 |
  |               |                 |                 |--B-T3----------->|-BindingActive-->|
  |               |                 |                 |  [UPD bindings,  |                 |
  |               |                 |                 |   UPD manifests] |                 |
  |               |                 |                 |--A-T3----------->|-AgentBound----->|
  |               |                 |                 |  [UPD agents]    |                 |
  |               |                 |                 |--SV-T3---------->|-ServiceActive-->|
  |               |                 |                 |  [UPD services]  |                 |
  |               |                 |                 |--create rows-->|                 |
  |               |                 |                 |  [INS tasks]     |                 |
  |               |---Cmd{TaskStart>|---------------->|--T-T1-------->|-TaskAccepted--->|
  |               |                 |                 |  [UPD tasks]     |                 |
  |               |                 |                 |--CS-T2---------->|-CSOccupied----->|
  |               |                 |                 |  [UPD slots]     |                 |
  |               |---ArtChan open->|--CH-T1 CH-T2--->|                  |-ChannelOpen---->|
  |               |                 |                 |--T-T3----------->|-TaskRunning---->|
  |               |                 |                 |  [UPD tasks]     |                 |
  |               |--ArtifactFrame->|                 |                  |                 |
  |               |--TaskTelemetry->|                 |                  |                 |
```

The double bar marks the pause boundary between Phase A and Phase B. Calendar-time between them is the researcher's `docker run` lead time, bounded by `binding.pending_grace_ms` (default 60s) - see §3.1.3 for the timeout branch.

### §3.1.3 Failure branches

The most common branches; each names the FSM transition that observes the failure and the error surfaced. Branches are grouped by which architectural phase they fire in.

**Phase A failures (Overseer-side, before JWT issuance).**

- **Deploy rejected (`check_availability` guard at step 1)** - Overseer not in `ready` per §1.4. Error: `TEMPORARILY_UNAVAILABLE` (72) / `SUBSYSTEM_LOSS_*` (70+) per the §1.4 cell. No rows land. Webapp shows the error directly.
- **Service envelope exceeded (SV-T1 guard at step 2)** - Session resource envelope already at limit. Error: `ENVELOPE_EXCEEDED` (10). No Service row lands.
- **Pipeline busy (CS-T1 guard at step 5)** - Partial index `compute_slots_pipeline_single_activation` rejects. Error: `COMMAND_TARGET_WRONG_STATE` (41) with message "pipeline already activated". Service transitions to Stopped with `stopped_reason = 'spawn_failed'` (reused for slot-busy in v0.1; may get its own reason later). Workspace row destroyed.
- **Persistent storage loss during Phase A** - `SUBSYSTEM_LOSS_PERSISTENT_STORAGE` (70) raised; SV-T1 / CS-T1 / B-T1 rejects in-flight; Overseer transitions to `degraded` (`OverseerDegraded` event). Webapp receives the error and backs off.

**Phase A -> Phase B transition (pause-window failures).**

- **Registration grace timeout (B-T2 grace path)** - `binding.pending_grace_ms` (default 60s) elapses with `bindings.status = 'pending'` and no Registration arriving on `lifecycle.events`. Live grace ticker (`overseer-beta.md §1.7`) fires **B-T2** with `release_reason = 'registration_grace_timeout'`. ComputeSlot reservation released (Reserved -> Vacant reset). Service rolls forward via SV-T10 (last-Binding-released auto-stop, see `service-beta.md §2.5`) with `stopped_reason = 'delete_last_agent'` - beta reuses this reason because the slot was never occupied. Webapp polls `GET /api/services/{id}` and sees the Stopped state. Researcher can re-deploy.
- **JWT used after Session expired** - Session passes `expiring`-into-expired between Phase A return and Phase B Registration. Gateway rejects the JWT-bearing CommandChannel handshake at step 10 with `UNAUTHENTICATED`; Phase B never starts; B-T2 grace eventually fires.

**Phase B failures (Gateway-driven).**

- **Registration rejected (A-T1 guard at step 12)** - JWT-implied `(session_id, binding_id, service_id)` does not match a `pending` Binding row (e.g., Binding already released by B-T2 grace), envelope exceeded, or Session not `active`/`expiring`. Error: `REGISTRATION_INVALID` (20) or `ENVELOPE_EXCEEDED` (10). No Agent row lands.
- **Skill mismatch (A-T2 guard at step 14)** - Agent's declared Skills do not cover the Manifest's Task Skills. Error: `SKILL_MISMATCH` (31). A-T18 (Registered -> Terminated, `skill_mismatch`) fires; its cascade releases the Pending Binding via B-T2 (`release_reason = skill_mismatch`).
- **Manifest rejected by Agent (ManifestAck rejected at step 20)** - Agent decodes Manifest and self-rejects (Skill mismatch surfaced application-side, SPEC invalidity). Error: `SKILL_MISMATCH` (31) or `SPEC_INVALID` (32). Binding fires B-T10 (Manifest rejection cascade) -> Releasing with `release_reason = 'task_rejected'`. Service transitions to Stopped with `stopped_reason = 'manifest_rejected'`.
- **Manifest ack timeout (step 17 -> 20)** - Agent never sends ManifestAck within `service.deploy_dispatch_timeout_ms` (10s). Error: `DISPATCH_TIMEOUT` (44). Service transitions to Stopped with `stopped_reason = 'dispatch_timeout'`.
- **Sink open failure (SK-T1 at step 18)** - Credential or target invalid (e.g., ObjectSink path not writable, TerminalSink upstream unreachable). Error: `SINK_OPEN_FAILED` (62). Service transitions to Stopped (treated as a deploy failure; resembles the Manifest-rejected path).
- **Agent heartbeat miss mid-Phase-B (A-T11 at any step ≥ 15)** - Three missed heartbeats (`agent.heartbeat_miss_threshold_ms` = 15s). Binding cascades to Draining (B-T4); Service cascades. The `§2.1.5` restart lineage may apply - see SEQ-3 (later).
- **Gateway becomes unavailable mid-Phase-B** - Any step that requires CommandChannel fails. For already-connected Channels, INV-GW1 (connection persistence through A-T8 soft-restart) governs continuity; for new Channel opens (TelemetryChannel at step 15, ArtifactChannel at step 27), CH-T1 is rejected. Error: `GATEWAY_UNAVAILABLE` (60).

### §3.1.4 Invariants asserted during SEQ-1

Every invariant below is checked at one or more boundaries named within this sequence. Rows are the anchor points; the invariant body in the cited FSM file owns the statement.

| Invariant | Asserted at SEQ-1 step | File |
|---|---|---|
| INV-O4 (envelope atomicity - via IR-O4) | 2, 12 | overseer-beta.md §1.6 |
| INV-SN1 (Session envelope atomicity, row-lock) | 2, 12 | session-beta.md §2.7 |
| INV-SV2 (Service refs Session in active/expiring) | 2 | service-beta.md §2.5 |
| INV-SV1 (Service-Binding count consistency) | 6, 22 | service-beta.md §2.5 |
| INV-A10 (Agent has non-empty Skills before Ready) | 14 | agent-beta.md §2.1 |
| INV-B1 (Binding has Active only after Channels Open) | 21 (B-T3 guard) | binding-beta.md §2.3 |
| INV-B2 (Binding's manifest_id immutable) | 6, 21 | binding-beta.md §2.3 |
| INV-B5 (release_reason immutable) | branch §3.1.3 B-T2 grace path | binding-beta.md §2.3 |
| INV-T1 (Task has compute_slot_id from Accepted onward) | 25 | task-beta.md §2.2 |
| INV-CS1 (1:1 Task <-> Slot runtime) | 26 | compute-slot-beta.md §2.8 |
| INV-CS3 (Pipeline single-activation, v0.1 scope) | 5 (partial index) | compute-slot-beta.md §2.8 |
| INV-CS7 (field-fill consistency) | 5, 26 (CHECK constraint) | compute-slot-beta.md §2.8 |
| INV-CH1 (Open implies handshake complete) | 10, 15, 27, 28 (CH-T2) | channel-beta.md §2.10 |
| INV-CH2 (Channel ID uniqueness) | 10, 15, 27 (CH-T1) | channel-beta.md §2.10 |
| INV-CH6 (ManifestChannel embedded) | 17 | channel-beta.md §2.10 |
| INV-SK1..INV-SK4 (Sink provisioning) | 18, 19 | sink-beta.md §2.11 |
| INV-P1 (Envelope wraps every cross-boundary message) | every wire step | proto-catalog-beta.md |
| INV-P2 (`session_id` required post-registration) | every post-step-13 envelope | proto-catalog-beta.md |
| INV-P6 (Event delivery is Session-scoped) | every Event emission | proto-catalog-beta.md |
| INV-M3 (`accept_task` (T-T1) commits before `manifests.body` is persisted) | 4 (composition + augmentation), 6 (B-T1 commit); precedes step 23 spec ordering | manifest-beta.md |
| INV-M4 (`manifests.body` carries the FULL augmented shape, never rewritten) | 6 (B-T1 commit), 17 (delivered to agent verbatim - via gRPC handshake under BYO-infra) | manifest-beta.md |

### §3.1.5 Timing budget

Reference values live in `timeouts-beta.md`; this table is informational. Phase A is bounded by Overseer transaction budgets (sub-second on a healthy DB); Phase B is bounded by Agent-side handshakes plus the pause window.

| Boundary | Budget | Source |
|---|---|---|
| **Phase A pause window (B-T1 issuance -> A-T1 receipt)** | **60000ms** | **`binding.pending_grace_ms`** |
| CommandChannel open (CH-T1 -> CH-T2) | 2000ms | `gateway.handshake_timeout_ms` |
| Registration -> Ready (A-T1 -> A-T2) | 30000ms | `agent.registration_window_ms` |
| TelemetryChannel open (CH-T1 -> CH-T2) | 2000ms | same |
| Manifest dispatch + ack (step 17 -> 20) | 10000ms | `service.deploy_dispatch_timeout_ms` |
| Sink handshake (SK-T1 -> SK-T2) | 5000ms | `sink.open_budget_ms` |
| B-T3 activation (step 20 -> 21) | 5000ms | `binding.pending_ack_ms` |
| T-T2 accept ack (step 24 -> 25) | 5000ms | `task.accept_ack_ms` |

A healthy Deploy completes Phase A in <1s and Phase B in <5s once the researcher's `docker run` lands. Pause-window expiry fires B-T2 grace per §3.1.3; Phase B step expiry transitions the Service to Stopped per §3.1.3.

### §3.1.6 Recovery behavior during SEQ-1

If the Overseer crashes mid-sequence, `overseer-beta.md §1.7` Recovery applies. Behavior differs by which architectural phase the crash interrupted:

- **Crash inside Phase A.** Each Phase A step is its own DB transaction; partial state is the issue. SV-T1 + workspace INSERT is one transaction; SV-T2 start (`UPDATE services.status='deploying'`) is its own; CS-T1 + B-T1 + manifest INSERT is one transaction. On restart, Stage 2 sweeps `services` and `bindings` rows with no terminal state set: a `services.status='deploying'` row whose Binding is missing rolls back to `stopped` with `stopped_reason='deploy_canceled'`; a `bindings.status='pending'` row whose grace timer has not yet expired stays in `pending` and the live ticker (`§1.7`) re-arms with the original `created_at`. The webapp's `DeployServiceResponse` is lost only if the crash interrupted between B-T1 and the response write - the operator re-reads `GET /api/services/{id}` to recover the `binding_id` (the `gateway_url` is fixed; the `token` can be re-minted from the persisted Binding row by an admin endpoint, later).

- **Crash inside the Phase A -> Phase B pause window.** Stage 1 of `§1.7` releases stale Pending Bindings - bindings older than `binding.pending_grace_ms` fire B-T2 with `release_reason='registration_grace_timeout'` and the cascade runs as in §3.1.3. Bindings within the grace window are kept pending; the live ticker resumes monitoring. The researcher's docker run, if launched mid-crash, retries Gateway connection (the SDK's reconnection loop) and Phase B begins on the new Overseer's gateway_consumer.

- **Crash inside Phase B.** Stage 1 re-probes CommandChannel, TelemetryChannel, ArtifactChannel for connected Agents. Channels stay Open through Overseer restart (INV-GW1; the Gateway is a separate process from the Overseer and survives the restart). Stage 2 sweeps `agents` / `bindings` / `tasks` rows. A Binding in `pending` whose Agent has reached `ready` is resumed at step 17 (Manifest transmit) - idempotent via `manifests.idempotency_key`. A Binding in `pending` whose Agent is in `lost` cascades B-T7 + B-T6 with `release_reason='agent_lost'` (later, when SEQ-3 lands; v0.1-beta-2 conservatively cascades B-T2 grace).

- **BYO-infra delivery: Phase A atomicity simplifies the crash window (v0.1-beta-2).** Under handshake-delivery the agent never waits on a server-internal transport - the augmented `manifests.body` is either committed (the gRPC handshake will return it on reconnect) or not (Phase A's transaction stack rolled back; the boot reconciler's existing "stale pending Binding" sweep handles it). No agent-side timeout, no `manifests.transmitted_at IS NULL` republish branch. The server-internal Kafka publish on `control.manifests` may have failed during Phase A - that publish is not load-bearing for v0.1-beta-2 (`manifest-beta.md §2.4` / §5.4), so the failure is logged but does not affect agent delivery. future work that adds a `control.manifests` consumer will revisit this trade-off.

### §3.1.7 Related sequences

The sequences that layer on top of SEQ-1's groundwork:

- **SEQ-2 Delete** (use-case step 6) - specified below in §3.2.
- **SEQ-3 Agent Disconnect** - A-T11 Lost fires mid-SEQ-1; branches into restart (A-T8, §2.1.5 lineage) or terminate via A-T15 after grace. Folded into SEQ-4 Stage 2 (§3.4.6) rather than a standalone section.
- **SEQ-4 Overseer Crash Recovery** - specified in §3.4; backed by the durable `channels` table so `INV-CH5`/`INV-CH7` survive restart.
- **SEQ-5 Graceful Shutdown (Platform Drain)** - specified in §3.5; uses the durable Channel state and the `agent.reconnect_grace_ms` tunable.

---

## SEQ-2: Delete (RemoteAgent)

The operator deletes an Agent from the webapp. The sequence ends when the Agent's Binding is Released, its Tasks Completed, its ComputeSlot Vacant, its Service Stopped (if this was the Service's last Binding), the Agent Terminated, and the Session envelope counters decremented. Backs `../txy/txy-beta.md §6`. Delete is a **System Operation** (taxonomy §Operations / Delete), not a user-issued Command; the Overseer decomposes it internally into two wire Commands dispatched serially: `BINDING_RELEASE` then `AGENT_TERMINATE`.

### Participants

| Role | FSM / system |
|---|---|
| Operator | Webapp -> Overseer REST admission |
| Gateway | `gateway-beta.md §2.9` (unchanged from SEQ-1; INV-GW1 preserves CommandChannel through the sequence) |
| CommandChannel, TelemetryChannel, ArtifactChannel(s) | `channel-beta.md §2.10` (provisioning-contract only; close is transport-layer, not a normative FSM transition in v0.1) |
| Overseer | `overseer-beta.md §1` |
| Session | `session-beta.md §2.7` |
| Agent (RemoteAgent) | `agent-beta.md §2.1` (A-T4 Bound -> Ready; new A-T16 Ready -> Terminated) |
| Service | `service-beta.md §2.5` (SV-T10 Active -> Stopped shortcut) |
| Binding | `binding-beta.md §2.3` (B-T4 -> B-T6 -> B-T8) |
| Workspace | row only (`schema-beta.md workspaces.destroyed_at`) |
| ComputeSlot | `compute-slot-beta.md §2.8` (CS-T3 -> CS-T4) |
| Task | `task-beta.md §2.2` (T-T8 Running -> Stopping -> T-T9 Completed) |
| Sink | `sink-beta.md §2.11` (provisioning-contract only; teardown is operational) |
| Artifacts | `schema-beta.md artifacts` (final DataArtifact lineage row from the drain flush) |
| Persistence | `schema-beta.md` (Postgres) |

### Preconditions

- Overseer is in `ready` (§1.3). Subsystems healthy.
- Gateway is in `ready`.
- Session is in `active`.
- Service `SVC-*` is in `active`.
- Agent `RA-*` is in `bound`, holding exactly one active Binding `BND-*` (one-Binding-per-Agent is the v0.1 shape; multi-Binding-per-Agent is out of scope).
- Binding `BND-*` is in `active` with exactly one Task under the single-Task Manifest restriction (taxonomy §Tasks / beta scope).
- Task is in `running` on ComputeSlot `CS-*` (`occupied`).
- All four of SEQ-1's Channels are Open: CommandChannel, TelemetryChannel, ArtifactChannel × 2.

### §3.2.1 Choreography - happy path

Steps are numbered. Each step names the triggering transition (or wire frame) and its Effects. Persistence writes are bracketed. Wire frames use proto-catalog message names.

**Architectural split (mirrors §3.1.1 SEQ-1).** SEQ-2 implements as a two-phase walker keyed on the BINDING_RELEASE CommandAck round-trip:

- **Phase A - Overseer-side synchronous.** Steps 1-6. Run inside `Scheduler::delete_agent` in response to the operator's `DELETE /api/agents/{id}`. Composes Command{BINDING_RELEASE}, sends it, fires the immediately-local B-T4 + T-T8 cascade, returns 202 Accepted to the webapp with `(agent_id, binding_id, command_id)`.
- **Phase B - ack-driven.** Steps 8-21. Run inside `Scheduler::complete_release` callable from `gateway_consumer` on receipt of `lifecycle.events.CommandAck` for the BINDING_RELEASE command. Drives T-T9 -> CS-T3/CS-T4 -> B-T6 (with workspace destroy as part of the same transaction, see step 13) -> B-T8 -> A-T4 -> SV-T10 -> composes+dispatches AGENT_TERMINATE -> A-T16. Steps 22-23 (channel teardown + webapp confirmation) follow as transport/observation events.

The pause window between Phase A return and CommandAck arrival is bounded by `gateway.command_ack_window_ms` (5s; see §3.2.5). On expiry, `Scheduler::sweep_pending_commands` (`overseer-beta.md §1.7` Step 2 + the live ticker per §1.8.2) routes through `handle_agent_lost` per §3.2.3 Agent Lost branch.

**Phase A - Operator trigger & Command composition**

1. **Operator clicks Delete** on Agent `RA-*` in the webapp. Webapp issues the Delete REST call against the Overseer control plane (out-of-band REST; no new wire message).
2. **Overseer resolves the delete target.** Read path: `SELECT * FROM agents WHERE agent_id = $1 AND session_id = $2`; then `SELECT ... FROM bindings WHERE agent_id = $1 AND status IN ('active','draining')`. Exactly one Binding is expected under the v0.1 shape.
3. **Overseer composes `Command{BINDING_RELEASE, BindingTarget(BND-*)}`** with a fresh `command_id`.
4. **Overseer sends Envelope{Command}** over the existing CommandChannel. No CommandChannel reopen; INV-GW1 keeps it intact from SEQ-1.

**Phase B - Binding Draining & Task Stopping (B-T4, T-T8)**

5. **Overseer fires B-T4** (Active -> Draining) for the target Binding.
   - Guard: Binding in Active.
   - Persist: `UPDATE bindings SET status='draining', draining_at=now() WHERE binding_id=$1 AND row_version=$2`.
   - Emit: Event `BindingDraining(binding_id, reason='operator_stop')`.
6. **IR-BT3 cascades: T-T8** fires (Running -> Stopping) for every non-terminal Task on the Binding. Under the v0.1 single-Task restriction this is exactly one Task.
   - Persist: `UPDATE tasks SET status='stopping', row_version=row_version+1 WHERE binding_id=$1 AND status='running'`.
   - Start `stop_drain_timeout` timer per Task (default 60s, `timeouts-beta.md task.stop_drain_timeout_ms`).
7. **Agent (SDK) drains.** Flushes in-flight buffers, completes the in-progress Emit. Produces a final Artifact per open ArtifactChannel:
   - `Envelope{ArtifactFrame{kind=ARTIFACT_KIND_DATA, lineage{service_id=SVC-*, task_id=TSK-*, restart_epoch=n, sequence=s+1}, sink_id=<ObjectSink>, partial=false, payload=<final Parquet batch>, payload_schema_ref=<pinned>}}` -> local ArtifactChannel (Parquet writer flushes and closes the file handle).
   - `Envelope{ArtifactFrame{kind=ARTIFACT_KIND_LOGS, ..., sink_id=<TerminalSink>}}` -> upstream ArtifactChannel (final log line). Optional per taxonomy.
   - External source connections (WSS, REST) closed.
   - Persist lineage rows on the platform side as frames land: `INSERT INTO artifacts (artifact_id, session_id, service_id, task_id, kind, sink_id, restart_epoch, sequence, payload_schema_ref, partial, emitted_at, ...) VALUES (...)`. `artifacts` is table 10 per `schema-beta.md`.

**Phase C - Task Completed (T-T9) + CommandAck**

8. **Overseer fires T-T9** (Stopping -> Completed) once drain completes within `stop_drain_timeout`.
   - Persist: `UPDATE tasks SET status='completed', completed_at=now()`.
   - Emit: Event `TaskCompleted(task_id, artifacts_emitted=<count>)`.
9. **Agent sends `Envelope{CommandAck{command_id=<BINDING_RELEASE>, outcome=Accepted}}`** on CommandChannel.

**Phase D - ComputeSlot release (CS-T3, CS-T4)**

10. **Overseer fires CS-T3** (Occupied -> Releasing) for `CS-*`.
    - Persist: `UPDATE compute_slots SET state='releasing', releasing_at=now()`.
    - Emit: Event `ComputeSlotReleasing`.
11. **Overseer fires CS-T4** (Releasing -> Vacant) once cleanup bookkeeping completes.
    - Persist: `UPDATE compute_slots SET state='vacant', current_activation_id=NULL, current_task_id=NULL, current_binding_id=NULL, released_at=now()`.
    - The field-fill CHECK constraint on `compute_slots` asserts INV-CS7.
    - Emit: Event `ComputeSlotVacant`.

**Phase E - Binding Releasing & Released (B-T6, B-T8) + Workspace destroy**

12. **Overseer fires B-T6** (Draining -> Releasing) now that all Tasks are terminal.
    - Guard: every Task on this Binding ∈ {Completed, Failed}.
    - Persist: `UPDATE bindings SET status='releasing', releasing_at=now(), release_reason='operator_stop'`. `release_reason` is immutable from this point (INV-B5).
    - Emit: Event `BindingReleasing`.
13. **Overseer destroys the Workspace** atomically with step 12's B-T6 transaction. Persist: `UPDATE workspaces SET destroyed_at=now() WHERE workspace_id=<BND-*.workspace_id>` issued in the same transaction as the B-T6 `UPDATE bindings`. No FSM for Workspace in v0.1; workspace is service-lifecycle-scoped and cleared as an effect of the Binding release. Implementation note: the workspace destroy effect lives inside the `transition_binding_to_releasing` primitive (B-T6) and the `force_release_binding` primitive (B-T7, agent-lost path per §3.2.3); the SV-T10 primitive at step 16 does not carry this effect (workspace destroy is owned by B-T6/B-T7, not SV-T10).
14. **Overseer fires B-T8** (Releasing -> Released).
    - Guard: INV-B7 holds (no bound Task in a non-terminal state).
    - Persist: `UPDATE bindings SET status='released', released_at=now()`.
    - Emit: Event `BindingReleased(release_reason='operator_stop')`.
    - Drives IR-AB2: Agent A-T4 since this is the Agent's last Binding.
    - Drives IR-SVB: Service SV-T10 since this is the Service's last non-Released Binding **and** `release_reason ≠ task_rejected` (INV-SV6 satisfied).

**Phase F - Agent Ready & Service auto-stop (A-T4, SV-T10)**

15. **Overseer fires A-T4** (Bound -> Ready) for the Agent.
    - Guard: no Bindings in {Active, Draining, Releasing}.
    - Persist: `UPDATE agents SET status='ready', updated_at=now()`.
    - Emit: Event `AgentReady`.
16. **Overseer fires SV-T10** (Active -> Stopped) for the Service.
    - Guard (INV-SV6): `release_reason ≠ task_rejected` - satisfied, it's `operator_stop`.
    - Persist (one transaction with the Session envelope update): `UPDATE services SET status='stopped', stopping_at=now(), stopped_at=now(), stopped_reason='delete_last_agent'`; `UPDATE sessions.envelope_counters` decrementing the services count, wrapped in `SELECT ... FOR UPDATE` on the sessions row (INV-SN1).
    - Emit: Event `ServiceStopped(service_id, stopped_reason='delete_last_agent')`.

**Phase G - Agent Terminate (A-T16)**

17. **Overseer composes `Command{AGENT_TERMINATE, AgentTarget(RA-*)}`** with a fresh `command_id`.
18. **Overseer sends Envelope{Command}** over CommandChannel. Precondition for A-T16 now holds (Agent in Ready).
19. **Agent receives AGENT_TERMINATE.** Begins graceful shutdown: closes any SDK-local state; does not emit further Artifacts.
20. **Overseer fires A-T16** (Ready -> Terminated) for `RA-*`.
    - Guard: Agent in Ready; no Bindings in {Active, Draining, Releasing}.
    - Persist (wrapped in `SELECT ... FOR UPDATE` on the sessions row): `UPDATE agents SET status='terminated', terminated_at=now(), terminated_reason='operator_stop'`; `UPDATE sessions.envelope_counters` decrementing the agents count (e.g., 3 -> 2).
    - Emit: Event `AgentTerminated(agent_id, terminated_reason='operator_stop')`.
21. **Agent sends `Envelope{CommandAck{command_id=<AGENT_TERMINATE>, outcome=Accepted}}`** and exits. The SDK process may now terminate.

**Phase H - Channel teardown (transport-layer; Channel FSM §2.10 is provisioning-contract only in v0.1)**

22. **Gateway observes CommandChannel and TelemetryChannel close** as the SDK disconnects. ArtifactChannels close with their Sink handles (local ObjectSink file closed in Phase B; upstream TerminalSink stream closed after final frame in Phase B). SEQ-2's Delete path takes the Channels straight to `closed`/`failed` (terminal) - it does not route through the SEQ-5 Drain (`CH-T3 Draining -> CH-T4 Closed`) sequence, because there is no reconnection target (the Agent is being terminated, not drained-for-resume). With the durable `channels` table now present (`schema-beta.md` table 12), the terminal rows MAY be written for audit, but SEQ-2's correctness does not depend on them; if omitted, SEQ-4 Stage 1 re-probe reconciles any residual rows to `failed`.

**Phase I - Webapp confirmation**

23. **Webapp receives** the `BindingReleased`, `ServiceStopped`, and `AgentTerminated` events (in that causal order). Renders the Agent as removed; updates the Session resource tile from `3/3` to `2/3`. Operator may now Deploy a new Service into the now-vacant ComputeSlot.

**Sequence complete.** The Service's row and its lineage (`manifests`, `tasks`, `artifacts`) are preserved under `service_id = SVC-*` for audit; the Service is terminal (Stopped) and re-Deploying the same Pipeline creates a new Service under a new Service ID.

### §3.2.2 Happy-path swimlane

```
SDK                     Gateway          Overseer         Persistence        Event bus
 |                         |                 |                  |                 |
 |                         |                 |<-- REST Delete   |                 |
 |                         |                 |    (out-of-band) |                 |
 |                         |                 |                  |                 |
 |                         |                 |--B-T4----------->|-BindingDraining>|
 |                         |                 |  [UPD bindings]  |                 |
 |<--Cmd{BINDING_RELEASE}--|<----------------|                  |                 |
 |                         |                 |--T-T8----------->|                 |
 |                         |                 |  [UPD tasks      |                 |
 |                         |                 |   status=stopping]|                |
 |--ArtifactFrame{final}-->|                 |                  |                 |
 |  (Parquet + TerminalSink)                 |                  |                 |
 |                         |                 |  [INS artifacts] |                 |
 |--CommandAck(BR, OK)---->|---------------->|                  |                 |
 |                         |                 |--T-T9----------->|-TaskCompleted-->|
 |                         |                 |  [UPD tasks]     |                 |
 |                         |                 |--CS-T3---------->|-CSReleasing---->|
 |                         |                 |--CS-T4---------->|-CSVacant------->|
 |                         |                 |  [UPD slots]     |                 |
 |                         |                 |--B-T6----------->|-BindingReleasing|
 |                         |                 |  [UPD bindings,  |                 |
 |                         |                 |   UPD workspaces]|                 |
 |                         |                 |--B-T8----------->|-BindingReleased>|
 |                         |                 |  [UPD bindings]  |                 |
 |                         |                 |--A-T4----------->|-AgentReady----->|
 |                         |                 |  [UPD agents]    |                 |
 |                         |                 |--SV-T10--------->|-ServiceStopped->|
 |                         |                 |  [UPD services,  |                 |
 |                         |                 |   UPD sessions]  |                 |
 |<--Cmd{AGENT_TERMINATE}--|<----------------|                  |                 |
 |                         |                 |--A-T16---------->|-AgentTerminated>|
 |                         |                 |  [UPD agents,    |                 |
 |                         |                 |   UPD sessions]  |                 |
 |--CommandAck(AT, OK)---->|---------------->|                  |                 |
 |  <SDK exits>            |                 |                  |                 |
 |                         | <Channels close>|                  |                 |
```

### §3.2.3 Failure branches

- **Drain timeout (T-T10)** - `task.stop_drain_timeout_ms` expires with drain incomplete. Task: Stopping -> Failed via T-T10 with `partial=true` on any in-flight Artifacts; `CommandAck(command_id=<BINDING_RELEASE>, status=PARTIAL)`. Binding: B-T6 fires with `release_reason = 'force'` (not `'operator_stop'`). Service: still SV-T10 (INV-SV6 - `force ≠ task_rejected`). Delete completes with the `force` release reason; lineage artifacts are preserved but flagged `partial`.
- **`BINDING_RELEASE` CommandAck timeout** - No ack within `gateway.command_ack_window_ms` (5s). Error: `DISPATCH_TIMEOUT` (44). At-least-once semantics apply: Overseer re-reads Binding state before retrying; if Binding is already in Draining with Tasks in Stopping, the retry is a no-op. Actual drain is bounded by `task.stop_drain_timeout_ms` independently.
- **Agent Lost during drain (A-T12)** - `A-T12` fires (Draining -> Lost) with 120s grace. On grace expiry, A-T15 drives B-T7 force-release with `release_reason='agent_lost'`. B-T7 carries the workspace destroy effect (`UPDATE workspaces SET destroyed_at=now()`) atomically in its transaction, parallel to step 13 in the happy path - required for the "identical structural outcome" clause below to hold. Service transitions via SV-T10 (`agent_lost ≠ task_rejected`, INV-SV6 holds). The Agent is Terminated via A-T15, not A-T16; Phase G is skipped. Structural outcome - Binding Released, Service Stopped, ComputeSlot Vacant, Workspace destroyed, envelope decrement - is identical; only the release/termination reasons differ.
- **`AGENT_TERMINATE` rejected (A-T16 guard fails)** - Target Agent holds a non-Released Binding at Phase G (race: a concurrent Bind fired between Phases F and G). Error: `COMMAND_TARGET_WRONG_STATE` (41). Overseer re-enters Phase E for the residual Binding. v0.1 single-Binding-per-Agent shape makes this race narrow.
- **Persistent storage loss mid-sequence** - Any `UPDATE` rejects with `SUBSYSTEM_LOSS_PERSISTENT_STORAGE` (70); Overseer transitions to `Degraded` (event `OverseerDegraded`). Delete pauses; resume is driven by Recovery (§3.2.6). Row-version optimistic concurrency (`row_version` on `bindings`, `services`, `agents`, `compute_slots`) ensures retries stay correct.
- **Event bus loss during emission** - `SUBSYSTEM_LOSS_EVENT_BROADCAST` (73); transitions still land, event fan-out is best-effort. Webapp degraded banner per §1.4.
- **Gateway unavailable during AGENT_TERMINATE dispatch** - `GATEWAY_UNAVAILABLE` (60). Phase G retries after backoff; Phases A-F are already persisted so the sequence resumes at Phase G cleanly.

### §3.2.4 Invariants asserted during SEQ-2

| Invariant | Asserted at SEQ-2 step | File |
|---|---|---|
| INV-B4 (Binding monotone progression) | 5, 12, 14 | `binding-beta.md §2.3.3` |
| INV-B5 (`release_reason` immutable) | 12 (entry to Releasing) | `binding-beta.md §2.3.3` |
| INV-B7 (Releasing implies Tasks terminal) | 14 (B-T8 guard) | `binding-beta.md §2.3.3` |
| INV-T5 (terminal absorbingness) | 8 (T-T9) | `task-beta.md §2.2.3` |
| INV-A3 (Ready has no active work) | 15 (A-T4), 20 (A-T16 guard) | `agent-beta.md §2.1.3` |
| INV-A5 (Stop is PlatformAgent-only) | 17 - `AGENT_TERMINATE ≠ Stop`; `A-T16` does not violate | `agent-beta.md §2.1.3` |
| INV-A7 (Terminated is absorbing) | 20 | `agent-beta.md §2.1.3` |
| INV-CS1 (1:1 Task <-> Slot runtime) | 11 (CS-T4 post-condition) | `compute-slot-beta.md §2.8` |
| INV-CS7 (field-fill consistency) | 11 (CHECK constraint on `compute_slots`) | `compute-slot-beta.md §2.8` |
| INV-SV6 (auto-stop excludes `task_rejected`) | 16 (SV-T10 guard) | `service-beta.md §2.5` |
| INV-SN1 (Session envelope atomicity, row-lock) | 16, 20 | `session-beta.md §2.7` |
| INV-P1 (Envelope wraps every cross-boundary message) | every wire step | `proto-catalog-beta.md` |
| INV-P3 (one Event variant per boundary-crossing transition) | all emitted Events | `proto-catalog-beta.md` |
| INV-P4 (`restart_epoch` propagates) | 7 (final ArtifactFrame) | `proto-catalog-beta.md` |

### §3.2.5 Timing budget

Reference values live in `timeouts-beta.md`; this table is informational.

| Boundary | Budget | Source |
|---|---|---|
| `BINDING_RELEASE` CommandAck | 5000ms | `gateway.command_ack_window_ms` |
| Task drain (T-T8 -> T-T9 or T-T10) | 60000ms | `task.stop_drain_timeout_ms` |
| Binding drain budget (total) | 60000ms | `binding.drain_budget_ms` |
| Workspace destroy | - | no explicit budget; bounded by DB write |
| `AGENT_TERMINATE` CommandAck | 5000ms | `gateway.command_ack_window_ms` |

A healthy Delete completes well under the sum of these budgets. Budget expiry on drain takes the T-T10 failure branch described in §3.2.3.

### §3.2.6 Recovery behavior during SEQ-2

If the Overseer crashes mid-sequence, `overseer-beta.md §1.7` Recovery applies:

- **Stage 1** re-probes Channels. INV-GW1 preserves CommandChannel / TelemetryChannel through Overseer restart (the Gateway is a separate process). ArtifactChannels that were mid-drain may have closed on the Agent side when the final Emit completed; re-probe confirms.
- **Stage 2** sweeps Binding / Task / Service rows. A Binding in `draining` with all Tasks in `completed` resumes at B-T6 -> B-T8 (Phase E). A Binding in `releasing` resumes at B-T8 (Phase E step 14). A Service in `active` with all Bindings `released` resumes at SV-T10 (Phase F step 16). An Agent in `ready` with a pending AGENT_TERMINATE (in-flight Command) resumes at Phase G (step 17) via dispatch-idempotent re-send by `command_id`.
- **Channel state during SEQ-2** - even before the `channels` table landed (`schema-beta.md` table 12), SEQ-2 Recovery was safe because all channels in play are already terminal or terminating when Recovery runs - there is no ongoing steady-state Artifact emission to reconcile. With the durable table now present, SEQ-4 Stage 1 re-probes any residual SEQ-2 channel rows the same way it does for SEQ-5; SEQ-2's correctness does not depend on it.

### §3.2.7 Open issues

- **`AGENT_TERMINATE` as a System Operation primitive.** A-T16 is new in v0.1-beta-2. If later work introduces a first-class `Delete` wire message that bundles both sub-Commands, Phase A / Phase G merge; the underlying FSM transitions remain the same.
- **Wire `TASK_CANCEL` / `TaskCanceled` without matching FSM transition.** `CommandKind.TASK_CANCEL = 44` and `Event.TaskCanceled` exist in `proto-catalog-beta.md` but no `T-T` transition writes a `canceled`-equivalent state today. Reconcile later either by removing the enum members or by introducing a `Canceled` state in `task-beta.md §2.2.1`.
- **`services.stopped_reason` broader than `stopped_reason_intent`.** A precedence-alignment drift; not exercised by Step 6, left for a follow-up pass.

---

## SEQ-4: Overseer Crash Recovery

The Overseer process restarts (crash, OOM-kill, deploy rollout) and must reconcile durable state before resuming work. The sequence begins at process boot in `initializing` (§1.2) and ends with the Overseer in `ready` (all subsystems healthy, all in-flight entities reconciled) or `degraded` (a subsystem is still down). This is **not** an operator- or Agent-triggered sequence - it is self-driven on boot. It is the cross-FSM trace of the reconciliation protocol specified normatively in `overseer-beta.md §1.7`; this section adds the durable-`channels`-table view and the per-FSM transition accounting that §1.7's prose leaves implicit. Backs `../txy/txy-beta.md §7` (the platform half of Drain -> Recovery; the researcher-side half is SEQ-5).

The key property SEQ-4 guarantees is **INV-O5 (Reconciliation before Ready)**: the Overseer admits no new System Operation until every pre-crash Binding, Command, Channel, and Agent has been resolved to a definite state.

### Participants

| Role | FSM / system |
|---|---|
| Overseer | `overseer-beta.md §1` (T1 Initializing -> Ready / Degraded) |
| Gateway | `gateway-beta.md §2.9` - **separate process, survives the Overseer crash** (IR-O6) |
| Agent(s) (RemoteAgent) | `agent-beta.md §2.1` - survive on client hardware; may be `bound`, `draining`, or `lost` from the Overseer's pre-crash view |
| Session | `session-beta.md §2.7` (rows reloaded; envelope counters re-derived) |
| Service / Binding / Task / ComputeSlot | rows reloaded and swept |
| Channel | `channel-beta.md §2.10` - re-probed via the durable `channels` table (table 12) |
| Command | `schema-beta.md commands` - pending log swept (`overseer-beta.md §1.7` step 2) |
| Persistence | `schema-beta.md` (Postgres) - **assumed recovered**; if down, SEQ-4 cannot start (Overseer stays `initializing`/`degraded`) |
| Event bus | re-attached; `OverseerReady` / `OverseerDegraded` emitted at settle |

### Preconditions

- The Overseer process is starting fresh; in-memory state is empty.
- Persistent Storage is reachable (if not, the Overseer cannot leave `initializing` - see §3.4.3).
- The Gateway is independently `ready`/`listening` (IR-O6); RemoteAgent transports it holds are intact (INV-GW1 - they survived the Overseer crash because the Gateway is a separate process).
- Durable rows from before the crash exist: `bindings`, `tasks`, `services`, `commands`, `channels`, `agents`, `sessions`.

### §3.4.1 Choreography - happy path

Stages mirror `overseer-beta.md §1.7`. Persistence reads/writes are bracketed.

**Stage 0 - Boot & subsystem probe**

1. **Process boots into `initializing`** (Overseer state S-O1). In-memory registries empty.
2. **Probe the four subsystems** - persistent storage, message delivery, process spawning, event broadcast. Each healthy probe clears its subsystem-loss flag. Persistent storage MUST be healthy to proceed past Stage 0; the other three may be absent (the Overseer would settle into `degraded` at Stage 3, not `ready`).

**Stage 1 - Channel & live-Binding re-probe** (budget `overseer.reconcile_stage1_budget_ms`, 30s)

3. **Load live Bindings**: `SELECT * FROM bindings WHERE status IN ('pending','active','draining')`.
4. **Re-probe Channels per Binding** using the durable `channels` table: `SELECT * FROM channels WHERE binding_id = $1 AND status IN ('opening','open','draining','backpressured','error')` (backed by `channels_live_idx`). For each:
   - Transport still held by the Gateway (INV-GW1 / INV-CH5: the row was `open` with a `restart_epoch`, and the Gateway confirms the connection) -> Channel stays `open`; no write.
   - Transport gone (Gateway reports no connection) -> CH-T10: `UPDATE channels SET status='failed', closed_at=now()`. A `failed` Channel on a live Binding marks that Binding for force-release in Stage 2.
5. **Resolve `pending` Bindings** (§1.7 step 1): Agent never connected -> B-T2 release (`release_reason='registration_grace_timeout'` if past `binding.pending_grace_ms`, else leave for the live ticker); Agent connected pre-crash but Binding never activated -> resume Phase B of SEQ-1 (re-activate, manifest served from `manifests.body` via handshake - no republish, INV-M4).

**Stage 2 - Orphan sweep** (budget `overseer.reconcile_stage2_budget_ms`, 2min)

6. **Reconcile `active` Bindings' Agents** (§1.7 step 1, IR-O5):
   - RemoteAgent connected (Gateway lifecycle topic + Stage 1 Channel `open`) -> Binding valid; resume management.
   - RemoteAgent disconnected -> start/resume the `agent.reconnect_grace_ms` (60s) window; this is the **SEQ-3 Agent Disconnect** path folded in. On reconnect within grace -> A-T14 (Lost -> prior state), Channel stays `open`. On grace expiry -> A-T15 (Lost -> Terminated), B-T7 force-release (`release_reason='agent_lost'`), CH-T10 on the Binding's Channels, workspace destroy in the B-T7 transaction.
7. **Reconcile `draining` Bindings** (§1.7 step 1, the prior-Drain survivors - the SEQ-5 reconnection target): wait up to `agent.reconnect_grace_draining_ms` (120s) for RemoteAgent reconnection. On reconnect -> match to the draining Binding, transition back to `active` (resume telemetry + command flow, Channel `draining`->`open` is a no-op since INV-CH5 kept it open), log "resumed draining binding". On timeout -> B-T7 release, CH-T10, log "draining binding timed out".
8. **Sweep `pending` Commands** (§1.7 step 2): `SELECT * FROM commands WHERE status='pending'` (backed by `commands_pending_issued_idx`). Issued > `command_timeout` ago -> `UPDATE commands SET status='timeout', completed_at=now()`. Else -> re-deliver by `command_id` (dispatch-idempotent).
9. **Sweep orphaned Services** (§1.7 step 3): `active` Service with no `active` Binding -> SV-T10 `UPDATE services SET status='stopped', stopped_at=now(), stopped_reason='delete_last_agent'` + envelope decrement.

**Stage 3 - Settle**

10. **Re-derive Session envelope counters** from the reconciled child-row counts (defends against `envelope_counters` drift left by any pre-crash raw-SQL cleanup - see §3.4.3) and `UPDATE sessions.envelope_counters` under `SELECT ... FOR UPDATE` (INV-SN1).
11. **Settle Overseer state**: all four subsystems healthy -> O-T1 `OverseerReady` (S-O3 Ready). A subsystem still down -> O-T3 `OverseerDegraded` (S-O4 Degraded), subsystem-loss flag retained, the `overseer.degraded_refresh_ms` (5s) probe loop continues until O-T4 `OverseerRecovered`. **Only now** are System Operations admitted (INV-O5).

**Sequence complete.** The Overseer holds an authoritative, ghost-free view; every pre-crash entity is in a definite state.

### §3.4.2 Boot-reconcile swimlane

```
(boot)        Persistence        Gateway           Channels(tbl)      Event bus
  |                |                |                    |                 |
  |--probe-------->| storage OK     |                    |                 |
  |--probe-------------------------->| ready (INV-GW1)   |                 |
  |--SELECT live bindings----------->|                   |                 |
  |<---------------|                 |                   |                 |
  |--SELECT live channels per binding------------------->|                 |
  |   Gateway holds transport? ----->| yes -> stay open  |                 |
  |                |                  | no  -> CH-T10 --->| status=failed   |
  |--resolve pending (B-T2 / resume SEQ-1 Phase B)       |                 |
  |--reconcile active agents (grace 60s; A-T14|A-T15+B-T7)                 |
  |--reconcile draining agents (grace 120s; resume|B-T7) |                 |
  |--sweep pending commands (timeout|re-deliver)         |                 |
  |--sweep orphan services (SV-T10) ->| [UPD services]   |                 |
  |--re-derive envelope_counters ---->| [UPD sessions]   |                 |
  |--settle: O-T1 Ready | O-T3 Degraded ---------------------------------->| OverseerReady
  |                                                                          | /Degraded
```

### §3.4.3 Failure branches

- **Persistent storage still down at Stage 0** - the Overseer cannot read any durable row. It does NOT leave `initializing` (or settles `degraded` with `persistent_storage=false` if partial). `SUBSYSTEM_LOSS_PERSISTENT_STORAGE` (70). No System Operation is admitted. The `overseer.degraded_refresh_ms` loop retries the probe. This is the one subsystem whose absence blocks recovery entirely.
- **Stage 1 budget exceeded** (`overseer.reconcile_stage1_budget_ms`, 30s) - too many live Bindings / slow Gateway probe. The Overseer settles `degraded` rather than blocking indefinitely; Stage 2 continues in the background under the `degraded` probe loop. New work is gated until Channels are resolved.
- **Channel row says `open` but Gateway has no transport** - the expected disconnect path; CH-T10 -> `failed` -> Binding force-release in Stage 2. Not an error, a reconciliation outcome.
- **`envelope_counters` drift** - a pre-crash raw-SQL cleanup (operator surgery) left `sessions.envelope_counters` inconsistent with the actual child-row counts. Stage 3 step 10 **recomputes** counters from `COUNT(*)` over reconciled `services`/`agents`/`tasks` rather than trusting the stored value. This closes the punch-list "`envelope_counters` drift after raw SQL cleanups (no recompute path)" gap: SEQ-4 Stage 3 *is* the recompute path.
- **Two Overseers race on boot** (rolling deploy overlap) - INV-O1 single-logical-owner is enforced by an advisory lock / leader election outside this sequence; the loser stays `initializing`. Out of scope for the FSM trace; noted so the reader knows reconciliation assumes a single writer.
- **Gateway also restarted** (correlated failure) - transports did NOT survive; every live Channel re-probes to `failed`; every Binding force-releases; Services stop. Recovery is correct but lossy - RemoteAgents re-register fresh via SEQ-1. This is the degenerate case INV-CH5/INV-GW1 do not cover (they cover Overseer-only restart).

### §3.4.4 Invariants asserted during SEQ-4

| Invariant | Asserted at SEQ-4 step | File |
|---|---|---|
| INV-O5 (Reconciliation before Ready) | 11 (settle gate) | `overseer-beta.md §1.5` |
| INV-O1 (Single logical Overseer) | 0 (leader election precondition) | `overseer-beta.md §1.5` |
| INV-CH5 (Gateway-persistent Channels survive restart) | 4 (Channel stays `open`) | `channel-beta.md §2.10` |
| INV-CH7 (Recovery re-probes live Channels) | 4 | `schema-beta.md` cross-table |
| INV-GW1 (Gateway transport independence) | 4, 6, 7 | `gateway-beta.md §2.9` |
| INV-B5 (`release_reason` immutable) | 6, 7 (B-T7) | `binding-beta.md §2.3.3` |
| INV-SN1 (Session envelope atomicity, row-lock) | 9, 10 | `session-beta.md §2.7` |
| INV-M4 (`manifests.body` carries augmented shape, served on reconnect) | 5 (SEQ-1 Phase B resume) | `manifest-beta.md §4` |
| INV-P3 (one Event per boundary-crossing transition) | 11 (O-T1/O-T3) | `proto-catalog-beta.md` |

### §3.4.5 Timing budget

| Boundary | Budget | Source |
|---|---|---|
| Stage 1 (Channel + live-Binding re-probe) | 30000ms | `overseer.reconcile_stage1_budget_ms` |
| Stage 2 (orphan sweep) | 120000ms | `overseer.reconcile_stage2_budget_ms` |
| Disconnected `active` Agent grace | 60000ms | `agent.reconnect_grace_ms` |
| Draining Binding reconnect window | 120000ms | `agent.reconnect_grace_draining_ms` |
| Pending Command staleness | `command_timeout` | `gateway.command_ack_window_ms` derived |
| Degraded re-probe cadence | 5000ms | `overseer.degraded_refresh_ms` |

### §3.4.6 Notes

- **Relationship to `overseer-beta.md §1.7`.** §1.7 is the normative protocol; SEQ-4 is its cross-FSM choreography view. Where they could diverge, §1.7 wins (Atlas precedence). The one thing SEQ-4 adds normatively is the **durable Channel re-probe** (step 4) - pre-Iteration-5 §1.7 re-probed Channels by live Gateway query only; the `channels` table makes the re-probe survivable and gives `failed` a durable home.
- **SEQ-3 Agent Disconnect is folded in.** A bare Agent disconnect (no Overseer crash) is the live-ticker analog of Stage 2 step 6: heartbeat miss (`agent.heartbeat_miss_threshold_ms`) -> A-T11 (Lost) -> `agent.reconnect_grace_ms` -> A-T14 (resume) or A-T15 (terminate + B-T7). It needs no separate section; the transitions and budgets are identical.

---

## SEQ-5: Graceful Shutdown (Platform Drain)

The platform operator drains the Overseer for maintenance (deploy, host migration, scale-down). Unlike SEQ-2 Delete - which tears a Service *down* - SEQ-5 puts the platform to sleep **without terminating researcher-side RemoteAgents**: they keep running on client hardware, detect the Gateway-leg closure, and enter a reconnection loop, so that when the platform returns (via SEQ-4) their `draining` Bindings re-activate and data collection resumes with lineage continuity. This is the researcher-resilience half of `../txy/txy-beta.md §7`. The defining contract is **IR-O2 (Drain asymmetry)**: PlatformAgents are Stopped and waited-on; RemoteAgents are *not* commanded - their Bindings are persisted `draining` and their Channels drained, and the Overseer does not wait for them.

### Participants

| Role | FSM / system |
|---|---|
| Operator (platform) | platform control plane -> Overseer (`SIGTERM` / admin drain endpoint) |
| Overseer | `overseer-beta.md §1` (O-T6 Ready -> Draining; -> Stopped) |
| Gateway | `gateway-beta.md §2.9` - closes its RemoteAgent legs as the Overseer drains (IR-O6) |
| Agent (RemoteAgent) | `agent-beta.md §2.1` - **not commanded**; detects closure, enters reconnect loop, keeps running |
| Agent (PlatformAgent) | `agent-beta.md §2.1` - receives Stop Command, drains, terminates (IR-O2) |
| Binding | `binding-beta.md §2.3` - RemoteAgent Bindings -> `draining` (persisted, not released); PlatformAgent Bindings -> released |
| Task | `task-beta.md §2.2` - T-T8 Stopping -> T-T9 Completed (final flush) |
| Channel | `channel-beta.md §2.10` - CH-T3 Draining -> CH-T4 Closed (durable in `channels`) |
| Sink | `sink-beta.md §2.11` - final Parquet flush + close |
| Webapp | renders "platform maintenance / reconnecting" overlay + Overseer health-mode = Draining |
| Persistence | `schema-beta.md` (Postgres) |

### Preconditions

- Overseer in `ready`. One or more `active` Bindings exist (mix of RemoteAgent and PlatformAgent).
- For each RemoteAgent Binding: CommandChannel + TelemetryChannel + ArtifactChannel(s) `open` in the `channels` table.

### §3.5.1 Choreography - happy path

**Phase A - Drain initiation (O-T6)**

1. **Operator signals drain** - `SIGTERM` to the Overseer process, or an admin drain endpoint. The Overseer fires **O-T6** (Ready -> Draining).
   - Persist: subsystem flags unchanged; Overseer state `draining`.
   - Emit: Event `OverseerDraining`. The webapp's health-mode indicator flips to **Draining** and the "platform maintenance - reconnecting" overlay arms (it shows once the WS connection drops in Phase D).
2. **Overseer partitions Bindings by Agent location** (IR-O2): RemoteAgent vs PlatformAgent.

**Phase B - PlatformAgent drain (commanded, waited-on)**

3. For each **PlatformAgent** Binding: Overseer composes `Command{AGENT_DRAIN | task_pause->stop, BindingTarget}` and dispatches in-process. Waits up to `service.stop_drain_budget_ms` (2min) for CommandAck. On ack -> T-T8 -> T-T9, CS-T3 -> CS-T4, B-T4 -> B-T6 -> B-T8 (released, `release_reason='normal'`), workspace destroy in the B-T6 tx, A-T5 -> A-T7 (drain, then terminate). On timeout -> force-stop the process, B-T7 (`release_reason='force'`). (This is structurally SEQ-2 Phase B-F driven by drain rather than delete.)

**Phase C - RemoteAgent drain (NOT commanded)**

4. For each **RemoteAgent** Binding: Overseer fires **B-T4** (Active -> Draining) - *persisted, not released*.
   - Persist: `UPDATE bindings SET status='draining', draining_at=now(), draining_reason='platform_drain'`.
   - Emit: Event `BindingDraining(reason='platform_drain')`.
5. **IR-BT3 cascade: T-T8** (Running -> Stopping) for the Binding's Task; the Overseer signals the SDK to checkpoint via the *closing* of the Channel rather than a Stop Command.
6. **Overseer fires CH-T3** (Open -> Draining) on the Binding's Channels: `UPDATE channels SET status='draining', drain_started_at=now()`. In-flight frames settle.
7. **RemoteAgent SDK performs a final flush**: completes the in-progress Emit, writes the final Parquet batch (Sink close), emits a final `ArtifactFrame{partial=false}` with the next `sequence` on the same `restart_epoch` (INV-CH4/INV-P4 continuity). Lineage rows land in `artifacts`.
8. **Overseer fires CH-T4** (Draining -> Closed) once in-flight settles within `agent.reconnect_grace_ms`: `UPDATE channels SET status='closed', closed_at=now()`. The Task is left at T-T9 Completed for this epoch; the **Binding stays `draining`** (it is NOT released - this is the difference from SEQ-2).

**Phase D - Gateway leg closure & researcher-side resilience**

9. **The Gateway closes its RemoteAgent transport legs** (IR-O6) as the Overseer finishes Phase C. The webapp WS connection drops; its overlay shows "platform maintenance - reconnecting".
10. **The RemoteAgent detects the closure and enters its reconnection loop** - it keeps running on client hardware, retrying the Gateway with backoff. It does NOT exit. Its external source connections (WSS) may stay open or be re-established by the SDK independently; no new Artifacts flow upstream while the platform is down (the upstream ArtifactChannel is Closed).

**Phase E - Overseer Stopped**

11. **Overseer waits only for PlatformAgent Bindings** (IR-O2) to reach Released/timeout. It does NOT wait for RemoteAgents. Once PlatformAgent Bindings are settled, the Overseer fires the Draining -> Stopped transition.
    - Persist: final state flush; `draining` RemoteAgent Bindings and their `closed` Channels remain durable for SEQ-4 to find.
    - Emit: Event `OverseerStopped`. Process exits.

**Sequence complete (platform asleep).** Durable residue: RemoteAgent Bindings in `draining`, their Channels in `closed`, their Tasks in `completed` for the pre-drain epoch, lineage in `artifacts`. The RemoteAgent process is alive and reconnecting. **Recovery is SEQ-4**: when the Overseer comes back, Stage 2 step 7 matches each reconnecting RemoteAgent to its `draining` Binding, transitions it back to `active`, and a fresh Task epoch resumes collection - lineage continues under the same `service_id`/`task_id` with an incremented `restart_epoch`.

### §3.5.2 Drain swimlane (RemoteAgent leg)

```
Operator     Overseer            Channels(tbl)     RemoteAgent SDK      Webapp
  |             |                     |                  |                |
  |--SIGTERM--->|--O-T6 Draining----------------------------------------->| health=Draining
  |             |  (Event OverseerDraining)              |                |
  |             |--B-T4 (persist draining, NOT release)  |                |
  |             |--T-T8 (Task Stopping) -->|             |                |
  |             |--CH-T3 ----------------->| status=draining               |
  |             |                          |--signal---->| final flush     |
  |             |                          |             |--ArtifactFrame->|
  |             |                          |<--settled---| (partial=false) |
  |             |--CH-T4 ----------------->| status=closed                 |
  |             |  (Binding STAYS draining)|             |                |
  |  <Gateway closes RemoteAgent leg> ----------------->| reconnect loop  |
  |             |                                        | (keeps running) | overlay:
  |             |--wait PlatformAgent bindings only------|                | "reconnecting"
  |             |--Draining -> Stopped (OverseerStopped) |                |
  |             |  <process exits>                       | ...retrying... |
  |          ( ... platform down ... )                   |                |
  |          ( SEQ-4 on restart: match draining binding, B back to active)|
```

### §3.5.3 Failure branches

- **RemoteAgent final-flush exceeds `agent.reconnect_grace_ms`** - CH-T4 cannot fire cleanly; the Channel force-closes via CH-T10 (`failed`) and the final Artifact is flagged `partial=true`. The Binding still stays `draining` (recoverable); SEQ-4 will resume it, and the partial frame is a known lineage gap, not a correctness break.
- **PlatformAgent drain timeout** - `service.stop_drain_budget_ms` (2min) expires; force-stop + B-T7 (`release_reason='force'`). Overseer proceeds to Stopped regardless (it must not hang on a stuck PlatformAgent).
- **Operator force-drain (no grace)** - an immediate shutdown skips Phase C settle; RemoteAgent Channels are left `open`/`draining` in the table and re-probe to `failed` in SEQ-4 Stage 1. Bindings still `draining` -> SEQ-4 attempts reconnect-resume; if the SDK's in-flight write was mid-batch, the next epoch starts clean (the partial batch is the SDK's local concern). Lossier but safe.
- **Overseer crashes mid-drain** - indistinguishable from SEQ-4's normal input: half-`draining` Bindings, some Channels `draining`/`closed`. SEQ-4 Stage 1/2 reconcile them. This is why SEQ-5 + SEQ-4 compose: SEQ-5's durable residue is exactly SEQ-4's expected input.
- **Persistent storage loss during Phase C** - `SUBSYSTEM_LOSS_PERSISTENT_STORAGE` (70); the `draining`/`closed` writes cannot land. Overseer -> `degraded`; drain pauses. On storage return, the drain resumes or the next boot's SEQ-4 reconciles from the last durable state.

### §3.5.4 Invariants asserted during SEQ-5

| Invariant | Asserted at SEQ-5 step | File |
|---|---|---|
| IR-O2 (Drain asymmetry: RemoteAgent not commanded) | 2, 4, 11 | `overseer-beta.md §1.6` |
| INV-CH3 (Reliability class immutable through drain) | 6, 8 | `channel-beta.md §2.10` |
| INV-CH4 (Sequence monotone within Channel) | 7 (final frame) | `channel-beta.md §2.10` |
| INV-P4 (`restart_epoch` propagates) | 7 | `proto-catalog-beta.md` |
| INV-B4 (Binding monotone progression) | 4 (-> draining) | `binding-beta.md §2.3.3` |
| INV-B-drain-not-release (RemoteAgent Binding stays draining) | 8, 11 | `binding-beta.md §2.3` / IR-O2 |
| INV-SN1 (envelope atomicity) | 3 (PlatformAgent release path) | `session-beta.md §2.7` |
| INV-GW1 (Gateway leg independence) | 9 | `gateway-beta.md §2.9` |

### §3.5.5 Timing budget

| Boundary | Budget | Source |
|---|---|---|
| PlatformAgent drain wait | 120000ms | `service.stop_drain_budget_ms` |
| RemoteAgent Channel drain settle (CH-T3 -> CH-T4) | 60000ms | `agent.reconnect_grace_ms` |
| Task final flush (T-T8 -> T-T9) | 60000ms | `task.stop_drain_timeout_ms` |
| RemoteAgent reconnect (across the restart) | 120000ms | `agent.reconnect_grace_draining_ms` (consumed in SEQ-4) |

### §3.5.6 Recovery behavior

SEQ-5 has no in-sequence recovery of its own - it *is* the controlled-shutdown half. Its output (durable `draining` Bindings + `closed` Channels) is the input to **SEQ-4 §3.4.1 Stage 2 step 7**, which performs the reconnect-and-resume. The two sequences are designed as a pair: SEQ-5 guarantees the residue is durable and self-consistent; SEQ-4 guarantees it is reconciled on return. Use-case step 7 ("researcher-side resilience") is demonstrable only when both run end-to-end: drain the platform, observe the RemoteAgent stay alive and reconnect, observe collection resume with `restart_epoch` incremented under the same `service_id`.

### §3.5.7 Open issues

- **`draining_reason` column on `bindings`.** Phase C step 4 writes `draining_reason='platform_drain'` to distinguish a platform-drain `draining` Binding (recoverable, SEQ-4 resumes it) from a delete-drain `draining` Binding (SEQ-2, will be released). `binding-beta.md §2.3.1` and `schema-beta.md bindings` should carry a `draining_reason` enum `{operator_stop, platform_drain}` - a one-line schema follow-up; until it lands, the two are disambiguated by whether a `BINDING_RELEASE` Command exists for the Binding (SEQ-2 has one, SEQ-5 does not).
- **`OverseerDraining` / `OverseerStopped` Event variants.** Confirm both exist in `proto-catalog-beta.md events.proto` (O-T6 emits `OverseerDraining`; the Draining -> Stopped transition emits `OverseerStopped`). If only `OverseerDegraded`/`OverseerReady` are wired, add the two drain variants in the typed-Envelope migration.
- **PlatformAgent docker spawn is the precondition for the Phase B half being live.** Until the PlatformAgent spawn path lands (backlog), SEQ-5 is exercised RemoteAgent-only; Phase B is spec-complete but untested against a real PlatformAgent.
- **Webapp overlay trigger.** The "reconnecting" overlay arms on `OverseerDraining` but renders on WS-drop; if the WS drop precedes the Event (race), the overlay must also key off the raw socket close, not only the typed Event. Webapp Drain-UX task detail.

## Sources

- [fsm-beta.md - §3 sequences index](fsm-beta.md)
- [overseer-beta.md - §1.3 Overseer states, §1.4 Matrix, §1.6 IR-O4, §1.7 Recovery](overseer-beta.md)
- [agent-beta.md - §2.1 Agent, incl. §2.1.5 restart lineage](agent-beta.md)
- [task-beta.md - §2.2 Task](task-beta.md)
- [binding-beta.md - §2.3 Binding](binding-beta.md)
- [service-beta.md - §2.5 Service](service-beta.md)
- [session-beta.md - §2.7 Session](session-beta.md)
- [compute-slot-beta.md - §2.8 ComputeSlot](compute-slot-beta.md)
- [gateway-beta.md - §2.9 Gateway](gateway-beta.md)
- [channel-beta.md - §2.10 Channel](channel-beta.md)
- [sink-beta.md - §2.11 Sink](sink-beta.md)
- [schema-beta.md - persistence writes named in SEQ-1](schema-beta.md)
- [proto-catalog-beta.md - Envelope, Registration, Manifest, Command, events](proto-catalog-beta.md)
- [errors-beta.md - failure-branch error kinds](errors-beta.md)
- [timeouts-beta.md - Phase timing budgets](timeouts-beta.md)
