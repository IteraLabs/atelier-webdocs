# Atelier FSM Atlas - Service (§2.5)

Part of the **State Machine Atlas v0.1-beta-2**. See `fsm-main.md` for the reading guide, notation, §2.4 FSMs - scope status, and §3 Cross-FSM Sequences. Owns the `INV-SV*` invariant prefix. Cross-references: `overseer.md` (§1, §1.4 Operation Availability Matrix), `session.md` (§2.7), `binding.md` (§2.3), `compute-slot.md` (§2.8). Participates in **SEQ-1 Deploy** (`sequences.md`) as the unbounded activation mode of a Pipeline; SV-T1 -> SV-T2 -> SV-T3 traces the deploy happy path. Participates in **SEQ-2 Delete** (`sequences.md §3.2`) as the auto-stop target via SV-T10 (Active -> Stopped) when the deleted Agent's Binding is the Service's last Binding; `stopped_reason = 'delete_last_agent'`.

§2.6 Experiment FSM is enumerated in `fsm-main.md §2.4` and remains deferred per the v0.1-beta-2 beta scope (taxonomy §ACTIVATION MODES).

---

## 2.5 Service FSM

The Service FSM captures the lifetime of a Service - the unbounded activation mode of a Pipeline. A Service is created by Deploy, transitions through provisioning and manifest dispatch, reaches a steady-state Active with ≥1 Binding actively running Tasks, and terminates either naturally (all Bindings released) or under operator/Overseer direction. The Service's identity and Pipeline reference are immutable; Workspace, Bindings, and Artifacts are owned by the Service's lifetime; Sessions contain Services.

This FSM is the Overseer's primary bookkeeping handle for Deploy (SEQ-1). Binding FSM (§2.3) transitions drive Service state; Service FSM transitions gate Binding creation and release cascades.

### 2.5.1 States

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  SERVICE STATES                                                              │
│                                                                              │
│   Provisioning ──► Deploying ──► Active ◄──► Updating                        │
│        │                │            │                                       │
│        │                │            │                                       │
│        ▼                ▼            ▼                                       │
│     Stopped ◄──── Stopped ◄──── Stopping ──► Stopped                         │
│        │                                        │                            │
│        │                                        │                            │
│        └────────────────► Archived ◄────────────┘                            │
│                                                                              │
│  Updating: states enumerated, transitions deferred (v0.1-beta-2 scope).      │
│  Archived: absorbing terminal.                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

**S-SV1: Provisioning.** Deploy System Operation accepted. The Service row and Workspace row are being persisted; the Pipeline is being bound to this activation; the Manifest is being composed. **No Binding exists yet** - B-T1 (Binding creation) is deferred to SV-T2 so that Binding creation and Manifest transmission remain atomic (B-T1 effects).

Entry: SV-T1 (Deploy accepted).
Exit: SV-T2 (pre-Dispatch work complete) or SV-T4 (aborted before Dispatch).

**S-SV2: Deploying.** The Overseer has Dispatched the Manifest (B-T1 fired -> the single Binding is Pending, ComputeSlots are hard-reserved, Manifest transmitted on ManifestChannel). For RemoteAgent: the Overseer is waiting for the Agent to connect through the Gateway, Register, and return a ManifestAck. For PlatformAgent: the Overseer has spawned the Agent via Process Spawning and is waiting for Register + ManifestAck.

Entry: SV-T2.
Exit: SV-T3 (ManifestAck: all accepted -> Binding Active) or SV-T5 (ManifestAck: ≥1 rejection, or Dispatch timeout).

**S-SV3: Active.** Steady state. ≥1 Binding is in `Active` (B-T3 has fired). Tasks are `Running` (T-T3) or eligible. Artifacts are being produced. The Service is visible on the webapp as operational. The Service remains Active through Overseer Drain if all its Bindings are on RemoteAgents (those Bindings persist as `draining` without Service-level transition; see IR-SVO2).

