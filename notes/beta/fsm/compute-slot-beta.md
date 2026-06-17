# Atelier FSM Atlas - ComputeSlot (§2.8)

Part of the **State Machine Atlas v0.1-beta-2**. See `fsm-beta.md` for the reading guide, notation, §2.4 FSMs - scope status, and §3 Cross-FSM Sequences. Owns the `INV-CS*` invariant prefix. Cross-references: `service-beta.md` (§2.5), `binding-beta.md` (§2.3), `task-beta.md` (§2.2), `sink-beta.md` (§2.11). Participates in **SEQ-1 Deploy** (`sequences-beta.md`) - CS-T1 soft-reserves at SV-T1, CS-T2 hard-reserves at SV-T2/B-T1, and CS-T2 grounds the 1:1 Task<->Slot runtime relationship (INV-CS1).

---

## 2.8 ComputeSlot FSM

The ComputeSlot FSM captures the lifecycle of a Pipeline position across activations. A ComputeSlot is a structural entity owned by a Pipeline (one row per `(pipeline_id, slot_ordinal)`); Tasks from successive Service activations occupy it one at a time. The taxonomy establishes the socket-vs-plug distinction: the Slot is the socket (schema-bearing, reusable), the Task is the plug (Skill-bearing, per-activation). This FSM formalizes the socket's state as the plug is inserted, replaced, or removed.

This FSM is the authority for ComputeSlot occupancy; any violation of INV-CS1 (1:1 Task<->Slot runtime relationship) indicates a bug in the Service, Binding, or Overseer driver for this FSM.

### 2.8.1 States

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  COMPUTESLOT STATES                                                          │
│                                                                              │
│     Vacant ──► Reserved ──► Occupied ──► Releasing ──► Vacant                │
│        │          │                                        │                 │
│        │          └───────────────────────────────────────►│                 │
│        │              (abort before Occupied: reservation   │                 │
│        │               released, slot resets to Vacant)     │                 │
│        │                                                   │                 │
│        └──────────────► Retired ◄──────────────────────────┘                 │
│                                                                              │
│  Retired: absorbing terminal for this row (Pipeline topology retirement).    │
│  The Retired edge is Update-driven and deferred in v0.1.                     │
└──────────────────────────────────────────────────────────────────────────────┘
```

**S-CS1: Vacant.** Slot row exists in persistent storage; no Task is assigned; no activation currently holds the slot. This is the state immediately after Pipeline creation and after every successful activation's release. Fields `current_activation_id`, `current_task_id`, `current_binding_id` are NULL. The input/output schemas are populated (Pipeline-level attributes) and immutable in v0.1.

Entry: Pipeline creation (initial write); reservation-release reset (abort before Occupied); CS-T4 (release after Occupied).
Exit: CS-T1 (soft reserve by an activation); CS-T6 (retire - deferred).

**S-CS2: Reserved.** Slot has been soft-reserved by SV-T1 (Service activation entering Provisioning). No Task is executing in the slot yet; no Binding holds it; the slot is earmarked so that no other activation can CS-T1 against it. `current_activation_id` is set; `current_task_id` and `current_binding_id` are NULL.

Entry: CS-T1.
Exit: CS-T2 (hard reserve by B-T1) or reservation-release reset (abort before Occupied -> Vacant).

**S-CS3: Occupied.** Slot is actively hosting a Task. `current_activation_id`, `current_task_id`, `current_binding_id` are all non-NULL. Schema compatibility between Task I/O schemas and Slot I/O schemas was validated at CS-T2 entry; the Task is running (T-T3 fired in the Task FSM) or eligible to run (T-T1 Accepted).

Entry: CS-T2.
Exit: CS-T3 (Task reaches a terminal state, or Binding is released/drained).

**S-CS4: Releasing.** Task has reached a terminal state (Completed or Failed) or its Binding is terminating (B-T4, B-T7), and the Slot is winding down its reference: any in-flight Artifact emission from this slot is allowed to drain to ArtifactChannel; the `current_*` fields are preserved for the duration so that lineage queries during the window resolve.

Entry: CS-T3.
Exit: CS-T4 (release complete - slot returns to Vacant).

**S-CS5: Retired.** Absorbing terminal for this row. The Pipeline topology has been updated to remove this `slot_ordinal`; the row is kept for lineage but no future activation may reference it. Entry only via Update System Operation (deferred in v0.1-beta-2).

Entry: CS-T6 (deferred).
Exit: none (terminal).

### 2.8.2 Transitions

```
CS-T1:  Vacant ──► Reserved
        Trigger:  SV-T1 (Service activation entering Provisioning, per §2.5).
        Guard:    Slot is in Vacant;
                  no other activation holds current_activation_id for this row
                    (enforced by atomic row-lock on (pipeline_id, slot_ordinal));
                  Slot I/O schemas are populated and valid.
        Effects:  Persist ComputeSlot row: state=reserved, current_activation_id,
                    reserved_at;
                  (current_task_id and current_binding_id remain NULL).

