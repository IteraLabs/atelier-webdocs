# Atelier FSM Atlas - Book families: OrderBook / TradeBook (§2.13)

Part of the **State Machine Atlas v0.1-beta**. See `fsm-beta.md` for the reading guide, notation, §2.4 scope status, §2.4.1 Ownership Matrix. Owns the `INV-BK*` invariant prefix. Cross-references: `feed-beta.md` (§2.12 Feed - the bound subscription), `task-beta.md` (§2.2 the Sync Skill within the Ingest Task), `errors-beta.md` (`ErrorKind`).

A **`…Book`** is a composable type-suffix (Taxonomy HOW §Ingest / Data Plane): *a stateful registry FSM of one market-data type*. It is composed `<Specialization><Domain>Book` and is **never written bare** - always `SourcedOrderBook`, `SourcedTradeBook`, `SyntheticOrderBook`, `SyntheticTradeBook`. This section specifies the shared **core** FSM and the **Sourced** specialization (the reconstruction half used by the BYOI Data Pipeline). The **Synthetic** specialization is enumerated for cross-reference and **reserved** (its generation half belongs to the Synthetic Markets engine and is not specified here).

The OrderBook/TradeBook FSMs are **foundational and lineage-free** (INV-BK6): they carry no Artifact/Channel lineage, so the same core is reusable by the Synthetic specialization without revision.

---

## 2.13 The core `…Book` FSM and the Sourced specialization

### 2.13.1 Domains and specializations

- **Domain prefix** ∈ {`Order`, `Trade`, … extensible: `Funding`, `Liquidation`, `OpenInterest`}. This section instantiates **`OrderBook`** (a price-level / per-order limit book) and **`TradeBook`** (an ordered public-trade log).
- **Specialization prefix** ∈ {`Sourced` (reconstruction from an external venue feed), `Synthetic` (generation; reserved)}.
- The **core** FSM (`Empty → Live → Closed`) is shared by every specialization. A specialization refines `Live` and supplies an `apply` contract.

### 2.13.2 Core states

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  CORE …Book STATES (shared by all specializations)                            │
│                                                                                │
│     Empty ──► Live ──► Closed                                                  │
│                                                                                │
│  The Sourced specialization refines Live into { Synced ⇄ Gapped }.            │
│  The Synthetic specialization refines Live with an engine-agnostic apply       │
│  (reserved, not specified here).                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

**S-BK1: Empty.** The book is constructed for a `(venue, instrument)` with a `max_depth` and a **reconstruction-model** (Sourced) or a generator (Synthetic), but holds no state - no seed has been applied.

Entry: BK-T1 (book created). Exit: BK-T2 (seed applied -> Live).

**S-BK2: Live.** The book holds reconstructed (Sourced) or generated (Synthetic) state and accepts `apply`. The Sourced specialization refines Live into **Synced** (S-BK2a) and **Gapped** (S-BK2b).

Entry: BK-T2. Exit: BK-T6 (-> Closed).

**S-BK2a: Synced** (Sourced refinement of Live). The book is current and source-continuity has been verified; deltas apply in place while continuity holds.

**S-BK2b: Gapped** (Sourced refinement of Live). Source-continuity broke (a sequence gap, an out-of-order delta, or a checksum mismatch); a `ResyncNeeded` has been raised and the book awaits a re-seed. **No further input is applied while Gapped** (INV-BK2/INV-BK5).

**S-BK3: Closed** (terminal). The book is finalized (the bound Feed closed or the Task drained).

Entry: BK-T6. Exit: terminal.

### 2.13.3 Sourced transitions

```
BK-T1:  (creation) ──► Empty
        Trigger:  The Sync Skill constructs a SourcedOrderBook (orders) or
                  SourcedTradeBook (trades) for the bound Feed's
                  (venue, instrument).
        Guard:    None.
        Effects:  Initialize the book with max_depth and the venue's
                  reconstruction-model (config); set sequence cursor unset.

BK-T2:  Empty ──► Live (Synced)
        Trigger:  The seed is applied - a REST/in-band snapshot
                  (snapshot-seeded models) or the first frame
                  (full-refresh models).
        Guard:    Seed valid (parses; satisfies the model's seed rule).
        Effects:  Populate the book; set the sequence cursor; mark Synced.

BK-T3:  Synced ──► Synced   (the source-agnostic apply, steady state)
        Trigger:  A normalized delta/frame arrives.
        Guard:    The reconstruction-model's CONTINUITY predicate holds:
                    - FullRefresh: always (each frame replaces the book);
                    - SeqDelta{RangeInclusive}: update spans past the cursor;
                    - SeqDelta{ExactPrev}: prev == cursor;
                    - ChecksumDelta: post-apply checksum matches the venue's.
        Effects:  Apply the delta (level insert/update/delete, or trade
                  append/dedup for TradeBook); advance the cursor.

BK-T4:  Synced ──► Gapped
        Trigger:  A delta FAILS the continuity predicate (gap, out-of-order,
                  or checksum mismatch).
        Guard:    Continuity predicate false.
        Effects:  Raise ResyncNeeded { reason, recovery_action ∈
                  {Resubscribe, RestSnapshot, ReqOnSocket} }; do NOT apply
                  the delta; signal the bound Feed (F-T4).

BK-T5:  Gapped ──► Synced
        Trigger:  A fresh seed arrives from the Feed's recovery action.
        Guard:    Seed valid; continuity re-established from the new cursor.
        Effects:  Re-seed/replace the book; reset the cursor; mark Synced.

BK-T6:  (Empty | Synced | Gapped) ──► Closed
        Trigger:  The bound Feed closes (F-T5/F-T12) or the Ingest Task
                  drains.
        Guard:    None.
        Effects:  Finalize; release the book.
```

