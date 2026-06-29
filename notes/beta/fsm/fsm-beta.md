# Atelier Engine - State Machine Atlas v0.1-beta-2

Companion document to the **Taxonomy v0.1-beta-2** (see `../txy/txy-beta.md`). The taxonomy defines _what_ each entity is; this atlas defines _how_ each entity behaves over time - its states, transitions, guards, effects, and interactions with other state machines.

**Precedence.** Where a topic is covered by both documents, the FSM Atlas takes precedence over the Taxonomy for dynamic behavior (states, transitions, guards, effects, interaction rules); the Taxonomy takes precedence for static definitions (names, identifiers, scoping, ontology). A conflict resolved in one document must be reflected in the other within the same version. The Atlas spans this file and its sibling files (listed below); section numbers are preserved across files so that a reference like `§2.1` or `§1.4` resolves to the same content regardless of the file it lives in.

---

## File Index

The Atlas v0.1-beta-2 is organized one FSM per file. Section numbers stay stable across files - a reference like `§2.1` or `§2.10` resolves to the same content regardless of which file owns it.

| File | Contents |
|---|---|
| `fsm-beta.md` (this file) | Reading guide, notation, invariant testability convention, §2.4 FSMs scope status, §2.4.1 FSM Ownership Matrix, §3 Cross-FSM Sequences index |
| `overseer-beta.md` | §1 Overseer FSM - dependencies, states, transitions, Operation Availability Matrix, invariants, interaction rules, reconciliation protocol |
| `agent-beta.md` | §2.1 Agent FSM (incl. §2.1.5 RemoteAgent restart lineage resolution) |
| `task-beta.md` | §2.2 Task FSM |
| `binding-beta.md` | §2.3 Binding FSM |
| `service-beta.md` | §2.5 Service FSM |
| `session-beta.md` | §2.7 Session FSM |
| `compute-slot-beta.md` | §2.8 ComputeSlot FSM |
| `gateway-beta.md` | §2.9 Gateway FSM (minimal) |
| `channel-beta.md` | §2.10 Channel provisioning contract (minimal) |
| `sink-beta.md` | §2.11 Sink provisioning contract (minimal) |
| `feed-beta.md` | §2.12 Feed FSM (data-plane Ingest subscription; Agent-owned) |
| `book-beta.md` | §2.13 Book families — OrderBook / TradeBook core + Sourced specialization (Synthetic reserved) |
| `schema-beta.md` | Postgres persistence schema (DDL for ten tables, incl. lineage-only `artifacts` promoted in v0.1-beta-2) |
| `proto-catalog-beta.md` | Wire-format SSoT: Envelope, control, telemetry, data, events, services |
| `errors-beta.md` | Semantic catalog for the `ErrorKind` enum |
| `timeouts-beta.md` | Catalog of time-bounded decision points and tunables |
| `sequences-beta.md` | Cross-FSM interaction sequences (SEQ-1 Deploy, SEQ-2 Delete, SEQ-4 Crash Recovery, SEQ-5 Platform Drain specified; SEQ-3 folded into SEQ-4) |
| `overledger-beta.md` | **Account layer (§A), out of the core Atlas** — the `atelier-overledger` Token economy: Ledger (§A.1), Checkout (§A.2), Plan (§A.3), Entitlement (§A.4) FSMs + Metering (§A.5). Persists in `overledger-db`, not `schema-beta.md`; couples to the core only via `SN-T1` envelope resolution, the existing `SN-T6` `plan_revoked` trigger, and Event subscription. Companion to the Taxonomy ACCOUNT LAYER section. |

---

## Reading This Document

Each FSM specification follows a consistent structure:

- **States** - The complete, finite set of states the entity can occupy. Every entity is in exactly one state at any time.
- **Transitions** - Directed edges between states. Each transition specifies:
  - **Trigger** - What causes the transition (an event, a command, a timeout, or an internal condition).
  - **Guard** - A boolean precondition that must be true for the transition to fire. If the guard fails, the trigger is rejected and the entity remains in its current state.
  - **Effects** - Side effects produced when the transition fires: DB writes, events emitted, state changes on other FSMs.