Entry: SV-T3.
Exit: SV-T6 (Service-initiated Stop), SV-T7 (Update requested - deferred), SV-T10 (auto-stop when last Binding releases naturally).

**S-SV4: Updating.** Service topology or configuration is being updated while Active. **Transitions into and out of Updating are deferred in v0.1-beta-2** (Update System Operation is not in beta scope). The state is enumerated so that Update-related references elsewhere resolve, and so that future work does not renumber states.

Entry: SV-T7 (deferred).
Exit: SV-T8 (deferred).

**S-SV5: Stopping.** Service-initiated shutdown in progress. The Overseer has driven each Active Binding to `Draining` via B-T4. The Service waits for all Bindings to reach `Released`. Service is not accepting new operations that would create Bindings under this Service.

Entry: SV-T6.
Exit: SV-T9 (all Bindings Released).

**S-SV6: Stopped.** All Bindings associated with this Service are `Released`. The Service is not operating. The Service row and all lineage (Manifests, Tasks, Artifacts, Commands) are preserved. Re-Deploying the same Pipeline creates a new Service under a new Service ID; this Service's ID stays Stopped.

Entry: SV-T4 (abort before Dispatch), SV-T5 (manifest_rejected), SV-T9 (graceful shutdown), SV-T10 (auto-stop).
Exit: SV-T11 (Archive).

**S-SV7: Archived.** Absorbing terminal. The Service has been removed from the operating set (retention window elapsed or explicit archive action). Rows remain in persistent storage for audit and lineage queries.

Entry: SV-T11.
Exit: none (terminal).

### 2.5.2 Transitions

