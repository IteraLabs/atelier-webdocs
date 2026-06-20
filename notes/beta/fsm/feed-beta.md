# Atelier FSM Atlas - Feed (§2.12)

Part of the **State Machine Atlas v0.1-beta**. See `fsm-beta.md` for the reading guide, notation, §2.4 FSMs - scope status, §2.4.1 Ownership Matrix, and §3 Cross-FSM Sequences. Owns the `INV-F*` invariant prefix. Cross-references: `agent-beta.md` (§2.1 RemoteAgent, §2.1.5 restart lineage), `task-beta.md` (§2.2 Ingest Task lifecycle, Stop/Drain), `book-beta.md` (§2.13 the OrderBook/TradeBook FSM families), `channel-beta.md` (§2.10 DataChannel / ArtifactChannel), `sink-beta.md` (§2.11 Sink), `errors-beta.md` (`ErrorKind`).

`Feed` is the **data-plane** noun introduced for the BYOI Data Pipeline (Taxonomy HOW §Ingest / Data Plane): a live, Agent-run subscription to one `(venue, instrument, datatype)` market-data stream from an **external** exchange. The external venue connection is the **Ingest Skill mechanism**, not an Atelier `Channel`; the `Feed` FSM models the *subscription* lifecycle that rides on it. The `Feed` FSM is **Agent-owned** (RemoteAgent in `atelier-sdk`; §2.4.1); the platform observes Feed state via the TelemetryChannel and there is **no durable Feed row**.

---

## 2.12 Feed lifecycle

A `Feed` is identified by a **`FeedId`** (UUIDv4), **allocated by the Agent** at creation (like an `ArtifactId`; §Identifiers), scoped to its `Task`. `datatype ∈ {orders, trades}` selects the bound reconstruction book (§2.13): an `orders` Feed drives a `SourcedOrderBook`, a `trades` Feed drives a `SourcedTradeBook`. A single venue socket is shared Ingest mechanism that may carry many Feeds; a connection drop fans `Reconnecting` to all Feeds on that socket.

