# Atelier FSM Atlas - Agent (§2.1)

Part of the **State Machine Atlas v0.1-beta-2**. See `fsm-beta.md` for the reading guide, notation, §2.4 FSMs - scope status, and §3 Cross-FSM Sequences. Owns the `INV-A*` invariant prefix. Cross-references: `overseer-beta.md` (§1 Overseer FSM, §1.4 Operation Availability Matrix), `task-beta.md` (§2.2), `binding-beta.md` (§2.3), `gateway-beta.md` (§2.9). Participates in **SEQ-1 Deploy** (`sequences-beta.md`) as the RemoteAgent that Registers (A-T1/A-T2), Binds (A-T3), and runs Tasks. Participates in **SEQ-2 Delete** (`sequences-beta.md §3.2`) as the Agent whose A-T4 (Bound -> Ready) follows the last Binding release and whose A-T16 (Ready -> Terminated) closes the sequence on `AGENT_TERMINATE`.

This file also covers **§2.1.5 Open items and resolutions** - the resolved Gateway-persistence contract referenced by `gateway-beta.md §2.9` INV-GW1 and `channel-beta.md §2.10` INV-CH5.

---

## 2.1 Agent FSM

The Agent FSM captures the runtime lifecycle of a RemoteAgent or PlatformAgent. Both types share the same state space - the Remote/Platform distinction is an immutable attribute (INV-A9), not a state split - with one asymmetry: PlatformAgents receive Stop during Overseer Drain, RemoteAgents do not (IR-O2 / IR-AO1).

