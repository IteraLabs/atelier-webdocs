# Atelier FSM Atlas - Task (§2.2)

Part of the **State Machine Atlas v0.1-beta-2**. See `fsm-main.md` for the reading guide, notation, §2.4 FSMs - scope status, and §3 Cross-FSM Sequences. Owns the `INV-T*` invariant prefix. Cross-references: `agent.md` (§2.1), `binding.md` (§2.3), `compute-slot.md` (§2.8), `sink.md` (§2.11), `channel.md` (§2.10). Participates in **SEQ-1 Deploy** (`sequences.md`) - Tasks are the unit of work whose `Pending -> Accepted -> Running` progression (T-T1/T-T3) closes the Deploy sequence.

---

## 2.2 Task FSM

The Task FSM captures the lifecycle of a single Task from dispatch through a terminal state. Tasks are the unit of work in Atelier. Acceptance, rejection, execution, pausing, stopping, and restarting all terminate in one of three absorbing states: `Completed`, `Failed`, or `Rejected`.

### 2.2.1 States

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  TASK STATES                                                                 │
│                                                                              │
│         Pending                                                              │
│          │  │                                                                │
│  accept  │  │  reject                                                        │
│          ▼  ▼                                                                │
│      Accepted  Rejected (terminal)                                           │
│          │                                                                   │
│          ▼                                                                   │
│       Running ◄──► Paused                                                    │
│         │ │ │                                                                │
│         │ │ └──► Restarting ──┐                                              │
│         │ │          │        │                                              │
│         │ │          ▼        │                                              │
│         │ └───► Stopping      │                                              │
│         │         │  │        │                                              │
│         ▼         ▼  ▼        ▼                                              │
│     Completed   Failed ◄──────┘                                              │
│                                                                              │
│  Terminal (absorbing) states: Completed, Failed, Rejected                    │
└──────────────────────────────────────────────────────────────────────────────┘
```

**S-T1: Pending.** Task has been dispatched as part of a Manifest. The Agent has not yet responded with a `ManifestAck`.

**S-T2: Accepted.** The Agent accepted this Task in its `ManifestAck`. Execution is imminent. The Task's ComputeSlot is reserved.

**S-T3: Running.** The Agent is actively executing the Task. Artifacts may be produced and emitted.

**S-T4: Paused.** Execution suspended via Pause Command. State preserved; no new Artifacts produced. Connections to external sources may be dropped or quiesced depending on the Task type.

**S-T5: Restarting.** Soft-restart in progress, cascaded from Agent A-T8. Task identity preserved; `restart_epoch` has been incremented on entry. Bounded by `stop_drain_timeout` (INV-T8).

**S-T6: Stopping.** Stop Command received (Task-scoped or Agent-scoped cascade); the Agent is draining buffers and finalizing in-flight Artifacts. Bounded by `stop_drain_timeout`.

**S-T7: Completed.** Absorbing terminal. Task finished normally (natural completion or graceful Stop acknowledgment).

**S-T8: Failed.** Absorbing terminal. Task ended abnormally: runtime error, drain timeout with partial flag, Restart timeout, `agent_lost` cascade, or Binding force-release.

**S-T9: Rejected.** Absorbing terminal. Task was never executed: the Agent rejected it in `ManifestAck` with one of the three v0.1 reasons (`SKILL_MISMATCH`, `SPEC_INVALID`, `INTERNAL_ERROR`), or a sibling Task rejection in the same Manifest cascaded into `PEER_REJECTED` (taxonomy §Acceptance and rejection).

### 2.2.2 Transitions

```
T-T1:  Pending ──► Accepted
       Trigger:  ManifestAck.TaskAcceptance.accepted == true for this Task ID.
       Guard:    ManifestAck schema valid; INV-T6 holds.
       Effects:  Reserve the Task's ComputeSlot;
                 record acceptance in persistent storage;
                 contributes to Binding B-T3 (Pending -> Active) when ALL sibling Tasks
                 also accept.

