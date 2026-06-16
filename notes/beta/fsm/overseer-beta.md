# Atelier FSM Atlas - Overseer (§1)

Part of the **State Machine Atlas v0.1-beta-2**. See `fsm-beta.md` for the reading guide, notation, file index, §2.4 FSMs scope status, and §3 Cross-FSM Sequences. Owns the `INV-O*` invariant prefix. Cross-references: `agent-beta.md` (§2.1), `task-beta.md` (§2.2), `binding-beta.md` (§2.3), `service-beta.md` (§2.5), `session-beta.md` (§2.7), `compute-slot-beta.md` (§2.8), `gateway-beta.md` (§2.9), `channel-beta.md` (§2.10), `sink-beta.md` (§2.11) - every other FSM cites §1 and the Operation Availability Matrix in §1.4.

---

## 1. Overseer FSM

The Overseer is the orchestration process that manages the lifecycle of all other entities. Its state determines the system's operational capability - what operations can be requested and what guarantees the system provides.

### 1.1 Dependencies

The Overseer requires four infrastructure subsystems (taxonomy §System Health). Each can be independently available or unavailable:

| Subsystem | Purpose |
|---|---|
| **Persistent Storage** | Durable state for Sessions, Services, Bindings, Tasks, Commands |
| **Message Delivery** | ManifestChannel and CommandChannel transport to RemoteAgents via Gateway |
| **Process Spawning** | PlatformAgent process lifecycle |
| **Event Broadcast** | WebSocket broadcast to the webapp dashboard |

The taxonomy defines three operational modes for the Overseer:

- **Full**: all four subsystems available -> all operations permitted.
- **Degraded**: one or more subsystems unavailable -> operations that require the unavailable subsystem are rejected with a specific error naming the subsystem; operations that do not require it continue normally.
- **Unavailable**: the Overseer is not accepting operations (during initialization, recovery, or drain).

### 1.1.1 Composition (logical vs physical)

The Overseer is **one logical actor**. Its FSM states (§1.2), transitions (§1.3), Operation Availability Matrix (§1.4), invariants (§1.5), interaction rules (§1.6), and reconciliation protocol (§1.7) all describe a single logical state machine. "Single logical Overseer" in `INV-O1` means exactly that - a single authoritative state per platform deployment, reached by at most one live owner at a time.

Internally, the logical Overseer integrates two orchestration concerns: envelope checking + Dispatch (Scheduler concerns) and Agent lifecycle + Command dispatch + telemetry ingestion (WorkerManager concerns) are co-located in one stateful actor. This is a pinned design choice, not an implementation detail: the `§1.4` Matrix and the `§1.7` reconciliation protocol read authoritative in-memory state on a single ownership boundary, and cannot be split across processes without reintroducing the coordination gaps that a "logical single" invariant is meant to forbid (ghost entities, `pending` Commands with no owner to time them out, envelope TOCTOU between concurrent Deploys on the same Session).

The **Gateway** is a separate, **stateless** process. It terminates Agent transports, runs the `A-T1` handshake (per `agent-beta.md §2.1.2` pin), fans Events to subscribers under `INV-P6` (`proto-catalog-beta.md`), and hands inbound `Envelope`s onward for the Overseer to consume. It holds no authoritative FSM state (`fsm-beta.md §2.4.1`: Gateway is sole-owner of the Gateway FSM only; every other FSM is elsewhere). `IR-O6` (peers, not parent-child) is preserved by this split - a live Gateway with a dead Overseer means "connections held, no new work accepted", never "Gateway drives FSMs on its own".

**Overseer <-> Gateway transport is Kafka.** Inbound envelopes (Registration, Manifest, CommandAck, Heartbeat, TaskTelemetry, ArtifactFrame) land on Overseer-bound topics; outbound envelopes (Command, RegistrationResponse, ManifestAck, Event) land on Gateway-bound topics. The reliability class per envelope variant follows the `Channel` category matrix in `channel-beta.md §2.10`. This choice has three load-bearing consequences that the FSMs rely on:

