# Atelier FSM Atlas - Binding (§2.3)

Part of the **State Machine Atlas v0.1-beta-2**. See `fsm-beta.md` for the reading guide, notation, §2.4 FSMs - scope status, and §3 Cross-FSM Sequences. Owns the `INV-B*` invariant prefix. Cross-references: `agent-beta.md` (§2.1), `task-beta.md` (§2.2), `service-beta.md` (§2.5), `compute-slot-beta.md` (§2.8), `channel-beta.md` (§2.10). Participates in **SEQ-1 Deploy** (`sequences-beta.md`) as the Agent-Workspace link whose B-T3 (Pending -> Active) is the deploy-complete gate. Participates in **SEQ-2 Delete** (`sequences-beta.md §3.2`) as the Agent-scoped release path B-T4 -> B-T6 -> B-T8 whose `release_reason = 'operator_stop'` drives Service SV-T10 auto-stop and Agent A-T4.

---

## 2.3 Binding FSM

The Binding FSM captures the lifetime of the Agent-Workspace link that runs one or more Tasks under a single Manifest. The Binding is the unit of orchestration bookkeeping: Service active counts, Session resource envelopes, and Drain reconciliation are all indexed by Binding.

### 2.3.1 States

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  BINDING STATES                                                              │
│                                                                              │
│   Pending ──► Active ──► Draining ──► Releasing ──► Released (terminal)      │
│      │          │                         ▲                                  │
│      │          │                         │                                  │
│      │          └── (stop / lost / end) ──┘                                  │
│      │                                                                       │
│      └── (manifest rejection cascade, B-T10) ───► Releasing                  │
│                                                                              │
│  release_reason is recorded on entry to Releasing and is immutable           │
│  thereafter (INV-B5).                                                        │
└──────────────────────────────────────────────────────────────────────────────┘
```

**S-B1: Pending.** Binding created during Dispatch. Manifest is staged. Awaiting `ManifestAck` from the Agent. ComputeSlots are reserved but no Task is yet Accepted.

**S-B2: Active.** Every Task in the Manifest has been accepted by the Agent. Tasks are in {`Accepted`, `Running`, `Paused`, `Stopping`, `Restarting`}. Channels are open. This is the steady-state.

**S-B3: Draining.** Overseer has initiated drain for this Binding. No new Task work is dispatched. Existing Tasks are being moved toward terminal states via T-T8 (Stopping) or allowed to reach natural completion, depending on the drain path. For RemoteAgents during Overseer Drain, this is the persisted state that Recovery matches against after a platform restart.

**S-B4: Releasing.** All Tasks have reached terminal states (or will shortly via T-T11). Platform-side cleanup is in progress: ComputeSlots being vacated, Channels being closed, Service and Session counts being updated. `release_reason` is set on entry and immutable (INV-B5).

**S-B5: Released.** Absorbing terminal. All platform-side state cleaned up. Binding row remains in persistent storage for audit and lineage.

**release_reason enum.** Set on entry into `Releasing` (or directly into `Released` on the Pending-cascade path) and immutable thereafter:

- **`normal`** - Graceful completion: PlatformAgent Stop acknowledged cleanly; or all Tasks reached `Completed`.
- **`operator_stop`** - User-initiated Stop Command (Agent-scoped) completed before Drain.
- **`force`** - Drain or Stop timeout exceeded `stop_drain_timeout`; force-release applied.
- **`agent_lost`** - Agent disconnected and grace expired (Agent A-T15).
- **`task_rejected`** - One or more Tasks in the Manifest rejected in `ManifestAck` (taxonomy §Acceptance and rejection).
- **`task_failed`** - All Tasks in the Binding reached `Failed` (e.g., restart-failure cascade via T-T14).
- **`registration_grace_timeout`** - Binding sat in `Pending` longer than `binding.pending_grace_ms` (`timeouts-beta.md §T.5`) without a Registration arriving via the Gateway to fire A-T1 -> A-T3 -> B-T3. Live ticker fires B-T2 with this reason; ComputeSlot reservation released without ever being occupied. BYO-infra path: covers the case where a Service is created but no RemoteAgent ever connects.
- **`skill_mismatch`** - Agent registered (A-T1) but its declared Skills did not cover the bound Manifest's required Skills, so A-T2 guard failed and A-T18 fired (`agent-beta.md §2.1.2 A-T18`). The Pending Binding is actively released by A-T18's cascade with this reason - distinct from `registration_grace_timeout` which represents passive grace expiry without a Registration ever arriving. Distinguishes "agent connected but wrong shape" from "agent never showed up" in forensic queries on `bindings.release_reason`.

**draining_reason enum.** Set on entry into `Draining` (B-T4), in the `bindings.draining_reason` column. Distinguishes the two reasons a Binding drains, which otherwise look identical at the row level:

- **`operator_stop`** - SEQ-2 operator Delete: the Binding is draining on its way to `Released` (a `BINDING_RELEASE` Command exists for it).
- **`platform_drain`** - SEQ-5 O-T6 Platform Drain: the Overseer drained for maintenance. A RemoteAgent Binding is persisted `draining` and NOT released (IR-O2); the RemoteAgent keeps running on client hardware, and SEQ-4 (`sequences-beta.md §3.4` Stage 2) re-activates the Binding when the Overseer returns. No `BINDING_RELEASE` Command exists.

### 2.3.2 Transitions

```
B-T1:  (creation) ──► Pending
       Trigger:  Overseer Dispatches a Manifest.
       Guard:    Overseer mode permits Dispatch per §1.4 (`overseer-beta.md`);
                 Agent Registered; Workspace provisioned;
                 ComputeSlots exist and are vacant;
                 len(manifest.tasks) == 1 - v0.1-beta-2 single-Task Manifest
                   restriction per taxonomy §Tasks / beta scope; guard failure
                   rejects Dispatch with ErrorKind.SPEC_INVALID
                   (errors-beta.md §E.4) and no Binding row lands.
       Effects:  BindingId is ALLOCATED at B-T1 by the Overseer (sole owner of
                   the Binding FSM per IR-O3 and `fsm-beta.md §2.4.1`).
                   BindingId is generated as UUIDv4 at the moment the Binding
                   row lands and is returned to the Agent on the success path
                   in `ManifestAck.Accepted.binding_id`
                   (`proto-catalog-beta.md §control.proto`). The inbound `Manifest`
                   body MUST NOT carry a `binding_id`; any such field is
                   rejected with ErrorKind.SPEC_INVALID.
                 Persist Binding row (status=pending);
                 reserve ComputeSlots;
                 transmit Manifest on ManifestChannel.
                 Under BYO-infra (v0.1-beta-2) the Manifest body committed
                   at B-T1 is the FULL augmented shape per INV-M4 - operator-
                   input + `idempotency_key` + `[metadata]` table + canonical
                   `[[metadata.tasks]]` allocated via `accept_task` (T-T1)
                   inside the same Phase A transaction stack. The body is
                   never rewritten at runtime; the Gateway's gRPC handshake
                   returns it verbatim to the agent (`manifest-beta.md §2.3`).
                   The gRPC `ManifestChannel` path restores the
                   step 23 spec ordering (T-T1 after `ManifestAck`).