- **Invariants** - Properties that must hold in every reachable state. Invariants are the specification's test suite: if an invariant is violated, the system has a bug.
- **Interaction Rules** - How this FSM constrains or is constrained by other FSMs.

### Notation

State diagrams use ASCII. Transitions are labeled as `trigger [guard] / effect`. Guards are in square brackets; effects follow the slash. If a transition has no guard, the brackets are omitted. If it has no effect beyond the state change itself, the slash is omitted.

### Invariant testability

Every invariant declared in the Atlas (e.g., `INV-A1`, `INV-SV2`, `INV-CH5`) carries an implicit **testability contract**: the invariant MUST name a specific boundary - almost always a transition - at which the assertion can fire in test. The convention:

- **Anchoring.** Each invariant is anchored to one or more of: (a) a transition's Guard (checked before the transition fires), (b) a transition's post-condition (checked after Effects land), or (c) a state-entry predicate (checked every time the state is entered).
- **Naming.** Invariant IDs use the prefix of the subject FSM: `INV-A*` for Agent, `INV-SV*` for Service, `INV-SN*` for Session, `INV-CS*` for ComputeSlot, `INV-GW*` for Gateway, `INV-CH*` for Channel, `INV-SK*` for Sink, `INV-B*` for Binding, `INV-T*` for Task, `INV-O*` for Overseer, `INV-F*` for Feed, `INV-BK*` for the OrderBook/TradeBook families. Cross-tier invariants use the FSM that *enforces* the check.
- **Test form.** An integration test for invariant `INV-X` drives the system to the boundary named in the invariant's body and asserts the condition. Property-testable invariants (e.g., "sequence monotone within a Channel") get a randomized driver; point-testable invariants (e.g., "channel_id unique") get a specific trigger.
- **Listing.** An invariant body ends with an italicized *Testability:* line naming the boundary. If the boundary is obvious from the invariant statement itself, the line may be omitted - but never silently. Omission means "implicit at the only transition that writes this field."
- **Governance.** An invariant declared without a reachable boundary is a bug in the spec, not a contract. Reviewers reject invariants they cannot anchor.

Why this matters: invariants are the spec's test suite. If every invariant has a named boundary, generating an assertion harness is mechanical; missed invariants become visible gaps rather than invisible ones.

**Example.**

> **INV-CH2: Channel ID uniqueness.** `channel_id` is unique within a deployment for the lifetime of the Channel row. It is allocated at CH-T1.
> *Testability:* assert at CH-T1 post-condition that the channels-row insert succeeds without a primary-key collision; property test drives concurrent CH-T1 with 1000 parallel `channel_id` allocations.

---

### 2.4 FSMs - scope status (v0.1-beta-2)

The Atlas v0.1-beta-2 specifies the FSMs required to close SEQ-1 Deploy. Specified FSMs live in the file listed in the File Index; deferred FSMs are enumerated here with a note on when they are expected.

**Specified in v0.1-beta-2**

| FSM | File | Depth |
|---|---|---|
| Overseer | `overseer-beta.md` §1 | full |
| Agent | `agent-beta.md` §2.1 | full (incl. §2.1.5 RemoteAgent restart lineage; A-T16 Ready -> Terminated on AGENT_TERMINATE added for SEQ-2) |
| Task | `task-beta.md` §2.2 | full |
| Binding | `binding-beta.md` §2.3 | full |
| Service | `service-beta.md` §2.5 | full |
| Session | `session-beta.md` §2.7 | full |
| ComputeSlot | `compute-slot-beta.md` §2.8 | full |
| Gateway | `gateway-beta.md` §2.9 | minimal (enough to back INV-GW1 / §2.1.5) |
| Channel | `channel-beta.md` §2.10 | provisioning contract only |
| Sink | `sink-beta.md` §2.11 | provisioning contract only |
| Feed | `feed-beta.md` §2.12 | full (data-plane; Agent-owned) |
| OrderBook / TradeBook | `book-beta.md` §2.13 | core + Sourced specialization (Synthetic reserved) |

**Deferred**

