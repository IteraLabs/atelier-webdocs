# Atelier FSM Atlas - Sink (§2.11)

Part of the **State Machine Atlas v0.1-beta-2**. See `fsm-main.md` for the reading guide, notation, §2.4 FSMs - scope status, and §3 Cross-FSM Sequences. Owns the `INV-SK*` invariant prefix. Cross-references: `task.md` (§2.2), `binding.md` (§2.3), `compute-slot.md` (§2.8), `channel.md` (§2.10). Participates in **SEQ-1 Deploy** (`sequences.md`) - SK-T1/SK-T2 reach Ready synchronously during the first ArtifactChannel CH-T1 against the Sink; INV-SK4 gates B-T3 (Binding Active) on every Manifest-declared Sink being Ready.

This section specifies **only the provisioning states** (Idle -> Ready). Internal states (Streaming, Writing, Backpressured, Error, Closed) are enumerated for cross-reference; their transitions/invariants are deferred to post-beta work.

---

## 2.11 Sink provisioning contract (minimal)

Sinks are the final destinations where Artifacts are materialized (taxonomy §DESTINATIONS). They come in three storage categories - ObjectSink (file storage), DBSink (database), TerminalSink (webapp live viewer) - and two location axes - platform-side, client-side, or colocated with the producing ComputeSlot. Sinks are addressed by `sink_id` and scoped to a Workspace.

This section specifies **only the provisioning states** - enough to ground SEQ-1 Deploy's "open Sinks" step (Manifest sink_assignments must reach Ready before B-T3 Active). Runtime internal states (Streaming, Writing, Backpressured, Error, Closed) are enumerated for cross-reference but their transitions/invariants are **deferred** to post-beta.

### 2.11.1 States

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  SINK PROVISIONING STATES (minimal)                                          │
│                                                                              │
│     Idle ──► Ready                                                           │
│                │                                                             │
│     ┌──────────┼──────────┬──────────┐                                       │
│     ▼          ▼          ▼          ▼                                       │
│  Streaming  Writing  Backpressured  Error   (deferred post-beta)             │
│     │          │          │          │                                       │
│     └──────────┴──────────┴──────────┤                                       │
│                                      ▼                                       │
│                                    Closed   (deferred post-beta)             │
│                                                                              │
│  v0.1-beta-2 scope: Idle, Ready are normative.                               │
│  Streaming, Writing, Backpressured, Error, Closed: enumerated only.          │
└──────────────────────────────────────────────────────────────────────────────┘
```

**S-SK1: Idle.** The Sink row exists in persistent storage (provisioned as part of the Workspace or explicitly by the operator) but is not currently bound to any Artifact producer. Its configuration has been validated at creation time but the first emission handshake has not occurred.

Entry: Sink creation (initial write); SK-T3 (deferred release from Ready after Task termination in a post-beta revision).
Exit: SK-T1 (first-use handshake begins).

**S-SK2: Ready.** The Sink has completed its first-use handshake with a producer (a Task via its ArtifactChannel, per CS-T2 effects). It is provisioned for Artifact emission: its container exists (bucket/table/terminal-session), its format metadata is confirmed, its reliability class is declared, and it has advertised itself to any consumers (e.g., the webapp for TerminalSink). This is the state B-T3 requires: all Manifest-declared Sinks must be in Ready for the Binding to reach Active.

Entry: SK-T2.
Exit: Streaming / Writing / Backpressured / Error / Closed (all deferred).

**S-SK3: Streaming** (enumerated, deferred). An ArtifactChannel is actively writing to the Sink.

**S-SK4: Writing** (enumerated, deferred). A single-shot write in progress (non-streaming Artifacts - one file, one row set).

**S-SK5: Backpressured** (enumerated, deferred). Producer is being flow-controlled by the Sink (e.g., DB write queue full, object-store rate limit).

**S-SK6: Error** (enumerated, deferred). Transient write failure; may recover.

**S-SK7: Closed** (enumerated, deferred). Sink reached end-of-life: Workspace is being destroyed, or an explicit close was requested.

### 2.11.2 Transitions (normative for v0.1)

```
SK-T1:  Idle ──► (first-use handshake in progress)
        Trigger:  First Artifact producer opens an ArtifactChannel to this Sink
                  (CS-T2 effects for the first Task that references the Sink in
                  its sink_assignments).
        Guard:    Sink is in Idle; Sink configuration is valid (credentials,
                  endpoint, bucket/table/terminal-session exists or can be
                  created); reliability class per sink type is consistent with
                  requested ArtifactChannel reliability.
        Effects:  Begin handshake: for ObjectSink, verify bucket access and
                    desired prefix writability; for DBSink, verify connection
                    and table existence + column schema; for TerminalSink,
                    establish the webapp live-viewer stream.
        State:    Internal sub-state of Idle during handshake - not separately
                  modeled (see Notes).