T-T2:  Pending ──► Rejected
       Trigger:  EITHER ManifestAck.TaskAcceptance.accepted == false (self-rejection
                 with rejection_reason ∈ {SKILL_MISMATCH, SPEC_INVALID,
                 INTERNAL_ERROR})
                 OR any sibling Task in the same Manifest was rejected (PEER_REJECTED
                 cascade via IR-BT2).
       Guard:    INV-T6 holds.
       Effects:  Record rejection_reason on Task;
                 on self-rejection path: contributes to Binding B-T10
                   (Pending -> Releasing with release_reason = task_rejected);
                 on peer_rejected path: already inside B-T10.

T-T3:  Accepted ──► Running
       Trigger:  Agent begins execution of the Task on its ComputeSlot.
       Guard:    Binding Active; Agent ∈ {Ready, Bound};
                 ComputeSlot is the one reserved by T-T1.
       Effects:  Emit TaskRunning; begin accepting Artifacts on outbound
                 ArtifactChannels.

T-T4:  Running ──► Paused
       Trigger:  Pause Command received (Task-scoped targeting this Task, or
                 Agent-scoped targeting this Task's Binding).
       Guard:    Overseer mode permits Pause per §1.4 matrix (`overseer.md`).
       Effects:  Agent quiesces the Task; Artifact production halts;
                 Ack(CMD_ID, status=OK).

T-T5:  Paused ──► Running
       Trigger:  Resume Command received (same scoping rules as T-T4).
       Guard:    Overseer mode permits Resume per §1.4 matrix (`overseer.md`).
       Effects:  Agent resumes the Task; Artifact production resumes;
                 Ack(CMD_ID, status=OK).

T-T6:  Running ──► Completed
       Trigger:  Task's natural completion condition met (e.g., bounded Experiment
                 reached programmed end; internal termination signal received).
       Guard:    none
       Effects:  Finalize outstanding Artifacts;
                 release ComputeSlot reservation;
                 emit TaskCompleted.

T-T7:  Running ──► Failed
       Trigger:  Unrecoverable runtime error (e.g., source disconnect beyond retry
                 budget, schema validation failure at Emit, fatal exception in
                 Transform).
       Guard:    none
       Effects:  Log error; flush partial Artifacts with partial=true;
                 emit TaskFailed;
                 contributes to Binding B-T5 if last non-terminal Task.

T-T8:  {Running, Paused} ──► Stopping
       Trigger:  Stop Command received (Task-scoped, Agent-scoped cascade, or Binding
                 drain cascade via IR-BT3).
       Guard:    Overseer mode permits Stop per §1.4 matrix (`overseer.md`).
       Effects:  Begin drain: flush buffers, finalize in-flight Emit operations,
                 close external source connections;
                 start stop_drain_timeout timer;
                 Ack will be emitted on entry to Completed or Failed.

T-T9:  Stopping ──► Completed
       Trigger:  Drain finished within stop_drain_timeout; all Artifacts finalized
                 cleanly.
       Guard:    Timer not expired.
       Effects:  Emit TaskCompleted; release ComputeSlot;
                 Ack(CMD_ID, status=OK).

T-T10: Stopping ──► Failed
       Trigger:  stop_drain_timeout expired with drain incomplete.
       Guard:    Timer expired.
       Effects:  Mark in-flight Artifacts with partial=true;
                 emit TaskFailed with reason=drain_timeout;
                 Ack(CMD_ID, status=PARTIAL).

T-T11: {Accepted, Running, Paused, Stopping, Restarting} ──► Failed
       Trigger:  Binding release cascade with release_reason ∈ {agent_lost, force}
                 (via IR-BT3 from Binding B-T6 / B-T7).
       Guard:    none
       Effects:  Mark any in-flight Artifacts as partial=true;
                 emit TaskFailed with reason matching release_reason;
                 no Ack is required (the Command path is assumed lost).