1. **Drain durability.** `O-T6` / `O-T7` (`Ready|Degraded -> Draining`) can persist `RemoteAgent Binding = draining` independent of Gateway availability - the Gateway is not a state holder, and envelopes already accepted by Kafka are durable even if the Gateway bounces.
2. **Degraded-mode asymmetry holds.** `§1.4` key decision #2 ("Command to PlatformAgents survives Message Delivery loss") remains coherent: in-process PlatformAgent CommandChannel does not traverse Kafka, so PlatformAgents stay reachable when the Kafka cluster is the lost subsystem.
3. **INV-P6 enforcement is single-hop.** `EventSubscribe` enforcement happens at the Gateway (the transport seam), not at the Overseer - the Overseer emits per-Session Events to Kafka without needing to know who is currently subscribed.

**Invariants are defined on logical state, never on per-process state.** `INV-O1` through `INV-O5` assert properties of the single logical Overseer. Any physical split that introduced per-process FSMs would require either (a) proving the composed logical invariant still holds, with a new interaction rule naming the proof boundary, or (b) introducing a new FSM for the split component. v0.1-beta-2 does neither - the composition is logical-single, physical-single for the Overseer, and physical-separate-but-stateless for the Gateway.

### 1.2 States

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  OVERSEER STATES                                                             │
│                                                                              │
│  Initializing ─► Ready ◄─► Degraded                                         │
│                    │            │                                             │
│                    │            │                                             │
│                    ▼            ▼                                             │
│                 Draining ◄─────┘                                             │
│                    │                                                         │
│                    ▼                                                         │
│                 Stopped                                                      │
│                                                                              │
│  Note: Initializing can also fail → Stopped (fatal startup error)            │
└──────────────────────────────────────────────────────────────────────────────┘
```

**S1: Initializing**

The Overseer is starting up. It is establishing connections to its infrastructure subsystems, loading configuration, recovering in-flight state from Persistent Storage (taxonomy §Recovery), and rebuilding any in-memory registries.

Properties:
- No operations are accepted. All API endpoints return `503 Service Unavailable`.
- Existing Agents from a prior run may be in unknown states. The Overseer must reconcile before accepting new work.
- The webapp should display a startup indicator, not an empty fleet.

Entry: process start.
Exit: all critical dependencies connected and state reconciled -> `Ready`; or fatal error -> `Stopped`.

**S2: Ready**

The Overseer is fully operational. All dependencies are available. All System Operations defined in the taxonomy are permitted.

Properties:
- Deploy, Run, Dispatch, Bind, Assign, Command, Delete - all available.
- Session limits are enforced.
- Telemetry and Artifact consumers are running.
- Health check endpoint returns `200 OK`.

Entry: from `Initializing` (first boot) or from `Degraded` (recovery).
Exit: dependency failure -> `Degraded`; shutdown signal -> `Draining`.

**S3: Degraded**

One or more non-critical dependencies are unavailable or unhealthy. The Overseer continues operating with reduced capability. The specific degradation depends on which dependency is lost.

Sub-states (not a formal state split - tracked as a capability bitfield):

| Lost Subsystem | Capability Impact |
|---|---|
| Message Delivery (producer) | Cannot Deploy new remote Services (Manifest delivery requires Message Delivery). Cannot issue Commands to RemoteAgents. Can still manage PlatformAgents locally (in-process CommandChannel). Can still read persistent state. |
| Message Delivery (consumers) | Cannot receive telemetry, artifacts, or lifecycle events from RemoteAgents. Remote fleet goes dark on the dashboard. PlatformAgents unaffected. |
| Process Spawning | Cannot spawn new PlatformAgents. Can still deploy remote Services (the user provides their own infrastructure). Can still command existing PlatformAgents. |
| Persistent Storage | **Critical degradation.** Cannot create Services, Bindings, Commands, or Sessions. Can still command existing in-memory PlatformAgents. Cannot enforce Session limits. Read-only queries degrade to stale data. This is the closest to Unavailable while still technically serving. |

Properties:
- Operations that require the lost subsystem are rejected with a specific error. The error must name the unavailable subsystem.
- Operations that do not require the lost subsystem continue normally.
- The Overseer actively probes the lost subsystem for recovery.
- The webapp should display a degradation banner with the specific impact.
- Health check endpoint returns `200 OK` with a degraded body (not `503` - the system is still serving).

Entry: from `Ready` (dependency failure detected).
Exit: all subsystems recovered -> `Ready`; shutdown signal -> `Draining`; Persistent Storage lost while already degraded -> remains `Degraded` with expanded capability loss.

**S4: Draining**

The Overseer has received a shutdown signal (SIGTERM, manual shutdown, or orchestrator-initiated). It is gracefully winding down all managed entities before stopping itself. Drain is **preserving**: it suspends management without destroying structural state, so that the Overseer can resume management after restart (taxonomy §Drain).

Properties:
- No new operations accepted. All API endpoints return `503 Service Unavailable` with a `Retry-After` header.
- **PlatformAgents**: The Overseer issues Stop Commands (Agent-scoped, targeting each PlatformAgent's Binding ID) to all active PlatformAgents. Their runtime is platform infrastructure that will go offline. Waits for Acknowledgments with a configurable `drain_timeout`. On timeout, force-stops the process and updates the Binding to `released`. PlatformAgent Services are marked `stopped` in Persistent Storage.
- **RemoteAgents**: The Overseer does **not** issue Stop Commands. RemoteAgents run on client infrastructure unaffected by the platform shutdown. Instead, the Overseer persists all active RemoteAgent Bindings, Tasks, and Channel state as `draining` in Persistent Storage and closes its end of the Channels. The RemoteAgent detects the Channel closure and enters a reconnection loop. After restart and Recovery, the Overseer matches the reconnecting RemoteAgent to the persisted `draining` Binding and re-activates it.
- This Remote/Platform asymmetry during Drain is the one case where their lifecycle diverges: PlatformAgents are stopped because their host is shutting down; RemoteAgents are preserved because their host is not.
- Message Delivery is best-effort during Drain - if the message bus is unavailable, PlatformAgents are force-stopped via process termination, and RemoteAgents detect Channel closure independently.
- The webapp should display "System shutting down - Remote Agents will reconnect automatically."

Entry: shutdown signal received from `Ready` or `Degraded`.
Exit: all PlatformAgent Bindings released (or timeout) AND all RemoteAgent Bindings persisted as `draining` -> `Stopped`.

**S5: Stopped**

Terminal state. The Overseer process is about to exit. All managed state has been persisted or abandoned.

Properties:
- No operations possible.
- Process exits after this state is reached.

Entry: from `Draining` (graceful) or from `Initializing` (fatal error).
Exit: none (terminal).

### 1.3 Transitions

```
O-T1:  Initializing ──► Ready
     Trigger:   All critical dependencies connected AND state reconciliation complete
     Guard:     Persistent Storage reachable AND Event Broadcast channel open
     Effects:   - Log "Overseer ready" with subsystem status summary
                - Begin accepting API requests
                - Start health probe timers for each subsystem
                - If Message Delivery consumers available: spawn gateway consumer tasks
                - Emit OverseerReady event via Event Broadcast

