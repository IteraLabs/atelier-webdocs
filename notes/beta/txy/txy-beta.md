# Atelier Engine — Taxonomy & Review (txy-beta) v0.1-beta-2

Single source of truth for the Atelier Engine's static vocabulary **and** the method used to keep that vocabulary consistent across the platform. This document produces no output of its own — it **is** the reference that every other surface defers to. It is durable: terms and method change slowly and deliberately; concrete, dated audit results do not live here.

It answers two questions, and is organized in two parts accordingly:

- **What is X?** — **Part I**, the normative term ontology: names, identifiers, scopes, typologies, and the operation surface.
- **How do I check that repo R speaks X correctly?** — **Part II**, the operational review method: the canonical-surface index, the seven checks, the violation taxonomy, and the reconciliation passes.

**Reach.** Every repo across the Atelier Platform that names an entity defers to this document — `atelier-proto`, `atelier-sdk`, `atelier-overseer` (overseer + gateway crates), `atelier-overdex`, `atelier-overplex`, `atelier-overledger`, `atelier-webapp`, `atelier-infra`, and any future consumer. Taxonomy drift in any one repo radiates to all of them: a Skill renamed in the wire contract breaks the SDK, the overseer, and the webapp simultaneously. The taxonomy is the shared contract that prevents that. A repo "not on the hook" for any FSM is still on the hook for every taxonomy surface it touches.

**Precedence (load-bearing).** Where this taxonomy and the FSM Atlas overlap: **the Taxonomy wins on static definition** — names, identifiers, scoping and nesting, ontology, term-composition rules, the operation surface, and the canonical typology. **The Atlas wins on dynamic behavior** — states, transitions, guards, effects, invariants, wire encoding, persistence, error semantics, and timeouts. A conflict must be resolved on both sides within the same version cut.

## How this document is organized

- **Part I — Definitions.** WHO / WHAT / WHERE / HOW / OBJECTS / DESTINATIONS / ACTIVATION / EXPERIMENTS / COLOCATION / STRUCTURAL / IDENTIFIERS / ACCOUNT LAYER. The normative ontology; the answer to "what is X".
- **Part II — Review & Governance.** The canonical surface (an index of Part I), the seven checks (C1–C7), the violation taxonomy (Classes A–H), the per-repo surface map, and the three reconciliation passes. The procedure that keeps every repo conformant to Part I.
- **Findings live elsewhere.** This reference is durable. Concrete, dated, per-repo audit results are recorded in `reports/`, not here — so the method ages well and the findings layer can churn independently.

---

# Part I — Definitions (What is X?)

## Naming Conventions

Three orthogonal axes compose every entity term in the system:

- **Location prefix** — `Remote` (client-side, user infrastructure) or `Platform` (server-side, IteraLabs infrastructure).
- **Type suffix** — `Agent` (entity that executes Tasks), `Workspace` (scoped execution environment), `ComputeSlot` (pipeline position occupied by a Task), `Channel` (typed communication path), `Sink` (artifact destination), `Task` (declarative work unit), `Skill` (composable capability trait).
- **Composition** — any prefix + any suffix produces a self-describing term. The name is the definition.

System Processes (**Gateway**, **Overseer**) do not follow the prefix + suffix convention. They are platform infrastructure that exists outside the Agent model — they hold no Skills, execute no Tasks, and occupy no ComputeSlots. They are named by function. Do not retrofit them into the Agent model.

---

## WHO — Agents

- **Agent** — Any entity that holds identity, possesses Skills, and executes Tasks within a Pipeline. Agents are the units of execution. An Agent is generic over its Skills — specialization comes from the Tasks it receives, not from its type. All Agents share the same lifecycle: Register → Bind → Assign → Execute. Identified by an **Agent ID**.

- **RemoteAgent** — An Agent deployed on the client's infrastructure (Remote Domain). Connects outbound to the platform through the Gateway. Bound to a RemoteWorkspace. Executes Tasks at RemoteComputeSlots. The client controls the runtime environment; the platform controls the Task specification.

- **PlatformAgent** — An Agent deployed on IteraLabs infrastructure (Platform Domain). Spawned and managed by the Overseer. Bound to a PlatformWorkspace. Executes Tasks at PlatformComputeSlots. The platform controls both the runtime environment and the Task specification.

RemoteAgent and PlatformAgent are structurally identical: same interface (Skills + Tasks), same lifecycle (Register → Bind → Assign → Execute), same Commands, same Channels. The only difference is **where** they run and **how** they connect. A RemoteAgent connects through the Gateway; a PlatformAgent is spawned directly within the Platform Domain by the Overseer. If you know how one works, you know how the other works — with one documented exception during Drain (see WHAT — Operations → Drain).

---

## WHO — System Processes

System Processes are foundational platform processes that enable Agent execution but are not Agents. They hold no Skills, execute no Tasks, and occupy no ComputeSlots. They exist at the infrastructure level — the same conceptual depth as the Domain boundaries themselves.

- **Gateway** — A boundary process at the trust boundary between the Remote Domain and the Platform Domain. Authenticates RemoteAgents, bridges protocols, enforces validation, and routes Channels. Stateless with respect to data content; holds connection state only. Identified by a **Gateway ID** — multiple Gateways may exist with different types or capacity.

- **Overseer** — The orchestration process that manages the lifecycle of all other entities in the system. The Overseer is to Services, Bindings, and Tasks what the Gateway is to Channels — it makes them possible but does not participate in the data flow. Responsibilities:

  - **Session management** — creates and enforces resource envelopes (concurrent Agents, Pipelines, throughput limits).
  - **Service lifecycle** — creates, monitors, and tears down Services.
  - **Manifest dispatch** — composes and dispatches Manifests through the ManifestChannel.
  - **Binding and Assignment** — creates Bindings (Agent → Workspace), validates Skill sets, and Assigns Tasks to ComputeSlots.
  - **Skill validation** — on Registration, validates the Agent's declared Skill set against pending Tasks.
  - **Command routing** — issues Commands to Agents and Tasks, receives Acknowledgments.
  - **PlatformAgent spawning** — creates and manages PlatformAgent instances within the Platform Domain.
  - **Resource enforcement** — monitors Session limits, billing boundaries, and operational health.
  - **System health management** — monitors its own infrastructure dependencies, advertises current operational capability, and rejects operations whose infrastructure requirements are not met (see WHAT — System Health).
  - **Recovery** — on startup, reconciles in-flight state from persistent storage before accepting new operations (see WHAT — Recovery).
  - **Drain coordination** — on shutdown, orchestrates a graceful wind-down of all managed entities before stopping (see WHAT — Operations → Drain).

  The Overseer does not process data — it does not Ingest, Transform, or Emit. It observes, decides, and acts on the lifecycle of every other entity. Identified by an **Overseer ID** — in practice a single logical Overseer exists per platform deployment, though it may be internally distributed.

The Gateway and the Overseer are complementary: the Gateway controls **what crosses the boundary** between Domains; the Overseer controls **what happens within** the system across both Domains. Together they form the system's control surface, and they operate independently — the Gateway can accept and hold RemoteAgent connections while the Overseer is still initializing or recovering. Registration is a synchronous exchange between the Agent and the Overseer: the Gateway forwards the Registration message on the CommandChannel's bidirectional stream, and the Overseer validates and responds on the same stream before the Agent proceeds. The Gateway does not cache, queue, or independently act on Registrations.

---

## WHO — Personas

Personas are the humans driving the platform. They are distinct from Agents (Personas execute no Tasks, hold no Skills, occupy no ComputeSlots) and from System Processes (Personas hold no Gateway/Overseer identity). Three terms name the same human viewed from different aspects; using them interchangeably is a spec drift, not a synonym choice.

