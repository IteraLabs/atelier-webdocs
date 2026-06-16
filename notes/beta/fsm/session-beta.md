# Atelier FSM Atlas - Session (§2.7)

Part of the **State Machine Atlas v0.1-beta-2**. See `fsm-beta.md` for the reading guide, notation, §2.4 FSMs - scope status, and §3 Cross-FSM Sequences. Owns the `INV-SN*` invariant prefix. Cross-references: `overseer-beta.md` (§1, §1.6 IR-O4), `service-beta.md` (§2.5), `agent-beta.md` (§2.1). Participates in **SEQ-1 Deploy** (`sequences-beta.md`) - SN-T2 (Active) is the precondition that admits SV-T1 and A-T1; INV-SN1 is the atomicity mechanism backing the Deploy envelope check.

---

## 2.7 Session FSM

The Session FSM captures the lifetime of an authenticated, time-bound client scope that bounds every runtime artifact the platform produces on behalf of a user. A Session owns an envelope: the maximum set of concurrent Agents, concurrent Services/Experiments, and throughput rates that may exist under it. The Session outlives any single activation - multiple Services and Experiments may be created, run, and stopped within a single Session. The Session ends when its TTL expires, when an operator or the platform force-closes it, or when its authentication is revoked externally.

Session is the outer scope of every non-Overseer FSM in this Atlas. Service (§2.5), Binding (§2.3), Agent (§2.1), Task (§2.2), ComputeSlot (§2.8), and Workspace (persistence-only at v0.1) are all scoped to a Session. The Session FSM is therefore the single point at which resource-envelope enforcement and scope-lifetime cascade are anchored.

### 2.7.1 States

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  SESSION STATES                                                              │
│                                                                              │
│     Created ──► Active ◄─► Expiring ──► Expired ──► Closed                   │
│                    │                        ▲                                │
│                    │                        │                                │
│                    └────────────────────────┘                                │
│                        (SN-T6 emergency)                                     │
│                                                                              │
│  Closed: absorbing terminal.                                                 │
│  Expiring ↔ Active is bidirectional (TTL renewal).                           │
└──────────────────────────────────────────────────────────────────────────────┘
```

**S-SN1: Created.** Transient. The Session row has been authenticated and persisted; the envelope has been resolved from the identity's plan/quota policy; the row is marked `status=created` but not yet open for operations. This state exists so that envelope computation, audit logging, and event emission happen before the Session is visible to the operation layer.

Entry: SN-T1 (authenticated handshake).
Exit: SN-T2 (initialization complete) or SN-T6 (emergency close during init).

**S-SN2: Active.** Steady state. The Session accepts Deploy and Run System Operations subject to its envelope and to Overseer mode (§1.4). Its envelope counts are maintained atomically by the Overseer per IR-O4 and this FSM's INV-SN1. Child Services transition freely under IR-SVS rules; Sessions do not observe Service internal state beyond the envelope count.

Entry: SN-T2, SN-T5 (TTL extension from Expiring).
Exit: SN-T3 (expiry warning elapsed), SN-T6 (emergency close).

**S-SN3: Expiring.** Soft grace zone. The Session has entered its warning window - `ttl - expiry_warning_window ≤ now < ttl`. The Session continues to accept envelope-compatible operations; no new behavior is forced on children. The warning is surfaced to the webapp so the user can renew the TTL (-> SN-T5) or allow natural expiry (-> SN-T4). This state is necessary so that in-flight Deploys can complete gracefully and so that a renewal decision has time to propagate without racing SV-T1.

Entry: SN-T3.
Exit: SN-T4 (TTL elapsed), SN-T5 (renewal accepted), SN-T6 (emergency close).

**S-SN4: Expired.** Terminal operation-wise, but not absorbing: child Services are being cascaded to Stopping/Stopped via IR-SNS2. No new Deploy, Run, or other envelope-consuming operation is accepted. The Session row is preserved; Session-scoped reads (artifact lineage, audit) still resolve.

Entry: SN-T4, SN-T6.
Exit: SN-T7 (Closed - all child Services have reached Stopped or Archived).

**S-SN5: Closed.** Absorbing terminal. All child Services have reached Stopped or Archived; the Session has no live runtime artifacts. The Session row and all scoped lineage remain in persistent storage. A new Session from the same identity gets a new Session ID; this Session's ID stays Closed.

Entry: SN-T7.
Exit: none (terminal).

### 2.7.2 Transitions

```
SN-T1:  (creation) ──► Created
        Trigger:  Authentication handshake succeeds (identity verified, policy
                  resolved, TTL anchored to issuance time).
        Guard:    Overseer mode ∈ {Full, Degraded} (Degraded may still authenticate
                  read-only Sessions; write-capable Sessions require Full - this
                  gate lives on the authentication path and is referenced here for
                  completeness).
        Effects:  Persist Session row (status=created, session_id, identity_id,
                    envelope = {concurrent_services, concurrent_agents,
                                throughput_rates, …},
                    issued_at, ttl, expiry_warning_window);
                  initialize envelope counters to zero;
                  emit SessionCreated event.