### 2.1.1 States

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  AGENT STATES                                                                │
│                                                                              │
│  Registering ──► Registered ──► Ready ◄───► Bound                            │
│       │              │            │           │    ▲                         │
│       │              │            │           │    │                         │
│       │              │            └──► Restarting ─┘                         │
│       │              │            │           │                              │
│       │              │            ▼           ▼                              │
│       │              │         Draining ◄─────┘ (cascade)                    │
│       │              │            │                                          │
│       │              │            ▼                                          │
│       ├──────────────┼────────► Terminated                                   │
│       │              │                                                       │
│       └─► (Lost) ◄───┘ - reconciles back to prior state or to Terminated     │
└──────────────────────────────────────────────────────────────────────────────┘
```

**S-A1: Registering.** Handshake in progress; Agent announced via the Gateway (RemoteAgent) or by the Overseer's spawner (PlatformAgent). Not yet routable. No Bindings.

**S-A2: Registered.** Gateway has terminated the handshake successfully and allocated `agent_id`; Skill set is on the Agent record but the Overseer has not yet validated that those Skills cover the bound Manifest's required Skills. No Bindings active. Distinct from `Ready` because under the BYO-infra path (`sequences-beta.md §3.1.1`) the Manifest exists in Phase A before the Agent registers, and the Skill-subset check is the Overseer-side gate from `Registered` to `Ready` (A-T2). The state is therefore short-lived in the happy path but has its own failure exit (A-T18 for Skill mismatch). For the legacy non-BYO path, where no Manifest is yet bound when Registration arrives, the Skill-subset check is trivially satisfied and A-T2 fires immediately after A-T1.

**S-A3: Ready.** Registered, Skill-validated, and operable; no active Bindings. Eligible for Binding assignment. Accepts Restart but not Stop (no active work for PlatformAgent; Stop is not addressed to RemoteAgents at all per IR-AO1).

**S-A4: Bound.** Registered and operable; ≥1 Binding in {`Active`, `Draining`, `Releasing`}. Eligible for further Binding assignment subject to capacity.

**S-A5: Draining.** Winding down. No new Binding assignments. Existing Bindings in `Draining` or `Releasing`. Entered by Stop (PlatformAgent path) or by Overseer Drain cascaded through all of the Agent's Bindings (RemoteAgent path).

**S-A6: Restarting.** Soft-restart in progress. Agent identity, Agent ID, Skill set, and all Task IDs are preserved (INV-A1, taxonomy §Restart mechanics). Every Running Task cascades into Task `Restarting` (IR-AT1). Bounded by `stop_drain_timeout` (INV-A6).

**S-A7: Lost.** Connection dropped. Reconciliation grace timer running. Bindings are provisionally retained pending reconnection. The grace duration depends on the state the Agent was in when connection dropped: 60s from {`Ready`, `Bound`}, 120s from `Draining`, `stop_drain_timeout` from `Restarting` (IR-AO4).

**S-A8: Terminated.** Absorbing terminal state. Agent removed from the operating set. PlatformAgents: process has exited. RemoteAgents: deregistered.

### 2.1.2 Transitions

```
A-T1:  Registering ──► Registered  [Gateway-driven; RemoteAgent + PlatformAgent]
       Trigger:  Gateway reports successful handshake with valid capability
                 payload (RemoteAgent: outbound gRPC bidirectional CommandChannel
                 stream against Gateway, JWT validated against
                 `GATEWAY_JWT_SECRET`; PlatformAgent: spawner reports process
                 launch + capability advertisement complete).
       Guard:    Overseer mode ∈ {Full, Degraded} (`§1.4`);
                 envelope has room for +1 Agent (IR-O4);
                 capability payload structurally valid (well-formed Skill enum,
                   non-empty Skill set);
                 for RemoteAgent path: JWT-implied `(session_id, binding_id,
                   service_id)` resolves to an existing `bindings` row in
                   `pending`.
       Effects:  AgentId is ALLOCATED at A-T1 by the Gateway (the sole process
                   that terminates the Registration handshake per
                   `gateway-beta.md §2.9` / `fsm-beta.md §2.4.1`). AgentId is
                   generated as UUIDv4 and returned to the Agent in
                   `RegistrationResponse.Accepted.agent_id`
                   (`proto-catalog-beta.md §control.proto`). The inbound
                   `Registration` body carries `agent_alias` only (plus
                   `agent_type`, `skills`, `host_identity`, `target_session_id`);
                   it MUST NOT carry an `agent_id`, and MUST NOT carry a
                   `binding_id`. Any such field is rejected with
                   ErrorKind.REGISTRATION_INVALID.
                 Insert into registry; index by Skill set;
                 emit AgentRegistered (transition_id = "A-T1").
       Note:     A-T1 stops at Registered (NOT Ready) so that the Overseer-side
                 Skill-subset check against the bound Manifest can fire as a
                 separate transition (A-T2). Under the BYO-infra path
                 (`sequences-beta.md §3.1.1` Phase B step 12), the Manifest exists in
                 Phase A before Registration arrives; the Skill-subset gate is
                 the load-bearing check. For the legacy non-BYO path (no
                 Manifest bound at Registration time), A-T2 fires trivially
                 immediately after A-T1 - see A-T2 Note.

A-T2:  Registered ──► Ready  [Overseer-driven; Skill-subset check]
       Trigger:  Overseer-side validation that the Agent's declared Skills cover
                 the bound Manifest's required Skills.
       Guard:    Skill set non-empty (INV-A10);
                 if Manifest bound: Agent's Skills ⊇ Manifest's required Skills;
                 if no Manifest bound (legacy path): trivially satisfied.
       Effects:  Persist `agents.status='ready'`;
                 emit AgentReady(agent_id, restart_epoch=0)
                 (transition_id = "A-T2").
       Note:     For BYO-infra (`sequences-beta.md §3.1.1` Phase B step 14), A-T2
                 uses the Phase-A-composed Manifest as the right-hand side of
                 the subset check. Skill-mismatch failure exits via A-T18.