- **Researcher** — the *persona* (who they are). The quant or ML researcher the platform is built for. Appears in product positioning, marketing surfaces, and use-case narratives. Never appears in FSM transition prose.
- **Operator** — the *role at an action point* (what they do here). The Researcher acting on the platform — submitting a Deploy, clicking Pause/Delete, triggering a Command. Appears in FSM specs where precision about who-initiates matters (sequence swimlane labels, transition effects, Binding release-reason rationale). Equivalent to "Researcher as actor".
- **User** — the *auth/identity record* (their persisted account). The Researcher's identity row in the platform's authentication system. Appears in DB schema (the `users` table, `sessions.identity_id` aliasing) and authentication code (JWT subject claims). Never appears in FSM transition prose or product copy.

Pick the term whose scope matches the surface being written: **Researcher (who) → Operator (what they do at this transition) → User (their auth artifact)**.

---

## WHO — MCP Control Layer

- **MCP (Model Context Protocol) layer** — A first-class **agent-control surface**: a programmatic "UI for coding agents" (e.g., an LLM coding assistant) that drives the platform the way the webapp drives it for a human Operator. The machine-facing peer of the webapp dashboard.
- **What it fronts.** The MCP layer exposes the **public** surfaces of the platform components — `atelier-sdk`, `atelier-overplex`, `atelier-overdex`, `atelier-overledger`, `atelier-overseer`, `atelier-proto`, `atelier-webdocs` — as callable tools. It invents no new operations: each tool maps onto an existing taxonomy Operation or a read of a documented surface.
- **Tool inventory → mapping.** `deploy_data_agent` → Deploy; `run_experiment` → an overdex Experiment run (see EXPERIMENTS); `send_service_command` → Command; `stop_agent` → Delete; `list_services` / `get_service_status` / `list_experiments` → reads of Service / Experiment state; `query_colocation` → a read of the Colocation oracle (see COLOCATION). Reads are **not** a separate operation category — there is no "Query" System Operation; a read is a query against an existing surface.

---

## WHAT — Skills & Tasks

### Skills

A **Skill** is a composable capability trait that an Agent possesses. Skills define what an Agent *can* do. An Agent's Skill set is declared at Registration and is immutable for the lifetime of that registration. Skills are analogous to Rust traits: they define an interface contract, not an implementation. The same Skill (e.g., Ingest) may be implemented differently by different Agents.

Skills map to Operations. The first four map to Data Operations; Report maps to the TelemetryChannel (a System Channel) rather than to a Data Operation. The base Skills (the closed set of five) are:

- **Ingest** — Connect to an external source (WSS, REST) and produce a raw data stream. Continuous and stateful: the Agent maintains the connection, handles reconnection, and sequences events.
- **Sync** — Synchronize one or more ingested data streams to a clock, producing periodic snapshots at a configured interval. Stateful: the Agent maintains a clock, aligns incoming events to it, and emits a consolidated snapshot each tick. Sync consumes the output of Ingest and produces time-aligned data for Emit or Transform. Without Sync, ingested data flows through as raw, unaligned events.
- **Transform** — Apply computation to data within a ComputeSlot. The only Skill that changes data content (as opposed to location or metadata). *Wire-reserved in v0.1-beta-2: the `TRANSFORM` enum member exists but no Agent implements it yet.*
- **Emit** — Materialize an Artifact and deliver it to a Sink through an ArtifactChannel. Every Emitted Artifact is tagged with a Service ID, a Task ID, and an Artifact ID.
- **Report** — Produce telemetry: status, metrics, health signals, and operational logs. Streamed through the TelemetryChannel.

Skills compose freely. A RemoteAgent streaming raw trades possesses `{Ingest, Emit, Report}`. A RemoteAgent producing synchronized orderbook snapshots at 100ms possesses `{Ingest, Sync, Emit, Report}`. A PlatformAgent performing data normalization possesses `{Transform, Emit, Report}`. A full-stack Agent could possess all five. The Skill set is the same regardless of whether the Agent is Remote or Platform — location does not constrain Skills.

### Tasks

A **Task** is a declarative work unit that occupies a ComputeSlot and declares the Skills it requires. Tasks are the unit of work in the system. An Agent executes a Task only if its Skill set is a superset of the Task's required Skills. Identified by a **Task ID**.

A Task specifies:
- **Required Skills** — the set of Skills needed to execute it (e.g., `{Ingest, Emit}`).
- **TaskSpec** — the parameters of the work: source configuration, processing rules, Sink assignments, datatype subscriptions, and any domain-specific settings.
- **ComputeSlot** — the positional slot in a Pipeline where the Task executes (see WHERE — Scopes → ComputeSlot).

A single Agent can execute multiple Tasks concurrently, each at a different ComputeSlot, provided all ComputeSlots are in the same Domain as the Agent. A RemoteAgent can only execute Tasks at RemoteComputeSlots; a PlatformAgent only at PlatformComputeSlots. An Agent holds exactly one Binding (one Workspace) at a time — multiple concurrent Tasks share that single Binding. The Agent is the executor; the Task is the work.

#### Acceptance and rejection

On Dispatch, the Agent inspects every Task in the Manifest and emits a `ManifestAck` carrying a per-Task acceptance decision. A Task may be rejected with one of three reasons in v0.1:

- **`SKILL_MISMATCH`** — the Agent's Skill set does not satisfy the Task's required Skills.
- **`SPEC_INVALID`** — the TaskSpec is malformed, references an unknown datatype, or targets an unreachable resource.
- **`INTERNAL_ERROR`** — any other local failure during acceptance (resource allocation failure, configuration error, unexpected condition).

Rejections are **non-retryable in v0.1**. The Overseer does not re-dispatch, reassign, or queue a rejected Task. A rejected Task is terminal.

**Multi-Task Manifest cascade.** If any Task in a Manifest is rejected, the entire Binding fails. Accepted sibling Tasks are transitioned to Rejected with the internal `PEER_REJECTED` reason, and the Binding is released with `release_reason = task_rejected`. This is a deliberate all-or-nothing policy for v0.1 — a partial Binding (some Tasks running, some rejected) is rejected as inconsistent.

**Single-Task Manifests.** A Manifest carries exactly one Task. The multi-Task model above (per-Task acceptance, `PEER_REJECTED` cascade, all-or-nothing policy) remains normative; a Manifest with `len(tasks) != 1` is rejected by the Binding FSM at `B-T1` with `SPEC_INVALID`. The multi-Task `PEER_REJECTED` paths in the Task, Binding, Service, ComputeSlot, and Sink FSMs are therefore not reachable while Manifests are single-Task; `PEER_REJECTED` is catalogued in `TaskRejectionReason` (Atlas proto catalog, `§control.proto`) as dormant.

The state transitions, invariants, and interaction rules governing acceptance, rejection, and the Binding cascade are specified in **FSM Atlas §2.2 (Task FSM)** and **§2.3 (Binding FSM)**.

---

## WHAT — Operations

There are **eight System Operations**, plus the runtime Data Operations and the platform Infrastructure Operations. The eight are the canonical verbs of the system; seven of them (all but Drain) are exposed at user-facing or inter-actor surfaces and are the subject of the C3 operation-surface check (Part II). **Drain** is issued by the Overseer to itself and is audited through the Atlas drain sequence rather than a user-facing verb.

### System Operations

System Operations manage the creation, assignment, and teardown of the system's structural entities. They are issued by the Overseer or initiated by Agents during registration. Each has **infrastructure requirements** — the set of platform subsystems that must be available for it to execute. If any required subsystem is unavailable, the Overseer rejects the operation with an error naming the missing subsystem. Infrastructure requirements are distinct from entity-state preconditions: a precondition is a logical constraint on domain objects ("the Agent's Skill set satisfies the Task"); an infrastructure requirement is a physical constraint on platform subsystems ("persistent storage is writable").