```
SV-T1:  (creation) ──► Provisioning
        Trigger:  Deploy System Operation accepted by the Overseer.
        Guard:    Overseer mode = Full (§1.4 matrix - Deploy requires all subsystems);
                  Session ∈ {Active, Expiring} (§2.7);
                  Session envelope check passes atomically (IR-O4).
        Effects:  Persist Service row (status=provisioning, session_id, pipeline_id,
                    agent_type, created_at);
                  persist Workspace row (scoped to Session, Domain, Service);
                  compose Manifest object (not yet persisted to Manifest table);
                  soft-reserve target ComputeSlots (CS-T1 - see §2.8);
                  emit ServiceProvisioning event.

SV-T2:  Provisioning ──► Deploying
        Trigger:  Pre-Dispatch work complete (Workspace persisted, Manifest composed,
                  Agent spawn for PlatformAgent path complete OR connection credential
                  generated for RemoteAgent path).
        Guard:    Overseer still in Full mode;
                  Session envelope still within limits;
                  Workspace row persisted;
                  target ComputeSlots still vacant.
        Effects:  Persist Service status=deploying;
                  fire B-T1 (Binding Pending: Binding row persisted, ComputeSlots
                    hard-reserved via CS-T2, Manifest persisted and transmitted on
                    ManifestChannel);
                  for PlatformAgent path: Overseer confirms spawn; for RemoteAgent
                    path: Overseer surfaces Gateway URL + JWT in webapp;
                  emit ServiceDeploying event.

SV-T3:  Deploying ──► Active
        Trigger:  The Service's Binding reaches Active (B-T3) - all Tasks in its
                  Manifest acknowledged as accepted.
        Guard:    INV-SV1 holds (1 Binding in Active);
                  Session still in {Active, Expiring}.
        Effects:  Persist Service status=active, activated_at;
                  Tasks fire T-T3 (Accepted -> Running) in their own FSM;
                  emit ServiceActive event.

SV-T4:  Provisioning ──► Stopped
        Trigger:  Deploy aborted before Dispatch - user cancellation; subsystem loss
                  detected during Provisioning (e.g., Persistent Storage pool
                  exhausted mid-persist); Session envelope invalidated by a
                  concurrent operation (IR-O4 race detection); spawn failure for
                  PlatformAgent path.
        Guard:    No Binding exists (B-T1 has not fired).
        Effects:  Persist Service status=stopped, stopped_at,
                    stopped_reason ∈ {deploy_canceled, subsystem_loss,
                      session_envelope_invalidated, spawn_failed};
                  destroy Workspace row;
                  release soft-reserved ComputeSlots (CS-T* back to Vacant);
                  emit ServiceStopped event.

SV-T5:  Deploying ──► Stopped
        Trigger:  The Service's Binding reaches Released via the B-T10 cascade
                  (manifest rejection: self-rejection or PEER_REJECTED) and then
                  B-T8 with release_reason = task_rejected;
                  OR Dispatch timeout (Agent never Registers / Manifest never acked
                  within dispatch_timeout).
        Guard:    Binding has not passed through Active (did not reach B-T3).
        Effects:  Persist Service status=stopped, stopped_at,
                    stopped_reason ∈ {manifest_rejected, dispatch_timeout};
                  destroy Workspace row;
                  ComputeSlots released via CS-T* (from Reserved back to Vacant);
                  emit ServiceStopped event.
        Note:     Per `fsm-main.md §2.4`, the manifest-rejection cascade is a failed
                  Deploy, not a natural stop; this transition skips Stopping.

SV-T6:  Active ──► Stopping
        Trigger:  Service-initiated shutdown - operator Stop of the Service
                  (Agent-scoped Stop on every Active Binding under this Service);
                  OR Overseer Drain cascade for a Service whose Bindings are all on
                    PlatformAgents (IR-SVO2);
                  OR Delete System Operation targeting the last Active Binding under
                    this Service (Delete sequence cascade);
                  OR Session SN-T4 / SN-T6 cascade (IR-SVS2).
        Guard:    ≥1 Binding in {Pending, Active, Draining, Releasing}.
        Effects:  Persist Service status=stopping, stopped_reason_intent (one of
                    {operator_stop, drain, delete_last_agent, session_expired});
                  for each Binding in {Active}: fire B-T4 (Active -> Draining);
                  for each Binding in {Pending}: fire B-T2 (Pending -> Releasing
                    with release_reason derived from stopped_reason_intent);
                  emit ServiceStopping event.

SV-T7:  Active ──► Updating
        Trigger:  Update System Operation accepted by the Overseer.
        Guard:    Overseer mode = Full; Session ∈ {Active, Expiring}.
        Effects:  DEFERRED in v0.1-beta-2 (Update is not in beta scope).

SV-T8:  Updating ──► Active
        Trigger:  Update completion ack.
        Effects:  DEFERRED in v0.1-beta-2.

SV-T9:  Stopping ──► Stopped
        Trigger:  Every Binding under this Service has reached Released.
        Guard:    Zero Bindings in {Pending, Active, Draining, Releasing}.
        Effects:  Persist Service status=stopped, stopped_at, stopped_reason
                    (the recorded stopped_reason_intent from SV-T6);
                  emit ServiceStopped event.

SV-T10: (Active | Deploying | Provisioning) ──► Stopped
        Trigger:  Auto-stop - last Binding under this Service reached Released
                  naturally (B-T5 release via all-Completed / task_failed, or B-T7
                  via agent_lost, or B-T6 via graceful drain from a non-Service-
                  initiated source, or - Iteration 5 - B-T2 via
                  registration_grace_timeout when a BYO-infra deploy's Agent never
                  connected and the only Pending Binding grace-released), with
                  release_reason ≠ task_rejected.
        Guard:    Zero Bindings in {Pending, Active, Draining, Releasing};
                  prior Service state ∈ {Active, Deploying, Provisioning}
                  (NOT Stopping - if Stopping, SV-T9 is the correct transition);
                  every Released Binding under this Service has
                    release_reason ≠ task_rejected (guaranteed; see INV-SV6).
        Effects:  Persist Service status=stopped, stopped_at, stopped_reason=auto_stop;
                  emit ServiceStopped event.
        Note (Iteration 5): broadened from "Active ──► Stopped" to admit the
                  pre-Active deploy states, so the §1.8.1 grace ticker
                  (sweep_pending_bindings) can stop a Service whose only Pending
                  Binding timed out before the Agent connected. The boot reconciler
                  (§1.7 step 3) does the same for orphans found at boot.

SV-T11: Stopped ──► Archived
        Trigger:  Explicit archive action OR retention window elapsed
                  (archive_threshold since stopped_at).
        Guard:    none (Stopped is already terminal for operation purposes;
                  INV-SV1 already holds).
        Effects:  Persist Service status=archived, archived_at;
                  remove from operating-set indexes (lineage queries still resolve);
                  emit ServiceArchived event.
```