SN-T2:  Created ──► Active
        Trigger:  Initialization complete - Session row durably persisted,
                  envelope counters initialized, event emitted.
        Guard:    Persistent Storage subsystem available (the ack path for SN-T1
                  effects).
        Effects:  Persist Session status=active, activated_at;
                  Session becomes visible to the operation layer (Deploy/Run
                    Commands accept this session_id);
                  emit SessionActive event.

SN-T3:  Active ──► Expiring
        Trigger:  `now ≥ ttl - expiry_warning_window` - the expiry warning clock
                  fires. Alternatively: platform operator proactively shortens TTL
                  into the warning window.
        Guard:    Session is in Active.
        Effects:  Persist Session status=expiring, expiring_at;
                  emit SessionExpiring event (webapp surfaces renewal affordance).
                  No child state is changed.

SN-T4:  Expiring ──► Expired
        Trigger:  `now ≥ ttl` with no renewal accepted during the warning window.
        Guard:    Session is in Expiring; Overseer mode ∈ {Full, Degraded}
                  (cascade path must be able to persist and deliver Commands -
                  see IR-SNO4 for degraded-cascade behavior).
        Effects:  Persist Session status=expired, expired_at,
                    expire_reason=ttl_elapsed;
                  cascade per IR-SNS2: every child Service in {Provisioning,
                    Deploying, Active, Updating} takes SV-T4 or SV-T6 as
                    appropriate; every child Service already in Stopping is
                    left to complete via SV-T9;
                  emit SessionExpired event.

SN-T5:  Expiring ──► Active
        Trigger:  Renewal accepted - the identity's policy re-issues TTL, or
                  operator override extends TTL past `now + expiry_warning_window`.
        Guard:    Session is in Expiring; renewal authorization validated.
        Effects:  Persist Session ttl (new value), activated_at (re-anchored only
                    for audit of re-activation - original issued_at is preserved);
                  clear expiring_at;
                  emit SessionRenewed event, then SessionActive event.
        Note:     No child state is touched. In-flight operations continue.

SN-T6:  {Active, Expiring, Created} ──► Expired
        Trigger:  Emergency termination - authentication revoked upstream; operator
                  force-close; compliance kill; identity's plan revoked and policy
                  mandates immediate termination.
        Guard:    none (this is the emergency exit).
        Effects:  Persist Session status=expired, expired_at,
                    expire_reason ∈ {auth_revoked, operator_force_close,
                                     compliance_kill, plan_revoked};
                  cascade per IR-SNS2 as in SN-T4, but with an operator_force
                    stopped_reason_intent on SV-T6 so that children record the
                    distinction from TTL-driven shutdown;
                  emit SessionExpired event.