- **Register** — Establish an Agent's identity and Skill set within a Session. Precondition for all other Operations. Performed by RemoteAgents on first connection through the Gateway, or initiated by the Overseer when spawning PlatformAgents. The declared Skill set is validated by the Overseer and becomes immutable for the registration's lifetime. Infrastructure: persistent storage (record the registration); message delivery (RemoteAgents — the Gateway↔Overseer stream must be operational); process spawning (PlatformAgents — the spawner must be available).

- **Bind** — Associate an Agent with a Workspace within a Service. Precondition: a valid Manifest exists. Postcondition: the Agent is authorized to operate within the Workspace's resource boundaries. A Binding links Agent to Workspace — the ComputeSlot assignment is carried by the Task, not the Binding. Idempotent. Infrastructure: persistent storage (create and persist the Binding row).

- **Assign** — Place a Task at a ComputeSlot and designate a bound Agent to execute it. Precondition: the Agent's Skill set satisfies the Task's required Skills, and the Task's schemas are compatible with the ComputeSlot's declared input/output schemas. Postcondition: the Task occupies the ComputeSlot and the Agent begins execution. Assign connects a Binding (Agent + Workspace) to a Task (work + ComputeSlot). Infrastructure: persistent storage.

- **Deploy** — Activate a Pipeline as a Service. The act of defining, provisioning, and starting a long-lived pipeline instance. The verb associated with Services. Infrastructure: **all subsystems** — persistent storage, message delivery, process spawning, event broadcast. Deploy creates structural state across every subsystem; partial creation produces irrecoverable inconsistency, so Deploy is rejected unless all are available.

- **Dispatch** — Deliver a Manifest to an Agent. Requires that the target Agent has already Registered. For RemoteAgents, the Overseer stages the Manifest and associated Binding in a pending state, then waits for the Agent to connect through the Gateway and Register; only after successful Registration does it deliver the Manifest via the ManifestChannel. For PlatformAgents, the Overseer spawns the Agent, waits for Registration, and delivers directly. Once delivered, the Agent inspects the referenced Tasks, checks its Skills, and emits a per-Task acceptance decision via `ManifestAck` (see Skills & Tasks → Acceptance and rejection). Infrastructure: persistent storage, message delivery.

- **Command** — An imperative instruction issued to an Agent or a Task. The base Commands are **Pause** (suspend execution, maintain state), **Resume** (continue from paused state), **Stop** (terminate execution, drain and flush), and **Restart** (soft in-process re-initialization preserving Agent and Task identities; increments per-Task `restart_epoch` on Artifact lineage; applies symmetrically to both Agent types — see **Restart mechanics**). Identified by a **Command ID**. Fire-and-ack: the Overseer expects an Acknowledgment referencing the originating Command ID. Infrastructure: message delivery for RemoteAgents (CommandChannel routes through the Gateway and message bus); none for PlatformAgents (the CommandChannel is in-process).

  **Command scoping.** Every Command carries a **target** that determines its scope — either a **Task ID** (Task-scoped) or a **Binding ID** (Agent-scoped):

  - **Task-scoped Command** — affects only the named Task. The Agent identifies the target Task by its Task ID and applies the instruction to that Task alone; other Tasks continue unaffected. Example: Pause Task `TSK-401` while Task `TSK-402` keeps running.
  - **Agent-scoped Command** — affects the Agent and all its active Tasks. The Agent receives the Command targeted at its Binding ID and applies it to itself and every Task it is executing. Example: Stop Agent `RA-17` via Binding `BND-140`, stopping all its Tasks.

  The user determines the scope through the webapp: per-Task controls (Pause, Resume) and per-Agent controls (Stop, Restart, Delete). The webapp encodes the choice as `{"target_task": …}` or `{"target_binding": …}`; the Overseer forwards the Command with the target intact; the Agent interprets the scope. A Task-scoped Command naming a Task the Agent is not executing is rejected with an Acknowledgment carrying status `REJECTED`. On the wire the `Command` message carries the scoping target as a `oneof target` with `TaskId` and `BindingId` variants, alongside `CommandId` and `CommandKind`.

  **Restart mechanics.** A Restart is a **soft-restart**: the Agent process re-initializes its internal state in place without being torn down and re-spawned. Agent identity (Agent ID), all active Bindings, and all Task IDs are preserved; the Skill set declared at Registration is preserved (Restart is not a re-registration). Artifact lineage carries a per-Task `restart_epoch` counter that increments on each successful Restart of a Task; post-restart Artifacts reference the same Task ID with a higher `restart_epoch`, letting consumers distinguish pre- and post-restart lineage without breaking Task identity. The Restart must complete within the existing `stop_drain_timeout`; if it does not, the affected Tasks transition to Failed and their Bindings are released. Restart applies symmetrically to both Agent types, is not permitted while the Overseer is Draining, and is restricted to Full mode in v0.1 (FSM Atlas §1.4, Operation Availability Matrix).

- **Delete** — Remove an Agent and its associated structural state from the system. Delete is a System Operation, not a Command — it destroys the Binding and structural state rather than instructing an Agent. The Overseer executes it as a sequence: issue a `BINDING_RELEASE` Command (Agent-scoped via `BindingTarget`) → wait for drain and Acknowledgment → release the Binding → destroy the Workspace → mark the ComputeSlot vacant → auto-stop the Service if this was its last Binding (`SV-T10`) → issue `AGENT_TERMINATE` (`A-T16`) → deregister the Agent and decrement Session envelope counters. Delete is the inverse of Bind. Infrastructure: persistent storage; message delivery for RemoteAgents (to deliver `BINDING_RELEASE` and `AGENT_TERMINATE`). Full choreography, invariants, failure branches, timing, and Recovery behavior are specified in **FSM Atlas SEQ-2 Delete (§3.2)**.

- **Drain** — Gracefully wind down all managed entities in preparation for a platform shutdown or maintenance window. Drain is a system-level operation issued to the Overseer itself, not to individual Agents. Unlike Delete, Drain is **preserving**: it suspends management without destroying structural state, so the Overseer can resume after restart.

  - For **PlatformAgents**: issue Stop Commands to all active PlatformAgents (their runtime is going offline). Wait for Acknowledgments with a configurable timeout; on timeout, force-stop the process and mark the Binding `released`. PlatformAgent Services are marked `stopped`. After restart, the Overseer may re-spawn them if the Service is configured for automatic recovery.
  - For **RemoteAgents**: do **not** issue Stop Commands — they run on client infrastructure unaffected by a platform shutdown. Instead, the Overseer persists all active RemoteAgent Bindings, Tasks, and Channel state as `draining` and closes its end of the Channels. The RemoteAgent detects the closure and enters a reconnection loop. After the Overseer restarts and completes Recovery, the RemoteAgent reconnects, the Overseer matches it to the persisted `draining` Binding, re-activates it, and resumes telemetry and command flow.

  This Remote/Platform asymmetry during Drain is the one case where the two Agent lifecycles diverge: PlatformAgents are stopped because their host is shutting down; RemoteAgents are preserved because their host is not. Infrastructure: persistent storage. Message delivery is best-effort during Drain.

### Data Operations

Data Operations are the runtime expression of Skills, performed by Agents executing Tasks. Each corresponds to a Skill.

- **Ingest** (Skill: Ingest) — Connect to an external source and produce a raw data stream. Continuous and stateful.
- **Sync** (Skill: Sync) — Synchronize ingested streams to a clock and produce periodic snapshots. Stateful and clock-driven.
- **Transform** (Skill: Transform) — Apply computation to data within a ComputeSlot. The only Operation that changes data content. *Reserved — no Agent implements Transform in v0.1-beta-2.*
- **Emit** (Skill: Emit) — Materialize an Artifact and deliver it to a Sink through an ArtifactChannel.