CS-T2:  Reserved ──► Occupied
        Trigger:  SV-T2 -> B-T1 (Binding creation). The Manifest that B-T1 transmits
                  identifies the Task that will occupy this Slot.
        Guard:    Slot is in Reserved;
                  current_activation_id = activation driving B-T1 (sanity check);
                  Task's declared input/output schemas MUST be compatible with
                    Slot's input/output schemas (INV-CS2);
                  target Agent's Skill set contains the Task's required Skill.
        Effects:  Persist ComputeSlot row: state=occupied, current_task_id,
                    current_binding_id, occupied_at;
                  (Task FSM fires T-T1 Accepted; Binding FSM fires B-T1 Pending).

CS-T3:  Occupied ──► Releasing
        Trigger:  Task reaches a terminal state (T-T6 Completed, T-T7 Failed, or the
                  stop-path terminals T-T9 Completed / T-T10 Failed - reference Task
                  FSM §2.2);
                  OR Binding B-T4 (Active -> Draining), B-T7 (agent_lost release),
                    B-T10 (manifest-rejection release) applied to this Slot's
                    current_binding_id.
        Guard:    Slot is in Occupied;
                  termination/drain signal has been acknowledged by the Task FSM
                    (for T-T* path) or Binding FSM (for B-T* path).
        Effects:  Persist ComputeSlot row: state=releasing, releasing_at;
                  (current_* fields preserved for lineage during the window).

CS-T4:  Releasing ──► Vacant
        Trigger:  Release completion - any draining Artifact has been Emitted to
                  its Sink (or explicitly discarded on agent_lost with grace
                  expired), and the Task/Binding has reached its terminal state.
        Guard:    Slot is in Releasing;
                  for Task T-T6 / T-T9 Completed: ArtifactChannel drained to EOS marker;
                  for T-T7 / T-T10 Failed: lineage records finalized;
                  for B-T7 agent_lost: grace window elapsed OR reconnect declared
                    unrecoverable.
        Effects:  Persist ComputeSlot row: state=vacant, current_activation_id=NULL,
                    current_task_id=NULL, current_binding_id=NULL, released_at;
                  the Service's SV-T9 or SV-T10 (or auto-stop/drain path) may now
                    observe zero Occupied/Releasing slots for its activation.

CS-T6:  (Vacant | Occupied) ──► Retired
        Trigger:  Pipeline topology Update retires this slot_ordinal.
        Guard:    Update System Operation in progress for this Pipeline.
        Effects:  DEFERRED in v0.1-beta-2 (Update is not in beta scope). When
                    specified, retire is an any-state -> Retired terminal that
                    clears the `current_*` triple. The Update path drains an
                    Occupied slot through the normal CS-T3 -> CS-T4 path before
                    retiring whenever possible.