SK-T2:  (handshake complete) ──► Ready
        Trigger:  Handshake succeeded - Sink target confirmed writable with
                  correct format and reliability class.
        Guard:    For ObjectSink: bucket/prefix accessible with configured
                  credentials, desired format (Parquet / CSV / Arrow IPC /
                  JSON / binary) confirmed supported;
                  For DBSink: connection established, target table exists,
                  Artifact schema compatible with table columns (schema-on-write
                  subset OR schema-on-read declared);
                  For TerminalSink: webapp session established, output stream
                  attached.
        Effects:  Persist Sink status=ready, ready_at, reliability_class;
                  register the Sink as a valid Artifact destination so that
                  subsequent ArtifactChannel CH-T1 requests from additional
                  Tasks can skip re-handshake (they verify Sink is in Ready
                  and attach);
                  emit SinkReady event.
```

**Deferred transitions** (enumerated for cross-reference, not normative in v0.1):
`SK-T3 Ready -> Idle`, `SK-T4 Ready -> Streaming`, `SK-T5 Streaming -> Ready`, `SK-T6 Ready -> Writing`, `SK-T7 Writing -> Ready`, `SK-T8 * -> Backpressured`, `SK-T9 Backpressured -> *`, `SK-T10 * -> Error`, `SK-T11 Error -> *`, `SK-T12 * -> Closed`.

Handshake failure in v0.1 surfaces as an error to the opening ArtifactChannel; the Sink remains in Idle; the Manifest is rejected (PEER_REJECTED cascade per B-T10), leading to SV-T5 for the Service.

### 2.11.3 Reliability classes (per Sink type)

| Sink type | Typical reliability class | ArtifactChannel direction | Notes |
|---|---|---|---|
| ObjectSink (local) | at-least-once with sequence numbers | local | Writes to local disk on producing ComputeSlot host. |
| ObjectSink (S3/GCS) | at-least-once with idempotency (object-key de-dupe) | upstream (if platform) / lateral (if client) | Idempotency via deterministic object keys. |
| DBSink | at-least-once with idempotency key (row-level upsert) OR exactly-once (txn) | upstream / lateral | Declared per-table; exactly-once requires single-writer constraint. |
| TerminalSink | best-effort (visual output; gaps are user-visible but not fatal) | upstream | Connected to webapp live-viewer stream; cannot be replayed from durable storage. |

The reliability class is declared at SK-T2 (Sink reaches Ready); ArtifactChannel CH-T1 reads it and handshakes on that class. A mismatch (Task requests stronger reliability than Sink supports) rejects CH-T1.

### 2.11.4 Invariants (provisioning-level only)

**INV-SK1: Ready implies handshake complete.**
A Sink in Ready MUST have passed SK-T2 with target confirmed writable and reliability class declared. Asserted at SK-T2 boundary.

**INV-SK2: Sink ID uniqueness and Workspace scope.**
`sink_id` is unique within a deployment. The Sink's Workspace reference is immutable from creation.

**INV-SK3: Reliability class immutable once Ready.**
Once SK-T2 fires, the Sink's declared reliability class cannot be changed without a full close + re-provision cycle (deferred).

**INV-SK4: B-T3 gating.**
B-T3 (Binding Pending -> Active) requires every Sink listed in the Binding's Manifest sink_assignments to be in Ready. If any referenced Sink fails SK-T2, the Manifest is rejected; the Binding follows B-T10 -> B-T8 (release_reason = task_rejected); the Service follows SV-T5 (manifest_rejected).

**INV-SK5: Sink-first, ArtifactChannel-second.**
A Sink reaches Ready (SK-T2) **before** any ArtifactChannel CH-T2 against it. CH-T1 against an Idle Sink triggers SK-T1 -> SK-T2 synchronously as part of the channel open handshake; the ArtifactChannel CH-T2 fires only after the Sink has SK-T2'd.

**INV-SK6: TerminalSink requires a webapp session.**
TerminalSinks cannot reach Ready without a subscribed webapp session. If the user closes the webapp tab and the TerminalSink is in Ready (no live viewer), behavior is defined by the deferred Streaming/Error transitions; for v0.1 the Sink remains Ready but any emitted Artifact is dropped (best-effort reliability class makes this acceptable).

### 2.11.5 Interaction rules (selected, minimal)

- **IR-SKO1:** CS-T2 (ComputeSlot -> Occupied) verifies that every Sink referenced in the Task's sink_assignments either is in Ready OR can be driven from Idle to Ready via SK-T1 -> SK-T2 atomically during CS-T2.
- **IR-SKO2:** B-T1 persists the Manifest including sink_assignments; SK-T1 fires against each referenced Sink that is still in Idle.
- **IR-SKO3:** SV-T6 (Service -> Stopping) does not cascade to Sink state transitions in v0.1 - Sinks stay in Ready through the Binding drain and are reused if a new Binding under a new Service activates against the same Workspace. Sink close is a Workspace-level teardown, which for v0.1 happens when the Service reaches Stopped (destroy Workspace row per SV-T4/SV-T5 effects) - the Sink close transition is deferred.
- **IR-SKO4:** Overseer Recovery (§1.7) re-probes Sinks for every Active Binding it reconciles. Sinks that were in Ready stay in Ready if re-probe succeeds; if re-probe fails (e.g., S3 bucket became unreachable during Overseer downtime), the Sink transitions to Error (deferred) and the Binding is driven to Draining (B-T4) with a specific `drain_reason = sink_unavailable`.

### 2.11.6 Notes

- **First-use vs. creation.** Sink rows are created at Workspace provisioning time (part of SV-T1 persist), but they start in Idle. The first ArtifactChannel CH-T1 against a Sink triggers SK-T1 - this is the contract. Pre-provisioning Sinks to Ready at Workspace creation is a post-beta optimization (allows parallel handshakes) but is not required.
- **Internal sub-state of Idle during handshake.** SK-T1 begins the handshake; if it takes non-trivial time (DB connect, S3 bucket verification), the Sink is conceptually in a "handshaking" micro-state but the FSM does not model it - success fires SK-T2 (Idle -> Ready), failure returns an error to the caller and the row stays Idle. Full state modeling of this phase is deferred.
- **Sink reuse across Tasks.** A single Sink in Ready can accept ArtifactChannels from multiple Tasks within the same Service (subject to the Sink's concurrency class). The Sink FSM does not track per-Task connections; the ArtifactChannels do (§2.10).
- **TerminalSink and TerminalSink live viewer.** The webapp's live-viewer integration is a separate component (webapp-side); the Sink FSM's contract is that the TerminalSink is Ready iff a webapp session is attached. Operationally, the webapp subscribes to the Overseer's event stream for TerminalSink output.
- **Testability.** Every `INV-SK*` is asserted at SK-T2 or the ArtifactChannel CH-T1 boundary. INV-SK4 is specifically tested by an integration test that provisions a Manifest with a deliberately-broken ObjectSink (bad credentials) and asserts B-T3 never fires and SV-T5 fires with `stopped_reason=manifest_rejected`.
