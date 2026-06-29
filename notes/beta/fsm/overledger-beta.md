# Atelier FSM Atlas - Account Layer (§A) — overledger

Companion to the **State Machine Atlas v0.1-beta-2** and the **Taxonomy** (`../txy/txy-beta.md` → ACCOUNT LAYER). The core Atlas (`fsm-beta.md` §1–§3) owns the orchestration ontology — Sessions, Services, Bindings, Tasks, Agents. This file owns the **account layer**: the token economy that sits *above* the Session boundary and is owned by `atelier-overledger`. It is the dynamic companion to the Taxonomy's ACCOUNT LAYER section the same way `binding-beta.md` is the dynamic companion to the Binding noun.

**Out-of-core by construction.** Per the Taxonomy, billing is "named for coverage … not part of the core orchestration ontology or the FSM Atlas." This file honors that boundary:

- **Section numbers use the `§A.*` namespace**, not the core `§2.x` line. The account layer is not a core Atlas FSM and must not consume a write-once core section number (`fsm-beta.md` house convention). `§A.1` Ledger, `§A.2` Checkout, `§A.3` Plan, `§A.4` Entitlement, `§A.5` Metering, `§A.6` Interaction Rules.
- **Persistence is `overledger-db` (Postgres), not `schema-beta.md`.** The core Atlas schema (`schema-beta.md`, ten tables in overseer-db) describes orchestration state. The account-layer tables — `billing_credit_ledger`, `billing_checkouts`, `billing_subscriptions`, and the optional `billing_entitlements` — live in a separate Postgres database (`overledger-db`) and are referenced here, never added to the core schema.
- **Invariant prefixes are account-layer-local**, declared in this file and deliberately absent from the core `INV-*` legend (`fsm-beta.md`): `INV-LG*` Ledger, `INV-CK*` Checkout, `INV-PL*` Plan, `INV-ENT*` Entitlement, `INV-MET*` Metering. Transition prefixes likewise: `CK-T*`, `PL-T*`, `ENT-T*` (the Ledger has no FSM, so no `LG-T*`). None collide with the core legend (`A`, `T`, `B`, `O`, `CH`, `SK`, `F`, `BK`, `SV`, `SN`, `CS`, `GW`).

**Notation** follows the Atlas (`fsm-beta.md` → Reading This Document): transitions are `trigger [guard] / effect`; each `INV-*` ends with an italic `*Testability:*` line naming the boundary where the assertion fires.

**Token vocabulary, deferred code rename.** This file is written in the canonical noun **Token** (Taxonomy → ACCOUNT LAYER). The implementation still names the unit `credit` (`CreditKind`, `billing_credit_ledger`, `/internal/credits/*`); the credit→token rename is a deferred, separate change that keeps the physical table name. Where this spec says "the Ledger debits a Token," the code today writes a row in `billing_credit_ledger`. The spec leads; the code follows.

---

## §A.0 The account-layer boundary and the coupling principle

The account layer **meters**; the core orchestration layer **emits**. This is the single load-bearing rule of the reconciliation, and every section below is a consequence of it.

- **No core transition writes the Ledger.** No `SV-T*`, `B-T*`, `A-T*`, `T-T*`, or `SN-T*` gains a billing Effect. A core transition that charged a Token would invert the boundary the Taxonomy drew and couple orchestration correctness to balance state.
- **Metering is a subscriber.** `atelier-overledger` (and its data-plane meter, the overwatch ingester) observe orchestration **Events** already emitted on the wire (`proto-catalog-beta.md §services.proto` `Gateway.EventSubscribe`, per the Ownership Matrix observer contract) and the overdex Experiment-run boundary, and debit Tokens as a downstream effect. The orchestration FSMs neither know nor care that metering happens.
- **Enforcement rides the existing envelope.** The one place the core already consults the account layer is `SN-T1` (Session creation), which resolves the envelope "from the identity's plan/quota policy" (`session-beta.md` §2.7.5). That policy **is** the account-layer Plan (§A.3). Quota enforcement (`INV-SN1`) therefore needs no new code — it already gates `SV-T1` / `A-T1` on a Plan-derived envelope.
- **The one cross-tier signal already exists.** `SN-T6` already lists `expire_reason = plan_revoked` ("identity's plan revoked and policy mandates immediate termination"). The account layer drives that existing administrative trigger; it does not add a transition (§A.6, IR-ENT-SN2).