```

**Reservation-release reset (abort before Occupied).** When a Reserved slot's activation aborts before occupancy (SV-T4 Service abort, or SV-T5 manifest rejected before B-T3 Active), the reservation is released and the slot **resets directly to Vacant** - `state=vacant, current_activation_id=NULL, reserved_at=NULL`. This reset is not a numbered transition: the implementation performs a direct state update on a slot that never reached Occupied (it never held a Task), so there is no Releasing window to drain. The numbered Occupied -> Releasing -> Vacant path (CS-T3 -> CS-T4) applies only to slots that were Occupied.

### 2.8.3 Invariants

**INV-CS1: 1:1 Task-Slot runtime relationship.** At any instant, for any ComputeSlot row in state Occupied: exactly one Task (by `current_task_id`) is associated; and for any Task in a slot-occupying state (Accepted, Running, Paused, Stopping, Restarting - per `task-beta.md` INV-T1): exactly one Slot (by `current_task_id` reverse lookup) is associated. Enforced at CS-T2 boundary (set current_task_id) and CS-T4 boundary (clear current_task_id).

**INV-CS2: Schema compatibility.** At CS-T2, the Task's declared input schema MUST equal or be subsumed by the Slot's input schema, AND the Task's declared output schema MUST equal or be subsumed by the Slot's output schema. Violation rejects the transition; the Manifest is then rejected (PEER_REJECTED cascade per §2.3 B-T10).

**INV-CS3: Pipeline-scoped single-activation lock in v0.1.** At any instant, for any `(pipeline_id, slot_ordinal)` row: at most one non-NULL `current_activation_id` value across all slots of that Pipeline. Equivalently: at most one concurrent Service activation per Pipeline in v0.1-beta-2. This is a v0.1-beta-2 simplification (see Notes §2.8.5); the ComputeSlot FSM itself does not preclude per-activation row instancing in a later version.

**INV-CS4: Slot ordinal and schemas immutable.** `slot_ordinal`, `input_schema`, `output_schema` are set at Pipeline creation and are immutable for the lifetime of the Slot row. Updating the Pipeline topology creates new rows and retires old ones (CS-T6), never mutates existing rows.

**INV-CS5: Retired is absorbing.** No transition exits Retired.

**INV-CS6: Release completeness gates Service termination.** SV-T9, SV-T10, SV-T5, SV-T4 require all Slots held by the Service's activation to be in Vacant. Specifically: SV-T4 / SV-T5 require all this activation's Reserved Slots returned to Vacant via the reservation-release reset, and any Slots that reached Occupied before a rejection returned to Vacant via CS-T3 -> CS-T4 (the rare spawn-then-reject case); SV-T9 / SV-T10 require all Slots in Vacant via CS-T4.

**INV-CS7: Field-fill consistency with state.**

| State | current_activation_id | current_task_id | current_binding_id |
|---|---|---|---|
| Vacant | NULL | NULL | NULL |
| Reserved | non-NULL | NULL | NULL |
| Occupied | non-NULL | non-NULL | non-NULL |
| Releasing | non-NULL (preserved) | non-NULL (preserved) | non-NULL (preserved) |
| Retired | NULL | NULL | NULL |

### 2.8.4 Interaction Rules

**ComputeSlot <-> Pipeline (IR-CSP)**

- **IR-CSP1:** Pipeline creation populates the Slot row set from the Pipeline's topology. Each Slot row carries the Pipeline's declared I/O schemas for that ordinal position.
- **IR-CSP2:** Pipeline deletion is permitted only when all its Slots are in Vacant or Retired. This rule lives on the Pipeline table; the ComputeSlot FSM enforces the precondition at Slot-row level.

**ComputeSlot <-> Service (IR-CSS)**

- **IR-CSS1:** SV-T1 fires CS-T1 on every Slot in the target Pipeline's topology, atomically (all-or-nothing - if any Slot is not Vacant, SV-T1 is rejected with `COMMAND_TARGET_WRONG_STATE`).
- **IR-CSS2:** SV-T2 fires CS-T2 on every reserved Slot (exactly once each, via the single Binding's B-T1 in v0.1).
- **IR-CSS3:** SV-T4 releases every Reserved Slot (reservation-release reset -> Vacant); SV-T5 releases Reserved Slots the same way, and drives CS-T3 -> CS-T4 on any Slots that reached Occupied before the rejection (rare: reject-after-occupy).
- **IR-CSS4:** SV-T6 (Stopping) fires CS-T3 on every Occupied Slot via the B-T4 cascade; the Service then waits in Stopping until every Slot has reached Vacant (INV-CS6).

**ComputeSlot <-> Task (IR-CST)**

- **IR-CST1:** T-T3 (Task Accepted -> Running) is admissible only when the owning Slot is Occupied (CS-T2 has fired). The Task FSM driver checks the Slot state before firing T-T3.
- **IR-CST2:** T-T6 (Task Completed), T-T7 (Failed), and the stop-path terminals T-T9 (Completed) / T-T10 (Failed) each fire CS-T3 on the owning Slot.

**ComputeSlot <-> Binding (IR-CSB)**

- **IR-CSB1:** B-T1 effects include CS-T2 firing for every Slot covered by the Manifest.
- **IR-CSB2:** B-T4 (Active -> Draining), B-T6, B-T7, B-T10 fire CS-T3 on every Occupied Slot held by this Binding.
- **IR-CSB3:** B-T8 (Releasing -> Released) requires every Slot covered by the Binding to have reached Vacant (i.e., CS-T4 fired). This is the Binding-level mirror of INV-CS6.

### 2.8.5 Notes

- **Intra-slot Skill composition (Sync).** A single ComputeSlot hosts the full Ingest -> Sync -> Emit Skill chain of its occupying Task. **Sync is an intra-slot composition, not a slot boundary**: the Task ingests from its source, aligns events to a clock, and emits the consolidated output all within the one Slot it occupies. The Slot's input/output schemas are defined at the slot level (the data shape entering and leaving the Slot); the Ingest -> Sync -> Emit pipeline runs inside the occupying Task and is not modeled as separate Slots. A multi-Slot Pipeline composes Tasks across Slots (one Slot's output feeds the next), but Sync itself never spans a Slot boundary.
- **Pipeline-scoped rows, single-active-Service constraint.** In v0.1-beta-2, a Pipeline can have at most one active Service at a time (INV-CS3). This simplification keeps ComputeSlot state single-valued without introducing per-activation instance rows. A later version may relax to concurrent activations by instancing rows per activation or by extending state to a map.
- **Update-driven transition deferred.** CS-T6 is the Update-path transition; it is enumerated for completeness and deferred with the Update System Operation.
- **Schema subsumption.** INV-CS2's "equal or subsumed by" allows a Task with a more general output schema to occupy a slot with a more specific output schema (covariant output) and a Task with a more specific input schema to occupy a slot with a more general input schema (contravariant input). The precise subsumption rule is part of the Schema subsystem (out of scope for v0.1 FSM work; treat as equality for the beta implementation).
- **Sink attachment.** ComputeSlot does not directly track Sink attachment; the Task's `sink_assignments` field (per Manifest) carries that. CS-T2 verifies the assigned Sinks exist and are in Ready state via §2.11.
- **Testability.** Every `INV-CS*` is asserted at its transition boundary. `INV-CS1` is the load-bearing invariant and is asserted at both CS-T2 (setting) and CS-T4 (clearing) - violations are structural bugs in the Task<->Slot join logic.