### Infrastructure Operations

Infrastructure Operations are performed by the platform's Channel and process infrastructure, not by Agents. They require no Skills and produce no Artifacts.

- **Transit** — Move data from one ComputeSlot to the next across a Channel. Includes serialization, schema validation, and sequence tracking. Performed by the Channel infrastructure (DataChannel, ArtifactChannel). Transit does not change data content — it changes data location.

---

## WHAT — System Health

The Overseer's operational capability depends on the availability of its infrastructure subsystems. Four subsystems are defined, with the operations they gate:

| Subsystem | Description | Operations gated |
|---|---|---|
| **Persistent Storage** | Durable state for Sessions, Services, Bindings, Tasks, Commands | All mutating System Operations (Register, Bind, Assign, Deploy, Dispatch, Command, Delete, Drain). Read-only queries degrade to stale data if unavailable. |
| **Message Delivery** | ManifestChannel and CommandChannel transport to RemoteAgents via the Gateway | Dispatch (to RemoteAgents), Command (to RemoteAgents), Register (RemoteAgents) |
| **Process Spawning** | PlatformAgent process lifecycle (Docker, local process) | Register (PlatformAgents), Deploy when the Manifest targets a PlatformAgent |
| **Event Broadcast** | WebSocket broadcast to the webapp dashboard | No System Operations gated — but loss means the webapp goes dark. The Overseer keeps operating; the user loses visibility. |

The Overseer is always in one of three operational modes:

- **Full** — all four subsystems available; all operations permitted.
- **Degraded** — one or more subsystems unavailable; operations requiring an unavailable subsystem are rejected with a specific error naming it; operations that do not require it continue.
- **Unavailable** — not accepting operations (during initialization, recovery, or drain).

The Overseer advertises its mode to the webapp via Event Broadcast. On entering or exiting Degraded mode, it emits an event naming the affected subsystems and the consequently unavailable operations, so the webapp can disable the corresponding UI controls rather than letting the user discover the degradation through errors. Degraded means partial service; Unavailable means no service — the webapp should show a degradation banner for the former and a system-offline indicator for the latter.

---

## WHAT — Recovery

When the Overseer starts (or restarts after a crash), it reconciles its in-memory state with persistent storage before accepting new operations. This phase is **Recovery**; the Overseer is `Unavailable` throughout. Recovery prevents ghost entities — Bindings, Services, or Tasks that exist in storage but no longer correspond to running Agents or active Channels. It proceeds in three stages:

**Stage 1 — Binding reconciliation.** Query all Bindings with status `pending` or `active`.
- For each `pending` Binding: the Agent never completed Registration (or the Overseer crashed before activating it). If pending longer than a configurable threshold, mark it `released`, update the Service, and log it; if recent, keep it pending and wait for the Agent.
- For each `active` Binding: check whether the Agent is still connected. For RemoteAgents, query the Gateway (or the message-bus lifecycle topic). If connected, the Binding is valid and management resumes; if disconnected, enter a grace period (configurable, default 60s) — resume on reconnect, otherwise release and update the Service. For PlatformAgents, check whether the process is still running; if exited, release and optionally re-spawn if the Service is configured for automatic recovery.
- For each `draining` Binding (set during a prior Drain): wait for the Agent to reconnect, then transition it back to `active` and resume management.

**Stage 2 — Command reconciliation.** Query all Commands with status `pending`. For each older than a configurable timeout, mark it `timeout`; for recent ones, re-deliver through the appropriate Channel.

**Stage 3 — Service reconciliation.** Query all Services with status `active`. For each whose Bindings were all released during Stage 1, mark the Service `stopped` and log the orphan.

After all three stages, the Overseer transitions to Full or Degraded (per subsystem availability) and begins accepting operations.

---

## WHERE — Scopes

Scopes form a constraint hierarchy: **Domain > Session > {Workspace, Agent} > Task**. Each level constrains the levels below it. The hierarchy is not strict containment — Workspace and Agent are **peers** at the same depth, linked by a Binding rather than nested within each other. A Workspace constrains what resources an Agent can use; an Agent constrains which Tasks it can execute. Both are scoped to a Session and exist within a specific Domain.

### Domain

- **Domain** — The top-level trust boundary. Answers: **whose infrastructure is this?** Two Domains exist: the **Remote Domain** (client infrastructure, user-controlled) and the **Platform Domain** (IteraLabs infrastructure, platform-controlled). Domains are fixed and structural and carry no IDs — they are not created or destroyed; they simply exist as the two sides of the system. The Gateway sits at the boundary: no Agent in the Remote Domain can address any entity in the Platform Domain except through the Gateway, and nothing in the Platform Domain can initiate a connection into the Remote Domain. A Domain defines **trust and network topology** (who controls the hardware, who can initiate connections, where the authentication boundary lies) — not resources, permissions, or configuration.

### Session

- **Session** — Authenticated, time-bound scope linking a client identity to platform resources. Answers: **who is this user and what are they allowed to do?** Defines the maximum resource envelope (concurrent Agents, Pipelines, throughput). Contains multiple Services and Experiments over its lifetime. A Session spans both Domains — a single Session can have RemoteAgents in the Remote Domain and PlatformAgents in the Platform Domain. The unit of billing, access control, and audit. Identified by a **Session ID**.

### Workspace

- **Workspace** — Scoped execution environment for a specific Agent. Answers: **what resources, configuration, and permissions does this Agent have?** Lives within a specific Domain and Session; defines the concrete resources the Agent can use (sources, compute, Sinks). Where a Domain says "whose hardware," a Workspace says "what subset of that hardware, configured how, for this Agent." Identified by a **Workspace ID**.
  - **RemoteWorkspace** — In the Remote Domain. Defines exchange access, datatypes, snapshot frequency, local Sink configuration. The client provides the hardware; the Workspace defines how the Agent uses it.
  - **PlatformWorkspace** — In the Platform Domain. Defines compute allocation (vCPU, RAM, GPU), processing parameters, platform Sink configuration. The platform provides the hardware; the Workspace defines how the Agent uses it.

### ComputeSlot

- **ComputeSlot** — A positional slot in a Pipeline that a Task occupies. Answers: **what position in the data flow does this work occupy, and what data shape does it expect?** Declares an **input schema** (what it consumes from the preceding slot or external source) and an **output schema** (what it produces for the next slot or Sink). These structural constraints determine which Tasks are compatible with the slot and enforce that the Pipeline's data flow is well-typed end to end. Identified by a **ComputeSlot ID**.
  - **RemoteComputeSlot** — A slot in the Remote Domain, occupied by a Task executed by a RemoteAgent.
  - **PlatformComputeSlot** — A slot in the Platform Domain, occupied by a Task executed by a PlatformAgent.

#### ComputeSlot ↔ Task relationship

ComputeSlot and Task have a **1:1 runtime relationship**: at any moment a ComputeSlot is occupied by exactly one Task, and a Task occupies exactly one ComputeSlot. They are distinct concepts at different levels:

- **ComputeSlot is structural** — belongs to a Pipeline, reusable across activations, defines positional constraints (input/output schemas, ordering). The **socket**.
- **Task is runtime** — belongs to a Service, created per activation, defines work parameters (Skills required, TaskSpec, Sink assignments). The **plug**.

The separation enables: **vacancy** (a ComputeSlot can exist without a Task); **reuse** (the same slot hosts different Tasks across activations); **schema enforcement** (on Assign, the Overseer validates Task↔slot schema compatibility); and **Pipeline composition** (topology can be defined, validated, and reasoned about before any Tasks are assigned).

---

## HOW — Channels