Composed: the account layer is wired to the core through **two pre-existing seams** (`SN-T1` envelope resolution, `SN-T6` `plan_revoked`) and **event subscription** — never through a new Effect on a core transition.

---

## §A.1 Ledger

The **Ledger** is the single enforcement primitive: an append-only log of signed Token deltas keyed by `(identity_id, TokenKind)`. Balance is `SUM(delta)`. It is **not an FSM** — like the core Atlas `artifacts` table, it is lineage-and-audit, never updated in place, with no per-row state machine. Its dynamics live entirely in the invariants below and in the Metering rules (§A.5).

**Persistence:** `billing_credit_ledger(id, user_id, kind, delta, reason, checkout_id?, ref_id?, created_at)` in `overledger-db`. `kind ∈ {data, compute, networking}` (the `TokenKind` typology). The four ledger operations — **Meter, Debit, Grant, Refund** (Taxonomy → ACCOUNT LAYER) — are all expressed as one append:

- **Grant** — `delta > 0`, `reason ∈ {signup_grant, …}`. The one-time new-account grant (50 data + 25 compute + 0 networking) and any promotional award.
- **Debit** — `delta < 0`, `reason` naming the metered work (`fit`, `forecast`, `ingest`, `agent_runtime`, …), `ref_id` the consuming entity.
- **Refund** — `delta > 0`, `reason` a `*_refund`, `ref_id` referencing the debit it compensates.
- **Meter** — the act of *deriving* a Debit amount from observed usage (bytes ingested, agent-seconds, fit cost) before the append. Meter is the measurement; Debit is the record.

### §A.1.1 Invariants

**INV-LG1: Balance is the signed sum.** For any `(identity_id, kind)`, the spendable balance is `SUM(delta)` over all rows, and a Debit is admitted only when the resulting balance is `≥ 0`. A fresh lead and a freshly-created account both start at `0/0/0` until the signup Grant lands.
*Testability:* assert at Debit pre-check that `current_balance + delta ≥ 0`; integration test posts a Debit exceeding balance and asserts rejection (the `402 PAYMENT_REQUIRED` path) with no row written.

**INV-LG2: Append-only.** No row is ever updated or deleted in the normal path; corrections are new compensating rows (Refund). The row, once written, is immutable audit.
*Testability:* implicit at every write site (the only statement is `INSERT`); property test asserts no `UPDATE`/`DELETE` against `billing_credit_ledger` outside migration.

**INV-LG3: Grant idempotency.** The one-time signup Grant for an identity lands at most once. Re-reading entitlements never re-grants.
*Testability:* assert at the Grant boundary (`ensure_signup_grant`, advisory-lock-guarded) that a second call for the same `identity_id` writes zero rows; covered by `crates/payments/tests/signup_grant.rs`.

**INV-LG4: Dev-bypass holds no auto-Tokens.** The `DEV_BYPASS_USER` identity is not a real account and is never auto-Granted; it stays `0/0/0`.
*Testability:* assert at the entitlements-read boundary that the dev-bypass identity is skipped by the Grant; covered by `signup_grant.rs::dev_bypass_identity_stays_zero`.

---

## §A.2 Checkout FSM

A **Checkout** is one purchase attempt that, on settlement, Grants Tokens. It is the shortest-lived account-layer FSM: a single forward path with one terminal alternative.