### 2.5.3 Invariants

**INV-SV1: State-Binding count consistency.**

| State | Bindings in {Pending, Active, Draining, Releasing} |
|---|---|
| Provisioning | 0 |
| Deploying | 1 (in Pending) |
| Active | ≥1 (in {Pending, Active, Draining, Releasing}, with ≥1 ever having reached Active) |
| Updating | ≥1 |
| Stopping | ≥0 (monotonically decreasing to 0) |
| Stopped | 0 |
| Archived | 0 |

**INV-SV2: Session reference integrity.** A Service in any non-{Stopped, Archived} state references a Session in {Active, Expiring}. If the Session transitions to Expired, the Service must transition toward Stopped within one state step (via SV-T6 cascade from IR-SVS2).

**INV-SV3: Pipeline reference immutable.** `pipeline_id` is set at SV-T1 and is immutable for the lifetime of the Service row. Updating may swap Tasks within the Pipeline's ComputeSlots but does not change `pipeline_id`.

**INV-SV4: Agent type immutable.** `agent_type` ∈ {Remote, Platform} is set at SV-T1 based on the Manifest's target and is immutable. The Service's Bindings inherit this agent_type (per INV-A9 on the Agents they bind to).

**INV-SV5: Deploy rejection path.** A Service reaching Stopped via SV-T5 has `stopped_reason = manifest_rejected` or `dispatch_timeout`, and its single Binding has `release_reason = task_rejected` (for manifest_rejected) or no release_reason was set (for dispatch_timeout - Binding never reached Pending successfully if spawn/register failed; reconcile specifics deferred to SEQ-1 details).

**INV-SV6: Auto-stop excludes task_rejected.** SV-T10 fires only when no Released Binding under this Service has `release_reason = task_rejected`. This is automatically true because task_rejected exits Binding from Pending via B-T10 (never from Active), which is captured by SV-T5, not SV-T10.

**INV-SV7: Terminal absorbingness.** Archived is absorbing. Stopped -> Archived is the only transition out of Stopped.

**INV-SV8: Monotone state progression.**
Forward-only progression along:
`Provisioning -> Deploying -> Active -> {Stopping -> Stopped | Stopped} -> Archived`.
Shortcut to Stopped exists from Provisioning (SV-T4), Deploying (SV-T5), and Active (SV-T10). Updating sits off Active bidirectionally (deferred). No backward transitions from Stopped to any pre-Stopped state.

### 2.5.4 Interaction Rules

**Service <-> Overseer (IR-SVO)**

- **IR-SVO1:** Overseer gates SV-T1 per the Operation Availability Matrix (§1.4 `overseer.md`). Deploy requires all four subsystems (persistent storage, message delivery, process spawning, event broadcast). Degraded Overseer rejects SV-T1.
- **IR-SVO2:** Overseer T6 (Ready/Degraded -> Draining) interacts with Service state by agent_type:
  - Service with only PlatformAgent Bindings: drives SV-T6 (Service-initiated shutdown).
  - Service with only RemoteAgent Bindings: does NOT drive SV-T6. Bindings transition to `draining` under Overseer Drain (Overseer T6 effects), but Service stays Active. After Overseer restart and Recovery (IR-O5), reconnecting RemoteAgent Bindings return to Active and Service remains Active throughout.
  - Service with mixed agent_types is out of scope in v0.1 (INV-SV4 makes agent_type uniform per Service).
