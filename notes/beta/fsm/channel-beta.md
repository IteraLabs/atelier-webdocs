# Atelier FSM Atlas - Channel (§2.10)

Part of the **State Machine Atlas v0.1-beta-2**. See `fsm-beta.md` for the reading guide, notation, §2.4 FSMs - scope status, and §3 Cross-FSM Sequences. Owns the `INV-CH*` invariant prefix. Cross-references: `agent-beta.md` (§2.1, §2.1.5), `binding-beta.md` (§2.3), `task-beta.md` (§2.2), `gateway-beta.md` (§2.9), `sink-beta.md` (§2.11). Participates in **SEQ-1 Deploy** (`sequences-beta.md`) - CH-T1/CH-T2 for CommandChannel, TelemetryChannel, and ArtifactChannels are the gates that IR-CHO1/CHO2/CHO3 impose on B-T3 (Binding Active) and T-T3 (Task Running).

This section specifies the **provisioning states** (Opening -> Open) and, the **drain/terminal states** (Draining -> Closed, and Failed) required by SEQ-4 Crash Recovery and SEQ-5 Graceful Shutdown. Backpressured and Error remain enumerated for cross-reference; their transitions/invariants are deferred work. Durable Channel rows are defined in `schema-beta.md` table 12 (`channels`).

---

## 2.10 Channel provisioning contract (minimal)

Channels are sustained, typed communication paths between Agents, between Agents and System Processes, or between System Processes. The taxonomy (HOW §Channels) enumerates five categories: Command, Manifest, Telemetry, Data, Artifact. Each has a direction (uni / bi), a category (System / Data), and a reliability class.

This section specifies the **provisioning states** - enough to ground SEQ-1 Deploy's "open Channels" step - plus the **drain/terminal states** (Draining, Closed, Failed) promoted to normative to ground SEQ-4 Recovery and SEQ-5 Drain. Backpressured and Error remain enumerated so other sections can reference them, but their transitions and invariants are **deferred** to a later Channel FSM draft.

### 2.10.1 States

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  CHANNEL PROVISIONING STATES (minimal)                                       │
│                                                                              │
│     Opening ──► Open                                                         │
│                   │                                                          │
│     ┌─────────────┼─────────────┐                                            │
│     ▼             ▼             ▼                                            │
│  Draining    Backpressured    Error     (Backpr./Error deferred)            │
│     │             │             │                                            │
│     ▼             ▼             ▼                                            │
│  Closed          Open         Failed                                         │
│                                                                              │
│  Normative: Opening, Open (beta); Draining, Closed, Failed (Iter. 5).        │
│  Enumerated only: Backpressured, Error.                                      │
└──────────────────────────────────────────────────────────────────────────────┘
```

**S-CH1: Opening.** The Channel has been requested (e.g., a gRPC stream has been initiated by the Agent against the Overseer or Gateway; a Data stream has been opened between two ComputeSlots). Handshake frames are being exchanged: category identifier, reliability class, initial sequence number, idempotency key (for exactly-once channels), and any category-specific metadata (e.g., `manifest_id` for ManifestChannel).

Entry: CH-T1 (Channel open requested).
Exit: CH-T2 (handshake complete -> Open) or rejection (returned as error; no state landed).

**S-CH2: Open.** Handshake complete; the Channel is admitting messages. The peer endpoints have agreed on the reliability class and have initialized per-class state (ack queues for at-least-once, idempotency-key dedupe for exactly-once, sequence numbers for best-effort-with-sequence). At this point the Channel is considered provisioned for the purposes of SEQ-1 Deploy gating (B-T3 requires Open Channels on CommandChannel, TelemetryChannel, and any ArtifactChannels the Manifest declares).

Entry: CH-T2.
Exit: Draining / Backpressured / Error / Closed / Failed (all deferred).

**S-CH3: Draining** (normative). Channel has received a shutdown signal (SEQ-5 graceful Drain, or a Binding/Agent release cascade) and is finishing in-flight messages before closing. No new frames are admitted on the data plane; the ack/idempotency state for in-flight frames is allowed to settle. The durable `channels.status='draining'` row is set at CH-T3 with `drain_started_at`; SEQ-5 walks it to Closed (CH-T4) or, past `agent.reconnect_grace_ms`, force-closes it to Failed (CH-T10).

Entry: CH-T3 (drain signal).
Exit: CH-T4 (in-flight settled -> Closed) or CH-T10 (grace expired -> Failed).

**S-CH4: Backpressured** (enumerated, deferred). Channel's receiving side is not keeping up; sender is being flow-controlled. For DataChannel and ArtifactChannel primarily.

**S-CH5: Error** (enumerated, deferred). Recoverable error state - e.g., a transient serialization failure. May recover to Open or proceed to Failed.

**S-CH6: Closed** (normative). Normal terminal - all in-flight messages delivered per reliability class, both sides acknowledge close. `channels.status='closed'` with `closed_at`. Reached via CH-T4 from Draining.

Entry: CH-T4.
Exit: terminal.

**S-CH7: Failed** (normative). Abnormal terminal - reliability contract could not be honored (handshake failure at Opening, transport loss while Open, or drain grace expiry while Draining); peer is notified; reconnection / replay is up to the SDK/Overseer. `channels.status='failed'` with `closed_at`. A Failed Channel on a live Binding triggers the Binding's force-release (B-T7) during SEQ-4 recovery.

Entry: CH-T10.
Exit: terminal.

### 2.10.2 Transitions (normative for v0.1)

```
CH-T1:  (creation) ──► Opening
        Trigger:  Channel-open request issued by one of the endpoints:
                    - CommandChannel: Agent -> Gateway (for RemoteAgent) or
                                       Agent -> Overseer (for PlatformAgent),
                                       initiated as part of Agent A-T1 Register.
                    - ManifestChannel: embedded within CommandChannel; opened
                                       at the same time.
                    - TelemetryChannel: Agent -> Gateway/Overseer, opened after
                                       CommandChannel handshake.
                    - DataChannel: opened between Agents or between an Agent and
                                       a platform-side ComputeSlot, per Manifest.
                    - ArtifactChannel: opened between a ComputeSlot and its
                                       assigned Sink, per Manifest sink_assignments.
        Guard:    For RemoteAgent-originating channels: Gateway is in Ready or
                  Degraded (§2.9). For PlatformAgent: direct path available.
        Effects:  Initiate transport handshake; negotiate reliability class per
                    channel category (see table below); assign channel_id.

