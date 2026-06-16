# Atelier Manifest - Body & Delivery Contract

Part of the **State Machine Atlas v0.1-beta-2**. SSoT for the Manifest TOML body shape, the `[metadata]` block contract, and the agent-side delivery path under the BYO-infra deploy model. Owns the `INV-M*` invariant prefix.

Cross-references:
- `proto-catalog-beta.md §control.proto` - wire-level `Manifest`, `TaskSpec`, `ManifestAck`, `AssignedTask` messages
- `schema-beta.md` table 7 (`manifests`) - persistence of the augmented body
- `sequences-beta.md §3.1.1` - SEQ-1 narrative; T-T1 at Phase A
- `binding-beta.md §2.3.2 B-T1` - composition + augmentation guard
- `task-beta.md §2.2.2 T-T1` - canonical `task_id` allocation at Phase A
- `agent-beta.md §2.1.2 A-T1` - agent receipt at gRPC handshake
- `overseer-beta.md §1.7` - boot reconciliation (server-internal)

---

**Delivery model - implemented vs. target.** This file describes the **handshake-delivery** model: the Gateway returns the augmented `manifests.body` to the agent in a `Gateway.Handshake` response (`HandshakeResult.toml_config`). That is the **target** shape. The **currently implemented wire** (`proto-catalog-beta.md §services.proto` + the SDK) delivers the Manifest over the **CommandChannel** - `Registration -> Manifest -> ManifestAck`, with the TOML body carried inside the `Manifest` message - and `services.proto` defines **no** `Handshake` RPC. Both are documented here: references below to `Gateway.Handshake` / `HandshakeResult.toml_config` describe the target shape, and the canonical `[[metadata.tasks]]` augmentation (§3, §4) is identical on either carrier, so the agent-side parse and the INV-M* invariants hold unchanged across both.

---

## 1. Why this file exists

The Manifest carries the operator's deploy intent from `POST /api/services` to the running Agent. Its body undergoes two transformations between submission and consumption, each with a different owner among the FSM files:

1. **Composition + augmentation** - operator-submitted TOML -> Overseer-composed body with platform-allocated IDs injected into a `[metadata]` block, including a `[[metadata.tasks]]` sub-array carrying canonical `task_id`(s). Happens during Phase A (`binding-beta.md §2.3.2 B-T1` + `task-beta.md §2.2.2 T-T1`).
2. **Delivery** - the persisted `manifests.body` is returned verbatim to the agent in the gRPC handshake response (`gateway-beta.md`, `agent-beta.md §2.1.2`, `proto-catalog-beta.md §services.proto`).

The composed-and-persisted body **is** the delivered body. There is no separate publication-time augmentation: the row in `manifests.body` already contains every field the agent needs.

Under v0.1-beta-2 BYO-infra the agent reads its Manifest from `HandshakeResult.toml_config` only. **The agent never speaks to Kafka or any other server-internal transport** - the Gateway is the trust boundary. Operator-facing surface area on the agent side is exactly two values: `ATELIER_GATEWAY_URL` + `ATELIER_TOKEN`.

A server-internal Kafka publish path on topic `control.manifests` exists (`control_publisher::publish_manifest`) and is preserved for future iterations (boot-reconciler republish, multi-Overseer-replica coordination, Gateway federation). For v0.1-beta-2 the publish is fire-and-forget and is **not load-bearing** - no agent or Gateway consumer depends on it. See §6.

---

## 2. Body lifecycle

### 2.1 Composition + augmentation (Phase A, B-T1 + T-T1)

At deploy time (`POST /api/services`) the Overseer's `Scheduler::deploy_service` walker performs the following inside a single transaction stack:

1. **Parse** operator-submitted `manifest_toml` (validates against the v0.1-beta-2 operator-input schema - `[collect]` + `[[workers]]`).
2. **Allocate** platform IDs: `service_id` (SV-T1), `binding_id` (B-T1 pre-allocation), `manifest_id` (composition).
3. **Inject `[metadata]` block** via `manifest_generator::inject_metadata` - `manifest_id`, `binding_id`, `service_id`.
4. **Fire `accept_task` (T-T1)** for every `TaskSpec` in the composed Manifest. Allocates one `tasks.task_id` UUIDv4 per spec entry; creates the `tasks` row at status `pending` (with `paused_at`, `running_at`, etc. unset).
5. **Inject `[[metadata.tasks]]`** via `manifest_generator::append_metadata_tasks` - emits one entry per `TaskSpec` carrying `manifest_task_id` (operator-correlation handle) and `task_id` (canonical UUIDv4 from step 4).
6. **Persist `manifests.body`** with the FULL augmented shape.