### 2.12.1 States

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  FEED STATES                                                                   │
│                                                                                │
│    Requested ──► Subscribing ──► Live                                          │
│         │             │           │  ▲                                         │
│         │             │           │  │                                         │
│         │             │      ┌────┴──┴─────┐                                   │
│         │             │      ▼             ▼                                   │
│         │             │   Resubscribing  Reconnecting                          │
│         │             │      │             │                                   │
│         │             │      └─────┬───────┘ (re-seed / re-subscribe → Live)   │
│         ▼             ▼            │                                           │
│      Rejected      Rejected       ▼                                           │
│                                  Draining ──► Closed                          │
│                                                                                │
│  Reconnecting ──► Failed (budget exhausted)                                    │
│                                                                                │
│  Terminal: Closed (normal), Rejected (unsupported), Failed (abnormal).         │
└──────────────────────────────────────────────────────────────────────────────┘
```

**S-F1: Requested.** The `Feed` has been created from the Ingest `Task`'s `TaskSpec` (one entry per `(venue, instrument, datatype)`); its `FeedId` is allocated. Nothing is on the wire yet. The venue has resolved to a registered exchange adapter (else the Feed never lands here - see F-T9).

Entry: F-T1 (Feed requested). Exit: F-T2 (subscribe sent -> Subscribing) or F-T9 (venue/datatype unsupported -> Rejected).

**S-F2: Subscribing.** The subscribe frame(s) for this `Feed` have been sent on the shared venue connection (per the adapter's protocol). The Feed is awaiting the venue's first data frame and, for snapshot-seeded reconstruction models, the seed that brings the bound book to `Synced`.

Entry: F-T2. Exit: F-T3 (first data + seed -> Live), F-T8 (connection lost -> Reconnecting), or F-T10 (venue rejects subscription -> Rejected).

**S-F3: Live.** Streaming. Decoded events are flowing; the bound `SourcedOrderBook` / `SourcedTradeBook` (§2.13) is in `Live` (`Synced` for delta venues). Normalized output is being Emitted as `DataArtifacts` (§2.12.3).

Entry: F-T3. Exit: F-T4 (book `Gapped` -> Resubscribing), F-T8 (connection lost -> Reconnecting), or F-T6 (Task Stop -> Draining).

**S-F4: Resubscribing.** Recovery from a reconstruction gap: the bound book signalled `Gapped` (`ResyncNeeded`), and the Feed is re-seeding per the venue's recovery action (`Resubscribe` / `RestSnapshot` / `ReqOnSocket`; §2.13). The venue connection is still up.

Entry: F-T4. Exit: F-T3 (re-seeded, book back to `Synced`/`Live` -> Live) or F-T8 (connection lost -> Reconnecting).

**S-F5: Reconnecting.** The shared venue connection dropped (transport loss, retryable per `DisconnectReason.is_retryable()`; `disconnect.rs`). The Feed is held while the connection is re-established by the Ingest mechanism's reconnect policy; the bound book is retained for re-seed.

Entry: F-T8. Exit: F-T2 (connection re-established -> Subscribing) or F-T11 (reconnect budget exhausted -> Failed).

**S-F6: Draining.** The Ingest `Task` received Stop/Drain (§2.2). The Feed stops subscribing and flushes the bound book's pending normalized output through Emit, bounded by `stop_drain_timeout` (`timeouts-beta.md`).

Entry: F-T6. Exit: F-T5 (drained in time -> Closed) or F-T12 (drain grace expired -> Closed, partial).

**S-F7: Closed** (normal terminal). The subscription is closed and in-flight output is finalized (possibly `partial`, F-T12). No further events.

Entry: F-T5 / F-T12. Exit: terminal.

**S-F8: Rejected** (terminal). The `(venue, instrument, datatype)` cannot be honored: no registered adapter for the venue/datatype (F-T9), or the venue rejected the subscription (F-T10). A structured `Error` is surfaced upstream (§2.12.4 INV-F5). This is the data-plane source of the agent self-rejection in tracker #11.

Entry: F-T9 / F-T10. Exit: terminal.

**S-F9: Failed** (terminal). Abnormal end - the venue connection could not be recovered within the reconnect budget. A structured `Error` is surfaced; the Ingest `Task` maps this to its terminal outcome (`TaskExit::Failed`).

Entry: F-T11. Exit: terminal.

### 2.12.2 Transitions

```
F-T1:   (creation) ──► Requested
        Trigger:  The RemoteAgent's Ingest Task instantiates a Feed for a
                  (venue, instrument, datatype) entry of its TaskSpec.
        Guard:    The venue resolves to a registered exchange adapter
                  (the boot self-check / registry resolve succeeds). On a
                  miss, the Feed goes directly to Rejected (F-T9).
        Effects:  Allocate FeedId (UUIDv4, Agent-local); bind the datatype
                  to a fresh SourcedOrderBook (orders) or SourcedTradeBook
                  (trades) in Empty (§2.13); report Feed=Requested on the
                  TelemetryChannel.

F-T2:   (Requested | Reconnecting) ──► Subscribing
        Trigger:  The shared venue connection is Open (established or
                  re-established).
        Guard:    Connection Open.
        Effects:  Send the adapter's subscribe frame(s) for this Feed
                  (plus any in-band seed request, e.g. an on-socket REQ);
                  arm the subscribe-confirmation timer.

F-T3:   (Subscribing | Resubscribing) ──► Live
        Trigger:  First decoded data frame received and the bound book has
                  reached Live: for snapshot-seeded models, the seed is
                  applied and the book is Synced; for full-refresh models,
                  the first frame replaces the book.
        Guard:    Bound SourcedOrderBook/SourcedTradeBook in Live (§2.13).
        Effects:  Mark Feed Live; begin Emitting DataArtifacts (§2.12.3);
                  report Feed=Live.

F-T4:   Live ──► Resubscribing
        Trigger:  The bound SourcedOrderBook/SourcedTradeBook signals
                  Gapped (ResyncNeeded; §2.13).
        Guard:    None (a gap MUST be recovered, never ignored - INV-F4).
        Effects:  Execute the venue recovery action
                  (Resubscribe | RestSnapshot | ReqOnSocket); increment the
                  resync counter (Report).

F-T5:   Draining ──► Closed
        Trigger:  The bound book's pending normalized output is flushed
                  through Emit within stop_drain_timeout.
        Guard:    No pending output; in-flight Emit complete.
        Effects:  Close the subscription; finalize Artifacts; report
                  Feed=Closed.