O-T2:  Initializing ──► Stopped
     Trigger:   Fatal error during startup (e.g., config invalid, Persistent Storage
                unreachable after max retries, port conflict)
     Guard:     none
     Effects:   - Log fatal error with cause
                - Process exit with non-zero code

O-T3:  Ready ──► Degraded
     Trigger:   Health probe detects subsystem failure (Message Delivery unreachable,
                Process Spawning unresponsive, Persistent Storage pool exhausted)
     Guard:     At least one subsystem is unhealthy
     Effects:   - Log degradation with specific subsystem and failure reason
                - Update capability bitfield (SubsystemHealth)
                - Emit OverseerDegraded { health, unavailable_subsystems, unavailable_operations }
                  via Event Broadcast
                - Start accelerated health probes for the failed subsystem

O-T4:  Degraded ──► Ready
     Trigger:   Health probe confirms all dependencies have recovered
     Guard:     All subsystems healthy (Persistent Storage, Message Delivery,
                Process Spawning, Event Broadcast)
     Effects:   - Log recovery
                - Restore full capability bitfield (SubsystemHealth::full())
                - Emit OverseerRecovered event via Event Broadcast
                - Resume normal health probe interval

O-T5:  Degraded ──► Degraded (self-transition)
     Trigger:   Additional dependency fails while already degraded, or a previously
                lost dependency recovers but others remain unhealthy
     Guard:     Capability bitfield changes
     Effects:   - Update capability bitfield
                - Log the change
                - Emit OverseerDegraded { health, unavailable_subsystems, unavailable_operations } event (updated)