Phase B (`Scheduler::complete_bind`, fired on receipt of `AgentRegistered` over Kafka `lifecycle.events`) handles binding activation only: A-T1 -> A-T2 -> B-T3 -> A-T3 -> SV-T3. It does NOT touch the manifest body or fire `accept_task` - those happened atomically at Phase A.

**Spec deviation from `sequences-beta.md §3.1.1` step 23**: the spec narrative places T-T1 after `ManifestAck` (step 22) under the canonical gRPC `ManifestChannel` model. Under v0.1-beta-2 BYO-infra T-T1 fires during Phase A, so the body persisted at B-T1 already carries the canonical task_id. See `sequences-beta.md §3.1.1` BYO-infra note and §3.1.6 recovery semantics. INV-M3 (§4) codifies the deviation.

### 2.2 Persistence

`manifests.body JSONB NOT NULL` holds the FULL augmented body: operator-input fields, `idempotency_key`, the `[metadata]` table, and the `[[metadata.tasks]]` array. INV-M4 (§4) constrains: every read of `manifests.body` after the B-T1 commit observes the augmented shape - the body is never rewritten at runtime.

### 2.3 Delivery (gRPC handshake)

When the agent's RemoteAgent process boots (`atelier-sdk/atelier-agent`), it:

1. Reads `ATELIER_GATEWAY_URL` + `ATELIER_TOKEN` from env.
2. Extracts `(session_id, binding_id, service_id)` from the JWT claims locally (signature verified server-side at handshake).
3. Opens a gRPC connection to the Gateway and calls `handshake()` per `proto-catalog-beta.md §services.proto::Gateway.Handshake`.

The Gateway's handshake handler:
1. Validates the JWT.
2. Allocates the canonical `agent_id` (A-T1 per W1-1).
3. Returns `HandshakeResult { agent_id, binding_id, session_id, manifest_id, toml_config }` where `toml_config` is the persisted `manifests.body` for the binding, serialized as TOML bytes (the augmented shape per §2.2).

The agent's `RemoteAgent::run`:
1. Parses `toml_config` via `detect_manifest` (existing TOML -> DataWorker/MarketWorker type detection).
2. Parses the `[[metadata.tasks]]` block via `parse_metadata_tasks` to extract the canonical `task_id` for v0.1-beta-2's single Task per Manifest.
3. Plumbs `canonical_task_id` into `UpstreamSinkConfig.task_id` for every spawned worker.
4. Spawns workers. Subsequent `ArtifactFrame` emissions carry `ArtifactLineage.task_id = canonical_task_id` - INV-M1.

The agent's wire surface is gRPC-only: Gateway URL + JWT. No Kafka client, no Postgres client, no Overseer-direct calls.

### 2.4 Server-internal Kafka publish (a later version, non-load-bearing in v0.1-beta-2)

The Overseer's `control_publisher::publish_manifest` continues to publish the augmented body to Kafka topic `control.manifests` (compacted, keyed on `binding_id`) during Phase A - same body that lands in `manifests.body`. For v0.1-beta-2 this publish exists but is not load-bearing:

- No agent consumes it (agent gets the body from the handshake).
- The Gateway does not subscribe to it (handshake handler reads from `manifests.body` directly via Overseer-side query, not from Kafka).
- The mechanism is preserved for future iterations - see §6.

If `publish_manifest` fails at the broker layer, Phase A still succeeds - the body is persisted, the handshake will return it. The publish error is logged but not fatal. future work that depends on the topic (boot-reconciler republish, etc.) will need to revisit this trade-off.

---

## 3. `[metadata]` block

The block is appended to the operator-input body at Phase A by `manifest_generator::inject_metadata` (composition-time IDs) + `manifest_generator::append_metadata_tasks` (canonical task_ids). The resulting body is persisted verbatim and delivered verbatim.

### 3.1 `[metadata]` (flat table)

Three keys, all allocated by the Overseer during Phase A composition:

| Key            | Type      | Source                              | Notes                                                             |
|----------------|-----------|-------------------------------------|-------------------------------------------------------------------|
| `binding_id`   | UUIDv4    | Overseer at B-T1                    | FK target for `commands.target_id` when `target_kind='binding'`.  |
| `service_id`   | UUIDv4    | Overseer at SV-T1                   | Operator-side correlation; recoverable from `binding_id` via FK.  |
| `manifest_id`  | UUIDv4    | Overseer at composition             | Stable per Manifest row; agent uses it for log correlation only.  |

### 3.2 `[[metadata.tasks]]` (array-of-tables)

One entry per `TaskSpec` in the composed Manifest. v0.1-beta-2's single-Task Manifest restriction (B-T1 guard, `binding-beta.md §2.3.2`; taxonomy §Tasks) means the array length is always 1. Forward-compatible with multi-Task (later).

| Field              | Type      | Source                            | Notes                                                                                                |
|--------------------|-----------|-----------------------------------|------------------------------------------------------------------------------------------------------|
| `manifest_task_id` | string    | Operator-input correlation handle | Opaque to the platform; never FK'd (INV-M2). v0.1-beta-2 placeholder: `"task-0"` until operator-input task IDs land in a later version. |
| `task_id`          | UUIDv4    | Overseer at T-T1 (Phase A)        | Canonical `tasks.task_id`. FK target for `artifacts.task_id` (INV-M1) and `commands.target_id` when `target_kind='task'`. |

### 3.3 What is NOT in the block

Explicitly omitted, with rationale (architectural decisions, not oversights):

- **No `agent_id` / `agent_ref`** - under BYO-infra the agent is allocated at A-T1 by the Gateway when the agent registers (Phase B), AFTER the manifest body is persisted (Phase A). The agent learns its own `agent_id` from `RegistrationResponse.Accepted.agent_id`, not from the Manifest.
- **No `[[metadata.sinks]]`** - sinks under BYO-infra are agent-local resources (Parquet path on the agent's filesystem; TerminalSink on the agent's TCP socket; etc.). Sink identities are operator-declared in `[[sink]]` and not platform-allocated.
- **No `composed_at` / `transmitted_at`** - timing metadata lives in `manifests.composed_at` / `manifests.transmitted_at` columns; not load-bearing for the agent.
- **No `session_id`** - the agent receives `session_id` via the Envelope header on subsequent gRPC streams (`proto-catalog-beta.md §common.proto`).

### 3.4 Worked example

Operator-input TOML submitted to `POST /api/services`:

```toml
[collect]
exchange    = "binance"
market_type = "spot"

[collect.datatypes.orderbook]
enabled = true
depth   = 50

[collect.datatypes.trades]
enabled = true

[collect.sync]
sync_mode       = "on_trade"
flush_threshold = 36000

[[collect.output]]
type = "parquet"
dir  = "datasets/collected/binance/"

[[workers]]
symbol = "BTCUSDT"
```

Composition + augmentation (Phase A) yields the row stored at `manifests.body`:

```toml
[metadata]
manifest_id = "8a1f4d20-3b6e-4c2a-91f7-d6e2b5a847f3"
binding_id  = "5c8e9a02-1f3d-44b6-bf25-0a1e7c8b2f50"
service_id  = "f3a91d4c-7b2e-4810-93c5-ad7e2b6f4108"

[collect]
exchange    = "binance"
market_type = "spot"

[collect.datatypes.orderbook]
enabled = true
depth   = 50

# … operator-input body unchanged …

[[workers]]
symbol = "BTCUSDT"

[[metadata.tasks]]
manifest_task_id = "task-0"
task_id          = "7b3f1a8e-c2d4-4a9b-86e3-f1d5a09c4e72"
```

Delivery (Phase B handshake) returns this exact body verbatim in `HandshakeResult.toml_config`.

---

## 4. Invariants

All `INV-M*` invariants are owned by this file. Other files reference but do not re-define.

### INV-M1 - `[[metadata.tasks]].task_id` is the canonical FK target for `artifacts.task_id`

Agent emitters MUST populate `ArtifactLineage.task_id` (`proto-catalog-beta.md §data.proto`) with the `task_id` value from the active Manifest's `[[metadata.tasks]]` entry whose `manifest_task_id` matches the worker's operator-input task ID. Use of any other UUID - including agent-locally-minted UUIDs - violates the `artifacts_task_id_fkey` constraint.