B-T2:  Pending ──► Releasing  [Pending exits without ManifestAck]
       Trigger:  EITHER Dispatch canceled before ManifestAck (e.g., operator canceled
                 Deploy; Session resource envelope invalidated; Manifest superseded)
                 OR pending grace expired (`binding.pending_grace_ms`,
                 `timeouts-beta.md §T.5`) without a Registration arriving - the BYO-infra
                 path where Phase A of SEQ-1 returned (gateway_url, token) to the
                 researcher and the researcher never launched their RemoteAgent.
       Guard:    No ManifestAck received yet.
       Effects:  release_reason ∈ {operator_stop, normal, registration_grace_timeout, skill_mismatch}
                   per cause:
                     - operator_stop / normal - active-cancel sub-trigger;
                     - registration_grace_timeout - passive grace-expiry sub-trigger
                       fired by the live ticker in `overseer-beta.md §1.7`;
                     - skill_mismatch - A-T18 cascade fired this transition because
                       the registered Agent failed the A-T2 Skill-subset guard
                       (`agent-beta.md §2.1.2 A-T18`).
                 Cancel Manifest transmission (no-op on the grace path -
                   ManifestChannel never opened);
                 release reserved ComputeSlots via CS-T3.
       Testability: cancel sub-trigger fires from Scheduler-side cancel API or
                 Session-envelope invalidation observer; grace sub-trigger fires
                 from `Overseer::pending_binding_ticker` reading
                 `bindings.created_at < now() - binding.pending_grace_ms`
                 (`overseer-beta.md §1.7`).