- **Channel** — A sustained, typed communication path between Agents, between an Agent and a System Process, or between System Processes. Every Channel has a direction, a category (System or Data), and reliability semantics. Identified by a **Channel ID**.

- **CommandChannel** — Bidirectional, System. Carries Commands downstream (Overseer → Agent) and Acknowledgments upstream (Agent → Overseer). For RemoteAgents, routed through the Gateway; for PlatformAgents, direct. Transport: gRPC bidirectional stream. Reliability: at-least-once with ack.
- **ManifestChannel** — Unidirectional downstream, System. Delivers Manifests from the Overseer to Agents. Transport: embedded within the CommandChannel. Reliability: exactly-once with idempotency key.
- **TelemetryChannel** — Unidirectional upstream, System. Carries status, metrics, health signals, and operational logs from Agents to the Overseer. For RemoteAgents, routed through the Gateway into the platform's event bus; for PlatformAgents, direct. Reliability: best-effort with sequence numbers; gaps tolerable via resync.
- **DataChannel** — Unidirectional upstream, Data. Carries primary ingested data from RemoteAgents through the Gateway into PlatformComputeSlots, and between PlatformComputeSlots internally. Reliability: at-least-once with sequence numbers and gap detection.
- **ArtifactChannel** — Unidirectional, Data. Transports Artifacts from their producing ComputeSlot to the designated Sink. Direction depends on Sink location: upstream to platform Sinks, lateral to client Sinks (e.g., S3), or local for colocated Sinks.

---

## HOW — Ingest / Data Plane

The data-plane layer names how a RemoteAgent's **Ingest** Skill turns external-exchange market data into Artifacts. It is **Service-scoped** (it names market-data, not platform-control, concepts) and **additive**: it introduces no new Channel, Sink, or Activation type.

- **Feed** — A live, Agent-run subscription to one **`(venue, instrument, datatype)`** market-data stream from an external exchange, where `datatype ∈ {orders, trades}`. The external venue connection is the **Ingest mechanism**, not an Atelier Channel. Identified by a **Feed ID** (Agent-allocated; see Identifiers); its lifecycle is the Feed FSM (`fsm` §2.12). A Feed is the data-plane realization of an account-layer **Subscription** (the watchlist of exchange+pair feeds; see Account Layer).

- **`…Book`** — A composable **type-suffix** = *a stateful registry of one market-data type*, composed `<Specialization><Domain>Book` and **never written bare**. Domain ∈ {Order, Trade, … extensible}; Specialization ∈ {Sourced (reconstruction), Synthetic (generation — out of scope for this version)}. The reconstruction half — **`SourcedOrderBook`** and **`SourcedTradeBook`** — is the **Sync** Skill's output; its dynamics are the OrderBook/TradeBook FSMs (`fsm` §2.13).

- **reconstruction-model** — The per-venue rule by which a `SourcedOrderBook`/`SourcedTradeBook` applies deltas (FullRefresh; SeqDelta{RangeInclusive|ExactPrev}; ChecksumDelta; L3; …). An **open axis** carried as SDK config, **not** a closed typology: adding a venue or a model is configuration, never a taxonomy edit (contrast the closed Skill / Sink / Channel typologies).

- **Skill mapping (data-plane).** Uses the existing five Skills, no additions: **Ingest** = the Feed + frame decode; **Sync** = the `SourcedOrderBook`/`SourcedTradeBook` reconstruction; **Emit** = materializing the book output as a `DataArtifact` to a Sink / DataChannel (lineage attaches here); **Report** = per-Feed telemetry. **Transform** is reserved for derived data.

- **DataArtifact shapes.** A Feed's output materializes as `DataArtifact`s (Artifact kind Data) — orderbook snapshots/deltas and public trades. These market-data **schemas are Service-scoped** and are not new closed-typology members (they must not appear at platform/shared scope).

---

## OBJECTS — Artifacts

- **Artifact** — A materialized output produced by an Agent executing a Task at a ComputeSlot, or by a System Process for audit and operational purposes. Every Artifact carries an **Artifact ID** and either a **Service ID** (Agent-produced, under a Service) or an **Experiment ID** (a ModelArtifact produced by an Experiment run); Agent-produced Artifacts additionally carry a **Task ID**. The Artifact is the logical object; its physical encoding depends on the Sink it is Emitted to. Typed by content:

  - **DataArtifact** — Primary or derived dataset (orderbook snapshots, feature vectors, volatility surfaces, signals).
  - **LogsArtifact** — Operational logs, execution traces, diagnostic records, anomaly reports.
  - **ModelArtifact** — Trained model, fitted parameter set, or quantitative output with associated fit metrics.
  - **ManifestArtifact** — Archived Manifest stored for audit and reproducibility; records the exact configuration that produced a deployment. Produced by the **Overseer** (a System Process), not by an Agent — ManifestArtifacts carry no Task ID, and on the wire they ride a distinct `ManifestArtifactFrame` rather than the Agent `ArtifactFrame`.

When an Agent receives a Stop Command (from a user Command, a Delete sequence, or a Drain), it must drain all buffered data and complete any in-progress Emit before sending its Acknowledgment; the Acknowledgment signals that all Artifacts are finalized. If the drain exceeds the configurable `stop_drain_timeout`, the Agent acks with a `partial` flag and the Overseer marks the affected Artifacts `partial` in metadata. Partial Artifacts are preserved (not discarded) but carry a warning that they may be incomplete.

---

## DESTINATIONS — Sinks

- **Sink** — The final destination where an Artifact is materialized. The Artifact defines *what* was produced (schema, semantics, lineage); the Sink defines *how and where* it is stored (format, protocol, location). Artifact and Sink are orthogonal — any Artifact type can, in principle, be Emitted to any Sink type. Identified by a **Sink ID**. Typed by storage medium (the closed set of three):

  - **ObjectSink** — Write to file storage (local disk, S3, GCS, or any object store). Artifact materializes as a file (Parquet, CSV, Arrow IPC, JSON, serialized binary).
  - **DBSink** — Write to a database through a connection. Artifact materializes as rows in a table or records in a collection. *Wire-reserved in v0.1-beta-2: the `DBSink` type exists but no Writer implements it yet (ObjectSink and TerminalSink are the live Sinks).*
  - **TerminalSink** — Print to the webapp's live terminal viewer. Artifact materializes as rendered output (log lines, status messages, diagnostic traces).

---

## ACTIVATION MODE

A Pipeline is a structural definition — an ordered sequence of ComputeSlots. It becomes active through a single mode:

- **Service** — The **sole activation mode**. Operational activation of a Pipeline: deployed via Deploy, runs, produces Artifacts. Monitored for health by the Overseer. Lifecycle: deploy → assign tasks → run → (runs until stopped or updated). Identified by a **Service ID**. All orchestration entities (Manifest, Binding, Task, ComputeSlot, Channel, Sink) are Service-scoped; all Agent-produced Artifacts carry the Service ID.

Boundedness (a fixed collection vs. continuous operation) is operator intent within the Service mode, not a separate activation mode. There is no second activation verb: a Pipeline is activated by **Deploy**, never by a distinct "Run".

---

## EXPERIMENTS

- **Experiment** — A bounded research run that **consumes a Service's collected data** and produces a **ModelArtifact**. An Experiment is **not** a Pipeline activation: it creates no Binding, Task, ComputeSlot, or Manifest and runs no Agent. It reads data a Service produced and derives a result. Identified by an **Experiment ID**, scoped to a Session. The unit of reproducibility and iteration.
  - **Training** — The Experiment kind in v0.1-beta-2: fit a model to a Service's event series. Carries an **open model field** (e.g., `hawkes`, `poisson`, …) selecting the estimator. Produces a ModelArtifact (fitted parameters + fit metrics).