*Testability:* sqlx integration test seeds a Service via `deploy_service`, drives an agent emission, asserts `SELECT count(*) FROM artifacts WHERE task_id = $expected` ≥ 1. Negative test: stub `UpstreamSink` to emit a fresh UUID and assert FK rejection.

### INV-M2 - `manifest_task_id` is opaque to the platform

`manifest_task_id` is operator-input vocabulary, echoed back in event payloads for operator-side correlation only. MUST NOT be FK'd against any persisted table, MUST NOT participate in any platform-allocation logic, and MUST NOT appear in any platform-emitted Envelope header.

*Testability:* `rg manifest_task_id atelier-lakehouse/overseer-db/migrations/` returns zero `REFERENCES` clauses.

### INV-M3 - `accept_task` (T-T1) MUST commit before `manifests.body` is persisted

Inside `Scheduler::deploy_service` (Phase A), the canonical `task_id` is allocated via `accept_task` BEFORE the augmented `manifests.body` is INSERTed. Mechanically: T-T1 commits the `tasks` row first; `append_metadata_tasks` reads the allocated UUID to build `[[metadata.tasks]]`; `INSERT INTO manifests` happens last, all inside one transaction stack.

This deviates from `sequences-beta.md §3.1.1` step 23 ordering (which places T-T1 after ManifestAck receipt). The deviation is scoped to the BYO-infra delivery path: the persisted body MUST already carry the canonical task_id at the moment the gRPC handshake handler reads it. The gRPC `ManifestChannel` path restores spec ordering via `ManifestAck.AssignedTask` - see §7.

*Testability:* sqlx integration test reads `manifests.body` after `deploy_service` returns successfully, parses `[[metadata.tasks]]`, asserts the `task_id` value matches `(SELECT task_id FROM tasks WHERE binding_id = $1)`.

### INV-M4 - `manifests.body` is the FULL augmented body (composition-time persistence)

Every row in `manifests` whose Phase A commit has succeeded carries the augmented shape: operator-input fields + `idempotency_key` + `[metadata]` table + `[[metadata.tasks]]` sub-array. Reads of `manifests.body` post-commit always observe the augmented shape. The body is never rewritten at runtime.

Rationale: BYO-infra delivery requires that `manifests.body` IS the body the agent will read at handshake. A two-stage (compose now, augment later) shape would require the Gateway's handshake handler to synthesize the augmented body on the fly - complexity without benefit. Phase A's transaction stack makes the augmented body the canonical persisted artifact.

*Testability:* sqlx test asserts `manifests.body::text LIKE '%metadata.tasks%'` AND `manifests.body::text LIKE '%[metadata]%'` for every row whose `binding_id IS NOT NULL`.

### INV-M5 - Agent hydrates canonical task_id at handshake completion (before worker spawn)

The Agent MUST parse `HandshakeResult.toml_config`'s `[[metadata.tasks]]` block before spawning any worker - and therefore before emitting any `ArtifactFrame`, `TaskTelemetry`, or other Envelope-carried message that references a `task_id`. The canonical `task_id` flows into `UpstreamSinkConfig.task_id` at config-build time inside `RemoteAgent::run()`.

Under handshake-delivery this invariant is trivial: the body is already in the agent's hand when `handshake().await` returns. No external transport wait, no race window between agent connect and first emit, no fail-loud timeout to tune.

*Testability:* unit test on `MarketWorker::from_config` asserts panic / Err if `canonical_task_id` is unset. Integration: simulate a handshake response with malformed `[[metadata.tasks]]`; assert agent process exits non-zero before any frame emission.

### INV-M6 - `control.manifests` topic is compacted (a-later-version only)

For the server-internal publish path (§2.4 / §6), the topic MUST have `cleanup.policy=compact`. For v0.1-beta-2 this is **informational only** - no agent or Gateway depends on the compacted semantics. future work that adds a consumer (boot reconciler, federation) will enforce this constraint at infrastructure setup.

*Testability:* future infrastructure assertion in the cluster-setup script.

### INV-M7 - Canonical `task_id` is stable across re-emissions

For a fixed `(binding_id, manifest_task_id)`, the canonical `task_id` remains stable across any re-emission of the Manifest body (Kafka republish from the boot reconciler, server-side body re-serialization, Overseer restart). The Overseer's T-T1 transition primitive is implemented as an upsert keyed on `(binding_id, manifest_task_id)` so the same `tasks.task_id` is returned across calls.