B-T3:  Pending ──► Active
       Trigger:  ManifestAck received with ALL Tasks accepted (every TaskAcceptance
                 has accepted=true).
       Guard:    INV-T6 holds.
       Effects:  Persist Binding status=active;
                 drive all bound Tasks T-T1 (Pending -> Accepted);
                 drive Agent A-T3 (Ready -> Bound) if this is the Agent's first Binding;
                 open Channels.

B-T4:  Active ──► Draining
       Trigger:  EITHER Overseer enters Draining AND this Binding is bound to a
                 RemoteAgent
                 OR Agent enters A-T5 Draining [PlatformAgent Stop path]
                 OR Stop Command (Agent-scoped) received that begins orderly drain
                 before release.
       Guard:    Binding in Active.
       Effects:  Persist Binding status=draining;
                 no new Task dispatch against this Binding;
                 drive {Running, Paused} Tasks to Stopping via T-T8
                   [PlatformAgent path];
                 RemoteAgent Drain path: Channels closed by Overseer (see Overseer
                   T6 in `overseer-beta.md`).

B-T5:  Active ──► Releasing
       Trigger:  All Tasks have reached terminal states (Completed or Failed) WITHOUT
                 a prior Draining phase.
       Guard:    Every Task on this Binding ∈ {Completed, Failed}.
       Effects:  release_reason = normal (if all Completed)
                 OR task_failed (if any Failed);
                 begin cleanup.

B-T6:  Draining ──► Releasing
       Trigger:  All Tasks reached terminal states OR stop_drain_timeout expired
                 with remaining non-terminal Tasks.
       Guard:    none
       Effects:  release_reason = normal (all terminals on time)
                 OR force (timeout path);
                 on force path: drive any non-terminal Tasks to Failed via T-T11.

B-T7:  {Pending, Active, Draining} ──► Releasing
       Trigger:  Agent lost and grace expired (Agent A-T15).
       Guard:    Binding not already in Releasing / Released.
       Effects:  release_reason = agent_lost;
                 force-fail all non-terminal Tasks via T-T11;
                 begin cleanup.

B-T8:  Releasing ──► Released
       Trigger:  All cleanup complete: ComputeSlots vacated, Channels closed,
                 Service/Session counts updated, persistent Binding row finalized.
       Guard:    INV-B7 holds.
       Effects:  Emit BindingReleased(binding_id, release_reason);
                 drive Agent A-T4 (Bound -> Ready) if this is the Agent's last Binding;
                 if last Binding of the Service: drive Service toward `stopped`
                 (Service FSM §2.5, planned; see `fsm-beta.md`).

B-T9:  (reserved - intentionally unused in v0.1-beta-2)
       Reserved to preserve the B-T10 label for the Manifest rejection cascade, per
       the design agreement in v0.1-beta-2 planning.

B-T10: Pending ──► Releasing  [Manifest rejection cascade]
       Trigger:  ManifestAck received with ≥1 TaskAcceptance.accepted == false.
       Guard:    INV-T6 holds.
       Effects:  release_reason = task_rejected;
                 drive self-rejected Tasks T-T2 with their reported rejection_reason
                   (SKILL_MISMATCH | SPEC_INVALID | INTERNAL_ERROR);
                 drive accepted sibling Tasks T-T2 with PEER_REJECTED (IR-BT2);
                 release reserved ComputeSlots;
                 no Binding ever reaches Active on this Manifest.

B-T11: Draining ──► Active  [SEQ-5 platform-drain resume]
       Trigger:  A RemoteAgent reconnects (Gateway AgentConnected) onto a Binding
                 drained by a platform drain (draining_reason='platform_drain',
                 IR-O2). Realizes `sequences-beta.md §3.4` Stage 2 step 7.
       Guard:    Binding in Draining with draining_reason='platform_drain'; the
                 reconnecting Agent matches the Binding's agent_id.
       Effects:  status='active', draining_reason cleared, active_at updated;
                 increment the Agent's restart_epoch (new lineage epoch for the
                 resumed collection); emit BindingActive. Distinct from a
                 delete-drain Binding (draining_reason='operator_stop'), which
                 proceeds to Releasing via B-T6 and never returns to Active.