A-T3:  Ready ──► Bound
       Trigger:  A Binding on this Agent reaches Active (B-T3).
       Guard:    none
       Effects:  None Agent-side; drives IR-AB2.
       Note:     Under BYO-infra (v0.1-beta-2) the Agent already holds the
                 FULL augmented Manifest body before A-T3 fires - it was
                 delivered verbatim in the gRPC handshake response
                 (`HandshakeResult.toml_config`, SEQ-1 step 11-13). The
                 body carries `[[metadata.tasks]]` per INV-M4
                 (`manifest-beta.md §4`); the Agent's `parse_metadata_tasks`
                 call at handshake-completion hydrates the canonical
                 `task_id` into `UpstreamSinkConfig.task_id` for every
                 spawned worker. INV-M5 (no lineage-bearing emission
                 before canonical-id hydration) is trivially satisfied:
                 the hydration step strictly precedes worker spawn
                 inside `RemoteAgent::run`. Failure mode on malformed
                 `[[metadata.tasks]]` per INV-M8: agent process exits
                 non-zero before any wire emission; Overseer observes
                 the loss via heartbeat-timeout cascade A-T11 (Bound ->
                 Lost) -> A-T15 (grace expiry -> Terminated), with B-T7
                 carrying `release_reason='agent_lost'`.

A-T4:  Bound ──► Ready
       Trigger:  Agent's last Binding reaches Released (B-T8).
       Guard:    No Bindings in {Active, Draining, Releasing}.
       Effects:  None.

A-T5:  Bound ──► Draining
       Trigger:  Stop Command received [PlatformAgent path]
                 OR all Agent Bindings reach Draining via Overseer drain cascade
                 [RemoteAgent path].
       Guard:    For Stop path: Agent is a PlatformAgent (IR-AO1).
       Effects:  Refuse new Binding assignments;
                 drive any non-Draining Bindings to Draining via B-T4
                   [PlatformAgent path only - RemoteAgent's Bindings are already
                   Draining by construction].

A-T6:  Ready ──► Terminated
       Trigger:  Stop Command received on idle PlatformAgent.
       Guard:    Agent is a PlatformAgent; no Bindings.
       Effects:  Terminate process; deregister; emit AgentTerminated.

A-T7:  Draining ──► Terminated
       Trigger:  All Bindings reached Released OR drain grace timer expired.
       Guard:    none
       Effects:  PlatformAgent: terminate process.
                 RemoteAgent: deregister (no platform-side process to kill).
                 Force-release any non-Released Bindings with release_reason=force;
                 emit AgentTerminated.

A-T8:  {Ready, Bound} ──► Restarting
       Trigger:  Restart Command received (Agent-scoped or Task-scoped targeting
                 this Agent).
       Guard:    Overseer mode = Full (§1.4 Restart matrix);
                 Agent not in {Draining, Lost}.
       Effects:  Signal Agent process to re-initialize in place;
                 all bound Tasks transition to Restarting (T-T12);
                 Bindings remain Active;
                 Artifact restart_epoch incremented per affected Task on entry;
                 start stop_drain_timeout timer.

A-T9:  Restarting ──► Bound
       Trigger:  Agent process signals re-init complete AND ≥1 Task returns to
                 Running via T-T13.
       Guard:    Within stop_drain_timeout.
       Effects:  Resume dispatch eligibility for remaining capacity;
                 clear restart timer.

A-T10: Restarting ──► Ready
       Trigger:  Agent process signals re-init complete AND all Tasks failed
                 (T-T14), cascading Bindings to Released with release_reason =
                 task_failed.
       Guard:    Within stop_drain_timeout.
       Effects:  Agent idle and operable; clear restart timer.

A-T11: {Ready, Bound} ──► Lost
       Trigger:  Gateway reports connection loss.
       Guard:    none
       Effects:  Start reconciliation grace timer (`agent.reconnect_grace_ms`, 60s);
                 mark Bindings as disconnected;
                 queue Commands at Overseer (IR-AO4).

A-T12: Draining ──► Lost
       Trigger:  Gateway reports connection loss while Agent in Draining.
       Guard:    none
       Effects:  Start reconciliation grace timer (`agent.reconnect_grace_draining_ms`, 120s, drain window);
                 Bindings remain in their current Draining / Releasing states.