F-T6:   (Subscribing | Live | Resubscribing | Reconnecting) ──► Draining
        Trigger:  The Ingest Task receives Stop/Drain (T-T*; §2.2), surfaced
                  as the shutdown signal threaded into the adapter spawn.
        Guard:    None.
        Effects:  Stop subscribing/recovering; drain the bound book's
                  pending output; arm the stop_drain_timeout timer.

F-T8:   (Subscribing | Live | Resubscribing) ──► Reconnecting
        Trigger:  The shared venue connection dropped (transport loss),
                  surfaced as WssExitReason -> DisconnectReason.
        Guard:    DisconnectReason.is_retryable() (disconnect.rs).
        Effects:  Hold the Feed and retain its bound book for re-seed; defer
                  to the Ingest mechanism's reconnect policy; report
                  Feed=Reconnecting.

F-T9:   Requested ──► Rejected
        Trigger:  The venue does not resolve to a registered adapter, or the
                  adapter does not support the requested datatype.
        Guard:    None (terminal).
        Effects:  Surface ErrorKind::SKILL_MISMATCH or ::SPEC_INVALID in a
                  structured Error (correlation to the offending TaskSpec
                  entry); report Feed=Rejected. Feeds tracker #11.

F-T10:  Subscribing ──► Rejected
        Trigger:  The venue rejects the subscription (e.g., unknown
                  instrument, malformed subscribe).
        Guard:    None.
        Effects:  Surface ErrorKind::SPEC_INVALID in a structured Error;
                  report Feed=Rejected.

F-T11:  Reconnecting ──► Failed
        Trigger:  The reconnect budget is exhausted (non-retryable
                  DisconnectReason, or max attempts/backoff window).
        Guard:    None (terminal).
        Effects:  Surface a structured Error with the transport cause;
                  report Feed=Failed; the Ingest Task maps this to
                  TaskExit::Failed.

F-T12:  Draining ──► Closed
        Trigger:  stop_drain_timeout elapsed with output still pending.
        Guard:    None.
        Effects:  Mark the remaining Artifacts partial in metadata; close
                  the subscription; report Feed=Closed (partial).