O-T6:  Ready ──► Draining
     Trigger:   Shutdown signal (SIGTERM, SIGINT, manual API call)
     Guard:     none
     Effects:   - Log "Overseer draining, platform_bindings={p_count}, remote_bindings={r_count}"
                - Stop accepting new API requests (return 503)
                - For each active PlatformAgent Binding:
                    Issue Command(Stop, target: Binding ID - Agent-scoped)
                    Start per-Agent drain timeout
                - For each active RemoteAgent Binding:
                    Persist Binding, Tasks, Channel state as `draining` in Persistent Storage
                    Close Overseer's end of CommandChannel, TelemetryChannel
                    (The closure the RemoteAgent actually observes is Gateway -> RemoteAgent;
                     the Overseer -> Gateway leg is internal and not monitored by the Agent.)
                    Do NOT issue Stop
                - Emit OverseerDraining event to WS broadcast

O-T7:  Degraded ──► Draining
     Trigger:   Shutdown signal received while degraded
     Guard:     none
     Effects:   Same as O-T6 (PlatformAgents get Stop, RemoteAgents get `draining`), but:
                - If Message Delivery is the lost subsystem:
                    PlatformAgents still receive Stop through in-process CommandChannel
                    RemoteAgent Bindings are persisted as `draining` (same as healthy Drain -
                    the RemoteAgent detects Channel closure independently)
                - If Persistent Storage is the lost subsystem:
                    Cannot persist RemoteAgent Bindings as `draining` - force-close Channels.
                    RemoteAgents will detect closure but Recovery cannot match them.
                    Log "drain without persistence: remote bindings will require manual
                    re-binding after restart"
                    PlatformAgents still receive Stop through in-process channels

O-T8:  Draining ──► Stopped
     Trigger:   All PlatformAgent Bindings released (or timeout) AND all RemoteAgent
                Bindings persisted as `draining` (or Persistent Storage unavailable)
     Guard:     none
     Effects:   - For any PlatformAgent Binding still active at timeout:
                    Force-stop process
                    Update Binding to `released`
                    Update Service to `stopped`
                    Log "forced stop: PlatformAgent {id} did not acknowledge within {timeout}s"
                - Verify all RemoteAgent Bindings have status `draining` in Persistent Storage
                - Flush any pending Event Broadcast events
                - Close Message Delivery connections
                - Close Persistent Storage connections
                - Log "Overseer stopped, draining_remote_bindings={count}"
                - Process exit