### §A.2.1 States

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  CHECKOUT STATES                                                             │
│                                                                              │
│     pending ──► succeeded (terminal)                                         │
│        │                                                                     │
│        └──────► expired   (terminal)                                         │
│                                                                              │
│  Both terminals are absorbing (INV-CK1).                                     │
└──────────────────────────────────────────────────────────────────────────────┘
```

**S-CK1: pending.** A `billing_checkouts` row exists; the provider pay-link was issued; no settled webhook has arrived.

**S-CK2: succeeded.** Absorbing terminal. A settled webhook arrived; the Grant landed in the Ledger.

**S-CK3: expired.** Absorbing terminal. The pay-link TTL elapsed before settlement; no Grant.

### §A.2.2 Transitions

```
CK-T1:  pending ──► succeeded
        Trigger:  Provider webhook arrives for this checkout (MoonPay Commerce
                  pay-link `POST /internal/payments/webhook/paylink`).
        Guard:    Settlement confirmed — `ParsedWebhook.settled` is true
                  (`meta.transactionStatus == "SUCCESS"`); the checkout is in
                  pending; the SKU is a Token pack.
        Effects:  Grant the SKU's server-side quantity into the Ledger
                    (delta = Sku::token_qty(), reason='purchase',
                    checkout_id=this) — quantity is NEVER read from the webhook
                    body (hardening, see §A.5 INV-MET1);
                  persist checkout status=succeeded.

CK-T2:  pending ──► expired
        Trigger:  TTL sweep finds `expires_at < now()` with no settlement.
        Guard:    Checkout still in pending.
        Effects:  Persist checkout status=expired; no Ledger row.
```

### §A.2.3 Invariants

**INV-CK1: Terminals absorbing.** `succeeded` and `expired` admit no further transition. A second webhook for a `succeeded` checkout is a no-op (idempotency, INV-CK2).
*Testability:* assert at CK-T1/CK-T2 guards that the checkout is in `pending`; replay test posts a duplicate settled webhook and asserts no second Grant.

**INV-CK2: Grant rides settlement only.** A Grant lands at CK-T1 only when `settled` is true; an unsettled or non-SUCCESS webhook is acknowledged (`200`) but mints nothing.
*Testability:* assert at CK-T1 guard; covered by the webhook-hardening tests (a non-SUCCESS body acks with zero Ledger delta).

**INV-CK3: Server-side quantity.** The Granted amount is `Sku::token_qty()`, resolved from the SKU, independent of any quantity field in the webhook body.
*Testability:* assert at CK-T1 effect; a webhook posting `quantity = 999999` for a 100-pack Grants exactly 100.

> **Mainnet gate (out of scope for this spec, tracked in the security audit).** CK-T1 in v0.1 trusts the bearer-authenticated webhook; on-chain settlement verification, HMAC signature checking, and idempotency keyed on the chain tx-signature remain open and gate public mainnet exposure. The FSM is correct; the trust model is not yet mainnet-ready.

---

## §A.3 Plan FSM

A **Plan** is the user's billing tier — the access subscription that, while `active`, unlocks the Session envelope and the right to buy Token packs. It is the noun the Taxonomy reserves as **Plan** (distinct from the data-plane **Subscription** = feed watchlist). Authoritative state is `billing_subscriptions.status` in `overledger-db`.

### §A.3.1 States

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  PLAN STATES                                                                 │
│                                                                              │
│   (none) ──► active ◄──► past_due ──► expired   (terminal)                   │
│                 │            │                                               │
│                 └────────────┴──────► cancelled (terminal)                   │
│                                                                              │
│  active ↔ past_due is bidirectional (lapse then renew).                      │
│  expired / cancelled are absorbing.                                          │
└──────────────────────────────────────────────────────────────────────────────┘
```

**S-PL1: active.** Provider reports the subscription paid and current; `current_period_end` is in the future. The only state that unlocks the Session envelope (IR-ENT-SN1) and admits Token purchases.

**S-PL2: past_due.** A renewal payment failed but the grace window has not closed. Envelope access is treated as lapsed (the projecting Entitlement reads `past_due`, §A.4); the Plan may still recover via PL-T5.

