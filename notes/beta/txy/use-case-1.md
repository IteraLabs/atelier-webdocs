# Atelier Engine - Taxonomy Examples v0.1-beta-2

Illustrative companion to **`txy-v0.1-beta-2.md`**. This document shows how the terms defined in the normative taxonomy compose end-to-end. It is non-normative: any apparent conflict between a term used here and its definition in the main taxonomy is resolved in favor of the main taxonomy. Read this document to check your mental model, not to look up a definition.

The document has two sections:

- **Reading the System End-to-End** - a dense single-pass narrative that threads every taxonomy term in the order the system exercises them at runtime.
- **Use Case: Bring-Your-Own-Infra Market Data Collection (Service)** - a seven-step worked example that traces a concrete quant-research deployment from Session creation through a platform maintenance Drain.

---

## READING THE SYSTEM END-TO-END

A client opens a **Session**, within which the **Overseer** either **Deploys** a **Service** or **Runs** an **Experiment** by **Dispatching** a set of **Manifests**. Each Manifest **Binds** an **Agent** to a **Workspace** and references one or more **Tasks**, each **Assigned** to a **ComputeSlot** within a **Pipeline**. The Overseer gates every mutating operation through its **System Health** model: each operation declares which infrastructure subsystems it requires (persistent storage, message delivery, process spawning, event broadcast), and the Overseer rejects the operation if any required subsystem is unavailable. The webapp reflects the Overseer's health mode so the user knows which operations are available before attempting them.

The receiving Agent inspects each Task's required **Skills** against its own Skill set. If satisfied, the Agent accepts the Manifest and begins executing the Tasks. If any Task requires a Skill the Agent does not possess, the Agent rejects that Task and reports the mismatch through the **CommandChannel**.

**RemoteAgents** in **RemoteWorkspaces** **Register** through a **Gateway**, declaring their Skill sets (e.g., `{Ingest, Sync, Emit, Report}`). Registration is synchronous: the Gateway forwards the Registration to the Overseer on the CommandChannel's bidirectional stream, and the Overseer validates and responds before the Agent proceeds. **PlatformAgents** in **PlatformWorkspaces** are spawned by the **Overseer** and Register directly. Both follow the same lifecycle from this point forward.

Agents execute Tasks at their assigned **ComputeSlots**. RemoteAgents execute Tasks at **RemoteComputeSlots**, **Ingesting** from external sources. Raw data **Transits** through the **DataChannel** across the Gateway into **PlatformComputeSlots**, where PlatformAgents execute **Transform** Tasks.

At each ComputeSlot, Agents executing Tasks **Emit** **Artifacts** through **ArtifactChannels** into designated **Sinks**. Every Artifact carries an **Artifact ID**, a **Task ID**, and the **Service ID** or **Experiment ID** of its activation, enabling cross-Sink traceability.

Throughout, **Commands** (each with a **Command ID**) flow through the **CommandChannel**. Each Command carries a target: a **Task ID** for Task-scoped Commands that affect a single Task, or a **Binding ID** for Agent-scoped Commands that affect the Agent and all its active Tasks. Telemetry flows through the **TelemetryChannel**, keeping the Overseer informed and the client's webapp dashboard live.

When a Service is stopped or an Experiment completes, all Tasks are terminated, Bindings are released, Workspaces are destroyed, ComputeSlots become vacant, and the complete lineage - Manifests, Tasks, Artifacts, and operational history - is preserved under the Service ID or Experiment ID.

If the Overseer restarts, it enters **Recovery** before accepting new operations. Recovery reconciles persistent state against live infrastructure: stale Bindings are released, orphaned Services are stopped, pending Commands are re-delivered or timed out. RemoteAgents that were active before the restart reconnect through the Gateway and resume their Bindings. The system returns to a consistent state without requiring manual intervention.

If the platform requires a maintenance shutdown, the Overseer executes **Drain**: PlatformAgents are stopped (their infrastructure is going offline), while RemoteAgent Bindings are persisted in a `draining` state so they can be resumed after restart. The researcher's data collection continues on their own hardware; only the platform's monitoring and command capability is temporarily interrupted.

---

## USE CASE: Bring-Your-Own-Infra Market Data Collection (Service)

### Scenario

A quant researcher deploys a continuous market data collection pipeline on their own AWS server. They store raw data locally as Parquet files and monitor the Service from the Atelier webapp. This is operational infrastructure, not an exploratory experiment - it should run indefinitely.

### 1. Session and Service Creation

The researcher authenticates with the Atelier webapp. The Overseer checks that all infrastructure subsystems are available (persistent storage, message delivery, process spawning, event broadcast) and establishes:

- **Session** `SES-71` - resource envelope: up to 3 concurrent RemoteAgents, 2 Pipelines.

The researcher configures a data collection Service. The Overseer creates:

- **Pipeline** `PIP-30` - single-slot topology, one RemoteComputeSlot at position 0.
- **Service** `SVC-18` - unbounded activation of Pipeline `PIP-30`, scoped to Session `SES-71`.

### 2. Manifest, Task, and Binding Preparation

The researcher's configuration becomes:

- **Task** `TSK-401`:
  - Required Skills: `{Ingest, Sync, Emit, Report}`
  - TaskSpec: Binance futures, pairs: BTC-USDT and ETH-USDT, datatypes: orderbook (L2 depth 20) and trades, snapshot frequency: 100ms
  - ComputeSlot: RemoteComputeSlot at position 0 in Pipeline `PIP-30`
  - Sinks: ObjectSink (local Parquet at `/data/binance/`), TerminalSink (webapp live viewer)

- **Manifest** `MAN-201`:
  - Agent type: RemoteAgent
  - Workspace config: Binance futures, 2 pairs, 100ms frequency
  - Tasks: [`TSK-401`]

The Overseer Dispatches `MAN-201` through the ManifestChannel and provisions:

- **RemoteWorkspace** `RW-55` - scoped to Binance futures, 2 pairs, 100ms frequency.
- **RemoteComputeSlot** `CS-80` - position 0 in Pipeline `PIP-30`.
- **Binding** `BND-140` - pending, linking Agent to `RW-55` within Service `SVC-18`.
- **ObjectSink** `SNK-61` - Parquet writer targeting `/data/binance/`, scoped to `RW-55`.
- **TerminalSink** `SNK-62` - webapp live viewer, scoped to `RW-55`.

The Overseer generates a connection credential (JWT scoped to Session `SES-71`, Binding `BND-140`) and surfaces it in the webapp: the Gateway endpoint URL and the token.

### 3. Agent Registration and Skill Validation

The researcher deploys the IteraLabs Docker image on their AWS instance with `GATEWAY_URL` and `TOKEN` as environment variables.

**RemoteAgent** `RA-17` starts and connects outbound to **Gateway** `GW-2`. The Gateway authenticates the token (confirms Session `SES-71`, Binding `BND-140`) and bridges the gRPC stream into the platform's Channel infrastructure.

`RA-17` **Registers** within Session `SES-71`, declaring its Skill set: `{Ingest, Sync, Emit, Report}`. Registration is synchronous - the Gateway forwards the Registration on the CommandChannel stream to the Overseer, and the Overseer validates and responds on the same stream. The Overseer confirms that `RA-17`'s Skills satisfy Task `TSK-401`'s requirements (`{Ingest, Sync, Emit, Report}` ⊇ `{Ingest, Sync, Emit, Report}` - satisfied). The Overseer activates Binding `BND-140` and **Assigns** Task `TSK-401` to `RA-17` at RemoteComputeSlot `CS-80`.

Four Channels are established:

- **CommandChannel** `CH-301` - bidirectional, Overseer <-> `RA-17` via `GW-2`.
- **TelemetryChannel** `CH-302` - upstream, `RA-17` -> `GW-2` -> Overseer event bus.
- **ArtifactChannel** `CH-303` - local, `RA-17` -> ObjectSink `SNK-61`.
- **ArtifactChannel** `CH-304` - upstream, `RA-17` -> `GW-2` -> TerminalSink `SNK-62`.

### 4. Task Execution: Continuous Ingestion and Emission

`RA-17` begins executing Task `TSK-401`. Using its **Ingest** Skill, it opens 2 WSS connections to Binance futures (BTC-USDT, ETH-USDT), subscribes to L2 depth and trade streams. Using its **Sync** Skill, it aligns the incoming events to a 100ms clock and produces a consolidated orderbook snapshot each tick.

Each snapshot triggers two parallel **Emit** operations:

**Emit -> ObjectSink `SNK-61`**: Orderbook snapshots and trades are serialized into Parquet batches and written to `/data/binance/`. Each flush produces a **DataArtifact** (e.g., `ART-5001`: BTC-USDT orderbook, 14:00:00-14:00:10 UTC, 100 snapshots, 2.3 MB). Every DataArtifact carries Service ID `SVC-18`, Task ID `TSK-401`, and its own Artifact ID. ArtifactChannel `CH-303` is local - no data crosses the Gateway.

**Emit -> TerminalSink `SNK-62`**: Live event feed pushed upstream through ArtifactChannel `CH-304` to the webapp terminal viewer. These are ephemeral **LogsArtifacts** rendered in real time.

Using its **Report** Skill, `RA-17` streams telemetry continuously through **TelemetryChannel** `CH-302`: messages/sec, total events, reconnect count, uptime, ObjectSink `SNK-61` health (bytes written, files flushed, queue depth). The webapp renders this as a live Service dashboard for `SVC-18`.