A-T13: Restarting ──► Lost
       Trigger:  Gateway reports connection loss while Agent in Restarting.
       Guard:    none
       Effects:  Repurpose stop_drain_timeout timer as grace window;
                 no separate timer started.

A-T14: Lost ──► {Ready, Bound, Draining, Restarting}
       Trigger:  Gateway reports reconnection; identity verified;
                 capability set matches registered capabilities.
       Guard:    Grace timer not expired; capability parity.
       Effects:  Restore prior state (tracked on Agent record);
                 resume Command processing;
                 clear grace timer.

A-T15: Lost ──► Terminated
       Trigger:  Reconciliation grace timer expires OR reconnection attempted with
                 capability mismatch.
       Guard:    none
       Effects:  Force-release all remaining non-Released Bindings with
                 release_reason = agent_lost;
                 remove from registry;
                 emit AgentTerminated.

A-T16: Ready ──► Terminated
       Trigger:  AGENT_TERMINATE Command received targeting this Agent. Dispatched
                 by the Overseer as Phase G of the Delete System Operation
                 (taxonomy §Operations / Delete; SEQ-2 `sequences-beta.md §3.2`).
                 Applies symmetrically to RemoteAgents and PlatformAgents; distinct
                 from Stop (A-T5, A-T6) and therefore not subject to INV-A5.
       Guard:    Overseer mode ∈ {Full, Degraded} (§1.4);
                 Agent in Ready - i.e., zero Bindings in
                 {Active, Draining, Releasing} (INV-A3 holds).
                 On guard failure (any remaining non-Released Binding) reject with
                 ErrorKind.COMMAND_TARGET_WRONG_STATE (41); Delete must complete
                 its BINDING_RELEASE phase first.
       Effects:  PlatformAgent: terminate process.
                 RemoteAgent: deregister (no platform-side process to kill);
                   transport-layer close of remaining Channels (CommandChannel,
                   TelemetryChannel, and any local ArtifactChannel whose Sink
                   handle is still open) - Channel FSM §2.10 provisioning-only in
                   v0.1-beta-2, so these closes are operational cleanup, not
                   normative FSM transitions.
                 Decrement `sessions.envelope_counters` agents count;
                 set `agents.terminated_reason = 'operator_stop'`;
                 emit AgentTerminated(agent_id, terminated_reason='operator_stop');
                 CommandAck(command_id, status=OK) emitted by the Agent on exit.

A-T17: Registering ──► Terminated  [handshake failure]
       Trigger:  Gateway signals handshake failure OR registration timeout
                 (`agent.registration_window_ms`, default 30s) before the
                 capability payload validates.
       Guard:    none
       Effects:  Drop Agent record; no Binding cleanup (none exist at
                 Registering - IR-AB1a holds);
                 set `agents.terminated_reason = 'registration_expired'` (when
                 a row was partially persisted) OR no row lands;
                 emit AgentTerminated(transition_id = "A-T17") if a row was
                 written, else no event.
       Renumbered from old A-T2 (Registering -> Terminated) when v0.1-beta-2
       added the Registered state. Spec-only relabel; no wire-format
       implication because the transition was never carried as a stable
       transition_id on Event.

A-T18: Registered ──► Terminated  [Skill mismatch]
       Trigger:  A-T2 guard rejected - Agent's declared Skills do not cover the
                 bound Manifest's required Skills.
       Guard:    none (this is the failure exit from Registered).
       Effects:  **Cascade order is release-then-terminate** so the Binding's
                 release_reason carries the proximate cause, not the downstream
                 grace-expiry.
                   1. Fire B-T2 on the bound Binding with
                      `release_reason='skill_mismatch'` (`binding-beta.md §2.3.1`,
                      §2.3.2 B-T2). The Pending Binding is actively released
                      with the skill-mismatch reason, distinct from the passive
                      `registration_grace_timeout` path in B-T2 that would
                      otherwise fire later via the live ticker.
                   2. Set `agents.status = 'terminated'`,
                      `agents.terminated_reason = 'skill_mismatch'`.
                   3. Emit `AgentTerminated(agent_id,
                      terminated_reason='skill_mismatch',
                      transition_id = "A-T18")`.
                 SV-T10 cascades from B-T2's slot release per
                 `service-beta.md §2.5` (Service auto-stops on last live Binding
                 release; INV-SV6 holds - `skill_mismatch ≠ task_rejected`).