**S-PL3: expired.** Absorbing terminal. The period ended with no renewal.

**S-PL4: cancelled.** Absorbing terminal. The user (or provider) cancelled.

### §A.3.2 Transitions

```
PL-T1:  (none) ──► active
        Trigger:  Subscription webhook (provider ACTIVE) for an identity with no
                  active Plan (`POST /internal/payments/webhook/subscription`).
        Guard:    No active Plan already exists for the identity.
        Effects:  Persist billing_subscriptions(status=active, provider_sub_id,
                    current_period_end); no Ledger row (a Plan is capacity, not
                    Tokens); drive Entitlement ENT-T1 (§A.4).

PL-T2:  active ──► past_due
        Trigger:  Subscription webhook (provider PAYMENT_PAST_DUE).
        Guard:    Plan in active.
        Effects:  Persist status=past_due; drive Entitlement ENT-T2.

PL-T3:  {active, past_due} ──► expired
        Trigger:  `current_period_end < now()` with no renewal, OR provider ENDED.
        Guard:    Plan in {active, past_due}.
        Effects:  Persist status=expired; drive Entitlement ENT-T4;
                  emit the plan-lapsed signal the Overseer consumes for SN-T6
                  `plan_revoked` (IR-ENT-SN2) only when policy mandates immediate
                  termination — otherwise the envelope simply stops admitting new
                  SV-T1/A-T1 (IR-ENT-SN1) and running work is left to its own
                  lifecycle.

PL-T4:  {active, past_due} ──► cancelled
        Trigger:  Subscription webhook (provider CANCELLED).
        Guard:    Plan in {active, past_due}.
        Effects:  Persist status=cancelled; drive Entitlement ENT-T4.

PL-T5:  past_due ──► active
        Trigger:  Renewal payment succeeds (provider RENEWED); re-anchors
                  `current_period_end`.
        Guard:    Plan in past_due.
        Effects:  Persist status=active, current_period_end (new); drive
                  Entitlement ENT-T3.
```

### §A.3.3 Invariants

**INV-PL1: Only active unlocks the envelope.** The Session envelope (`concurrent_services`, `concurrent_agents`) is resolved from a Plan only while it is `active`. In {past_due, expired, cancelled, none}, the identity resolves to the free-tier envelope.
*Testability:* assert at the `SN-T1` envelope-resolution boundary (`find_active_for_user`) that a non-active Plan yields the free envelope; integration test flips a Plan to past_due and asserts the next Session resolves reduced quota.

**INV-PL2: `current_period_end` always set.** Every non-`none` Plan carries a period end; PL-T5 re-anchors it on renewal.
*Testability:* assert at PL-T1/PL-T5 post-condition that `current_period_end` is non-null and in the future.

**INV-PL3: Terminals absorbing.** `expired` and `cancelled` admit no further transition; recovery is a new Plan (new PL-T1), not a resurrection.
*Testability:* assert at PL-T* guards that the source state is non-terminal.

---

## §A.4 Entitlement FSM

The **Entitlement** is the user-facing projection that answers "what may this identity do right now?" — a *derived* FSM whose transitions are the observable consequence of Plan transitions (§A.3) and Ledger balance crossings (§A.1), not independent triggers. It is the dynamic companion to the Taxonomy's **Entitlement** noun and to the `Entitlements { plan, credits }` DTO the webapp reads. Today it is computed on read (no stored row); formalizing it makes the access-tier and solvency semantics testable. A `billing_entitlements` table MAY back it later without changing these semantics.

It carries two orthogonal dimensions:

- **access_tier** — a projection of `Plan.status`: `none → free`, `active → pro`, `past_due → past_due`, `{expired, cancelled} → suspended`. Gates PRO features and the Session envelope.
- **solvency** — the sign of the Ledger balance per `TokenKind`. Gates Debit (INV-ENT1), orthogonal to tier (a free-tier identity may still hold signup-Granted Tokens).