Because this is a **Service** and not an Experiment, there is no expected end. The pipeline is designed to run indefinitely. DataArtifacts accumulate over hours, days, weeks - all tagged with `SVC-18` and `TSK-401`.

### 5. Operational Commands (Task-Scoped)

At 16:00 UTC, Binance announces scheduled maintenance. The researcher clicks "Pause Task" on `TSK-401` in the webapp:

- **Command** `CMD-88` (type: Pause, target: Task `TSK-401`).

This is a **Task-scoped Command**. The webapp encodes the target as `TSK-401`. The Overseer delivers the Command through **CommandChannel** `CH-301`: Overseer -> Gateway `GW-2` -> `RA-17`. The Agent identifies `TSK-401` among its active Tasks, halts that Task's WSS connections, and sends back an Acknowledgment referencing `CMD-88`. The webapp updates the Task's status to "Paused." If `RA-17` were executing a second Task `TSK-402` (e.g., trade streaming on a different pair), that Task would continue unaffected.

At 16:45 UTC, maintenance ends. The researcher clicks "Resume Task" on `TSK-401`:

- **Command** `CMD-89` (type: Resume, target: Task `TSK-401`).

`RA-17` resumes executing `TSK-401`, reconnects, and resumes Ingesting. A **LogsArtifact** `ART-5047` records the pause/resume gap with timestamps.

### 6. Delete (System Operation)

A week later, the researcher decides to stop collecting Binance data and wants to free the slot for a different exchange. The researcher clicks "Delete" on Agent `RA-17` in the webapp.

Delete is a System Operation, not a Command. The Overseer executes the full sequence:

1. **Command** `CMD-95` (type: Stop, target: Binding `BND-140` - Agent-scoped). Sent through CommandChannel `CH-301`. This is Agent-scoped because Delete tears down the entire Agent, not a single Task.
2. `RA-17` receives the Stop. It drains all buffered data, completes the in-progress Parquet flush (producing a final DataArtifact `ART-91000`), closes its WSS connections, and sends an Acknowledgment for `CMD-95`.
3. The Overseer receives the Acknowledgment. It releases Binding `BND-140` (status -> `released`), destroys RemoteWorkspace `RW-55`, and marks RemoteComputeSlot `CS-80` as vacant.
4. The Overseer updates Service `SVC-18` - since its only Binding is now released, the Service transitions to `stopped` with `stopped_at` set to now.
5. Channels `CH-301` through `CH-304` are closed.
6. The webapp receives a confirmation event and removes the Agent card. The Session's active agent count drops from 3/3 to 2/3. The researcher can now Deploy a new Service.

The complete lineage - all Manifests, Tasks, Artifacts (`ART-5001` through `ART-91000`), Commands (`CMD-88`, `CMD-89`, `CMD-95`), and Acknowledgments - is preserved under Service ID `SVC-18`.

### 7. Platform Maintenance (Drain)

Two weeks later, IteraLabs needs to deploy a backend update. The researcher now has two active Services: `SVC-22` (Bybit data, RemoteAgent `RA-19` on their AWS box) and `SVC-25` (a PlatformAgent `PA-3` doing data normalization).

The Overseer receives a shutdown signal and initiates **Drain**:

- **PlatformAgent `PA-3`**: The Overseer issues Command (Stop, Agent-scoped via Binding `BND-155`). `PA-3` drains its buffers, acknowledges, and the Overseer releases Binding `BND-155`. Service `SVC-25` is marked `stopped`.
- **RemoteAgent `RA-19`**: The Overseer does **not** Stop `RA-19` - it is running on the researcher's hardware, which is unaffected by the platform shutdown. Instead, the Overseer persists Binding `BND-150` as `draining` in persistent storage and closes its end of the Channels. `RA-19` detects the Channel closure, enters a reconnection loop, and continues writing Parquet locally via ObjectSink (ArtifactChannel `CH-310` is local, not affected by the platform being down).

The Overseer completes Drain and shuts down. The platform is updated. The new Overseer starts and enters **Recovery**:

1. **Binding reconciliation**: `BND-150` has status `draining`. The Overseer waits for `RA-19` to reconnect.
2. `RA-19`'s reconnection loop succeeds - it connects to the Gateway, which forwards the Registration to the new Overseer. The Overseer matches the Registration to `BND-150`, transitions the Binding back to `active`, and resumes telemetry and command flow.
3. **Service reconciliation**: `SVC-22` still has an active Binding. It remains `active`. `SVC-25`'s Binding was released during Drain - the Overseer can optionally re-spawn `PA-3` if `SVC-25` is configured for auto-recovery.

From the researcher's perspective: their Bybit data collection was never interrupted. The webapp showed "Platform maintenance - reconnecting..." for a few minutes, then the dashboard came back live. No data was lost.