```

### 2.12.3 Datatype binding and the Emit seam

- **One book per Feed, by datatype.** An `orders` Feed binds exactly one `SourcedOrderBook`; a `trades` Feed binds exactly one `SourcedTradeBook` (§2.13). The bound book's `Gapped`/`Synced`/`Live` states drive F-T4/F-T3 (INV-F4, INV-F3).
- **Emit references existing transport.** A Feed in Live Emits the bound book's normalized output as `DataArtifacts` (`ArtifactFrame`) via the **existing** Emit Skill, ArtifactChannel/DataChannel (§2.10), and Sink (§2.11). **Lineage attaches at Emit, never on the book or the Feed:** `ArtifactId` + `ServiceId` + `TaskId` + the `(task, restart_epoch)` monotone sequence (INV-CH4) + `restart_epoch` (INV-CH5). The `Feed` and the OrderBook/TradeBook FSMs stay **lineage-free** so the book FSMs are reusable outside ingestion (§2.13 notes).
- **`FeedId` is reporting metadata only.** It travels on the TelemetryChannel for per-Feed observability (decode-error rate, reconnect/resync counts, stream occupancy); it is not a wire join key for Artifacts (those use `ArtifactId`/`TaskId`/`ServiceId`).

### 2.12.4 Invariants

**INV-F1: FeedId uniqueness.**
`FeedId` is unique within the producing Agent for the lifetime of the Feed. Allocated at F-T1.
*Testability:* assert at F-T1 post-condition that the new `FeedId` collides with no live Feed on the Agent; property test drives concurrent F-T1 with 1000 parallel allocations.

**INV-F2: Exactly one bound book, matching datatype.**
A `Feed` binds exactly one book FSM, and its kind matches the Feed's datatype: `orders -> SourcedOrderBook`, `trades -> SourcedTradeBook`. The binding is established at F-T1 and never re-typed.
*Testability:* assert at the Live state-entry (F-T3) that an `orders` Feed holds one `SourcedOrderBook` and a `trades` Feed holds one `SourcedTradeBook`.

**INV-F3: Live implies bound book Live.**
A `Feed` in Live implies its bound `SourcedOrderBook`/`SourcedTradeBook` is in `Live` (and, for delta venues, `Synced`).
*Testability:* asserted at the F-T3 guard (pre-fire) and re-checked on every Live entry.

**INV-F4: A gap forces Resubscribing.**
While a `Feed` is Live, a `Gapped` signal from its bound book MUST transition the Feed to Resubscribing (F-T4); the Feed never continues to Emit on a gapped book.
*Testability:* assert at the F-T4 boundary; property test injects a sequence/checksum gap into the bound book and asserts the Feed leaves Live before any further Emit.

**INV-F5: Rejected/Failed surface a structured Error.**
A `Feed` reaching Rejected (F-T9/F-T10) or Failed (F-T11) MUST surface an `Error { kind ∈ ErrorKind, message, correlation_id, retryable, retry_after_ms }` upstream (per `errors-beta.md` / `proto-catalog-beta.md`), never a coarse status.
*Testability:* assert at the F-T9/F-T10/F-T11 effects that a structured `Error` with a valid `ErrorKind` is emitted; a bare boolean/string failure path is a violation.

**INV-F6: Drain is bounded.**
A `Feed` in Draining reaches Closed within `stop_drain_timeout`; output still pending at the deadline is marked `partial` (F-T12), never discarded silently and never blocking indefinitely.
*Testability:* drive F-T6 then assert Closed within `stop_drain_timeout` (F-T5) or Closed-with-`partial` past it (F-T12).

**INV-F7: FeedId is Agent-allocated, platform-observed.**
`FeedId` is allocated only at F-T1 (Agent-local) and only reported on the TelemetryChannel; no platform-side transition allocates a `FeedId` and there is no durable Feed row.
*Testability:* implicit at F-T1 (the only allocator); a reconciliation test asserts the platform never mints a `FeedId`.

### 2.12.5 Interaction rules

- **IR-F1:** A `Feed` runs **within an Ingest `Task`** (§2.2) at a RemoteComputeSlot. The Task's Stop/Drain (its shutdown signal) drives F-T6; the Feed's terminal outcome (Closed / Rejected / Failed) feeds the Task's `TaskExit` mapping (T-T terminal triggers).
- **IR-F2:** A `Feed`'s Emit rides the Task's ArtifactChannel/DataChannel (§2.10) and Sink (§2.11). The producer half of **INV-CH4** (monotone `(task, epoch)` sequence) and **INV-CH5** (`restart_epoch` lineage across A-T8) are satisfied at the Emit seam, not by the Feed.
- **IR-F3:** The `Feed` FSM is **Agent-owned** (RemoteAgent -> `atelier-sdk`; §2.4.1). The platform is an **observer**: it renders Feed state from TelemetryChannel reports (best-effort) and never executes Feed transitions or persists Feed state.
- **IR-F4:** The bound book FSM (§2.13) drives the recovery coupling: `Gapped -> F-T4`, `Synced/Live -> F-T3`.
- **IR-F5:** The venue connection is **shared Ingest mechanism**, not a `Channel`. A single connection drop fans F-T8 (Reconnecting) to every `Feed` carried on that socket; a single re-establish fans F-T2.

### 2.12.6 Notes

- **Why `Feed` is Agent-owned and not co-by-seam.** Unlike a `Channel` (§2.10, co-by-seam with a durable Overseer row), a `Feed` is an internal subscription on the Agent's external Ingest path. The platform learns of Feeds only through telemetry, which is why `FeedId` is Agent-allocated (INV-F7) and supports runtime-discovered feeds; cross-restart correlation rides `restart_epoch` (INV-CH5), not a durable Feed row.
- **Scope.** The external venue protocol (subscribe framing, heartbeat, frame codec, bootstrap, symbol codec, the reconstruction-model) is **open SDK config**, not specified here (Taxonomy HOW §Ingest / Data Plane). This section specifies only the subscription *lifecycle* and its coupling to the book FSMs and the Emit seam.
- **Deferred.** Per-connection fan-out/sharding planning, bounded-channel backpressure policy, and the per-Feed `SourceMetrics` catalog are operational concerns deferred with the P1 live path; they extend this contract without revising §2.12.1-§2.12.5.
- **Testability (general).** Every `INV-F*` is asserted at the transition boundary that establishes it (F-T1 for identity/ownership, F-T3 for the book binding, F-T4 for gap recovery, F-T9/T10/T11 for error surfacing, F-T5/T12 for bounded drain). See the invariant testability convention in `fsm-beta.md` preface.