- **IR-SVO3:** Overseer Recovery (§1.7) may transition a Service from Active to Stopped if reconciliation finds all its Bindings orphaned (e.g., every Binding's Agent was Lost and grace expired, no reconnect within the draining grace window).

**Service <-> Binding (IR-SVB)**

- **IR-SVB1:** SV-T2 fires B-T1 (Binding creation + ComputeSlot hard-reserve + Manifest transmit). The Binding's Service reference is set here and is immutable for the Binding's lifetime (INV-B1 counterpart on the Service side).
- **IR-SVB2:** Binding B-T3 (Pending -> Active) drives SV-T3 (Deploying -> Active) for this Service's only Binding in v0.1.
- **IR-SVB3:** Binding B-T8 (Releasing -> Released) drives:
  - SV-T9 if Service is in Stopping and this is the last non-Released Binding;
  - SV-T10 if Service is in Active, this is the last non-Released Binding, and `release_reason ≠ task_rejected`;
  - SV-T5 if Service is in Deploying, this is the single Binding, and `release_reason = task_rejected`.
- **IR-SVB4:** SV-T6 drives B-T4 on each Active Binding and B-T2 on each Pending Binding under this Service.

**Service <-> Session (IR-SVS)**

- **IR-SVS1:** SV-T1 requires Session in {Active, Expiring}. Envelope check is atomic with SV-T1 persist per IR-O4; the mechanism is specified in §2.7 (INV-SN1).
- **IR-SVS2:** Session SN-T4 (Expiring -> Expired) and SN-T6 (Active -> Expired emergency) cascade SV-T6 on every Service currently in {Provisioning, Deploying, Active, Updating}. Provisioning Services follow SV-T4 (no Binding to drain); others follow SV-T6.
- **IR-SVS3:** Service state contributes to Session envelope counts: `count(Services in {Provisioning, Deploying, Active, Updating, Stopping})` counts against Session's concurrent-Services limit; count of Agents bound under this Service counts against concurrent-Agents.

**Service <-> Pipeline (IR-SVP)**

- **IR-SVP1:** SV-T1 pins a Pipeline ID. The Pipeline's ComputeSlots are soft-reserved at SV-T1 (CS-T1) and hard-reserved at SV-T2 via B-T1 effects (CS-T2).
- **IR-SVP2:** ComputeSlot rows are Pipeline-scoped (one row per `(pipeline_id, slot_ordinal)`). v0.1-beta-2 constrains at most one concurrent Service activation per Pipeline (INV-CS3 in §2.8). Concurrent activations of the same Pipeline are a post-beta extension, at which point ComputeSlot rows may be instanced per activation without restructuring the FSM - see §2.8 Notes.

### 2.5.5 Notes

- **Updating is enumerated, not specified.** SV-T7 and SV-T8 are placeholders; implementations in v0.1-beta-2 MUST reject Update System Operations with a clear error (see errors catalog - `MODE_REJECT` or `UPDATE_NOT_SUPPORTED`).
- **Service ID allocation.** Service IDs are globally unique within a deployment; the allocator is out of scope here and lives with the persistence schema.
- **Single-Binding assumption in v0.1.** The Service FSM specifies behavior for ≥1 Binding, but v0.1-beta-2 Deploy produces exactly one Binding per Service (one Manifest -> one Binding). Multi-Binding Services are a post-beta extension; INV-SV1 and the cascades are written to accommodate it without restructuring.
- **Testability.** Every `INV-SV*` is asserted at the transition boundary it constrains and has a matching test. Every `IR-SV*` is enforced at the owning FSM's boundary (e.g., IR-SVB rules are enforced by the Binding FSM driver; IR-SVS rules by the Session FSM driver; IR-SVO rules by the Overseer). See the invariant testability convention in `fsm-main.md` preface.