- **2.6 Experiment FSM** - States: Provisioning, Running, Producing, Completing, Completed, Failed, Archived. Same shape as Service but with bounded lifecycle. Deferred because the beta scope cut is "Service only". No file yet. **Reconciliation (txy-fsm-code #4):** this "same shape as Service" sketch is a *non-normative* historical note — it is superseded by the Taxonomy, under which Experiments are **overdex-owned research runs with NO Atlas FSM** (`run -> completed | failed`, persisted in `overdex-db`; taxonomy C6). If a beta-3 Experiment surface lands it must remain overdex-owned and **must not** be a Pipeline activation (creates no Binding/Task/ComputeSlot/Manifest, runs no Agent).
- **Channel full lifecycle (§2.10)** - Draining, Closed, Failed are specified (for SEQ-4/SEQ-5) with durable rows in `schema-beta.md` table 12 (`channels`). Backpressured and Error remain enumerated for cross-reference, not fully specified.
- **Sink full lifecycle (§2.11)** - states Streaming, Writing, Backpressured, Error, Closed are enumerated in `sink-beta.md §2.11` for cross-reference but not fully specified.

---

### 2.4.1 FSM Ownership Matrix

Companion to §2.4. §2.4 declares *which* FSMs exist and at what depth; §2.4.1 declares *who owns* each FSM - which repo executes transitions, persists authoritative state, emits Events, and enforces invariants. Numbered §2.4.1 (not §2.5) because §2.5 is Service FSM (`service-beta.md`) under the Atlas's stable cross-file section IDs - this is the §2.4.x pattern the root `CLAUDE.md` house convention names when §2.4 is taken. Subordinate to the precedence rule (root `CLAUDE.md`, `../txy/txy-beta.md`): Atlas wins on dynamics, Taxonomy wins on static definition; this section clarifies the reach of "wins on dynamics" across repos.

#### What ownership means

An FSM in the Atlas has one or more **owners**. An owner of an FSM, for each instance it hosts, is the process that:

1. Executes transitions (applies `X-T*` logic - guards, effects).
2. Persists authoritative state (a row in the table named by `schema-beta.md`, or authoritative in-memory state backed by persistence).
3. Emits the corresponding `Event` variants on the wire per **INV-P3** (`proto-catalog-beta.md`).
4. Enforces the FSM's invariants (`INV-X*`).

A **non-owner** repo may carry the FSM's identifier (e.g., `BindingId`), be addressed by Commands that target that identifier, or reference the state in UI/logging, but it does not execute transitions or emit Events for that FSM.

An **observer** is a process that subscribes to Event Broadcast (`proto-catalog-beta.md §services.proto` `Gateway.EventSubscribe`) and renders state. Observers never own FSMs; they never persist or emit Events.

#### Ownership kinds

Three shapes appear in v0.1-beta-2:

- **Sole ownership.** One process owns every instance of the FSM. Used for platform-wide orchestration.
- **Co-ownership by AgentType.** The FSM runs wherever its Agent process runs. RemoteAgent instances live in `atelier-sdk`; PlatformAgent instances live in-process with the Overseer in `atelier-overseer/atelier-overseer` (per `overseer-beta.md §1.4` key decision #2: PlatformAgents use an in-process CommandChannel). Agent (§2.1) and Task (§2.2) use this shape.
- **Seam co-ownership.** The FSM has two endpoints on a transport, each tracking its own lifecycle and coordinating via wire protocol. Channel (§2.10) uses this shape. Sink (§2.11) is a variant: co-owned by `SinkType` rather than by seam, because the Writer process depends on the sink's medium and placement.

#### The matrix

| FSM | § | Ownership | Owner repo(s) - process | Persistence (per `schema-beta.md`) |
|---|---|---|---|---|
| **Overseer** | §1 | sole | `atelier-overseer/atelier-overseer` | in-memory + §1.7 reconciliation over `{sessions, services, bindings, tasks, agents, commands}` |
| **Session** | §2.7 | sole | `atelier-overseer/atelier-overseer` | `sessions` |
| **Service** | §2.5 | sole | `atelier-overseer/atelier-overseer` | `services` |
| **Binding** | §2.3 | sole | `atelier-overseer/atelier-overseer` | `bindings` (IR-O3: Overseer is sole creator/destroyer) |
| **ComputeSlot** | §2.8 | sole | `atelier-overseer/atelier-overseer` | `compute_slots` |
| **Gateway** | §2.9 | sole | `atelier-overseer/atelier-gateway` | in-memory (stateless by design; see `overseer-beta.md §1.1.1`) |
| **Agent** | §2.1 | co-by-AgentType | RemoteAgent -> `atelier-sdk`; PlatformAgent -> `atelier-overseer/atelier-overseer` | `agents` (platform-authoritative mirror of both) |
| **Task** | §2.2 | co-by-AgentType | RemoteAgent tasks -> `atelier-sdk`; PlatformAgent tasks -> `atelier-overseer/atelier-overseer` | `tasks` (platform-authoritative mirror of both) |
| **Channel** | §2.10 | co-by-seam | platform end -> `atelier-overseer/atelier-gateway`; Agent end -> `atelier-sdk` (RemoteAgent) or `atelier-overseer/atelier-overseer` (PlatformAgent) | `channels` durable (`schema-beta.md` table 12); Overseer owns row state, transport co-located at each seam |
| **Sink** | §2.11 | co-by-SinkType | ObjectSink -> producer-local (sdk or overseer); DBSink -> `atelier-overseer`; TerminalSink -> `atelier-overseer` for SK-T1/SK-T2 handshake, `atelier-webapp` for rendering | deferred; `workspaces.sinks` JSONB authoritative in v0.1-beta-2 |
| **Feed** | §2.12 | sole (Agent) | RemoteAgent -> `atelier-sdk` | none — lineage-only; telemetry-observed, no durable row (INV-F7) |
| **OrderBook / TradeBook** | §2.13 | foundational | Sourced specialization runs Agent-side (Sync Skill) -> `atelier-sdk`; Synthetic specialization reserved (P2) | none — lineage-free (INV-BK6) |

**Pure language:** `atelier-proto` - defines the wire contract between owners and between owners and observers. Owns no FSMs.

**Pure observer:** `atelier-webapp` - subscribes to Event Broadcast; renders; never persists; never executes transitions.

**Pure infrastructure:** `atelier-infra` - deployment, topic provisioning, observability. Owns no FSMs.

**Account layer (out of the core Atlas):** `atelier-overledger` - owns the Token economy (Ledger / Checkout / Plan / Entitlement FSMs, §A in `overledger-beta.md`) and persists it in `overledger-db`, not the `schema-beta.md` core schema. It owns **no core FSM**: it does not execute any `§1`/`§2.x` transition, and no core transition gains a billing Effect. It couples to the core only as a (a) **reader** at `SN-T1` (the "identity's plan/quota policy" the Session envelope resolves from is the account-layer Plan, §A.3 / `session-beta.md` §2.7.5), (b) **driver of the existing** `SN-T6` administrative trigger `expire_reason=plan_revoked` on entitlement suspension where policy mandates termination, and (c) **observer** that subscribes to orchestration Events (e.g., `BindingActive`/`BindingReleased`) to meter usage. The account-layer `INV-LG*`/`INV-CK*`/`INV-PL*`/`INV-ENT*`/`INV-MET*` prefixes are declared in `overledger-beta.md` and are deliberately absent from the core invariant legend.

#### Cross-ownership tie-breakers

Co-owned FSMs require a tie-breaker when owners' views diverge:

- **Agent FSM (co-by-AgentType).** The local Agent process is authoritative between heartbeats. The `agents` row is authoritative for platform queries and for `overseer-beta.md §1.7` reconciliation. On rebinding after A-T14 `Lost -> {Ready, Bound, Draining, Restarting}`, the Overseer reconciles its `agents.status` against the reconnecting Agent's self-reported phase, using `restart_epoch` per §2.1.5 to disambiguate lineage.
- **Task FSM (co-by-AgentType).** Same shape as Agent. Local Agent owns in-flight Task state; Overseer's `tasks` row is authoritative for platform queries. T-T12 (Task `Restarting` on Agent restart per IR-AT1/IR-AT2) is the coordination hand-off; post-restart Task state is re-emitted from the Agent's authoritative copy.
- **Channel FSM (co-by-seam).** Each end owns CH-T1 / CH-T2 for its own side. Transport closure at one end is observed as connection loss at the other; neither persists the peer's state. No shared persistence in v0.1-beta-2.
- **Sink FSM (co-by-SinkType).** Each Sink instance has exactly one Writer owner determined by SinkType + placement. The handshake owner (SK-T1, SK-T2) is the Writer's process. TerminalSink is the subtle case: the backend owns the provisioning handshake (it tracks whether a webapp client is subscribed), the webapp owns rendering.

#### Observer contract

Observers (today: `atelier-webapp`; tomorrow: any secondary dashboard, CLI, or exporter):

- Subscribe via `Gateway.EventSubscribe { session_id, transition_ids[] }` (`proto-catalog-beta.md §services.proto`).
- Receive `Envelope { payload: Event { body: ... } }` streams, Session-scoped per **INV-P6** (`proto-catalog-beta.md §Invariants`).
- Render state; never emit Events; never execute transitions; never persist state that shadows the owner.

Observer-local UI state (selected entity, open modal, form draft) is not an Atelier FSM and has no `X-T*` numbering.

#### Interaction with the precedence rule

This matrix is subordinate to the existing precedence rules and clarifies their reach:

- **FSM Atlas wins on dynamics** -> for each dynamic conflict, the *owner* of the FSM decides.
- **Taxonomy wins on static definition** -> name / identifier / scope conventions apply across *all repos*, owner or not.

Observers always defer to owner emissions: when a webapp-rendered state disagrees with the persisted or emitted state, the owner is right by construction and the observer should re-subscribe (or request the current `agent_status` / `task_telemetry` snapshot).

#### Use as a review lens

A **real FSM gap** against a repo exists only when the repo owns (or co-owns) the FSM. Non-owner absence is not a gap; it's expected. Apply this lens when reviewing any single repo's FSM coverage - the repo is only on the hook for the FSMs whose ownership cell names it.

#### Source citations

- `fsm-beta.md §2.4` FSMs scope status
- `overseer-beta.md §1.1.1` Composition (logical vs physical); §1.4 Operation Availability Matrix; key decision #2; IR-O3; IR-O6
- `agent-beta.md §2.1.2 A-T1` (Gateway-allocated AgentId); §2.1.5 RemoteAgent restart lineage; A-T8..A-T14; IR-AT1; IR-AT2
- `binding-beta.md §2.3.2 B-T1` (Overseer-allocated BindingId)
- `task-beta.md §2.2` T-T12 restart participation
- `proto-catalog-beta.md §services.proto` `Gateway.EventSubscribe`; §Invariants INV-P3, INV-P6
- Precedence rule (root `CLAUDE.md`)
- `schema-beta.md` table 6 `agents`, table 8 `bindings`, table 9 `tasks`, table 11 `commands`, table 12 `channels`; deferred `sinks`

---

## 3. Cross-FSM Interaction Sequences

These sequences show how multiple FSMs coordinate during key operations. Each sequence traces the state transitions across all participating FSMs.

**SEQ-1: Deploy** - specified in `sequences-beta.md §3.1`. Overseer + Session + Service + Binding + (Agent + Task + ComputeSlot after connection). Closes use-case steps 1-5.
**SEQ-2: Delete** - specified in `sequences-beta.md §3.2`. Overseer + Agent + Task + Binding + ComputeSlot + Service (+ Channel / Sink teardown as transport-layer cleanup). Closes use-case step 6. Introduces `agent-beta.md` A-T16 (Ready -> Terminated on AGENT_TERMINATE).
**SEQ-3: Agent Disconnect (unexpected)** - folded into SEQ-4 Stage 2 (`sequences-beta.md §3.4.6`); the live-ticker analog of heartbeat-miss -> A-T11 Lost -> grace -> A-T14/A-T15. Not given its own section.
**SEQ-4: Overseer Crash Recovery** - specified (`sequences-beta.md §3.4`). Backed by the durable `channels` table (`schema-beta.md` table 12) so INV-CH5/INV-CH7 survive restart; the cross-FSM choreography of `overseer-beta.md §1.7`.
**SEQ-5: Graceful Shutdown (Platform Drain)** - specified (`sequences-beta.md §3.5`). Uses SEQ-4's durable Channel state plus the named `agent.reconnect_grace_ms` tunable. Closes use-case step 7; composes with SEQ-4 for the researcher-side resume.