```

### 1.4 Operation Availability Matrix

This matrix defines which System Operations the Overseer can execute in each state.

| System Operation | Initializing | Ready | Degraded | Draining | Stopped |
|---|---|---|---|---|---|
| **Register** (RemoteAgent) | - | [0k] | [0k] if Message Delivery alive | - | - |
| **Register** (PlatformAgent) | - | [0k] | [0k] if Process Spawning alive | - | - |
| **Bind** | - | [0k] | [0k] if Persistent Storage alive | - | - |
| **Assign** | - | [0k] | [0k] if Persistent Storage alive | - | - |
| **Deploy** (Service) | - | [0k] | - (requires all subsystems) | - | - |
| **Run** (Experiment) | - | [0k] | - (requires all subsystems) | - | - |
| **Dispatch** (Manifest) | - | [0k] | [0k] if Message Delivery + Persistent Storage alive | - | - |
| **Command** (Pause / Resume / Stop, Task-scoped, RemoteAgent) | - | [0k] | [0k] if Message Delivery alive | - | - |
| **Command** (Pause / Resume / Stop, Agent-scoped, RemoteAgent) | - | [0k] | [0k] if Message Delivery alive | - (Binding persisted as `draining`; see O-T6 / IR-O2) | - |
| **Command** (Pause / Resume / Stop, Task-scoped, PlatformAgent) | - | [0k] | [0k] (in-process) | - | - |
| **Command** (Pause / Resume / Stop, Agent-scoped, PlatformAgent) | - | [0k] | [0k] (in-process) | Stop only (Drain) | - |
| **Command** (Restart, Task-scoped, RemoteAgent) | - | [0k] | - (Full only, v0.1) | - | - |
| **Command** (Restart, Agent-scoped, RemoteAgent) | - | [0k] | - (Full only, v0.1) | - | - |
| **Command** (Restart, Task-scoped, PlatformAgent) | - | [0k] | - (Full only, v0.1) | - | - |
| **Command** (Restart, Agent-scoped, PlatformAgent) | - | [0k] | - (Full only, v0.1) | - | - |
| **Delete** | - | [0k] | [0k] if Persistent Storage + Message Delivery (RemoteAgents) alive | - | - |
| **Drain** | - | [0k] | [0k] if Persistent Storage alive (best-effort otherwise) | - | - |
| **Query** (read-only) | - | [0k] | [0k] if Persistent Storage alive | [0k] (read-only) | - |

Key design decisions surfaced by this matrix:

1. **Deploy and Run require all subsystems.** These create structural state across Persistent Storage, Message Delivery, Process Spawning, and Event Broadcast. Partial creation produces irrecoverable inconsistency. Reject early.
2. **Command to PlatformAgents survives Message Delivery loss.** PlatformAgents use an in-process CommandChannel, not the Message Delivery subsystem. This dual-path architecture has a resilience benefit.
3. **Draining only allows Agent-scoped Stop commands - and only to PlatformAgents.** RemoteAgents do not receive Stop during Drain; their Bindings are persisted as `draining` instead (see taxonomy §Drain). No new work, no reconfiguration.
4. **Delete requires Persistent Storage.** Delete must update Binding, Service, and ComputeSlot state. If Persistent Storage is down, Delete cannot guarantee consistency, so it must be rejected. Delete also requires Message Delivery for RemoteAgents (to deliver the Stop Command that precedes Binding release).
5. **Command scoping is orthogonal to the matrix.** Task-scoped Commands (target: Task ID) and Agent-scoped Commands (target: Binding ID) have the same infrastructure requirements. The scoping target determines what the Agent does with the Command, not whether it can be delivered. The Overseer forwards the target intact; the Agent interprets the scope.
6. **Drain requires Persistent Storage** to persist RemoteAgent Bindings as `draining`. Without it, Drain falls back to best-effort: PlatformAgents are force-stopped via process termination, and RemoteAgents detect Channel closure independently - but Recovery cannot match them to prior Bindings.
7. **Restart requires Full mode (v0.1).** Restart is a soft-restart bounded by `stop_drain_timeout` (see Agent FSM INV-A6 in `agent-beta.md` and Task FSM INV-T8 in `task-beta.md`). Permitting Restart in Degraded mode risks partial completion: `restart_epoch` must be recorded on Artifact lineage (Persistent Storage), and Channels may need re-establishment through the Gateway (Message Delivery). v0.1 gates Restart to Full mode only. Future versions may relax this per-subsystem once each Restart sub-step is made independently retryable.

> **Taxonomy reconciliation (txy-fsm-code #3).** `Run` and `Query` are **not** canonical System Operations. Per the Taxonomy (which wins on the operation surface): Experiment is overdex-owned with **no Atlas FSM**, so there is no `Run` activation verb (Deploy is the sole activation); and a read is "a query against an existing surface," **not** a System Operation. The `Run (Experiment)` and `Query (read-only)` rows above are retained only as **availability shorthand** (read access remains during Degraded/Draining) and MUST NOT be exposed as System-Operation verbs. Removing `SystemOperation::Run`/`Query` from the `atelier-overseer` enum is tracked as txy-fsm-code action #3 (code half).

### 1.5 Invariants

**INV-O1: Single logical Overseer.**
At most one Overseer instance is active per platform deployment at any time. The Overseer ID is globally unique. If the Overseer restarts, the new instance must reconcile state from Persistent Storage before reaching `Ready` (taxonomy §Recovery). Two concurrent `Ready` Overseers with the same deployment ID is a critical bug. "Logical" is load-bearing here and is pinned in §1.1.1: the Overseer FSM describes a single logical actor integrating Scheduler + WorkerManager concerns; the Gateway is a separate stateless process and is NOT a second Overseer. A physical split of the logical Overseer across processes is out of scope for v0.1-beta-2 and would require an explicit follow-up invariant naming the composition boundary.

**INV-O2: State-capability consistency.**
The set of operations the Overseer accepts must exactly match the operation availability matrix for its current state. If the Overseer is `Degraded` with Message Delivery lost, and a Deploy request is accepted, the invariant is violated. This is testable: for every (state, operation) pair, the Overseer must either execute the operation or reject it with a specific error.

**INV-O3: Drain completeness.**
When the Overseer reaches `Stopped`, every Binding that was `Active` when `Draining` began must be in one of: `Released` with `release_reason ∈ {normal, force}` (PlatformAgents - stopped normally or timed out), or `Draining` (RemoteAgents - preserved for post-restart Recovery). No Binding may remain `Active` after the Overseer exits. Specifically: all PlatformAgent Bindings must be `Released` (with `release_reason = normal` on graceful Stop acknowledgment, or `release_reason = force` on drain timeout - their processes are gone in either case); all RemoteAgent Bindings must be `Draining` (persisted in Persistent Storage for Recovery to match on reconnection). The Binding's `release_reason` attribute is specified in §2.3 (`binding-beta.md`). Violating INV-O3 means either orphaned PlatformAgent processes or RemoteAgents that cannot resume after restart.

**INV-O4: Degradation visibility.**
Every transition into or within `Degraded` must emit a WS event to the webapp. The user must never be in a state where operations silently fail because a dependency is down. If the user sees a "Deploy" button, clicking it must either succeed or return an error that names the degraded subsystem.

**INV-O5: Reconciliation before Ready.**
After a restart, the Overseer must not reach `Ready` until it has reconciled in-flight state. Specifically:
- Services with `status='pending'` or `status='active'` in Persistent Storage must be verified: is the Agent still connected? Is the Binding still valid? If not, the Overseer transitions the stale entities to `stopped` / `released`.
- Commands with `status='pending'` (issued before the crash, never acked) must be re-issued or marked `failed`.
- This prevents ghost slots: entities that appear active in Persistent Storage but have no live Agent backing them.

### 1.6 Interaction Rules

The Overseer FSM constrains and is constrained by every other FSM in the system. These rules define the interaction contracts.

**IR-O1: Overseer gates all System Operations.**
No Bind, Assign, Deploy, Run, Dispatch, Command, or Delete can occur without the Overseer in state `Ready` or `Degraded` (with sufficient capabilities). The Overseer is the sole issuer of System Operations. No other entity may create a Binding, assign a Task, or issue a Command. Even PlatformAgent commands route through the Overseer, so that the Overseer's state can gate them.

**IR-O2: Overseer -> Agent lifecycle coupling (Drain asymmetry).**
When the Overseer enters `Draining`, the behavior depends on Agent location:
- **PlatformAgents**: must receive a Stop Command (Agent-scoped, targeting Binding ID) within `drain_propagation_timeout` (configurable, default 5s). The Overseer waits for Acknowledgment, then releases the Binding. On timeout, the Overseer force-stops the process and releases the Binding.
- **RemoteAgents**: do **not** receive a Stop Command. The Overseer persists their Bindings as `draining` and closes its Channel endpoints. The RemoteAgent detects the closure and enters a reconnection loop - it continues running on the client's hardware.

The Overseer does not wait for RemoteAgents at all during Drain. It only waits for PlatformAgent Bindings to be released (or timed out) before transitioning to `Stopped`. This is the one case where the Remote/Platform Agent lifecycle diverges.

**IR-O3: Overseer -> Binding lifecycle ownership.**
The Overseer is the sole creator and destroyer of Bindings. An Agent cannot create its own Binding (it requests one through Register + Dispatch). An Agent cannot release its own Binding (the Overseer releases it after Stop acknowledgment or timeout). This ownership rule ensures that the active Service count is always consistent with the set of active Bindings.

**IR-O4: Overseer -> Session enforcement.**
Before executing Deploy or Run, the Overseer checks the Session's resource envelope. This check must be atomic with the Service creation - no TOCTOU race where two concurrent Deploys both pass the check. This must be a serialized operation (e.g., transaction with row-level lock, or sequential queue per Session).

**IR-O5: Overseer recovery -> Agent state reconciliation.**
When the Overseer transitions from `Initializing` to `Ready`, it must reconcile with every Agent that was bound before the restart (taxonomy §Recovery, three stages). For RemoteAgents: check if the Gateway still has an active connection (query Message Delivery lifecycle topic). For PlatformAgents: check if the process is still running (Process Spawning status). For `draining` Bindings (from a prior Drain): wait for RemoteAgent reconnection and re-activate. If an Agent is gone, force-release the Binding and update the Service. This is the formalization of INV-O5.

**IR-O6: Overseer -> Gateway independence.**
The Overseer and Gateway are peers, not parent-child (taxonomy §System Processes: "operate independently"). The Gateway can be `Listening` while the Overseer is `Initializing`. The Gateway holds connections but does not process Commands or Manifests until the Overseer delivers them via Message Delivery. If the Overseer is `Degraded` with Message Delivery lost, the Gateway continues holding connections but receives no new instructions - existing connections remain open but idle. During Drain, the closure a RemoteAgent observes is the Gateway -> RemoteAgent leg; the Overseer -> Gateway leg is an internal platform concern and is not part of the RemoteAgent's monitoring surface.

### 1.7 State Reconciliation Protocol

This section details what happens during O-T1 (Initializing -> Ready), specifically the reconciliation step that prevents ghost entities after a restart.

```
RECONCILIATION SEQUENCE (during O-T1):

