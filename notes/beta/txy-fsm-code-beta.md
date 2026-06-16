# txy ↔ fsm ↔ code — Master Reconciliation Tracker (v0.1-beta-2)

> **Status rollup:** **8 / 24 done** · **1 doing** (#9 — channel lifecycle Phases 1–4 + recovery refinements landed & **live-verified**; remaining: P5 gateway handshake timers→#20, P6 `restart_epoch`→#10, per-Sink ArtifactChannel + real manifest idempotency key) · 0 blocked · **1 spec✓** (#3 — code half pending) · 14 todo — _updated 2026-06-16_. Bump this line whenever a row's **Status** changes.

**Purpose.** The single, priority-ranked action list to close the gap between the **Taxonomy** (`txy/txy-beta.md`), the **FSM Atlas** (`fsm/*-beta.md`), and the **codebase**. Each row is a discrete, independently-shippable unit of work, tracked live via the **Status** and **Owner** columns.

**Indexed in** [`INDEX.md`](INDEX.md) as the third leg (reconciliation ↔ code) beside `fsm/` and `txy/`.

**Evidence base.** Derived from `../../v0.1-integration.md` (repo root) — a live deployment (control plane built from source, SEQ-1 Deploy + SEQ-2 Delete driven end-to-end) plus a 50-agent static audit (10 FSMs scoped to owners per §2.4.1, 9 repos × Taxonomy C1–C7, 5 integration aspects). **All 26 load-bearing findings were adversarially verified (0 refuted).**

**How priority is ranked.** Descending by *(leverage × value) ÷ cost*, respecting dependencies and risk:
1. **Make the yardstick true first** — where the code is intentionally ahead, fix the spec (cheapest, removes phantom gaps).
2. **Unblockers next** — actions that other actions depend on (e.g. Channel wiring → recovery + Sink).
3. **Observable correctness** — gaps a user sees in the webapp or a process gets wrong.
4. **Wire cut + the big rename last** — coordinated, multi-repo, highest churn.

### Legend

- **Group / Wave** — `0·Config` (W0 quick wins) · `1·Spec` (W1 spec-first, doc-only) · `2·Wire` (W2 coordinated wire cut) · `3·FSM` (W3 code) · `4·Rename` (W3 cross-repo rename).
- **Status** — `Todo` · `Doing` · `Blocked` · `Done` · `Spec✓` (spec edited, awaiting code) — update in place as work progresses.
- **Owner** — defaults to the **lead repo/area** where the change starts; reassign to a person/team as you delegate. (Full ripple is in *Blast radius*.)
- **Complexity** — `S` ≤ ½ day · `M` 1–3 days · `L` ~1 week · `XL` multi-week / coordinated.
- **Blast radius** — `Contained` (1 repo, no wire) · `Moderate` (cross-file, 1 migration/config, or some re-verify) · `Wide` (multi-repo, wire-breaking, or needs live re-verification). Flags: `[wire]` consumers regen · `[runtime]` re-verify on a live stack · `[ops]` operational/topic/group · `[observer]` webapp-visible.

---

## Priority-ranked action list

| # | Group | Action | Status | Owner | Why (≤20w) | Impact (≤20w) | Finding | Complexity | Blast radius |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 1·Spec | Sweep `schema-beta.md` to match impl: nullable `bindings.agent_id`, add `container_id`, `agents.prior_status`, `tasks.paused_at`, `artifacts_emitted_at_idx` | Done | webdocs | Code is intentionally ahead (BYO-infra, recovery); stale DDL reports false gaps and misleads contributors | Audit/review process: removes ~5 phantom gaps; future schema work reads a correct yardstick | INT-DB-07..11 | S | Contained · webdocs |
| 2 | 1·Spec | Sweep `proto-catalog-beta.md`: add `TerminalEvent` + `Envelope` tag 32; record `skills` enum-vs-string; document `TASK_CANCEL` | Done | webdocs | Wire code is ahead of the catalog; the SSoT must match to stay authoritative | Review process + wire decisions; documents the webapp DATA-LOGS feed source | PROTO-TXY-01/02/03 | S–M | Contained · webdocs (gates #21) |
| 3 | 1·Spec | Resolve invented ops **Run / Query** — lift to spec or remove from Atlas §1.4 + overseer | Spec✓ | webdocs+overseer | They exist in both code and Atlas, violating the closed System-Operation set (Class C) | Operation-surface governance; overseer availability matrix and every API verb consumer | OVS-TXY-C3-01 | M | Moderate · webdocs+overseer (gates W3) |
| 4 | 1·Spec | Reconcile deferred "Experiment FSM = same shape as Service" sketch with taxonomy C6 | Done | webdocs | Sketch contradicts "Experiment has no Atlas FSM"; code follows taxonomy, not the sketch | Spec governance; prevents a future beta-3 Experiment-as-activation violation in overdex | domain-scope | S | Contained · webdocs |
| 5 | 0·Config | Provision `control.manifests` with `cleanup.policy=compact` (keyed by binding_id) | Done | infra | ManifestChannel is exactly-once-with-idempotency-key; an uncompacted topic breaks that reliability class | Deploy/recovery process: manifest redelivery correctness on Kafka; free now (clean slate) | INFRA-TXY-C5-01 | S | Moderate · infra `[ops]` |
| 6 | 0·Config | Rename `KAFKA_GROUP_ID` default `atelier-backend → atelier-overseer` (code+compose+k8s) | Done | infra/overseer | Stale dissolved-monolith identity persists in live consumer-group config | Ops/observability process: consumer-group naming, lag dashboards; free now (no offsets) | INT-06 | S | Moderate · overseer+infra `[ops]` |
| 7 | 0·Config | SDK `gateway_url` default `50051 → 50443`; fix overseer README port | Done | sdk | SDK default points at the retired port; platform standardized on 50443, so defaults fail | Agent runtime/onboarding: a RemoteAgent using defaults can't reach the gateway | INT-03 | S | Contained · sdk |
| 8 | 0·Config | Remove legacy `/api/workers` + `AgentManager` bridge, orphaned `model-artifacts/` dir, wrong README engine labels | Done | overseer+lakehouse | Legacy command bridge duplicates the FSM scheduler and can diverge from spec lifecycle | Contributor/onboarding process; eliminates a second, drift-prone command path | INT-09/10/11/14/15 | S–M | Contained · overseer+lakehouse |
| 9 | 3·FSM | **Wire the durable Channel FSM** into the Gateway handshake (CH-T1/T2 ×5), drain (CH-T3/T4), recovery re-probe (IR-CHO4/CH-T10); enforce IR-CHO1/CHO3 gates → **[plan below](#implementation-plan--9-wire-the-durable-channel-fsm)** | Doing | gateway+overseer | Correct DB layer has zero callers; `channels` table stays empty at runtime (confirmed live) | Recovery/drain process + webapp channel view; **unblocks #10,#13,#14** and SEQ-4/5 | CH-* cluster | M–L | Wide · overseer+gateway `[runtime]` |
| 10 | 3·FSM | **RemoteAgent soft-restart + `restart_epoch`** — real in-place re-init, ack on re-init (A-T9), increment epoch on lineage | Todo | sdk | SDK never re-inits and hardcodes `restart_epoch=0`, breaking lineage continuity across restarts | Artifact lineage + webapp restart view; consumers can't distinguish pre/post-restart data | AGT-SR-211-5, INV-CH5, TASK-FSM-07 | L | Wide · sdk `[runtime]` |
| 11 | 3·FSM | **ManifestAck per-Task rejection** — parse `TaskAcceptance` → `reject_task`/T-T2 + B-T10 cascade | Todo | overseer+sdk | Self-rejection/PEER_REJECTED is dead code; agents can't reject a bad manifest | Deploy process: a skill/spec mismatch fails the binding cleanly instead of silently running | BIND-B-T10, TASK-FSM-02 | L | Wide · overseer+sdk (enables #15) |
| 12 | 3·FSM | ~~**Dispatch `AGENT_TERMINATE`** in the Delete path~~ → **Done** (live-verified; agent-scoped route deferred, SDK process-exit flagged) | Done | overseer | Delete marks the agent terminated but never sends the command; the process keeps running | Delete flow + webapp fleet: the agent actually exits and its card clears | live SEQ-2 gap | S–M | Moderate · overseer `[runtime][observer]` |
| 13 | 3·FSM | **IR-O5 active-Binding liveness reconciliation** — gateway check + 60s grace, process check, channel re-probe | Todo | overseer | Boot recovery doesn't verify live agents/channels, risking ghost active bindings after a crash | Crash-recovery process; webapp fleet reflects reality post-restart | O-IRO5-liveness | M | Moderate · overseer (needs #9) |
| 14 | 3·FSM | **Sink provisioning Idle→Ready** — call `set_sinks`, fire SK-T1/T2, emit `SinkReady`, gate B-T3 (INV-SK4) | Todo | overseer+sdk | Provisioning never runs; B-T3 activates with no Sink-Ready gate, so a bad sink isn't caught | Deploy process + webapp sink status; a broken ObjectSink should block activation | SK-* cluster | M | Moderate · overseer+sdk (needs #9) |
| 15 | 3·FSM | **Service SV-T5** (`manifest_rejected`/`dispatch_timeout`) + route PlatformAgent drain through SV-T6 `Stopping` | Todo | overseer | No reject reason exists; drain skips `Stopping`, leaving services stuck (observed 3 days live) | Service lifecycle + webapp service status; eliminates stuck `stopping` rows | SV-T5, IR-SVO2 | M | Contained · overseer (needs #11) |
| 16 | 3·FSM | **Agent graceful drain** (A-T5/T6/T7) + **INV-A6 `restart_budget_ms`** timer + **A-T17** registration-window reaper | Todo | overseer+sdk | PlatformAgent graceful drain and restart/registration timers missing; stuck agents never reaped | Drain + reconciliation process; webapp stops showing zombie Registered/Restarting agents | AGT-T5/INV-A6/A-T17 | M–L | Moderate · overseer+sdk |
| 17 | 3·FSM | **Overseer HTTP contracts** — Degraded→`200`+degraded-body, Draining→`503`+`Retry-After`; O-T4 emit `OverseerRecovered`; real probes | Todo | overseer | Degraded wrongly returns 503; O-T4 emits the wrong event; observers can't read true status | Webapp degradation banner + load-balancer health checks read the correct state | O-INV-O2/O4, O-T4 | M | Moderate · overseer `[observer]` |
| 18 | 3·FSM | **Session SN-T6 emergency-close trigger** (auth-revoke/REST hook) + SN-T7 child-Agent guard + `Created`/SN-T2 split | Todo | overseer | Force-close logic exists but has no trigger; can't kill a session on auth-revoke/compliance | Admin/compliance process; webapp can surface forced session termination | SN-T6/T7, SN-S1 | S–M | Contained · overseer |
| 19 | 3·FSM | **ComputeSlot INV-CS2** — seed slots with Pipeline-derived schemas + CS-T2 guard; route A-T10 vacate through CS-T3/T4 | Todo | overseer | Slots seeded with empty schemas; the compatibility guard is vacuous, so pipelines aren't type-checked | Deploy/Assign process; prevents a schema-incompatible task occupying a slot | CS-INV-CS2, CS-T34-BYPASS | M | Contained · overseer |
| 20 | 3·FSM | **Gateway lifecycle** — Degraded/Stopping/Stopped + SIGTERM graceful shutdown + events; **INV-GW4 routing table** (reject unknown binding + refresh); IR-GWA1 | Todo | gateway | No graceful shutdown and no routing table; unknown bindings fail silently (spec is minimal-depth) | Shutdown/routing process; webapp loses no events and bad routes get rejected | GW-S3/S4, INV-GW4, IR-GWA1 | L | Moderate · gateway (confirm beta scope first) |
| 21 | 2·Wire | **`skills` field** — adopt enum in catalog (code is ahead) or revert wire to string | Todo | proto | Registration.skills is typed enum in code but string in the catalog; the wire shape must be agreed | Wire contract across proto/sdk/overseer; skill decoding at registration | PROTO-TXY-02 | M / L | Moderate (enum) / Wide (string) `[wire]` (needs #2) |
| 22 | 2·Wire | **`SinkType` `Parquet → Object`** — sdk sink-config serde tag, webapp enum (proto already correct) | Todo | sdk+webapp | Webapp/SDK use a format name for the canonical storage-medium SinkType | Manifest authoring (TOML) + webapp sink labels; aligns the SinkType typology | WEBAPP-C5-01, SDK-C5 | M | Wide · sdk+webapp+overdex+infra `[wire]` |
| 23 | 2·Wire | **`Worker` wire tags** — overseer WS `worker_id`/`workers`/`worker_deleted`, REST `/api/workers` | Todo | overseer+webapp | Worker-as-Agent rename leaks onto the observer wire and REST surface (Class A) | Webapp dashboard wire + overseer REST; must regen together; pairs with #24 | OVS-C1-01/02 | L | Wide · overseer+webapp `[wire][observer]` |
| 24 | 4·Rename | **`Worker → Task/Agent` language layer** across sdk/overseer/webapp/overdex; `WorkerId→TaskId`; add ID newtypes in `atelier-types`+models | Todo | sdk (lead) | Pervasive `Worker` noun conflates Agent and Task; no ID newtypes where the spec mandates them | Whole codebase + webapp vocabulary; compile-time ID safety; biggest readability/correctness win | SDK-C1/C2, OVS-C1/C2, WEBAPP-C1-01, OVDX-C1-03 | XL | Wide · sdk+overseer+webapp+overdex `[wire]` (with #23) |

---

## Dependencies & critical path

```
#1–#4 Spec sweep ─┐  (kill phantom gaps; #3 gates W3 op-surface)
#5–#8 Config      │
                  ▼
       ┌──────────────────── #9 Channel wiring (highest leverage) ───────────────────┐
       │                    │                              │                          │
   #13 IR-O5            #14 Sink                    (#10 restart_epoch independent) (SEQ-4/5)
                                                          │
   #11 ManifestAck reject ─→ #15 SV-T5                    └─→ INV-CH5/INV-GW1 meaningful
                  │
   #12 terminate · #16 agent drain · #17 HTTP · #18 session · #19 slot · #20 gateway  (parallelizable)
                  ▼
   #2 ─→ #21 skills wire ──┐
   #22 SinkType wire       ├──→ #24 Worker rename + #23 wire tags  (one coordinated cut, LAST)
```

**Two anchors.** **#9 (Channel wiring)** is the highest-leverage single action — pure caller-wiring on an already-complete DB layer — and it unblocks #13 (IR-O5), #14 (Sink), and SEQ-4/5 recovery. **#24 (Worker rename)** is the largest and riskiest; defer to last and land it in one cut with #23, because `WorkerId` doubles as the wire `task_id`.

## Fix-spec vs fix-code (where the gap actually is)

- **Fix the spec, not the code (W1, ~25% of items by count, ~5% by effort):** #1, #2, #4 — and the *spec half* of #3. The code is intentionally ahead; updating `atelier-webdocs` is the cheapest way to shrink the gap and stop chasing phantom findings.
- **Fix the code (W0/W3):** #5–#20 — wire up dead code, implement missing transitions, correct observable behavior.
- **Two-sided cut (W2/W3):** #21–#24 — wire contract + coordinated cross-repo renames; spec and code move together in one tagged version cut.

## What is NOT a gap (verified)

The control-plane core is sound and **ahead of the prior 109-item backlog**: drain-to-completion (O-T6/O-T7/O-T8), the `INV-SV8` skill-mismatch orphan, A-T8/A-T9/A-T10/A-T18, E7 live skill validation, and the Session TTL lifecycle (SN-T3/T4/T5/T7) are all implemented. Schema (96%), proto (92%), wiring (82%) and the five-repo carve-out are clean — no FSM logic leaked into any non-owner repo. `atelier-overplex` (98%) and `atelier-lakehouse` (93%) are essentially compliant.

---

## Implementation-plan candidates (assessment)

Not every row warrants an expanded plan. A row is a **strong candidate** when it scores high on all four:

| Criterion | Question |
|---|---|
| **Leverage** | Does completing it unblock other rows? |
| **Boundedness** | Is the work concrete enough to enumerate steps now? |
| **Known detail** | Do we already have file:line anchors and a clear DoD? |
| **Risk** | Is it risky enough that a sequenced plan de-risks it? |

Scoring the high-priority rows:

| # | Leverage | Boundedness | Known detail | Risk | Verdict |
|---|---|---|---|---|---|
| **#9 Channel wiring** | **High** (unblocks #13,#14,SEQ-4/5) | **High** (DB layer complete — pure caller-wiring) | **High** (primitives, schema, gate sites all located) | Med (new runtime gates) | **★ Plan it (below)** |
| #10 restart_epoch | Med (INV-CH5/GW1 lineage) | Med (re-init loop is new design) | Med | High (cross-FSM) | Runner-up |
| #11 ManifestAck reject | Med (enables #15) | Med (needs SDK + overseer co-design) | Med | Med | Runner-up |
| #24 Worker rename | High (taxonomy) | Low (383 hits; needs a rename script + wire cut) | Med | High | Plan only **after** scope decisions (#2,#3) |
| #1–#8 | n/a | Trivially bounded | High | Low | Self-evident — no plan needed |

**Pick: #9.** It is the only row that is simultaneously high-leverage, fully bounded (the persistence layer already exists and is correct — this is wiring, not design), and rich in known anchors. Planning it also de-risks the new B-T3/T-T3 gates by sequencing observation before enforcement. #10 and #11 are the natural next plans once #9 lands (ask to expand them).

---

## Implementation plan — #9: Wire the durable Channel FSM

> **One-line:** the durable Channel lifecycle is correct, complete **dead code with zero callers** — wire the existing primitives into the Gateway handshake, the deploy gates, recovery, and drain. *No new persistence design; no migration.*

### Definition of Done (spec invariants that must go green)

- Every connected Binding has durable `channels` rows that reach `open`: CommandChannel + ManifestChannel(embedded) + TelemetryChannel + one ArtifactChannel per declared Sink (CH-T1 → CH-T2). **Live check:** `SELECT count(*) FROM channels WHERE binding_id=…` > 0 (today: **0**).
- **INV-CH1** (Open ⇒ handshake complete), **INV-CH2** (channel_id unique), **INV-CH6** (ManifestChannel embedded, exactly-once idempotency key) assert at their boundaries.
- **IR-CHO1** (B-T3 requires CommandChannel + TelemetryChannel Open) and **IR-CHO3** (T-T3 requires declared ArtifactChannels Open) enforced as guards.
- **IR-CHO4** (SEQ-4 recovery re-probes channels per reconciled Binding; dead transport → CH-T10 `failed` → B-T7 force-release).
- **SEQ-5 drain** walks Open → Draining → Closed (CH-T3 / CH-T4).
- Handshake timers wired → `CHANNEL_OPEN_FAILED` (61) on expiry.
- `channels.restart_epoch` written (=0 at open); the non-zero increment on A-T8 lands with **#10** (INV-CH5).

### What already exists (do not rebuild)

- **Schema (complete):** `atelier-lakehouse/overseer-db/migrations/20260604000001_i5_channels.sql` — 7 status values, `reliability_class` enum, `restart_epoch`/`sequence_high`, status↔timestamp CHECK, `channels_idempotency_key_uniq`, `channels_live_idx`, `channels_draining_idx`.
- **Primitives (zero callers):** `atelier-overseer/atelier-overseer/src/db/queries/channels.rs` — `create_channel`, `mark_channel_open`, `mark_channel_draining`, `mark_channel_closed`, `mark_channel_failed`, `list_live_channels_for_binding`, `list_draining_channels`. Model at `db/models.rs:293`.

### Reliability-class mapping (pass at `create_channel`, per `channel-beta.md §2.10.3`)

| Category | reliability_class | Note |
|---|---|---|
| command | `at_least_once_ack` | bidi CommandChannel |
| manifest | `exactly_once_idempotency` | embedded in CommandChannel; reserve `idempotency_key` (INV-CH6) |
| telemetry | `best_effort_sequence` | |
| data | `at_least_once_sequence_gap` | |
| artifact | `sink_class` | inherits the Sink's class — **couples to #14** |

### Seam decision (per §2.4.1)

The `channels` row is **overseer-persisted** (the gateway is stateless). So the Gateway should **signal** open/close via a `lifecycle.events` event and the overseer's `gateway_consumer` calls `create_channel`/`mark_channel_open` — exactly mirroring how `AgentRegistered` lands the `agents` row today. Do **not** have the gateway write Postgres directly.

### Phased steps

**Phase 1 — Open durable rows on connect (CH-T1 → CH-T2), observation only.**
1. In `atelier-gateway/src/channels/command.rs` (CommandChannel accept, ~`:49–52`/`:107`), after JWT auth + binding resolution, emit a `ChannelOpening`→`ChannelOpen` lifecycle signal for category `command`; overseer `gateway_consumer` calls `create_channel(...'opening')` then `mark_channel_open`. Emit the `ChannelOpen` Event (INV-P3).
2. Same for the embedded **ManifestChannel** (category `manifest`, reserve `idempotency_key` from the manifest).
3. Same for **TelemetryChannel** on the second stream.
4. **ArtifactChannel(s)** — one per declared Sink (category `artifact`, class `sink_class`), opened when the agent opens the artifact stream (SEQ-1 step 27).
   *Land Phase 1 first and verify rows appear with no behavior change — see Verification.*

**Phase 2 — Enforce the channel gates (IR-CHO1, IR-CHO3).**
5. Add a B-T3 guard: CommandChannel + TelemetryChannel rows are `open` for the binding before B-T3 fires (today it fires off A-T2 with no precondition — `seq1_deploy.rs:435–436`).
6. Add a T-T3 guard: all declared ArtifactChannels are `open` (atomic with the T-T3 persist).

**Phase 3 — Recovery re-probe (IR-CHO4 / SEQ-4 Stage 1).**
7. In `reconcile_on_boot` (overseer `services/overseer/mod.rs:960–1184`), for each reconciled Binding call `list_live_channels_for_binding`; dead transport → `mark_channel_failed` (CH-T10) + B-T7 force-release. *(Also satisfies #13's channel half.)*

**Phase 4 — Drain (SEQ-5 / CH-T3, CH-T4).**
8. In `start_drain`/`finish_drain`, for `draining` RemoteAgent bindings call `mark_channel_draining` (CH-T3); on settle `mark_channel_closed` (CH-T4). The gateway SIGTERM closure couples to **#20**.

**Phase 5 — Handshake timers.**
9. Add `gateway.handshake_timeout_ms` / `channel.open_budget_ms` (default 2000) to `atelier-gateway/src/config.rs:8–23`; bound the currently-unbounded Registration/handshake await; on expiry raise `CHANNEL_OPEN_FAILED` (61).

**Phase 6 — restart_epoch hook (coupled to #10).**
10. Write `restart_epoch=0` at create; leave the increment-on-A-T8 hook for #10 (do **not** reset `status`/`sequence_high` on restart — that is INV-CH5).

### Tests / verification

- `seq1_deploy.rs`: assert `channels` has command + telemetry + artifact rows `open` for the binding (today: zero).
- New `seq4_recovery.rs` case: kill transport → re-probe → `failed` + B-T7.
- §2.10.6 joint test (with #10): channel survives A-T8, sequence continues, `restart_epoch` increments.
- **Live:** re-run the SEQ-1 deploy from `../../v0.1-integration.md §2` and confirm `SELECT count(*) FROM channels WHERE binding_id=…` > 0 (was 0 with 3 live channels).

### Risk & sequencing

overseer + gateway, `[runtime]` — B-T3/T-T3 become gated on channel state, so **land Phase 1 (rows, observational) before Phase 2 (gates)** to avoid regressing deploy on a channel-open race. DB layer is unchanged (no migration). Phases 3–5 are independent and can land in any order after Phase 1.

---

## Execution log

**2026-06-16 — Batch #1–#8 (spec-first + config tier) landed.** 7 Done · 1 Spec✓.

- **#1 `schema-beta.md`** ✓ — marked `bindings.agent_id` nullable (BYO-infra note) and added `bindings.container_id`, `agents.prior_status`, `tasks.paused_at`, and `artifacts_emitted_at_idx` (each cites its impl migration). The Atlas DDL now matches the live `overseer-db`.
- **#2 `proto-catalog-beta.md`** ✓ — added the `TerminalEvent` message + `Envelope.payload` tag 32; recorded the `skills` enum-vs-string divergence (resolution tracked as #21); annotated dormant `TASK_CANCEL`.
- **#3 Run/Query** — **Spec✓** (code half pending). Added a Taxonomy-reconciliation note to `overseer-beta.md §1.4` (Run/Query are *not* System Operations — retained only as availability shorthand). Removing `SystemOperation::Run`/`Query` from `atelier-overseer` remains as the code half.
- **#4 `fsm-beta.md §2.4`** ✓ — annotated the deferred Experiment-FSM sketch as non-normative and superseded by C6 (overdex-owned, no Atlas FSM).
- **#5 `provision-kafka-topics.sh`** ✓ — `control.manifests` now created with `cleanup.policy=compact`; fixed the stale `reconfigure` comment + a path typo. `bash -n` clean.
- **#6 `KAFKA_GROUP_ID`** ✓ — default `atelier-backend → atelier-overseer` in `config.rs`, `docker-compose.beta.yml`, `atelier-k8s/overseer/deployment.yaml`, and the crate README. *(Out of scope, noted: the README per-topic group examples and `docs/m3-boot-manual.md` still say `atelier-backend` — stale historical docs.)*
- **#7 gateway port** ✓ — SDK `gateway_url` default `50051 → 50443` (`gateway.rs` ×3 + the `orchestrator.rs` defaults test) and the overseer root README. The overseer's own `GATEWAY_URL` default was already `50443`.
- **#8 hygiene** ✓ — fixed the two wrong lakehouse README engine labels (`overledger-db` = PostgreSQL; `overplex-db` = ClickHouse). **Correction to the finding:** `/api/workers` no longer exists in the overseer, and `AgentManager` is the **live PlatformAgent DockerSpawner** (wired into every integration test) — correctly **retained**, not removed. The orphaned `atelier-overseer/model-artifacts/` dir (13 stale `hawkes_fit_*.json`, ~750 KB) is **flagged for manual removal** — pre-existing data not created in this session; suggest `rm -rf atelier-overseer/model-artifacts` + a `.gitignore` entry.

**Verification:** all edits grep-confirmed; the provisioner passes `bash -n`. Rust edits are string-literal defaults only (no compile risk) — run `cargo check -p atelier-overseer` / `-p atelier-connect` at your convenience. No live stack required (Docker is wiped).

**2026-06-16 — #9 (Channel wiring) Phase 1 landed → `Doing`.** Pure caller-wiring; **no proto/wire change** (the `ChannelOpening`/`ChannelOpen` Event variants, tags 90/91, and their handler name-map already existed). Scoped via a 6-agent recon workflow.

- Wired the dead `channels.rs` primitives into `Scheduler::complete_bind` (`scheduler.rs`): on **first connect, after B-T3**, it now creates + opens durable rows for all **5 logical channels** (command/manifest/telemetry/data/artifact) — **CH-T1 → CH-T2** — and emits `ChannelOpening`/`ChannelOpen`. Best-effort (`match`, no `?`) so a channel-row failure cannot regress the deploy; placed **below the pending-only idempotency guard** so duplicate at-least-once `connected` events don't double-create; `manifest` uses a fresh `idempotency_key` (avoids the `channels_idempotency_key_uniq` collision).
- **Deliberately did NOT** create channels in `resume_drained_bind` (INV-CH5: gateway-persistent channels survive A-T8 and must not cycle) — marked with a comment; reconnect de-dup is Phase 3/4.
- Updated the B-T3 doc-comment in `transitions.rs` (was "Channel state is in-memory / deferred table").
- **Hardened over the drafted code:** the channel-spec array is **explicitly typed** (`[(&str,&str,&str,Option<Uuid>,Option<Uuid>); 5]`) so the all-`None` `sink_id` column can't break type inference.
- **Verification:** grep-confirmed (callers now exist; were zero). `cargo check`/Docker build green.
- **✓ VERIFIED LIVE (2026-06-16):** rebuilt from the branch, redeployed on a fresh DB, drove SEQ-1 → **exactly 5 `open` channel rows** (command/manifest/telemetry/data/artifact; reliability classes per §2.10.3; `idempotency_key` on `manifest` only; `row_version=2`) with the deploy reaching `active/bound/running` — **no regression**. Was 0 rows pre-#9. (#5 also verified live: `control.manifests` → `cleanup.policy=compact`.)
- **Remaining for #9 → Done (Phases 2–6):** the B-T3/T-T3 gates (IR-CHO1/CHO3), recovery re-probe (IR-CHO4), drain (CH-T3/T4), gateway timers, and per-Sink ArtifactChannel + real manifest idempotency key. **Wire-change note:** terminal Channel events (`ChannelDraining`/`Closed`/`Failed`) are **not yet in the proto** — broadcasting those in Phase 2+ needs a wire change (DB-only landing does not).

**2026-06-16 — #9 Phase 2 (IR-CHO1/CHO3 gates) landed & verified.** Reordered `complete_bind` so channel opens are now **fatal gates**, not observational: added an `open_channel` helper (create→CH-T1→open→CH-T2, `Err` on failure); command/manifest/telemetry open **before B-T3** (IR-CHO1), data/artifact **before T-T3** (IR-CHO3). A failed open now aborts the bind. No deadlock (overseer is the row authority); `resume_drained_bind` still skips reopen (INV-CH5). Docker build green.
- **✓ Happy path verified:** fresh SEQ-1 → `active/bound/running`, 5 `open` channels; timestamps confirm ordering — control `opened_at` < `bindings.active_at` (B-T3); data/artifact `opened_at` between B-T3 and `tasks.running_at` (T-T3).
- **✓ Fault path verified:** renamed the `channels` table to force `create_channel` to fail → the bind **aborted** (`bind=pending`, `svc=deploying`, never active; overseer logged `complete_bind failed … relation "channels" does not exist`), proving the gate is fatal. Table restored, prior channel rows intact.
- **Uncommitted:** the Phase 2 edits (`scheduler.rs` + `transitions.rs`) sit in the overseer `fix/txy-fsm-for-beta` working tree — verified-compiling (Docker) + verified-runtime; commit + `cargo check` when ready.

**Next:** after your `cargo check`, finish **#9** (Phases 3–6: IR-CHO4 recovery re-probe, drain CH-T3/T4, gateway timers, per-Sink ArtifactChannel — Phase 2+ terminal-channel-event broadcast needs the proto add) or start **#10** (restart_epoch). Both need a re-deployed stack only for final live verification.

**2026-06-16 — #9 Phase 3/4 (recovery/drain channel lifecycle) — partial; live test surfaced a refinement.**
- **✓ CH-T10 (force-release → `failed`) verified live:** killed an agent → lost-sweep force-released the binding (`agent_lost`, ~70s) → all 5 channels → `failed` (wired in `handle_agent_lost_inner`).
- **✓ CH-T3 (drain → `draining`) verified live:** `docker stop` overseer → SIGTERM drain (`O-T6`→`O-T8`) → binding `draining(platform_drain)` + all 5 channels → `draining` (via new `fan_binding_channels` in `start_drain`).
- **⚠ Resume gap found by the live drain→restart test:** `reconcile_on_boot`'s SEQ-4 boot-resume (`B-T11`, agent stayed bound) re-activates the binding but does NOT route through `resume_drained_bind`, so the close-old+open-fresh handling didn't fire → binding `active` with channels stuck `draining`. Deeper point: our drain does **not** close the agent transport (no overseer→gateway coordination), so the gRPC connection is intact across the bounce — the channels should resume **`draining → open`** (survive), not close-old+open-fresh. **Refinement needed:** add a `draining → open` primitive and apply it in BOTH resume paths (reconcile boot-resume + `resume_drained_bind`); reserve close-old+open-fresh for the genuine lost-reconnect (dead-transport) case. `finish_drain` CH-T4 also still deferred.
- **Net:** CH-T3 + CH-T10 solid & verified; the resume-channel handling is the open piece (a small design refinement, not just wiring).

**2026-06-16 — #9 channel lifecycle closed out: model-A resume + `finish_drain` CH-T4 + boot-resume fresh-open — all live-verified.**
- **✓ Model-A `draining → open` resume (the refinement above):** added `channels::mark_channel_resumed` (draining→open, status-guarded) + `Overseer::fan_binding_channels`; the `reconcile_on_boot` boot-resume now resumes a crash-mid-drain Binding's surviving Channels in place (transport intact across an Overseer-only bounce). Verified live (boot log `B-T11` + channels reopened).
- **✓ `finish_drain` CH-T4 (`draining → closed`):** new `Overseer::finish_drain_channels` settles the drained RemoteAgent's Channels — clean close (CH-T4) within `agent.reconnect_grace_ms`, else force-close (CH-T10/`failed`, final Artifact a known partial). DB-only (`finish_drain` emits no Events; process is exiting). Verified live: `docker stop` overseer → `SEQ-5 drain: settled RemoteAgent draining Channels ch_t4_closed=5 ch_t10_failed=0`; all 5 channels `closed` w/ `closed_at`, Binding preserved `draining(platform_drain)`.
- **✓ Boot-resume opens FRESH Channels from the clean-drain residue (your call — Option 1):** because CH-T4 leaves Channels terminal `closed`, `reconcile_on_boot` now opens a fresh standard set (extracted `Scheduler::open_standard_channels`, also reused by `resume_drained_bind`) when the resumed Binding has no live Channel; `restart_epoch` unchanged (Agent never disconnected → continuous lineage; only the durable Channel rows renew). Verified live across a full `open → drain (CH-T4 closed) → boot (fresh open)` loop, twice: `SEQ-4 boot-resume: opened fresh Channels … opened=5`, Binding `active/bound`, 5 fresh `open` + accumulating terminal `closed` audit trail.
- **✓ Quality gate (your Task 2):** `atelier-overseer` clippy **0** / check **0** / **182 tests** green; `atelier-sdk` clippy **0** / check **0** / tests green. Pre-existing mechanical lints (collapsible-if, assert-bool, redundant-closure) auto-fixed; the intentional non-trait `from_str` in sdk `config/workers` allow-annotated. New tests: `seq5_finish_drain_closes_remote_channels_ch_t4`, `…_force_closes_stale_channel_ch_t10`, `seq4_boot_resume_opens_fresh_channels_after_clean_drain`; the SEQ-1/2 `recv_event` + count-drain helpers made channel-event-aware (skip CH-T1/CH-T2).
- **Remaining for #9:** P5 gateway handshake timers (→#20), P6 `restart_epoch` hook (→#10), per-Sink ArtifactChannel + real manifest idempotency key. The channel lifecycle core (open / IR-CHO1·CHO3 gates / drain CH-T3·T4 / recovery CH-T10 + boot-resume) is complete & live-verified. All changes uncommitted on `fix/txy-fsm-for-beta`.

**2026-06-16 — #12 (dispatch `AGENT_TERMINATE` on Delete) landed & live-verified → `Done`.** Chosen as the post-#9 next action by a 6-reader code-grounded readiness sweep (scored 88; runner-up #14 at 80) — a real live bug, not spec-tidiness: a BYO RemoteAgent (no `container_id`, so the SEQ-2 docker teardown is skipped) was marked `terminated` while its process kept running, and the green suite hid it (`seq2_delete` asserted the event, never a `commands` row).
- **Phase 1 — resolvable:** added a `CommandKind::AgentTerminate` arm to `Scheduler::resolve_command_target` (`→ ("agent_terminate","agent",agent_id)`, Conflict if no Agent attached); the `AgentRestart`-only A-T8 hook is untouched so terminate does not trigger a restart.
- **Phase 2 — dispatch:** `complete_release` now calls `issue_command_by_binding(.., AgentTerminate)` BETWEEN the SV-T9/T10 service-stop and the A-T16 terminal write (Phase G ordering), best-effort (publish failure logged, not fatal — Binding already Released/Slot vacated). Runs for BOTH agent types; it is the BYO agent's ONLY stop path.
- **Phase 3 — regression guard:** `seq2_delete` now asserts an `agent_terminate` row (`target_kind='agent'`, `target_id=agent_id`, `dispatched_at` set, `status='pending'` — dispatch leaves pending until ack, there is no `'dispatched'` status). Note: the `commands` table is keyed by `(target_kind,target_id)`, not `binding_id`.
- **✓ Live-verified (beta stack):** `DELETE /api/agents/{id}` → Phase A `binding_release` (acked) → ack-driven Phase B → overseer `published command (typed) kind=agent_terminate` → `CommandAck acked`; the SDK agent container logged `dispatching command to all workers … command=Stop kind=AgentTerminate`; final state `agent=terminated / binding=released / service=stopped`. Quality gate: clippy **0**, **182 tests** green.
- **SDK process-exit — completed in-session (was Wave-3.4 TODO), live-verified.** The orchestrator mapped `AgentTerminate → workers Stop` but never exited the process, so the container lingered after Delete. Fix (`atelier-sdk/atelier-connect/src/remote_agent/orchestrator.rs`): on `AgentTerminate` (distinct from `BindingRelease`, which only stops workers) `break` the run loop into the existing teardown. That exposed a latent teardown deadlock — `reporter_handle.await` had no timeout and the reporter's cancel is the `shutdown` watch (owned by `main`), which the local `break` can't trigger; the SIGTERM path only survived via docker's SIGKILL backstop. Bounded the reporter join (2s grace → `abort`). **Live-verified (rebuilt agent image):** `DELETE /api/agents/{id}` → agent logged `AGENT_TERMINATE — workers stopped, exiting agent process` → `shutdown complete` → **exit 0**, container `Exited (0)`; FSM `terminated/released/stopped`. SDK suite 247 green, clippy 0.
- **Remaining nit (non-blocking):** the data worker doesn't end its task handle promptly on `Stop` — teardown waits out the 10s per-worker timeout, so terminate-to-exit is ~12s. Bounded and correct; a worker-Stop-promptness optimization is a separate follow-up.
- **Agent-scoped `DELETE` route** left unbuilt (binding_id Kafka key routes correctly under single-binding-per-agent). All changes uncommitted on `fix/txy-fsm-for-beta` (overseer + sdk + webdocs).

**2026-06-16 — branch consolidation → `fix/txy-fsm-for-beta`.** All txy-fsm work consolidated onto a dedicated branch of that name across 5 repos: `atelier-overseer` (off `fix/qa-findings-f1-f5` = the dissolution+FSM-E1–E7 foundation, **not** the archived `main` monolith — which still bundles `atelier-payments` and won't compile), `atelier-infra`, `atelier-sdk`, `atelier-lakehouse` (README only; overplex migrations left to you), and `atelier-webdocs` (this `notes/` tree, newly version-controlled). Local only — not pushed; no co-author trailers.

---

*Maintenance: this is the durable reconciliation index — update **Status**/**Owner** in place as items land (use `Done`/strike-through) and re-rank the remainder. Findings evidence lives in `../../v0.1-integration.md`; the normative yardstick is `fsm/` + `txy/`; this file is linked from [`INDEX.md`](INDEX.md). When #9 lands, expand #10 and #11 into sibling plan subsections.*