T-T12: Running ──► Restarting
       Trigger:  Agent enters Restarting via A-T8 (IR-AT1).
       Guard:    none
       Effects:  Agent increments restart_epoch on this Task's Artifact lineage;
                 current buffers are discarded or persisted as partial per Task
                 configuration (default: discarded for streaming Tasks, persisted
                 for batch Tasks);
                 no Ack needed (Restart is fire-and-observe via telemetry).

T-T13: Restarting ──► Running
       Trigger:  Agent re-initialization for this Task succeeds within
                 stop_drain_timeout.
       Guard:    Agent in Restarting; re-init signaled complete for this Task.
       Effects:  Resume execution with restart_epoch incremented;
                 emit TaskRestarted(task_id, new_epoch);
                 contributes to Agent A-T9.

T-T14: Restarting ──► Failed
       Trigger:  Agent re-initialization for this Task fails OR stop_drain_timeout
                 expires during Restart.
       Guard:    Timer expired OR Agent reports re-init failure for this Task.
       Effects:  Emit TaskFailed with reason=restart_failed;
                 contributes to Agent A-T10 if all Tasks reach T-T14;
                 contributes to Binding B-T5 with release_reason=task_failed if last
                 non-terminal Task.
```

### 2.2.3 Invariants

**INV-T1: ComputeSlot occupancy.** A Task in {`Accepted`, `Running`, `Paused`, `Stopping`, `Restarting`} occupies exactly one ComputeSlot. Tasks in {`Pending`, `Completed`, `Failed`, `Rejected`} occupy none.

**INV-T2: Domain alignment.** A Task's ComputeSlot is in the same Domain as its Agent. RemoteAgent <-> RemoteComputeSlot; PlatformAgent <-> PlatformComputeSlot.

**INV-T3: Command target validity.** A Task-scoped Command must reference a Task ID that the target Agent is currently holding; otherwise the Agent acks with `status=REJECTED` and no state change occurs.

**INV-T4: Task ID preserved across Restart.** Task ID is immutable across soft-restart. `restart_epoch` is recorded on Artifact lineage, starting at 0 and incrementing on each successful entry into Running via T-T13.

**INV-T5: Terminal absorbingness.** States in {`Completed`, `Failed`, `Rejected`} are absorbing. No transitions leave these states.

**INV-T6: ManifestAck atomicity.** Within a single Manifest, the `Pending -> {Accepted, Rejected}` transitions for all Tasks are evaluated atomically from a single `ManifestAck`. Partial ManifestAcks (some Tasks responded, others not) are protocol errors.

**INV-T7: Rejected produces no Artifacts.** A Task that reaches `Rejected` never occupies its ComputeSlot beyond the pre-acceptance reservation, never emits on ArtifactChannels, and never contributes to `Artifact.task_id` lineage.

**INV-T8: Restart is bounded.** `Restarting` duration is bounded by `stop_drain_timeout`. The Task must reach T-T13 or T-T14 within that window.

**INV-T9: restart_epoch monotone.** `restart_epoch` on Artifact lineage is monotone non-decreasing across the Task's lifetime and strictly increasing on each successful T-T13.

### 2.2.4 Interaction Rules

**Task <-> Agent (IR-TA)**

- **IR-TA1:** Task `Accepted -> Running` (T-T3) requires Agent ∈ {`Ready`, `Bound`} and Binding `Active`.
- **IR-TA2:** Agent `Restarting` (A-T8) cascades all `Running` Tasks to `Restarting` (T-T12); Tasks in `Paused` stay `Paused` through the restart window unless their Binding is released.
- **IR-TA3:** Successful T-T13 contributes to Agent A-T9; all-Tasks T-T14 contributes to Agent A-T10.
- **IR-TA4:** Task `Stopping -> Completed` (T-T9) or `Failed` (T-T10) contributes to the Agent's readiness for A-T4 (Bound -> Ready) via Binding B-T6 -> B-T8.
- **IR-TA5:** Agent `Terminated` (A-T7 / A-T15) force-fails every non-terminal Task on this Agent via Binding cascade (T-T11).

Task <-> Binding interactions are specified in Binding IR-BT (`binding.md §2.3.4`).