```

**v0.1-beta-2 dormancy note - `PEER_REJECTED` cascade.** Under the beta single-Task Manifest restriction (taxonomy §Tasks / beta scope; enforced at `B-T1` guard with `SPEC_INVALID`), every Dispatched Manifest carries exactly one Task. The `PEER_REJECTED` branch of B-T10 - "drive accepted sibling Tasks T-T2 with PEER_REJECTED (IR-BT2)" - is therefore unreachable at runtime: a single-Task Manifest has no accepted sibling when its one Task self-rejects. In beta, B-T10 reduces to `release_reason = task_rejected` carrying the single Task's own `rejection_reason` ∈ {SKILL_MISMATCH, SPEC_INVALID, INTERNAL_ERROR}. The cascade plumbing is preserved intact - B-T10, IR-BT2 (§2.3.4), Task T-T2 (§2.2.2), `PEER_REJECTED` references in `compute-slot-beta.md INV-CS2`, `service-beta.md`, and `sink-beta.md`, and the `TaskRejectionReason.TASK_REJECTION_PEER_REJECTED` enum member (`proto-catalog-beta.md §control.proto`) - so that multi-Task (later) re-enablement does not require a cross-tree spec edit.

### 2.3.3 Invariants

**INV-B1: Single Agent.** A Binding references exactly one Agent.

**INV-B2: Single Workspace.** A Binding references exactly one Workspace.

**INV-B3: Task set from Manifest.** A Binding's Tasks are exactly those referenced in its dispatched Manifest. 1..N Tasks per Binding.

**INV-B4: Monotone progression.** State progression is monotone along the dataflow Pending -> Active -> Draining -> Releasing -> Released. Two shortcut paths exist: Pending -> Releasing (B-T2, B-T10) and Active -> Releasing (B-T5). No backward transitions.

**INV-B5: release_reason immutable.** Once set on entry to Releasing (or to Released via B-T8 from the B-T2 shortcut), `release_reason` is immutable for the lifetime of the Binding record.

**INV-B6: Active implies runnable Tasks.** A Binding in `Active` has ≥0 Tasks in {`Accepted`, `Running`, `Paused`, `Stopping`, `Restarting`} and exactly 0 in {`Rejected`}.

**INV-B7: Releasing implies Tasks terminal or being forced.** A Binding in `Releasing` has every Task either already in {`Completed`, `Failed`, `Rejected`} or being driven there by the release cascade (T-T11). B-T8 cannot fire while any bound Task remains in {`Accepted`, `Running`, `Paused`, `Stopping`, `Restarting`}.

**INV-B8: Released is absorbing.**

### 2.3.4 Interaction Rules

**Binding <-> Agent (IR-BA)**

- **IR-BA1a (Pre-Registration, BYO-infra path):** Binding creation (B-T1) MAY fire with no Agent record existing yet. Phase A of `sequences-beta.md §3.1.1` lands the Binding row in `pending` before the RemoteAgent registers; the live grace ticker (`overseer-beta.md §1.7`, `binding.pending_grace_ms`) bounds how long the Pending Binding may sit Agent-less before B-T2 fires with `release_reason='registration_grace_timeout'`. The Binding's eventual Agent is identified by the JWT claims that A-T1 validates on Registration receipt.
- **IR-BA1b (Activation, both paths):** Binding activation (B-T3) requires the bound Agent in state ∈ {`Ready`, `Bound`}. Under BYO-infra this resolves Agent identity at Phase B; under the legacy non-BYO path Agent is already Ready when B-T1 fires.
- **IR-BA2:** Binding B-T3 drives Agent A-T3 (Ready -> Bound) if this is the Agent's first Active Binding.
- **IR-BA3:** Binding B-T8 drives Agent A-T4 (Bound -> Ready) if this is the Agent's last Binding to release.
- **IR-BA4:** Agent A-T15 (Lost -> Terminated) drives B-T7 on every Binding the Agent held.
- **IR-BA5:** Agent A-T5 (Bound -> Draining) drives B-T4 on every Binding the Agent held on the PlatformAgent path; on the RemoteAgent path, B-T4 is driven by Overseer Drain (Overseer O-T6 in `overseer-beta.md`) and the Agent's A-T5 fires as a consequence.

**Binding <-> Task (IR-BT)**

- **IR-BT1:** Binding B-T3 (Pending -> Active) drives all bound Tasks T-T1 (Pending -> Accepted) atomically (INV-T6).
- **IR-BT2:** Binding B-T10 (Manifest rejection cascade) drives every bound Task to `Rejected` via T-T2. Tasks the Agent self-rejected carry their reported `rejection_reason`; Tasks the Agent accepted carry `PEER_REJECTED`.
- **IR-BT3:** Binding B-T4, B-T6, B-T7 release cascades drive non-terminal Tasks to `Stopping` (T-T8) and, on timeout or forced cases, to `Failed` (T-T11).
- **IR-BT4:** Binding B-T8 (Releasing -> Released) cannot fire while any bound Task is in a non-terminal state (INV-B7).