1. Query Persistent Storage for all Bindings with status IN ('pending', 'active', 'draining')
   │
   ├─ For each Binding with status='pending':
   │    Has the Agent ever connected? (check lifecycle.events topic)
   │    ├─ No  → The deploy was interrupted. Mark Binding='released',
   │    │         Service='stopped'. Log "stale pending binding {id}".
   │    └─ Yes → Agent connected but Overseer crashed before activating.
   │             Re-activate Binding, re-dispatch Manifest.
   │
   ├─ For each Binding with status='active':
   │    Is the Agent still connected?
   │    ├─ RemoteAgent: query Gateway health endpoint or lifecycle topic
   │    │   ├─ Connected → Binding is valid. Resume normal management.
   │    │   └─ Disconnected → Grace period (`agent.reconnect_grace_ms`, 60s).
   │    │       If Agent reconnects within grace → resume (A-T14).
   │    │       If not → release Binding (B-T7), update Service. The
   │    │       Channel rows for this Binding (`channels` table, status
   │    │       IN 'open'/'opening') are force-closed to 'failed' (CH-T10).
   │    │
   │    └─ PlatformAgent: check process status via Process Spawning
   │        ├─ Running → Binding is valid. Resume.
   │        └─ Exited → Release Binding, update Service. Optionally re-spawn
   │           if the Service is configured for automatic recovery.
   │
   └─ For each Binding with status='draining' (set during a prior Drain):
        The Overseer was shut down gracefully while this RemoteAgent was active.
        The RemoteAgent continued running on client infrastructure.
        ├─ Wait for Agent to reconnect through the Gateway.
        │   On reconnection → match to this draining Binding, transition
        │   Binding back to 'active', resume telemetry and command flow.
        │   Log "resumed draining binding {id} after reconnection".
        └─ If reconnect timeout exceeded (`agent.reconnect_grace_draining_ms`,
           120s) -> release Binding (B-T7), update Service. Draining Channel
           rows (`channels` table, status='draining') force-close to 'failed'
           (CH-T10).
           Log "draining binding {id} timed out, agent never reconnected".