SN-T7:  Expired ──► Closed
        Trigger:  Every child Service under this Session has reached Stopped or
                  Archived, and every child Agent has reached Terminated (via
                  the Agent's own §2.1 termination path under the cascade).
        Guard:    `count(Services in {Provisioning, Deploying, Active, Updating,
                    Stopping}) = 0` AND
                  `count(Agents in {Registered, Ready, Bound, Restarting, Lost,
                    Draining}) = 0`.
        Effects:  Persist Session status=closed, closed_at;
                  emit SessionClosed event;
                  Session becomes eligible for lineage archival (out of scope).
```

### 2.7.3 Invariants

**INV-SN1: Envelope enforcement atomicity.**
The envelope pre-check and the corresponding child-state increment (SV-T1 for Services; A-T1 for Agents) execute as a single serializable unit. Two concurrent SV-T1 attempts on the same Session cannot both pass the check if the second would exceed `concurrent_services`. This is the mechanism backing IR-O4 (Overseer -> Session enforcement). Implementation options: per-Session row-level lock with `FOR UPDATE` during envelope check + persist; or serialized queue keyed by `session_id`. Either is acceptable; what is normative is the *atomicity*, not the mechanism.

**INV-SN2: State-gated operation admission.**
Deploy and Run System Operations are admitted only when Session ∈ {Active, Expiring}. In any other state, the Overseer rejects the Operation with `ENVELOPE_EXCEEDED` (when state is Expired/Closed) or `COMMAND_TARGET_WRONG_STATE` (when state is Created and Session is not yet Active). Agent Registration (A-T1) is admitted only when Session ∈ {Active, Expiring}.

**INV-SN3: No new children after Expired.**
On entry to Expired (SN-T4 or SN-T6), the envelope counters stop accepting increments. Any concurrent SV-T1 / A-T1 that has not yet committed its atomic persist MUST fail. Counter-decrements (on child termination) continue; the counters are monotonically non-increasing across {Expired -> Closed}.

**INV-SN4: Monotone state progression.**
Forward-only along `Created -> Active -> Expired -> Closed`. The Active <-> Expiring pair is bidirectional *within* the Active region and does not violate monotonicity (Expiring is a sub-Active zone for envelope-admission purposes; see INV-SN2). No transition from Expired returns to any pre-Expired state; no transition from Closed exists.

**INV-SN5: Identity and Session ID immutability.**
`session_id` and `identity_id` are set at SN-T1 and are immutable for the lifetime of the Session row. Re-authentication by the same identity issues a new Session ID; it never resurrects a Closed Session.

**INV-SN6: Envelope monotonicity under membership.**
For any state S ∈ {Active, Expiring}: `envelope_counters(S) ≤ envelope_limits`. The counters are updated inside the SN-T1 / SN-T4 / SN-T6 / child-FSM transitions that are atomic with envelope mutation; therefore the counters never transiently exceed limits. Violation of this invariant is an observability bug in the atomic-envelope implementation and MUST be caught at the transition boundary.

**INV-SN7: Cascade trigger completeness.**
SN-T4 and SN-T6 MUST enqueue cascade work for every child Service currently in a non-terminal state and for every child Agent currently registered. The enqueue is atomic with the Session status mutation (one serializable unit with the Session row write). Missing a child is a correctness failure, not a best-effort gap.

**INV-SN8: TTL anchoring stability.**
`issued_at` and `ttl` are anchored at SN-T1 and changed only by SN-T5 (which re-sets `ttl` - `issued_at` remains frozen for audit purposes). No other transition modifies these fields.

### 2.7.4 Interaction Rules

**Session <-> Overseer (IR-SNO)**

- **IR-SNO1: IR-O4 atomicity mechanism lives here.** The Overseer's IR-O4 envelope check (§1.6 `overseer-beta.md`) is implemented as an atomic operation against this Session's row per INV-SN1. The Overseer does not maintain its own envelope cache; the Session row is the authoritative counter store.
- **IR-SNO2: Overseer does not drive SN-T3 or SN-T4.** Those are driven by the wall clock against `ttl`. The Overseer *observes* the warning / expiry clocks (a timer subsystem) and fires the transition on behalf of this FSM, but the semantic driver is time, not Overseer state.
- **IR-SNO3: Overseer drives SN-T6 only for explicit administrative triggers.** Subsystem degradation (Overseer O-T3/O-T4/O-T5) does NOT cascade SN-T6. Sessions survive Overseer Degraded mode; children admission is limited by §1.4 matrix, not by Session state transition.
- **IR-SNO4: Expiry cascade under Degraded.** If SN-T4 fires while Overseer is in Degraded mode, the cascade per IR-SNS2 is queued in durable state (Session status=expired, cascade pending) and drains as subsystems return. `ENVELOPE_EXCEEDED` is returned for any new Deploy/Run in the interim.
- **IR-SNO5: Overseer restart does not affect Session state.** Sessions persist across Overseer restart via the Session row. Recovery Protocol (§1.7) Stage 1 re-reads Session rows and re-initializes envelope counters from the actual child-state counts in persistent storage; it does not replay Session transitions.

**Session <-> Service (IR-SNS)**

- **IR-SNS1: Admission and envelope check.** SV-T1 requires Session ∈ {Active, Expiring}. The envelope pre-check for `concurrent_services` is atomic with SV-T1's persist per INV-SN1. Services in {Provisioning, Deploying, Active, Updating, Stopping} count against `concurrent_services`; Stopped and Archived Services do not (aligned with §2.5 IR-SVS3).
- **IR-SNS2: Expiry cascade.** SN-T4 and SN-T6 cascade to each child Service as follows:
  - Service in {Provisioning}: drive SV-T4 (Provisioning -> Stopped, `stopped_reason=session_envelope_invalidated` for SN-T4, `stopped_reason=operator_force_close` for SN-T6).
  - Service in {Deploying, Active, Updating}: drive SV-T6 (-> Stopping) with `stopped_reason_intent=session_expired` (SN-T4) or `operator_force_close` (SN-T6).
  - Service in {Stopping}: no-op - already draining, will complete via SV-T9.
  - Service in {Stopped, Archived}: no-op.
  The cascade is enqueued atomically with the Session status mutation per INV-SN7.
- **IR-SNS3: Counter decrement on Service termination.** SV-T4, SV-T5, SV-T9, SV-T10 all decrement `concurrent_services`. SV-T11 (Stopped -> Archived) does not decrement (Stopped is already outside the counted set per IR-SNS1). Decrement happens in the same transactional unit as the Service's status mutation so that the counter is always consistent with the child-state query.

**Session <-> Agent (IR-SNA)**

- **IR-SNA1: Registration envelope check.** A-T1 (Agent Registration) requires Session ∈ {Active, Expiring}. `concurrent_agents` is checked atomically with the Agent row persist per INV-SN1.
- **IR-SNA2: Expiry cascade.** SN-T4 and SN-T6 cascade to each child Agent indirectly - the cascade acts on the Agent's Bindings per IR-SNS2; once the Bindings are Released, the Agent follows its own termination path in §2.1 (A-T15 on grace, A-T16 on `AGENT_TERMINATE`). The Session FSM does not directly drive Agent transitions.
- **IR-SNA3: Counter decrement on Agent termination.** Entry to Agent `Terminated` decrements `concurrent_agents`, in the same transactional unit as the terminating transition's persist (A-T16 on the `AGENT_TERMINATE` path; A-T7 / A-T15 on the drain / grace paths).

**Session <-> Experiment (IR-SNE) - enumerated, deferred**

- **IR-SNE1 (deferred):** Experiment creation (corresponds to a Run Operation) would require Session ∈ {Active, Expiring} analogously to IR-SNS1. Deferred per the v0.1-beta-2 beta scope (taxonomy §ACTIVATION MODES).
- **IR-SNE2 (deferred):** Experiment cascade on SN-T4 / SN-T6 is the Experiment-FSM analogue of IR-SNS2. Deferred.

**Session <-> Workspace (IR-SNW)**

- **IR-SNW1:** Workspace rows are created by SV-T1 (one Workspace per Service activation, per §2.5) and scoped to this Session. The Session FSM does not track Workspace state; Workspace lifecycle is cascaded via the Service it belongs to.

### 2.7.5 Notes

- **Session is not a "process."** The Session row is passive state, not an event-driven component like the Overseer. The transitions SN-T3, SN-T4 are driven by time; SN-T5, SN-T6 by external authorization events. Specifying an FSM here is still worth it because it pins down the envelope atomicity contract (INV-SN1) that SEQ-1 Deploy depends on, and the cascade semantics (IR-SNS2) that §2.5 SV-T6 depends on.
- **Envelope shape is out of scope here.** The Session's envelope fields (`concurrent_services`, `concurrent_agents`, `throughput_rates`, etc.) are resolved from the identity's plan/quota policy at SN-T1. The authoritative list of envelope dimensions lives with the persistence schema (Session table) and the identity/billing layer (out of scope for v0.1-beta-2 FSM work).
- **Expiry warning window is operator-configurable.** `expiry_warning_window` is a per-plan default with a tenant override. It lives in the timeout/config catalog.
- **No Session-level Drain.** Overseer Drain (T6) handles the platform-shutdown scenario; Session Expiry handles the tenant-scope scenario. Mixing them is out of scope for v0.1-beta-2 - if both fire simultaneously, Overseer Drain wins (all child Services are SV-T6'd by the Overseer cascade), and the Session subsequently observes zero in-flight children and proceeds to SN-T7 when Expired fires.
- **TTL renewal does not re-anchor envelope.** SN-T5 extends TTL only. If the identity's plan/envelope changed since SN-T1, the new envelope is NOT applied to this Session - the user must re-authenticate to get a new Session with the new envelope. This is a v0.1-beta-2 simplification.
- **Testability.** Every `INV-SN*` is asserted at its owning transition boundary and has a matching test. `INV-SN1` specifically is asserted by an integration test that launches N concurrent SV-T1 attempts against a Session whose `concurrent_services` limit is N-1 and verifies exactly one SV-T1 fails with `ENVELOPE_EXCEEDED`. See the invariant testability convention in `fsm-beta.md` preface.