*Testability:* sqlx test - issue `deploy_service` for a fixed operator-input twice (idempotency_key collision raises 409); confirm that any republish path reads the same `tasks.task_id` value via the existing row.

### INV-M8 - Malformed `[[metadata.tasks]]` is fail-loud for the agent

The agent's `parse_metadata_tasks` returns a typed error (`ManifestParseError`) on any of: invalid TOML, missing `[metadata]` table, empty / missing `[[metadata.tasks]]`, non-UUID `task_id` field, missing `manifest_task_id` field. Inside `RemoteAgent::run` the parse failure is logged structured with `error_kind="MANIFEST_METADATA_MALFORMED"` and propagated via `?` to `main`, which exits the process non-zero.

Restart loop is the operator-visible signal; structured log gives the diagnostic context for the operator to forward. The agent never proceeds with synthetic / placeholder identifiers - that path is exactly the I4.5 PARTIAL regression.

*Testability:* unit tests on `parse_metadata_tasks` with 6+ corrupted fixtures (covered inline in `atelier-connect/src/remote_agent/orchestrator.rs`).

---

## 5. Failure & recovery

Simpler under handshake-delivery than under the prior Kafka-delivery model - Phase A's atomicity eliminates most of the race windows.

### 5.1 Overseer crash during Phase A

Phase A is a single transaction stack - either the FULL augmented body lands in `manifests.body` along with all the platform-allocated rows (`services`, `bindings`, `tasks`, `compute_slots`, `manifests`), or nothing lands. On restart, the boot reconciler (`overseer-beta.md §1.7`) sweeps partial state per existing semantics: `services` rows in `deploying` with no matching `bindings` row roll back to `stopped`; `bindings` in `pending` with valid grace timers stay pending.

The agent never sees a partially-composed body - the gRPC handshake either returns the full body or fails (binding not found / not pending).

### 5.2 Overseer crash between Phase A commit and Phase B activation

Bindings in `pending` with persisted (full augmented) `manifests.body` are recoverable. The boot reconciler resumes the binding activation cascade when the agent reconnects post-restart and triggers Phase B via `AgentRegistered`. The handshake re-reads `manifests.body` (now committed) and the agent receives the same body it would have on the pre-crash attempt.

### 5.3 Agent crash mid-handshake or pre-worker-spawn

If the agent crashes after receiving the handshake response but before spawning workers, no `ArtifactFrame` has been emitted. The Overseer-side state (`bindings`, `tasks`, `manifests`) is unchanged. On agent restart, the docker container re-runs `RemoteAgent::run` and the gRPC handshake re-fetches the same body - idempotent on the server side via `manifests.idempotency_key`.

### 5.4 Server-internal Kafka publish failure

If `control_publisher::publish_manifest` fails to ack from the broker (network blip, broker outage, etc.) during Phase A, the publish error is logged at WARN but does NOT roll back Phase A - `manifests.body` is persisted regardless. For v0.1-beta-2 this is acceptable because no agent or Gateway consumer depends on the topic. future work that wires consumers will revisit this trade-off.

### 5.5 Out of scope for v0.1-beta-2

- Manifest re-composition (operator deploys an updated body to an existing Binding) - single-Manifest-per-Binding for v0.1-beta-2 per `sequences-beta.md §3.1.7`.
- Schema evolution of the `[metadata]` / `[[metadata.tasks]]` block - additive only for v0.1-beta-2; renumbering bumps land in the sibling-directory mechanism (workspace `CLAUDE.md`).
- Server-internal Kafka consumer failure handling - when the topic becomes load-bearing.

---

## 6. Server-internal Kafka publication (future reference)

The Overseer publishes the augmented `manifests.body` to Kafka topic `control.manifests` during Phase A. The publish exists as scaffolding for future work; v0.1-beta-2 does not depend on it.

Topic configuration target (enforced at infrastructure setup once a consumer lands):

| Setting                      | Value                | Rationale                                                                                  |
|------------------------------|----------------------|--------------------------------------------------------------------------------------------|
| `cleanup.policy`             | `compact`            | INV-M6 - latest message per key (`binding_id`) wins                                        |
| `partitions`                 | ≥ 1                  | Single-partition acceptable for v0.1-beta-2                                                |
| `replication.factor`         | 1 (dev) / ≥ 3 (prod) | Standard Kafka durability                                                                  |
| `retention.ms`               | `-1` (infinite)      | Compaction handles cleanup                                                                 |
| `segment.bytes`              | `10485760` (10 MB)   | Small segments -> fast compaction for the low-volume Manifest stream                        |