### §A.4.1 States (access_tier)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  ENTITLEMENT access_tier                                                     │
│                                                                              │
│   free ──► pro ◄──► past_due ──► suspended                                   │
│              │                       ▲                                        │
│              └───────────────────────┘                                       │
│                                                                              │
│  Derived from Plan.status; solvency (Ledger sign) is an orthogonal axis.     │
└──────────────────────────────────────────────────────────────────────────────┘
```

### §A.4.2 Transitions (driven by Plan + Ledger)

```
ENT-T1:  free ──► pro          [driven by PL-T1] / unlock PRO features + envelope.
ENT-T2:  pro ──► past_due      [driven by PL-T2] / envelope treated as lapsed.
ENT-T3:  past_due ──► pro      [driven by PL-T5] / re-unlock.
ENT-T4:  {pro, past_due} ──► suspended
                               [driven by PL-T3/PL-T4] / PRO features locked;
                               where policy mandates, signal SN-T6 plan_revoked.
ENT-T5:  suspended ──► {free, pro}
                               [re-subscribe via new PL-T1, or grace lapse to free]
                               / re-evaluate from the Plan.
```

### §A.4.3 Invariants

**INV-ENT1: Debit requires solvency.** A Debit of `kind` is admitted only when `balance(identity, kind) ≥ amount` (INV-LG1). Solvency is independent of access_tier — a `free` identity spends its Granted balance; a `pro` identity is not exempt from the balance check.
*Testability:* assert at the Debit pre-check; a `pro` identity with zero `compute` balance is refused a compute Debit (`402`).

**INV-ENT2: PRO surface gated by active Plan.** PRO-only features and the elevated Session envelope are available only while `access_tier = pro` (equivalently `Plan.status = active`, INV-PL1). `past_due` and `suspended` resolve to the free envelope.
*Testability:* assert at the `SN-T1` envelope-resolution and the PRO-feature gate; flipping the Plan to suspended yields the free envelope on the next Session.

**INV-ENT3: Projection consistency.** `access_tier` is a pure function of `Plan.status`; it is never set independently of a Plan transition. Any stored `billing_entitlements.status` is a cache of that function and is reconciled on read.
*Testability:* assert at each ENT-T* that the post-state equals the projection of the current `Plan.status`; property test drives random PL-T* sequences and asserts the projection holds.

---

## §A.5 Metering — charge-to-transition map and invariants

Metering binds each money-grade charge to the orchestration moment it settles against, **as a subscriber to that moment's Event**, never as an Effect inside the core transition. The owning-entity column names where the moment lives; the metering site is always account-layer.

| # | Touchpoint | Token | Settles against | Guard/Effect/Periodic | Metering site (account-layer) |
|---|---|---|---|---|---|
| 1 | Model fit (Hawkes) | compute | overdex Experiment run (`run → completed`; overdex-owned, **no Atlas FSM** per Taxonomy C6) | Effect on convergence | overdex calls `/internal/credits/debit` (reason=`fit`, ref_id=fit_id) |
| 2 | Fit-persist refund | compute | same run, persist failure after debit | Effect (compensating) | overdex calls `/internal/credits/refund` (reason=`fit_refund`, ref_id=fit_id) |
| 3 | Forecast | compute | overdex forecast run | Effect on completion | overdex Debit (reason=`forecast`, ref_id=**forecast_id** — distinct from the fit's `ref_id=fit_id` so the two never collide under INV-MET1/INV-MET5), incremental price |
| 4 | Signup Grant | compute+data | first entitlements read (real account) | Effect, idempotent | overledger Grant (reason=`signup_grant`) — INV-LG3 |
| 5 | Token purchase | per SKU | Checkout CK-T1 | Effect on settlement | overledger Grant (reason=`purchase`) — §A.2 |
| 6 | Managed agent runtime | compute | Binding window: **B-T3** (= Pending→Active, opens the window; durable `bindings.active_at`) → **B-T8** (= Releasing→Released, closes it; emits `BindingReleased`) | On-release at B-T8 | overledger meters agent-seconds across the window by reading the durable `bindings` timestamps and observing `BindingReleased` (B-T8); ONE full-window Debit (reason=`agent_runtime`, ref_id=binding_id) at close. A long-lived Binding MAY accrue interim charges, but then each keys `ref_id=binding_id:epoch` so every charge is its own exactly-once unit under INV-MET1 (a fixed `ref_id=binding_id` would self-deduplicate). No Effect added to B-T3/B-T8. |
| 7 | Data at ingest | data | overwatch ingester sha256 exactly-once gate | Effect after dedup | ingester Debit (reason=`ingest`, ref_id=sha256) |
| 8 | Service / Agent slots | — (quota) | **SV-T1** (= Service-provision) / **A-T1** (= Agent-register) | Guard (envelope) | NOT a Debit — capacity quota via `INV-SN1`, Plan-gated (IR-ENT-SN1) |
| 9 | At-rest retention | data | billing-period sweep over resident bytes | Periodic | overledger/overwatch batch Debit (reason=`retention`) — P3, deferred |
| 10 | Networking (telemetry/connection/egress) | networking | — | — | Defined as a `TokenKind`; metering deferred to P3 (INV-MET5 prevents double-charging artifact bytes already metered as data) |

### §A.5.1 Metering invariants

**INV-MET1: Exactly-once.** Each unit of settled work is Debited at most once, keyed by `(identity_id, ref_id)` (or `sha256` for ingest). A retried Debit returns the existing Ledger reference; it does not double-charge.
*Testability:* assert at the Debit boundary (advisory-xact-lock + `find_debit_by_ref`); covered by `crates/payments/tests/debit_idempotency.rs` — a retried `(user_id, ref_id)` returns the same ledger ref with no second row.

**INV-MET2: Debit after settled work.** No Token is Debited before the work's owning moment commits — fit convergence (run→completed), Binding release (B-T8) for accrued runtime, the ingest dedup gate for persisted bytes. A pre-charge that the work never reaches is forbidden; the compensating path is Refund (INV-MET3).
*Testability:* assert that the Debit call site is downstream of the committing boundary; a fit that fails to converge writes no `fit` Debit.

**INV-MET3: Refund pairs a Debit.** A Refund references a prior Debit by `ref_id` and does not exceed it. Charge-then-fail must ship its Refund in the same path (touchpoint 2).
*Testability:* assert at the Refund boundary that a Debit with the same `ref_id` exists and `refund_amount ≤ debit_amount`.

**INV-MET4: Tenant isolation.** Every Ledger row and every meter event carries `identity_id`; no usage is attributed across tenants. The metered moment's Event must resolve to exactly one `identity_id` (binding_id → session_id → identity_id for runtime; the overdex caller's identity for fits).
*Testability:* assert at each Debit that `identity_id` is non-null and matches the work's owning Session; property test with two identities asserts no cross-attribution.

**INV-MET5: Charge each physical resource once.** A resource is metered at exactly one seam: data at the ingest dedup gate (not also at agent flush); runtime as agent-seconds across the Binding window (not also as connection-hours); slots as quota (not as Debits); artifact bytes as `data` (not also as `networking`).
*Testability:* assert at audit that no `(ref_id, kind)` is Debited by two distinct reasons; a single ingested file produces one `ingest` Debit, not an `ingest` plus a `parquet_flush`.

---

## §A.6 Interaction Rules

**Account layer ↔ Session (IR-ENT-SN)**

- **IR-ENT-SN1: Envelope resolution from Plan.** `SN-T1`'s "envelope … resolved from the identity's plan/quota policy" (`session-beta.md` §2.7.5) reads the account-layer Plan (§A.3): an `active` Plan yields the PRO envelope, any other state yields the free envelope (INV-PL1, INV-ENT2). This is a **read** by the Overseer at SN-T1; the account layer exposes the policy, the Overseer enforces it via `INV-SN1`. No new transition.
- **IR-ENT-SN2: Suspension drives the existing emergency exit.** When an Entitlement reaches `suspended` (ENT-T4) **and policy mandates immediate termination**, the account layer raises the plan-revocation signal that the Overseer already consumes as the `SN-T6` administrative trigger with `expire_reason = plan_revoked` (`session-beta.md` SN-T6; `IR-SNO3` "Overseer drives SN-T6 only for explicit administrative triggers"). The core cascade (IR-SNS2 → SV-T6) is unchanged; the account layer supplies the trigger, not the mechanism. Where policy does *not* mandate immediate kill, suspension simply stops the envelope from admitting new `SV-T1`/`A-T1` (IR-ENT-SN1) and running work completes on its own lifecycle.

**Account layer ↔ Binding (IR-ENT-B)**

- **IR-ENT-B1: Runtime metering across the Binding window.** Managed-agent runtime (touchpoint 6) is metered across the Binding's runtime window: it opens at B-T3 (Pending→Active, persisted `bindings.active_at`) and closes at B-T8 (Releasing→Released, which emits `BindingReleased`). The account layer brackets agent-seconds between these boundaries by reading the durable `bindings` timestamps and observing `BindingReleased`; a B-T11 platform-drain resume (which emits `BindingActive`) reopens the window. The canon emits no `BindingActive` at B-T3, so the open boundary is observed via the durable `bindings.active_at` (and any Binding-lifecycle Event the Overseer emits per INV-P3), not a named B-T3 event. Neither B-T3 nor B-T8 gains a billing Effect (§A.0). If the metering subscriber is down, orchestration is unaffected and the meter backfills from the durable timestamps.

**Account layer ↔ overdex Experiment runs (IR-ENT-X)**

- **IR-ENT-X1: Fit/forecast metering at the run boundary.** Experiment runs are overdex-owned with no Atlas FSM (Taxonomy C6). overdex Debits at `run → completed` (fit, forecast) and Refunds at persist-failure, calling `/internal/credits/{debit,refund}` directly. The core Atlas is not involved; this rule exists so the charge has a documented home.

**Account layer ↔ overwatch ingester (IR-ENT-OW)**

- **IR-ENT-OW1: Data metering at the dedup gate.** The premium at-rest tier Debits `data` Tokens at the ingester's sha256 exactly-once gate (touchpoint 7), keyed by `sha256` (INV-MET1). The agent-flush telemetry is observed for governance but is **not** a Debit site (INV-MET5), avoiding double-charging the same bytes.

---

## §A.7 Source citations

- `../txy/txy-beta.md` → ACCOUNT LAYER (Token, Ledger, Entitlement, Plan, Checkout nouns; TokenKind typology; Meter/Debit/Grant/Refund operations; Subscription-vs-Plan collision note).
- `fsm-beta.md` §2.4.1 FSM Ownership Matrix (overledger row: account layer, out of core FSM) and the invariant-testability convention this file follows.
- `session-beta.md` §2.7.2 SN-T1 (Session creation / envelope resolution — the "identity's plan/quota policy" wording is in §2.7.1 S-SN1 and §2.7.5 Notes, not §2.7.2), SN-T6 (`expire_reason=plan_revoked`), §2.7.4 IR-SNO3 / IR-SNS2, §2.7.5 Notes (identity/billing layer out of core FSM scope), INV-SN1 (envelope atomicity).
- `binding-beta.md` §2.3.2 B-T3 / B-T8 (the runtime-metering window) and §2.4.1 observer contract (Event subscription).
- Implementation: `atelier-overledger` (`ledger-types`, `crates/payments`, `crates/server`), `overledger-db` (`billing_credit_ledger`, `billing_checkouts`, `billing_subscriptions`); `atelier-overdex` (fit/forecast Debit); `atelier-overwatch` (ingest Debit). Charge matrix: `iteralabs-vault/.../drafts-v0.11/tokens-taxonomy-draft.md`.