2. Query Persistent Storage for all Commands with status='pending'
   │
   └─ For each pending Command:
        Was it issued more than command_timeout ago?
        ├─ Yes → Mark Command status='timeout'. The Agent either never
        │         received it or the Acknowledgment was lost.
        │         Log "stale pending command {id}, marking timeout".
        └─ No  → Re-deliver through the appropriate Channel (Message Delivery
                  for RemoteAgents, in-process for PlatformAgents).

3. Query Persistent Storage for all Services with status='active'
   │
   └─ For each active Service:
        Does it have at least one Binding with status='active'?
        ├─ Yes → Service is valid.
        └─ No  → All Bindings were released during reconciliation.
                  Mark Service status='stopped', stopped_at=now().
                  Log "orphaned service {id}, all bindings released".

4. Reconciliation complete -> transition to Ready.
```

**BYO-infra Manifest delivery (v0.1-beta-2).** Step 1's "Re-dispatch Manifest" branch is trivially handled under BYO-infra handshake-delivery: the augmented `manifests.body` was persisted atomically at Phase A's B-T1 commit (INV-M4, `manifest-beta.md §4`) and is never rewritten at runtime. The Gateway's gRPC handshake handler reads `manifests.body` and returns it verbatim to any agent that (re)connects post-restart - no Overseer-side republish is required, no agent is stranded by a missed transport, no transmission-timestamp tracking is load-bearing for the agent path. The boot reconciler's existing "stale pending Binding" sweep (`§1.7` Step 1) handles bindings whose Phase A never completed; bindings whose Phase A succeeded remain serviceable across Overseer restart with no reconciler action beyond what is already specified above. future work that adds a Kafka `control.manifests` consumer (e.g., a Gateway-side cache, cross-replica coordination) will revisit this branch to add an explicit republish step.

This protocol is what makes INV-O5 enforceable. It is the difference between "the system works if nothing crashes" and "the system recovers correctly after a crash." The `draining` Binding path (taxonomy §Drain, formalized in §2.3 Binding FSM - `binding-beta.md`) also makes the Drain -> Recovery cycle complete: RemoteAgents that survived a platform shutdown can seamlessly resume, rather than requiring manual re-deployment.

**Timeout rationale.** The grace for disconnected `active` Bindings (`agent.reconnect_grace_ms`, 60s) and the reconnect window for `draining` Bindings (`agent.reconnect_grace_draining_ms`, 120s) are not arbitrary. An `active` Binding that goes quiet is modelled primarily as a **network issue** - a transient TCP hiccup, a Gateway flap, or a brief client-side network change - which typically resolves within seconds; 60s is generous for that class of failure. A `draining` Binding, by contrast, survives a full Overseer restart: the reconnecting RemoteAgent must wait for the new Overseer to come up, complete in-process I/O for its own reconciliation (reading persistent storage, rebuilding registries, reopening Channels, resubscribing consumers), and only then accept the reconnection. The extra budget absorbs that orchestration cost, not a worse network.

---

### 1.8 Live State Maintenance

§1.7 describes boot-time reconciliation - the recovery sweep that fires once during O-T1 (Initializing -> Ready). This section describes the **live tickers** that run continuously while the Overseer is in `Ready` (or `Degraded`, with subsystem-loss flags), maintaining steady-state invariants on rows whose state can decay without an Overseer-side action firing. Tickers and the boot reconciler share their cleanup primitives - every ticker entry below names a `§1.7` Step it parallels - but tickers fire on a periodic schedule, not on a one-shot transition.

#### 1.8.1 Pending-Binding grace ticker - fires B-T2

**Schedule.** Every `overseer.degraded_refresh_ms` (default 5s - same cadence as the subsystem probe loop, scaled small relative to `binding.pending_grace_ms` so the late-fire window is bounded by the schedule granularity, not the grace window).

**Reads.** `SELECT id, service_id, created_at FROM bindings WHERE status = 'pending' AND created_at < now() - INTERVAL '{binding.pending_grace_ms} milliseconds'`.

**Action.** For each row returned, fire **B-T2** (`binding-beta.md §2.3.2`) with `release_reason = 'registration_grace_timeout'`. ComputeSlot reservation released via CS-T3; Service rolls forward via SV-T10 (last-Binding-released auto-stop, `service-beta.md §2.5`) with `stopped_reason = 'delete_last_agent'`. Emit BindingReleased event.

**Why a live ticker, not a single-shot.** The pause window between SEQ-1 Phase A return and Phase B start (`sequences-beta.md §3.1.1`) is calendar-time-driven by the researcher's `docker run` lead time. The Overseer cannot anticipate when (or whether) the grace window will expire - it has to poll. A live ticker is the cheapest possible mechanism: a single indexed read on `bindings(status, created_at)` per tick, no per-Binding state in memory.

**Distinct from §1.7 Step 1.** The boot reconciler's Step 1 also releases stale Pending Bindings, but it only fires once during boot. Without §1.8.1, a Pending Binding that lands on a healthy long-running Overseer would never release - there's no Overseer-side stimulus to fire B-T2 except this ticker. The boot reconciler covers the post-restart case; the ticker covers the steady-state case. Both target the same primitive (B-T2).

**Idempotency.** B-T2 is gated on `bindings.status = 'pending'` at fire-time (the transition primitive performs the UPDATE with `WHERE status='pending'`). A row that has already transitioned to `active` (Registration arrived just before the ticker fired) is not affected - the UPDATE matches zero rows and the ticker logs and moves on.

**Testability.** sqlx::test that inserts a `bindings` row with `created_at = now() - 65s` and `binding.pending_grace_ms = 60000`; runs the ticker; asserts `status = 'released'` and `release_reason = 'registration_grace_timeout'`.

#### 1.8.2 Pending-Command timeout ticker - fires Command timeout

**Mechanism.** The §1.7 Step 2 boot-time sweep has a live-operation analog: a periodic ticker. Both consult `commands.status = 'pending'` and `commands.issued_at + command_timeout`. Backed by `Scheduler::sweep_pending_commands` (`scheduler.rs:1123`).