- **Execution & ownership.** Experiments run **inline in `atelier-overdex`** (`run → completed | failed`), persisted in `overdex-db`. They are **not** orchestrated by the Overseer and have **no Atlas FSM** — the Atlas covers orchestration (Sessions / Services / Bindings / Tasks / Agents / …), not Experiment execution. An Experiment records the `service_id` whose data it consumed for provenance.

---

## COLOCATION

- **Colocation** — A **read-only latency oracle**: given an exchange, it returns the lowest-latency platform **region** (AWS) and a latency **score**. Sourced from `atelier-overplex`'s `cex_latest` probe table (`overplex-db`); consumed by `atelier-overdex` at managed-deploy time to pick a region when the operator pins none.
- **Region is an oracle output, not a scope.** Colocation yields an advisory region; it is **not** a Workspace, Domain, or deploy attribute in the orchestration ontology, carries no ID, and drives no FSM. The deploy path may read it to set a target region, but region is not a structural term. Multi-region / multi-cloud Agent spawn is deferred.

---

## STRUCTURAL TERMS

- **Skill** — A composable capability trait possessed by an Agent; determines which Tasks the Agent can execute. The base Skills are Ingest, Sync, Transform, Emit, Report. Declared at Registration, immutable for the registration's lifetime. Analogous to Rust traits — an interface contract, not an implementation.
- **Task** — A declarative work unit that occupies a ComputeSlot and declares its required Skills. Contains a TaskSpec and a reference to its ComputeSlot. Scoped to a Service. An Agent executes it only if its Skill set satisfies the requirements. Identified by a **Task ID**.
- **Manifest** — Declarative specification composing a Binding with one or more Task references: which Agent, which Workspace, which Tasks at which ComputeSlots, which Sinks. Scoped to a Service. The Overseer dispatches Manifests; the receiving Agent inspects the referenced Tasks, checks its Skills, and accepts or rejects. Identified by a **Manifest ID**.
- **Binding** — Runtime link between an Agent and a Workspace. Scoped to a Service. Created by the Overseer when a Manifest is Dispatched; released when the Agent's Tasks complete, the Service is stopped, or the Agent is Deleted. A Binding does not reference a ComputeSlot — that relationship is carried by the Task. A single Binding can support multiple Tasks executed by the same Agent in the same Workspace. Identified by a **Binding ID**.
- **Pipeline** — An ordered sequence of ComputeSlots where each slot's output feeds the next slot's input. Structural and reusable — the same topology can be activated by multiple Services with different Manifests and Tasks. Identified by a **Pipeline ID**.

---

## IDENTIFIERS

Every addressable object carries a unique, immutable identifier assigned at creation time.

| Object | Identifier | Scope | Purpose |
|---|---|---|---|
| Session | Session ID | Global | Root scope for billing, access control, audit |
| Service | Service ID | Session | Groups all Bindings, Tasks, Artifacts for one unbounded activation |
| Experiment | Experiment ID | Session | Identifies one bounded research run (overdex-owned); groups its ModelArtifacts |
| Pipeline | Pipeline ID | Global | References a reusable pipeline topology across Services |
| Manifest | Manifest ID | Service | Addresses a specific Binding + Task specification for dispatch and audit |
| Binding | Binding ID | Service | Addresses the runtime Agent–Workspace link |
| Task | Task ID | Service | Addresses a specific work unit at a ComputeSlot |
| Agent | Agent ID | Session | Distinguishes individual RemoteAgents and PlatformAgents |
| Overseer | Overseer ID | Global | Identifies the orchestration process instance |
| Gateway | Gateway ID | Global | Distinguishes Gateway instances (different types, capacity) |
| Workspace | Workspace ID | Session | Addresses a specific execution environment instance |
| ComputeSlot | ComputeSlot ID | Pipeline | Addresses a specific positional slot within a pipeline |
| Channel | Channel ID | Binding or System | Addresses a specific communication path between two endpoints |
| Sink | Sink ID | Workspace | Addresses a specific output destination instance |
| Artifact | Artifact ID | Service | Traces a specific output across Sinks |
| Feed | Feed ID | Task | One Agent-run `(venue, instrument, datatype)` subscription; **Agent-allocated**, telemetry-reported, no durable platform row |
| Command | Command ID | Task or Agent | Correlates an imperative instruction with its Acknowledgment. Target is a Task ID (Task-scoped) or Binding ID (Agent-scoped). |

### Identifier discipline (wire + language layer)

This is the static contract behind the C2 review check (Part II); it is normative here and enforced everywhere.

- **Wire shape.** Every `*_id` is a flat UUIDv4 `string` on the wire. The `*_id` field is authoritative; an optional `*_alias` (e.g., `RA-17`) may travel alongside but is **never load-bearing** — never an identity, never a join key. Wrapper-message identifier patterns (`message AgentId { string value = 1; }`) are non-conformant: they add a decode layer without adding any compile-time discipline at the wire.
- **Language layer.** In the Rust crates, each ID domain SHOULD be a distinct newtype (`AgentId(Uuid)`, `BindingId(Uuid)`, `TaskId(Uuid)`, …) so that passing a `BindingId` where an `AgentId` is expected is a compile error. This discipline lives in the SDK types crate and the backend models; it does not change the wire shape (the wire stays flat strings; the language layer wraps on decode and unwraps on encode).

---

## ACCOUNT LAYER (scoped out of core orchestration)

These are user-account concerns, named here for coverage. They are **not** part of the core orchestration ontology or the FSM Atlas; they sit above the Session boundary and are owned by other components. Their **dynamics** — states, transitions, invariants — are specified in the account-layer FSM companion `../fsm/overledger-beta.md` (§A), which is out of the core Atlas the same way these nouns are out of the core ontology. Because the account layer is out-of-core, these terms are audited only for boundary adherence (billing stays above the Session boundary; see Part II per-repo map → `atelier-overledger`) and are deliberately **not** added to the C1–C7 canonical surface.

- **Subscription** — A user's feed **watchlist**: the set of exchange + trading-pair data feeds they follow. An account-layer concept owned by the webapp/backend, not an orchestration entity (no FSM, no Binding/Task). It seeds what an operator may Deploy, but a Subscription is not itself a Service. **Naming collision (load-bearing):** "Subscription" is the data-plane watchlist *only*. The billing tier is a distinct noun, **Plan** (below); a billing-tier concept must never be called a Subscription, and a watchlist must never be called a Plan.
- **Billing** — Payment, token, and metering logic. An account-layer concern owned by **`atelier-overledger`**. The **Session** is the unit of billing in the core ontology (the boundary at which usage is counted), but the billing logic, Ledger, and Checkout flow live in overledger and are out of scope for the core. The unit of charge is the **Token** (below), not a "credit".
- **Token** — The unit of charge: a metered, spendable unit drawn down as an identity consumes platform resources. The name is the definition — a Token is consumed, Granted, and Refunded, and a balance of Tokens is what an identity holds. (The implementation still names the unit `credit` in code; the credit→token rename is a deferred, separate change that keeps the physical table `billing_credit_ledger`.)
- **TokenKind** — The closed typology of Tokens, mirroring the metered resource: **compute** (model fits, forecasts, managed-agent runtime), **data** (bytes ingested and retained), **networking** (transport — defined now; metered in a later phase). Exactly three members.
- **Ledger** — The append-only store of signed Token deltas keyed by `(identity, TokenKind)`; balance is their sum. Not an FSM (audit-and-lineage, never updated in place — like the Atlas `artifacts` table). The single enforcement primitive behind every Debit.
- **Plan** — The user's **billing tier**: the access subscription that, while active, unlocks the Session envelope and the right to purchase Token packs. The "identity's plan/quota policy" that `SN-T1` resolves the Session envelope from (FSM Atlas `session-beta.md` §2.7.5) is this Plan. Distinct from the data-plane Subscription (see collision note above).
- **Entitlement** — A derived view of what an identity may do right now: its access tier (a projection of Plan state) plus its Token balances (from the Ledger). The `Entitlements { plan, credits }` the webapp reads. Account-layer projection, not an orchestration entity.
- **Checkout** — One purchase attempt that, on settlement, Grants Tokens to the Ledger. Owned by overledger; its lifecycle is the Checkout FSM (`fsm/overledger-beta.md` §A.2).