```

### 2.1.3 Invariants

**INV-A1: Identity preserved across Restart.** Agent ID is immutable across soft-restart (A-T8 -> A-T9 / A-T10). `restart_epoch` is recorded on Artifact lineage, never on Agent state. Task IDs are likewise preserved.

**INV-A2: Binding-Agent reference integrity.** Any Binding in {`Active`, `Draining`, `Releasing`} references an Agent in state ∈ {`Ready`, `Bound`, `Draining`, `Restarting`, `Lost`}. `Released` Bindings may reference `Terminated` Agents (historical lineage).

**INV-A3: Ready has no active work.** An Agent in `Ready` has zero Bindings in {`Active`, `Draining`, `Releasing`}.

**INV-A4: Bound has active work.** An Agent in `Bound` has ≥1 Binding in {`Active`, `Draining`, `Releasing`}.

**INV-A5: Stop is PlatformAgent-only.** Stop Commands are delivered only to PlatformAgents (IR-O2 / IR-AO1). RemoteAgents reach `Draining` solely via Binding cascade.

**INV-A6: Restart is bounded.** Soft-restart duration is bounded by `stop_drain_timeout`. The Agent must reach A-T9, A-T10, or A-T13 within that window; otherwise the restart is treated as a failure (all affected Tasks routed through T-T14).

**INV-A7: Terminated is absorbing.**

**INV-A8: Lost processes no Commands.** An Agent in `Lost` processes no Commands; the Overseer queues or rejects per the Operation Availability Matrix.

**INV-A9: Agent type is immutable.** RemoteAgent vs PlatformAgent is set at Registration and does not change for the lifetime of the FSM instance.

**INV-A10: Skills non-empty before Ready.** An Agent in `Ready` (or any state reachable from Ready: `Bound`, `Draining`, `Restarting`, `Lost`) has a non-empty Skill set. Anchored at A-T2's guard. The Skill set is fixed at A-T1 and remains immutable thereafter (set per Registration, preserved across A-T8 soft-restart per INV-A1).

**INV-A2 update:** The state set in INV-A2 ("Any Binding in {Active, Draining, Releasing} references an Agent in state ∈ {Ready, Bound, Draining, Restarting, Lost}") is unchanged by the Registered state introduction. A Binding is only Active after B-T3 fires, and B-T3's guard requires the Agent be Ready (per IR-CHO1 + IR-CHO2 channels-open precondition, which itself implies A-T2 has fired). Registered Agents therefore never appear on the right-hand side of INV-A2.

### 2.1.4 Interaction Rules

**Agent <-> Binding (IR-AB)**

- **IR-AB1:** Binding activation (B-T3) requires Agent ∈ {`Ready`, `Bound`}.
- **IR-AB2:** Agent `Ready -> Bound` (A-T3) is driven by first Binding reaching Active; `Bound -> Ready` (A-T4) by last Binding reaching Released.
- **IR-AB3:** Agent `Bound -> Draining` (A-T5) cascades all non-Draining Bindings to Draining via B-T4 on the PlatformAgent path. On the RemoteAgent path, Bindings are already Draining by construction before A-T5 fires.
- **IR-AB4:** Agent `Terminated` (A-T7 / A-T15) force-releases all non-Released Bindings. `release_reason` is `force` when reached via A-T7 on drain timeout, and `agent_lost` when reached via A-T15 on grace expiry.

**Agent <-> Task (IR-AT)**

- **IR-AT1:** Agent `Restarting` (A-T8) drives all Tasks bound via this Agent into Task `Restarting` (T-T12).
- **IR-AT2:** Task `Restarting -> Running` (T-T13) contributes to Agent A-T9; all-Tasks-failed contributes to A-T10.
- **IR-AT3:** Agent `Terminated` force-fails any Task not in {`Completed`, `Failed`, `Rejected`} via the Binding release cascade (IR-BT3 / IR-TA5).

**Agent <-> Overseer (IR-AO)**

- **IR-AO1:** The Overseer delivers Stop only to PlatformAgents (counterpart to IR-O2). Attempts on RemoteAgents are rejected at the Command-accept boundary.
- **IR-AO2:** The Overseer delivers Restart symmetrically to both Agent types (counterpart to the Restart matrix rows in §1.4, `overseer-beta.md`).
- **IR-AO3:** The Overseer gates Command delivery on `Agent.state` per the Operation Availability Matrix; `Lost` gates everything except implicit reconciliation.
- **IR-AO4:** Reconciliation in `Lost` follows the protocol in §1.7 (`overseer-beta.md`) with grace timers: 60s from {`Ready`, `Bound`}, 120s from `Draining`, `stop_drain_timeout` from `Restarting`.
- **IR-AO5:** The Overseer dispatches `AGENT_TERMINATE` as Phase G of the Delete System Operation (SEQ-2 `sequences-beta.md §3.2`). Precondition: the target Agent is in `Ready` (zero non-Released Bindings). A-T16 fires on receipt; if the precondition is violated, the Command is rejected with `COMMAND_TARGET_WRONG_STATE` (41). Delete's preceding `BINDING_RELEASE` phase (IR-AB3 + B-T4/B-T6/B-T8 cascade via A-T4) is what brings the Agent to `Ready` for A-T16.

### 2.1.5 Open items and resolutions

**Resolved (v0.1-beta-2): Gateway connection persists through RemoteAgent soft-restart.**

The transport-layer behavior during RemoteAgent soft-restart was previously deferred to the Gateway FSM (§2.9). That deferral is resolved here for v0.1: the Gateway connection **persists** through RemoteAgent soft-restart. A-T8 (`{Ready, Bound} -> Restarting`) does not close or cycle the CommandChannel, the TelemetryChannel, or any open ArtifactChannel. The Agent process re-initializes in place on top of the existing transport; no re-handshake with the Gateway is required.

Consequences:

- **A-T13 remains the exceptional path.** `Restarting -> Lost` fires only when the Gateway independently observes a disconnect during an ongoing Restart (network loss, forced socket close by the Agent's host, Gateway-side error). Per A-T13 effects, the `stop_drain_timeout` timer is repurposed as the grace window in that case; no new timer is started.
- **`stop_drain_timeout` governs the in-process re-init duration** (INV-A6, INV-T8) on the normal Restart path. No separate reconnection grace applies because no reconnection is required on the normal path.
- **Channels survive Restart with their sequence state intact.** This is what makes `restart_epoch` a sufficient differentiator on Artifact lineage: the transport does not re-handshake, so lineage consumers see continuous sequence numbers on the underlying Channels interrupted only by the `restart_epoch` increment on Artifacts produced post-restart.
- **The forthcoming Gateway FSM (§2.9) must honor this contract in v0.1.** Specifically, Gateway states during an Agent-side soft-restart do not include any connection-cycle transition for that Agent's connection.

**Out of scope for v0.1.** A future version may relax this (e.g., cycle the transport for stronger isolation between pre- and post-restart epochs), at which point A-T13 becomes the *expected* path rather than the exceptional one, and the interaction between `stop_drain_timeout` and reconnection grace is revisited. That relaxation is explicitly out of scope for v0.1-beta-2.

**Open (v0.1-beta-2): none at this time.**