CH-T2:  Opening ──► Open
        Trigger:  Handshake complete - both endpoints have exchanged and
                  acknowledged category, reliability parameters, and initial
                  sequence state.
        Guard:    Handshake frames valid; initial sequence numbers within
                  acceptable range; idempotency key (where applicable)
                  uniquely reserved.
        Effects:  Mark Channel Open; begin admitting data-plane messages;
                  if this Channel was a gate for a higher-level FSM (e.g.,
                  B-T3 requires CommandChannel Open), signal the ready state
                  to that FSM.
```

**Drain/terminal transitions (normative):**

```
CH-T3:  Open ──► Draining
        Trigger:  Drain signal - SEQ-5 Graceful Shutdown reaches this
                  Channel's Binding/Agent, or a Binding release cascade
                  (B-T6/B-T7) reaches it.
        Guard:    Channel in Open.
        Effects:  Stop admitting new data-plane frames; let in-flight
                  ack/idempotency state settle; UPDATE channels SET
                  status='draining', drain_started_at=now(),
                  row_version=row_version+1.

CH-T4:  Draining ──► Closed
        Trigger:  In-flight frames settled per reliability class (ack
                  queue empty for at-least-once; final sequence flushed
                  for best-effort/gap classes) within
                  `agent.reconnect_grace_ms`.
        Guard:    Channel in Draining; no unacked in-flight frames.
        Effects:  UPDATE channels SET status='closed', closed_at=now(),
                  row_version=row_version+1. Signal Closed to the
                  higher-level FSM (Binding release proceeds).

CH-T10: (Opening | Open | Draining) ──► Failed
        Trigger:  Handshake failure (from Opening); transport loss with
                  no reconnect within grace (from Open, surfaced by
                  SEQ-4 recovery probe); drain grace expiry (from
                  Draining, `agent.reconnect_grace_ms` elapsed).
        Guard:    None - terminal failure path.
        Effects:  From Opening, no durable row lands (handshake failure
                  is returned as an error, SEQ-1 semantics unchanged).
                  From Open/Draining, UPDATE channels SET status='failed',
                  closed_at=now(), row_version=row_version+1; a Failed
                  Channel on a live Binding triggers B-T7 force-release
                  during SEQ-4 recovery.