These four account-layer **operations** act on the Ledger and are **not** core System Operations (they never appear on the orchestration wire): **Meter** (derive a charge amount from observed usage), **Debit** (record a consumption, `delta < 0`), **Grant** (award Tokens, `delta > 0`), **Refund** (compensate a prior Debit). They are listed here for coverage; the C3 operation-surface check audits only the eight core System Operations, not these.

---

# Part II — Review & Governance (How do I check repo R speaks X correctly?)

Part I says what each term is. Part II is the operational method that keeps every repo faithful to it: an index of Part I (the canonical surface), the seven checks that detect drift, the violation taxonomy that classifies a finding by how it must be fixed, the per-repo map of where findings cluster, and the three passes that turn a finding list into a change plan. The method is durable; the findings it produces are not — those are recorded per-repo in `reports/`.

## Role — Taxonomy vs FSM Atlas

The two normative bodies answer different questions and own different things.

- **This taxonomy** answers *"what is X?"* — names, identifiers, scoping and nesting, ontology, term-composition rules, the operation surface, and the canonical typology (Skills, Sink types, Activation mode, infrastructure subsystems, Artifact kinds, Recovery semantics).
- **The FSM Atlas** answers *"how does X change over time?"* — states, transitions, guards, effects, invariants, wire events, persistence DDL, error semantics, timeouts.

Where they overlap, the precedence is fixed (and restated from the top of this document because it is load-bearing): **the Taxonomy wins on static definition; the Atlas wins on dynamic behavior.** A conflict must be resolved on both sides within the same version cut. The two lenses compose: FSM ownership says "these repos must implement FSM Y"; taxonomy review says "these repos must speak term Z correctly." A change plan almost always touches both — keep them side by side when reading a divergence report.

## Reach — why review applies to every repo, not just FSM owners

Unlike the Atlas — read mostly by FSM owners — the taxonomy is read by **every repo that names an Atelier entity**, and a drift in any one of them radiates: a Skill renamed in the wire contract breaks the SDK, the backend, and the webapp at once. Taxonomy violations are everyone-violations by construction. This is why a dedicated taxonomy review matters even when FSM ownership is clean: a repo "not on the hook" for any FSM is still on the hook for every taxonomy surface it touches. The webapp owns no FSMs but must speak every noun correctly; the wire-contract crate owns no FSMs but defines the entire canonical surface for everyone else.

## The canonical surface

These seven surfaces are the index of Part I — every review check below targets exactly one of them. The canonical examples are the authoritative members; anything outside them is a candidate violation.

| Surface | Content | Canonical members |
|---|---|---|
| **Nouns** | Entity kinds and structural terms | Agent, RemoteAgent, PlatformAgent, Binding, Service, Experiment, Task, Manifest, Artifact, Sink, Channel, Session, ComputeSlot, Pipeline, Workspace, Domain, Overseer, Gateway |
| **Verbs** | System Operations | Register, Bind, Assign, Deploy, Dispatch, Command, Delete, Drain (8 defined; Drain is Overseer-self-issued, so the user/inter-actor verb surface audited by C3 is the other 7) |
| **Identifiers** | Shape and convention | UUIDv4 flat `string`; `*_id` authoritative; `*_alias` optional, never load-bearing; per-domain Rust newtype discipline; wrapper-message ID patterns are non-conformant (see Part I → Identifier discipline) |
| **Typologies** | Closed enumerations | Skill (5), AgentType (Remote/Platform), SinkType (3: Object/DB/Terminal), ArtifactKind (3: Data/Logs/Model + ManifestArtifact as a distinct message), Subsystem (4: Persistent Storage / Message Delivery / Process Spawning / Event Broadcast), ActivationMode (Service — sole mode) |
| **Scopes** | Nesting / envelope rules | Domain > Session > {Workspace, Agent} > Task; Session ⊇ Service ⊇ Binding ⊇ Task; Binding ⊇ {Agent, Workspace, ComputeSlot} |
| **Modes** | Operational axes | Overseer mode (Full / Degraded / Unavailable); Agent location (Remote / Platform); Activation (Service) |
| **Lifecycle concepts** | Named processes that cut across FSMs | Drain (preserving), Recovery (three-stage), Restart (soft, bounded by `stop_drain_timeout`), Ghost entity (an entity persisted in storage with no live counterpart — the condition Recovery exists to clear) |

`AgentType` and `Subsystem` appear above as wire/typology vocabulary that names the same things Part I defines as the Remote/Platform location axis and the four System-Health subsystems; the typology column is the closed-enumeration view of those definitions, used by the C4/C5-style enumeration checks.

## Sources of authority & precedence

In precedence order:

1. **This taxonomy (Part I)** — the normative source for every static definition.
2. **The precedence rule** — Taxonomy wins on static definition; Atlas wins on dynamic behavior.
3. **Illustrative companions** (worked examples, walkthroughs) — non-authoritative; they show how the terms compose, and lose to Part I on any conflict.
4. **Atlas files that *cite* the taxonomy** — bind the citation only; if a citing Atlas file conflicts with Part I, the taxonomy wins and the citation is updated.

## The seven checks (C1–C7)

Run each check against each repo. For every finding, classify it with the violation taxonomy (Classes A–H) and record `file:line`. The checks are durable; the concrete findings they produce for a given repo live in `reports/`.

**C1 — Canonical term usage.** Grep each Noun verbatim across the repo. Confirm each is either used correctly or genuinely unused. Flag synonyms, pseudonyms, and silent renames — a term that means a canonical entity under a non-canonical name is a drift even when it "works." Illustrative shapes: a `Worker` type used where the canonical noun is `Task`; a capability enum named `AgentCapability` instead of `Skill`; a location field named `AgentLocation` instead of `AgentType`; a `TerminalSink` vs `Terminal` inconsistency across layers.

**C2 — Identifier discipline.** Every `*_id` is a flat UUIDv4 `string` on the wire; `*_alias` is optional and never load-bearing; wrapper-message ID patterns are non-conformant. In Rust, each ID domain SHOULD be a distinct newtype so cross-domain misuse is a compile error (language-layer only; the wire stays flat strings). See Part I → Identifier discipline. The newtype discipline is expected to live in the SDK types crate and the backend models.

**C3 — Operation surface.** The System Operations are the canonical verbs exposed at user-facing and inter-actor surfaces (REST routes, gRPC methods, CLI subcommands, UI button labels). The audited set is the seven non-Drain operations (Drain is Overseer-self-issued and audited via the Atlas drain sequence). 1:1 renamings are acceptable (`deploy_service` for Deploy, `issue_command` for Command). **Invented verbs** with no taxonomy operation behind them are violations. **Missing verbs** — a canonical operation absent from a surface that should expose it — are violations.

**C4 — Skill enumeration.** Exactly five members: `INGEST`, `SYNC`, `TRANSFORM`, `EMIT`, `REPORT`, under an enum named `Skill`. A short set (a missing member), an extra member, or a renamed enum is a violation.

**C5 — Sink types.** Exactly three: `Object`, `DB`, `Terminal`. Anything else is a violation. Watch for a storage-medium sink surfaced under a format-specific name (e.g., an `ObjectSink` realized as a "Parquet" sink) or a non-canonical sink type appearing alongside the three.