### 2.13.4 The source-agnostic apply (open axis)

The **reconstruction-model** is an **open SDK-config axis**, NOT a closed typology - new venues and new models are config, never a spec edit. The currently-mapped models are `FullRefresh`, `SeqDelta{RangeInclusive}`, `SeqDelta{ExactPrev}`, `ChecksumDelta{fmt}`, and `L3` (per-order, order-id-keyed - used by `SourcedOrderBook` for venues like Bitso). The spec fixes the **contract** (the invariants below), not the value set. `TradeBook`'s apply is an ordered append with dedup; its continuity is the venue's trade-sequence where one exists (else best-effort), and `Gapped` means a missed trade-sequence recoverable by re-fetching trade history.

### 2.13.5 Invariants

**INV-BK1: Live implies seeded.**
A book in Live (Synced or Gapped) has had a valid seed applied (BK-T2); Empty has none.
*Testability:* assert at the BK-T2 post-condition; a delta applied in Empty (before any seed) is a violation.

**INV-BK2: Continuity-or-Gapped (the apply contract).**
In Synced, a normalized delta is applied **iff** the reconstruction-model's continuity predicate holds; otherwise the book transitions to Gapped (BK-T4) and the delta is **not** applied.
*Testability:* assert at the BK-T3 guard vs BK-T4; property test feeds in-order then gapped deltas and asserts apply-then-Gapped at the right boundary.

**INV-BK3: Monotone within Synced.**
Within a Synced period the book's sequence cursor advances monotonically per the model (non-decreasing for `RangeInclusive`; exact-prev-chained for `ExactPrev`).
*Testability:* property test with randomized in-order deltas asserts the cursor never regresses within Synced.

**INV-BK4: Checksum-validated (ChecksumDelta models).**
For a `ChecksumDelta` model, after applying a delta the book's computed checksum equals the venue's published checksum; a mismatch raises Gapped (BK-T4).
*Testability:* a golden-frame fixture whose published checksum the reconstructed top-N book reproduces; a perturbed fixture must raise Gapped.

**INV-BK5: No silent drop.**
Every input delta is either applied (advancing Synced) or causes a Gapped transition; none is silently discarded, and a Gapped book applies nothing until re-seeded. (This is the guarantee that closes the eval's delta-flattening and trade head-drop defects.)
*Testability:* assert at the apply boundary that the count of (applied + gap-triggering) inputs equals the count of inputs received; for `TradeBook`, every print in a batched frame is appended (no head-only drop).

**INV-BK6: Lineage-free.**
A book FSM carries no Artifact/Channel lineage (`ArtifactId`, the `(task,epoch)` sequence, `restart_epoch`); lineage attaches only at the Emit seam (§2.12.3).
*Testability:* structural - the book type exposes no lineage field; an integration test confirms a Synthetic-specialization book can be driven with no ingestion lineage present.

**INV-BK7: Domain shape.**
A `SourcedOrderBook` holds price-keyed levels (and, for `L3`, order-id-keyed entries aggregated to levels); a `SourcedTradeBook` holds an ordered, de-duplicated trade log.
*Testability:* domain unit tests on each book kind.

### 2.13.6 Interaction rules

- **IR-BK1:** A Sourced book is bound to **exactly one Feed** (§2.12 INV-F2). The Feed drives seed and recovery (BK-T2 / BK-T5) and observes `Gapped` (BK-T4 -> F-T4). The book never opens its own connection.
- **IR-BK2:** The book's output (snapshot / delta / trade) is consumed by the **Emit** Skill (§2.12.3); the book does not Emit and carries no lineage (INV-BK6).
- **IR-BK3 (foundational reuse):** The core `…Book` FSM and the lineage-free invariant (INV-BK6) are specialization-agnostic. The Synthetic specialization (reserved) reuses the core with an **engine-agnostic apply** (generator-agnostic: matching-engine fills, model output, or samples); it does not reuse the Sourced `Synced/Gapped` continuity machinery. No Sourced transition assumes a synthetic generator and vice-versa.

### 2.13.7 Synthetic specialization (reserved - enumerated, not specified)

`SyntheticOrderBook` / `SyntheticTradeBook` refine the core `Live` with an **engine-agnostic apply** and have **no `Synced`** state (there is no external source to be in sync with); a `Gapped`-analogue may exist in a different sense (e.g., a deliberate liquidity regime) and is **left undefined here**. The generation half - the `Exchange` matching engine, the `MarketAgent` population, the `Experiment`/`Service` activation - belongs to the Synthetic Markets engine and is **out of scope for this version**. This subsection exists only so cross-references resolve and so the core stays specialization-neutral (IR-BK3).

### 2.13.8 Notes

- **Testability (general).** Every `INV-BK*` is asserted at the transition boundary that establishes it (BK-T2 for seeding/identity, BK-T3/BK-T4 for the apply contract, BK-T4 for checksum/gap). The golden-frame fixture corpus (per-venue captured frames + their published checksums) is the harness for INV-BK4/INV-BK5; building it is a precondition for trusting any venue's reconstruction.
- **Relationship to the engine.** The core engine that BK-T3/BK-T5 drive is the existing depth-pruning, sequence-tracking book primitive (`atelier-types::orderbooks::OrderbookDelta` for `SourcedOrderBook`); this section wires it behind the FSM (closing the eval finding that the engine was bypassed in production).