Key format: UTF-8-encoded `binding_id` UUIDv4 string. Value format: UTF-8-encoded augmented TOML bytes - identical to the persisted `manifests.body`.

**Future consumers** (each lands its own iteration):
- **Boot-reconciler republish** - `overseer-beta.md §1.7` Step 1 could republish bindings in `pending` whose `manifests.transmitted_at IS NULL` for a Gateway-side cache.
- **Multi-replica coordination** - replicas observe Manifest state via the compacted topic.
- **Gateway federation** - multi-region Gateway deployments share Manifest state.

---

## 7. Wire-spec correspondence

The proto-catalog `Manifest` / `TaskSpec` / `ManifestAck` messages (`proto-catalog-beta.md §control.proto`) remain defined for the gRPC `ManifestChannel` path. Under v0.1-beta-2 BYO-infra the augmented TOML body delivered via `HandshakeResult.toml_config` is the actual carrier; the gRPC Manifest message and the `ManifestAck.AssignedTask` round-trip are reserved for future use.

Both shapes carry the same canonical-ID pairing:

| Wire-spec (gRPC, later)                  | v0.1-beta-2 (handshake-delivered TOML)        |
|----------------------------------------------|-----------------------------------------------|
| `Manifest.tasks[].task_id` (server-allocated on Ack) | `[[metadata.tasks]].task_id` (embedded in body) |
| `ManifestAck.Accepted.AssignedTask.manifest_task_id` | `[[metadata.tasks]].manifest_task_id`         |
| `ManifestAck.Accepted.AssignedTask.task_id`  | `[[metadata.tasks]].task_id`                  |

The v0.1-beta-2 path delivers the canonical pairing atomically in the handshake response, avoiding the `ManifestAck` round-trip and its accompanying timeout / retry mechanics.

---

## 8. Sibling edits

The following sibling files reference this SSoT. Each is a 1-3 line addition; no fact is restated:

- **`schema-beta.md` table 7 (`manifests`)** - inline comment: `body` holds the FULL augmented body per INV-M4; canonical `task_id` is recoverable via the join `manifests -> bindings -> tasks`. `## Cross-table invariants` section lists INV-M1, INV-M3, INV-M4 with `manifest-beta.md` pointers.
- **`sequences-beta.md §3.1.1`** - Phase A narrative includes `accept_task` (T-T1) + `[[metadata.tasks]]` injection. Step 17 BYO-infra note: handshake-delivery, no Kafka. §3.1.4 invariants table references INV-M3 / INV-M4. §3.1.6 recovery section: Phase A atomicity simplifies the crash-windows case.
- **`binding-beta.md §2.3.2 B-T1`** - Effects line: composition includes T-T1 + `[[metadata.tasks]]` injection; persisted body is the full augmented shape (INV-M4).
- **`agent-beta.md §2.1.2 A-T1`** - Effects line: handshake response carries the full augmented body; agent parses `[[metadata.tasks]]` at receipt; INV-M5 worker-spawn gate triggers from handshake completion, not Kafka.
- **`proto-catalog-beta.md §control.proto`** - status note on `Manifest`: v0.1-beta-2 uses `HandshakeResult.toml_config` for delivery; the gRPC `Manifest` message is reserved for the gRPC `ManifestChannel` path.
- **`overseer-beta.md §1.7`** - boot reconciler bullet: BYO-infra Manifest republish to Kafka is server-internal (later); v0.1-beta-2 reconciler preserves existing semantics.

---

## 9. Sources

- `proto-catalog-beta.md` - `Manifest`, `TaskSpec`, `ManifestAck`, `AssignedTask`, `HandshakeResult` wire messages
- `schema-beta.md` table 7 - `manifests` persistence
- `sequences-beta.md §3.1` - SEQ-1 Deploy narrative
- `binding-beta.md §2.3.2` - B-T1 composition + augmentation guard
- `task-beta.md §2.2.2` - T-T1 canonical `task_id` allocation (Phase A under BYO-infra)
- `agent-beta.md §2.1.2` - A-T1 registration + Manifest receipt
- `overseer-beta.md §1.7` - boot reconciliation
- `../txy/txy-beta.md §"BYO Market Data Collection"` - operator-side flow context