**C6 — Activation mode.** Service is the **sole** activation mode. Experiment is a research run owned by `atelier-overdex` (it consumes a Service's data → ModelArtifact), not a Pipeline activation; any Experiment emitted as a Pipeline-activation variant on the orchestration wire is a violation.

**C7 — Scope nesting.** Session ⊇ Service ⊇ Binding ⊇ Task; Binding ⊇ {Agent, Workspace, ComputeSlot}. Surfaces that list or persist entities must respect the nesting — a view or schema that flattens or omits a level (e.g., no Session scope, no Task level) is a violation.

## Per-repo primary surfaces

A shortcut map: for each repo, which checks typically produce findings. A repo scores clean on checks that do not land (e.g., an infrastructure repo is not expected to surface Identifiers or Typologies).

| Repo | Primary surfaces to audit |
|---|---|
| `atelier-proto` (wire contract) | C1 (message/enum names), C2 (flat-string identifiers), C3 (CommandKind), C4 (Skill), C5 (SinkType, ArtifactKind), C6 (Activation oneof) |
| `atelier-sdk` | C1 (type/module names; Worker-as-Task drift), C3 (command-enum vs Command), C5 (sink implementations), Domain leakage (market-data vocabulary at shared scope — Class D) |
| `atelier-overseer` | C3 (REST + gRPC server impls), storage extensions (table list vs the Atlas schema — Class G), C7 (nesting in queries + views), C2 (newtype models) |
| `atelier-webapp` | C1 (UI strings, component names), C3 (button labels, form actions), C7 (view hierarchy) |
| `atelier-infra` | C1 (topic names, deployment names), C5 (topic ↔ reliability-class mapping) |
| `atelier-overdex` | Experiment runs (genus + Training kind; overdex-owned, no Atlas FSM), Colocation oracle reads, MCP tool surface; C1 (names), C6 (Experiment is not a Pipeline activation) |
| `atelier-overplex` | Colocation oracle (`cex_latest`) — read-only latency/region source; Class D (market-data vocabulary stays Service-scoped) |
| `atelier-overledger` | Account layer (Token / Ledger / Plan / Entitlement / Checkout; dynamics in `fsm/overledger-beta.md` §A), out of core FSM — audit only that (a) billing stays above the Session boundary, (b) the billing tier is named **Plan** not Subscription, and (c) no metering Effect is added to a core transition (metering subscribes to Events). Not on the hook for C1–C7 core surfaces. |
| MCP control layer | C3 (tool inventory → Operation mapping), Class C (no invented verbs), no separate Query category |

## Violation taxonomy (Classes A–H)

Classify every finding by **fix shape** — the fix shape determines which repos change and in what order. The **cascade order** is the wave each violation lands in: wave 1 = spec edits, wave 2 = wire breakage, wave 3 = code-only moves.

| Class | Shape | Example | Fix shape | Wave |
|---|---|---|---|---|
| **A. Silent rename** | a canonical term under a non-canonical name | `AgentType` → `AgentLocation` | Wire-breaking. Fix in the wire contract first; consumers regen and rewrap. | 2 |
| **B. Missing member** | a closed enum missing a canonical member | `Skill.SYNC` absent | Wire-additive (safe). Fix in the wire contract; consumers pick it up on regen. | 3 |
| **C. Invented member** | an enum member with no taxonomy meaning | a `RECONFIGURE` command kind | Wire-subtractive (breaking). Remove from the wire; if legitimate, lift it into the spec (taxonomy operation + matching Atlas transition) first. | 1 (if lifted) or 2 (if removed) |
| **D. Domain leakage** | Service-specific vocabulary at shared/platform scope | Orderbook / Trade / MarketSnapshot / Hawkes named at a shared crate root | Architectural. Pull leaked terms into a Service-specific namespace; nothing at shared scope should name them. | 3 (post-wire) |
| **E. Ownership inversion** | an allocated ID carried on the inbound message that requests it | `BindingId` on an inbound `Manifest`; `AgentId` on an inbound `Registration` | Spec-first. Close the allocator ambiguity in the Atlas (B-T1 / A-T1), then fix wire + backend + sdk. | 1 |
| **F. Missing operation** | a canonical operation absent from the wire | a Command kind with a spec'd Atlas transition but no wire member | Wire-additive + code-additive. Verify the Atlas transition exists; add to the wire; plumb through backend; surface in webapp. | 2 |
| **G. Storage extension** | a persisted table not in the Atlas schema | a table present in the backend but absent from the schema | Spec-first. Decide: promote to a schema table (with lifecycle invariants), or exclude as wire-only with durability routed elsewhere. | 1 |
| **H. Under-typing** | a coarse status where the spec wants a structured type | an `AckStatus {ACCEPTED, REJECTED, FAILED}` where the spec wants a full `Error { kind, message, correlation_id, retryable, retry_after_ms }` | Wire-breaking. Fix in the wire contract; consumers rewrap failure paths. | 2 |

## Using this as a planning input

A complete review produces, per repo, a list where each entry is `(check, finding, violation-class, fix-shape, cascade-wave)`. Turn that into a plan in three passes:

1. **Pass 1 — Spec edits (wave 1).** Every Class E (ownership inversion) and Class G (storage extension), plus Class C *if* the invented member is legitimate and should be lifted. Land these as spec edits first — no code changes — and start no downstream work until the spec is clean.
2. **Pass 2 — Wire cut (wave 2).** Every Class A (rename), B (missing member), C (remove invented), F (missing operation now backed by a spec transition), H (under-typing). Bundle into one wire-contract cut; consumer repos regenerate and land their updates synchronously with it.
3. **Pass 3 — Code moves (wave 3).** Every Class D (domain leakage). Pull leaked vocabulary into Service-specific namespaces. No wire impact — do it last, once the wire has stabilized.

Within each wave, sequence by **blast radius**: wire-breaking changes with many consumers before pure-additive ones; backend lifts before webapp lifts; namespace moves before UI-copy edits. This ordering minimizes churn — spec decisions cascade into the wire, wire regen cascades into code, UI text is last — and makes every wave independently reviewable.

## Interaction with FSM ownership

Two lenses, kept side by side:

- **Precedence** — Taxonomy wins on static definition. Use it to decide when a naming or scoping conflict resolves taxonomy-first.
- **FSM Ownership Matrix** (FSM Atlas §2.4.1) — applies to FSM dynamics: which repo executes transitions, persists authoritative state, emits Events, and enforces invariants. A real FSM gap against a repo exists only where the repo owns or co-owns the FSM; non-owner absence is expected, not a gap.

Composed rule: **FSM ownership says "these repos must implement FSM Y"; taxonomy review says "these repos must speak term Z correctly."** Taxonomy applies to all repos regardless of FSM ownership — a repo that owns no FSMs is still fully on the hook for every taxonomy surface it touches.

---

## Maintaining this document

This is a single, durable source of truth — edit it with that in mind.

- **A new term needs a home and a one-line "the name is the definition" gloss**, placed in the correct Part I section (WHO / WHAT / WHERE / HOW / OBJECTS / DESTINATIONS / ACTIVATION / STRUCTURAL / IDENTIFIERS) — not appended at the end.
- **A new term also lands on a review surface.** When you add a noun, verb, identifier, typology member, scope, mode, or lifecycle concept, update the canonical surface (Part II) so the checks see it.
- **A term that gains dynamics must land an Atlas FSM in the same change set**; a new Atlas FSM whose subject is not yet a term must land the term here in the same change set. Keep the static/dynamic split clean and same-version.
- **Findings do not live here.** Running the C1–C7 checks against a repo produces dated, per-repo results — record those in `reports/`, and keep this document to the durable method and the durable definitions.