```

**Deferred transitions** (enumerated for cross-reference, not normative): `CH-T5 Open -> Backpressured`, `CH-T6 Backpressured -> Open`, `CH-T7 Open -> Error`, `CH-T8 Error -> Open`, `CH-T9 Error -> Failed`.

Handshake failure at Opening surfaces as an error to the requesting endpoint (no Channel row lands in persistent state); the endpoint's higher-level FSM decides whether to retry. This suffices for SEQ-1 Deploy. The Open/Draining -> Failed paths DO land a durable `channels` row so SEQ-4 recovery can observe and cascade them.

### 2.10.3 Reliability classes (per category)

| Channel category | Direction | Category | Reliability class | Notes |
|---|---|---|---|---|
| CommandChannel | bidirectional | System | at-least-once with ack | gRPC bidirectional stream. Per-Command ack by `command_id`. |
| ManifestChannel | downstream | System | exactly-once with idempotency key | Embedded in CommandChannel. `manifest_id` is the idempotency key. |
| TelemetryChannel | upstream | System | best-effort with sequence numbers | Gaps tolerable; consumer resyncs on reconnect. |
| DataChannel | upstream | Data | at-least-once with sequence numbers and gap detection | Consumer de-dupes by `(channel_id, sequence_number)`. |
| ArtifactChannel | depends on Sink | Data | per Sink reliability class (see §2.11) | Direction upstream for platform Sinks, lateral for client Sinks, local for colocated. |

The reliability class is part of the CH-T1 handshake; a mismatch between what the initiator requests and what the responder supports rejects at CH-T1 (no Channel row, error returned).

### 2.10.4 Invariants (provisioning-level only)

**INV-CH1: Open implies handshake complete.**
A Channel in Open MUST have completed the full reliability-class handshake. This is asserted at the CH-T2 boundary.

**INV-CH2: Channel ID uniqueness.**
`channel_id` is unique within a deployment for the lifetime of the Channel row. It is allocated at CH-T1.

**INV-CH3: Reliability class immutable.**
Once a Channel reaches Open (CH-T2), its reliability class cannot be changed. A downgrade (e.g., at-least-once -> best-effort) requires close + re-open.

**INV-CH4: Sequence numbers monotone within a Channel.**
For Channels whose reliability class includes sequence numbers (Telemetry, Data, ArtifactChannel-with-sequence), sequence numbers are strictly monotonically increasing within an Open period. On reconnect (when Channel is re-opened after being Closed/Failed), sequence numbers reset per the reliability class's resync rules (out of scope in v0.1).

**INV-CH5: Gateway-persistent Channels survive A-T8.**
Per INV-GW1 (§2.9) and the §2.1.5 resolution: for RemoteAgent-originating Channels routed via the Gateway, A-T8 Restart does NOT close or cycle the underlying transport. The Channel therefore stays in Open throughout A-T8 Restart; sequence numbers do not reset; idempotency keys remain reserved. This is the mechanism that makes `restart_epoch` sufficient as the lineage discriminator (Artifacts produced post-restart carry a new `restart_epoch` on the same Channel's sequence continuation).

**INV-CH6: ManifestChannel is embedded.**
The ManifestChannel is not a separate transport stream; it is a typed frame category within the CommandChannel. Its "opening" is a sub-step of CommandChannel handshake. Treating it as a distinct Channel is a taxonomy abstraction for reliability semantics (exactly-once with idempotency key), not a separate transport.

### 2.10.5 Interaction rules (selected, minimal)

- **IR-CHO1:** B-T3 (Binding Pending -> Active) requires the Binding's CommandChannel and TelemetryChannel to both be in Open (CH-T2 fired for both).
- **IR-CHO2:** B-T1 (Binding creation + Manifest transmit) requires the ManifestChannel (embedded in CommandChannel) to be in Open.
- **IR-CHO3:** T-T3 (Task Accepted -> Running) requires the Task's declared ArtifactChannels (one per Sink assignment) to be in Open OR to successfully open during the transition (atomic with T-T3 persist).
- **IR-CHO4:** Overseer Recovery (§1.7) Stage 1 re-probes Channels for every Binding it reconciles. Open Channels remain Open (Gateway INV-GW1 for RemoteAgent; direct transport continuity for PlatformAgent, noting that a Platform restart is an independent failure mode, out of scope for v0.1).

### 2.10.6 Notes

- **What's deferred.** Full FSM for internal states (Draining, Backpressured, Error, Closed, Failed) and their transitions/invariants. The deferred work is self-contained - it extends this contract downward; it does not revise §2.10.1-§2.10.5.
- **Sink-class ArtifactChannel reliability.** ArtifactChannel inherits its reliability class from the target Sink's class. The Sink FSM (§2.11) declares the class at Ready time; Channel CH-T1 reads it.
- **Testing INV-CH5.** An integration test fires A-T8 Restart on a connected RemoteAgent mid-stream on all five channel categories and asserts (a) none of the channels fire CH-T3 (Draining); (b) sequence numbers continue; (c) a new Artifact produced post-restart carries an incremented `restart_epoch` and a sequence number that continues the pre-restart run. This test is the joint assertion for INV-CH5, INV-GW1, and the §2.1.5 resolution.
- **Testability (general).** Every `INV-CH*` is asserted at the transition boundary that establishes it (primarily CH-T2). See the invariant testability convention in `fsm-beta.md` preface.
