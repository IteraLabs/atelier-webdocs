# FSM Atlas v0.1-beta-2 - Persistence Schema

Companion to `fsm-beta.md` and the per-FSM files (`overseer-beta.md`, `agent-beta.md`, `task-beta.md`, `binding-beta.md`, `service-beta.md`, `session-beta.md`, `compute-slot-beta.md`, `gateway-beta.md`, `channel-beta.md`, `sink-beta.md`). Defines the Postgres tables that hold state-bearing rows for every FSM declared in v0.1-beta-2.

Target: PostgreSQL 15+.
Extensions: `pgcrypto` (for `gen_random_uuid()`).

Twelve tables: `sessions`, `pipelines`, `compute_slots`, `workspaces`, `services`, `agents`, `manifests`, `bindings`, `tasks`, `artifacts`, `commands`, `channels`. Four promotions since the pre-plan's 8: `compute_slots` was added per Step 4 ComputeSlot FSM §2.8 (slot state mutates per activation and cannot live in the `pipelines.topology` JSONB without violating Pipeline-immutability); `artifacts` was promoted in v0.1-beta-2 from the deferred-tables list as lineage-only rows so that per-Service (`SVC-*`) Artifact lineage queries required by `../txy/txy-beta.md §4, §6` are durable without promoting payload content into Postgres; `commands` was promoted in v0.1-beta-2 so that `overseer-beta.md §1.7` reconciliation of stale `pending` Commands is durable across Overseer restart (previously in-memory); `channels` was promoted so that Channel identity, reliability class, sequence high-water mark, and `restart_epoch` survive Overseer restart (SEQ-4 Crash Recovery) and so that graceful Drain (SEQ-5) has a durable target to walk Draining -> Closed.

Conventions:

- IDs are UUIDv4, platform-generated.
- `alias` columns store the user-facing short ID (`RA-17`, `SES-71`, `SVC-18`, …) when assigned; aliases are auxiliary, never a primary key.
- States are `TEXT CHECK` rather than Postgres `ENUM` - adding/removing/renaming states is a single-statement constraint replacement; `ENUM` value mutation has known friction.
- Timestamps are `TIMESTAMPTZ`. Wall-clock authority is the Overseer host.
- Foreign keys default to `ON DELETE RESTRICT`. Service archival removes rows via an explicit job, not DB cascades.
- Every non-Session table carries `session_id` as the tenant-isolation column.
- `row_version BIGINT` on hot tables supports optimistic concurrency; the FSM driver includes `WHERE row_version = $N` in UPDATE clauses and retries on 0-row result.

---

## Schema

```sql
-- Atelier v0.1-beta-2 - Persistence Schema
-- Target: PostgreSQL 15+

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- =====================================================================
-- 1. sessions
--
-- Envelope-bearing outer scope. Session FSM §2.7.
-- =====================================================================

CREATE TABLE sessions (
    session_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alias               TEXT UNIQUE,                        -- e.g. 'SES-71'
    identity_id         UUID NOT NULL,                      -- external identity ref
    status              TEXT NOT NULL CHECK (status IN (
                            'created', 'active', 'expiring', 'expired', 'closed'
                        )),
    envelope            JSONB NOT NULL,                     -- {concurrent_services, concurrent_agents, throughput_*, ...}
    envelope_counters   JSONB NOT NULL DEFAULT '{}'::jsonb, -- current observed counts; authoritative
    issued_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    ttl_at              TIMESTAMPTZ NOT NULL,               -- issued_at + ttl
    expiry_warning_window INTERVAL NOT NULL DEFAULT '5 minutes',
    activated_at        TIMESTAMPTZ,
    expiring_at         TIMESTAMPTZ,
    expired_at          TIMESTAMPTZ,
    closed_at           TIMESTAMPTZ,
    expire_reason       TEXT CHECK (expire_reason IN (
                            'ttl_elapsed', 'auth_revoked', 'operator_force_close',
                            'compliance_kill', 'plan_revoked'
                        )),
    row_version         BIGINT NOT NULL DEFAULT 1,          -- optimistic concurrency
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX sessions_status_idx         ON sessions (status);
CREATE INDEX sessions_identity_id_idx    ON sessions (identity_id);
CREATE INDEX sessions_ttl_at_idx         ON sessions (ttl_at)
    WHERE status IN ('active', 'expiring');

-- Per-Session envelope-check row-lock uses `SELECT ... FOR UPDATE` on this row.
-- See INV-SN1 (atomicity backing IR-O4).


-- =====================================================================
-- 2. pipelines
--
-- Reusable structural topology. Referenced by multiple Services over time.
-- v0.1-beta-2: at most one concurrent activation per Pipeline (INV-CS3).
-- =====================================================================

CREATE TABLE pipelines (
    pipeline_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alias               TEXT UNIQUE,                        -- e.g. 'PIP-30'
    session_id          UUID NOT NULL REFERENCES sessions(session_id) ON DELETE RESTRICT,
    name                TEXT NOT NULL,
    topology            JSONB NOT NULL,                     -- ordered list of {slot_ordinal, input_schema, output_schema}
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (session_id, name)
);

CREATE INDEX pipelines_session_id_idx    ON pipelines (session_id);


-- =====================================================================
-- 3. compute_slots
--
-- Per-Pipeline position, state-bearing. ComputeSlot FSM §2.8.
-- =====================================================================

CREATE TABLE compute_slots (
    compute_slot_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id           UUID NOT NULL REFERENCES pipelines(pipeline_id) ON DELETE RESTRICT,
    slot_ordinal          INTEGER NOT NULL,
    input_schema          JSONB NOT NULL,                   -- pinned from pipeline.topology, immutable
    output_schema         JSONB NOT NULL,
    state                 TEXT NOT NULL CHECK (state IN (
                              'vacant', 'reserved', 'occupied', 'releasing', 'retired'
                          )),
    current_activation_id UUID,                             -- services.service_id (experiments (later version))
    current_task_id       UUID,                             -- tasks.task_id
    current_binding_id    UUID,                             -- bindings.binding_id
    reserved_at           TIMESTAMPTZ,
    occupied_at           TIMESTAMPTZ,
    releasing_at          TIMESTAMPTZ,
    released_at           TIMESTAMPTZ,
    row_version           BIGINT NOT NULL DEFAULT 1,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (pipeline_id, slot_ordinal),
    -- Field-fill consistency with state (INV-CS7). Defense-in-depth.
    CHECK (
        (state = 'vacant'    AND current_activation_id IS NULL
                             AND current_task_id       IS NULL
                             AND current_binding_id    IS NULL)
     OR (state = 'reserved'  AND current_activation_id IS NOT NULL
                             AND current_task_id       IS NULL
                             AND current_binding_id    IS NULL)
     OR (state = 'occupied'  AND current_activation_id IS NOT NULL
                             AND current_task_id       IS NOT NULL
                             AND current_binding_id    IS NOT NULL)
     OR (state = 'releasing' AND current_activation_id IS NOT NULL
                             AND current_task_id       IS NOT NULL
                             AND current_binding_id    IS NOT NULL)
     OR (state = 'retired'   AND current_activation_id IS NULL
                             AND current_task_id       IS NULL
                             AND current_binding_id    IS NULL)
    )
);

CREATE INDEX compute_slots_pipeline_id_idx ON compute_slots (pipeline_id);
CREATE INDEX compute_slots_state_idx       ON compute_slots (state);
-- Partial unique index enforces v0.1-beta-2 INV-CS3 single-activation lock:
CREATE UNIQUE INDEX compute_slots_pipeline_single_activation
    ON compute_slots (pipeline_id)
    WHERE current_activation_id IS NOT NULL;


-- =====================================================================
-- 4. workspaces
-- =====================================================================

CREATE TABLE workspaces (
    workspace_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alias               TEXT UNIQUE,                        -- e.g. 'WS-12'
    session_id          UUID NOT NULL REFERENCES sessions(session_id) ON DELETE RESTRICT,
    service_id          UUID NOT NULL,                      -- FK added after services table
    domain              TEXT NOT NULL CHECK (domain IN ('remote', 'platform')),
    config              JSONB NOT NULL,
    sinks               JSONB NOT NULL DEFAULT '[]'::jsonb, -- {sink_id, type, config, status}[]
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    destroyed_at        TIMESTAMPTZ
);

CREATE INDEX workspaces_session_id_idx ON workspaces (session_id);
CREATE INDEX workspaces_service_id_idx ON workspaces (service_id);


-- =====================================================================
-- 5. services
-- =====================================================================

CREATE TABLE services (
    service_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alias                   TEXT UNIQUE,                    -- e.g. 'SVC-18'
    session_id              UUID NOT NULL REFERENCES sessions(session_id) ON DELETE RESTRICT,
    pipeline_id             UUID NOT NULL REFERENCES pipelines(pipeline_id) ON DELETE RESTRICT,
    workspace_id            UUID REFERENCES workspaces(workspace_id) ON DELETE RESTRICT,
    agent_type              TEXT NOT NULL CHECK (agent_type IN ('remote', 'platform')),
    status                  TEXT NOT NULL CHECK (status IN (
                                'provisioning', 'deploying', 'active', 'updating',
                                'stopping', 'stopped', 'archived'
                            )),
    stopped_reason_intent   TEXT CHECK (stopped_reason_intent IN (
                                'operator_stop', 'drain', 'delete_last_agent',
                                'session_expired', 'operator_force_close'
                            )),
    stopped_reason          TEXT CHECK (stopped_reason IN (
                                'deploy_canceled', 'subsystem_loss',
                                'session_envelope_invalidated', 'spawn_failed',
                                'manifest_rejected', 'dispatch_timeout',
                                'operator_stop', 'drain', 'delete_last_agent',
                                'session_expired', 'operator_force_close',
                                'auto_stop'
                            )),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    activated_at            TIMESTAMPTZ,
    stopping_at             TIMESTAMPTZ,
    stopped_at              TIMESTAMPTZ,
    archived_at             TIMESTAMPTZ,
    row_version             BIGINT NOT NULL DEFAULT 1
);

CREATE INDEX services_session_id_idx       ON services (session_id);
CREATE INDEX services_pipeline_id_idx      ON services (pipeline_id);
CREATE INDEX services_status_idx           ON services (status);
-- Session envelope counter query path:
CREATE INDEX services_envelope_active_idx  ON services (session_id)
    WHERE status IN ('provisioning', 'deploying', 'active', 'updating', 'stopping');

-- Late FK from workspaces.service_id:
ALTER TABLE workspaces
    ADD CONSTRAINT workspaces_service_id_fkey
    FOREIGN KEY (service_id) REFERENCES services(service_id) ON DELETE RESTRICT
    DEFERRABLE INITIALLY DEFERRED;


-- =====================================================================
-- 6. agents
-- =====================================================================

CREATE TABLE agents (
    agent_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alias               TEXT UNIQUE,                        -- e.g. 'RA-17', 'PA-3'
    session_id          UUID NOT NULL REFERENCES sessions(session_id) ON DELETE RESTRICT,
    agent_type          TEXT NOT NULL CHECK (agent_type IN ('remote', 'platform')),
    skills              JSONB NOT NULL,                     -- list of Skill trait names
    host_identity       JSONB,
    status              TEXT NOT NULL CHECK (status IN (
                                'registered', 'ready', 'bound', 'restarting',
                                'lost', 'draining', 'terminated'
                            )),
    restart_epoch       INTEGER NOT NULL DEFAULT 0,         -- increments on A-T8 {Ready, Bound} -> Restarting (soft restart, INV-A1)
    registered_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_heartbeat_at   TIMESTAMPTZ,
    lost_at             TIMESTAMPTZ,
    prior_status        TEXT,                               -- status before A-T11/A-T12 entered Lost/Draining; A-T14 restores it; lost-grace sweep selects the grace window by it (impl: 20260604000003_i5_agent_prior_status)
    terminated_at       TIMESTAMPTZ,
    terminated_reason   TEXT CHECK (terminated_reason IN (
                                'operator_stop', 'session_expired', 'plan_revoked',
                                'platform_teardown', 'registration_expired',
                                'reconcile_orphaned',
                                -- Added by migration 20260510000000_i4_4_skill_mismatch
                                -- (A-T15 agent_lost path; A-T18 skill_mismatch).
                                'agent_lost', 'skill_mismatch',
                                -- migration 20260604000002: timeout-expiry reasons
                                -- (timeouts-beta.md §T.2) - reconnect_grace_timeout
                                -- (A-T15 grace expiry, agent.reconnect_grace_ms),
                                -- drain_timeout (A-T7, agent.drain_budget_ms), and
                                -- restart_budget_exceeded (Restart re-init bound,
                                -- task.stop_drain_timeout_ms) - written by the impl
                                -- but not previously admitted by this CHECK.
                                'reconnect_grace_timeout',
                                'drain_timeout', 'restart_budget_exceeded'
                            )),
    row_version         BIGINT NOT NULL DEFAULT 1,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX agents_session_id_idx         ON agents (session_id);
CREATE INDEX agents_status_idx             ON agents (status);
CREATE INDEX agents_envelope_active_idx    ON agents (session_id)
    WHERE status IN ('registered', 'ready', 'bound', 'restarting', 'lost', 'draining');


-- =====================================================================
-- 7. manifests
-- =====================================================================

CREATE TABLE manifests (
    manifest_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alias               TEXT UNIQUE,                        -- e.g. 'MAN-201'
    session_id          UUID NOT NULL REFERENCES sessions(session_id) ON DELETE RESTRICT,
    service_id          UUID NOT NULL REFERENCES services(service_id) ON DELETE RESTRICT,
    binding_id          UUID,                               -- FK added after bindings table
    idempotency_key     UUID NOT NULL UNIQUE,               -- per ManifestChannel exactly-once
    body                JSONB NOT NULL,
    composed_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- v0.1-beta-2 (deprecation-pending under handshake-delivery):
    -- transmitted_at tracked the Manifest's wire-emission time under the
    -- canonical gRPC ManifestChannel model (`proto-catalog-beta.md §control.proto`).
    -- Under BYO-infra (v0.1-beta-2) the body is delivered via the gRPC
    -- handshake response synchronously, so there is no asynchronous
    -- transmission event to timestamp; the column is set by the server-
    -- internal Kafka publish (`control_publisher::publish_manifest`,
    -- Phase A) as a best-effort breadcrumb, but no agent or Gateway
    -- path consumes it for v0.1-beta-2. Retained for the gRPC
    -- ManifestChannel revival and a later version Kafka consumers (boot
    -- reconciler republish, federation) where it regains load-bearing
    -- semantics. See `manifest-beta.md §2.4` and §6.
    transmitted_at      TIMESTAMPTZ,
    acked_at            TIMESTAMPTZ,
    ack_result          TEXT CHECK (ack_result IN ('accepted', 'rejected')),
    rejection_reason    TEXT,
    archived_as_artifact_id UUID                            -- ManifestArtifact reference; FK added after artifacts table
);

CREATE INDEX manifests_service_id_idx ON manifests (service_id);
CREATE INDEX manifests_binding_id_idx ON manifests (binding_id);

-- Body shape: `body` (above) holds the FULL augmented Manifest body per
-- INV-M4 - operator-input fields + `idempotency_key` + `[metadata]` table
-- (composition-time IDs: manifest_id, binding_id, service_id) + the
-- `[[metadata.tasks]]` sub-array carrying canonical `tasks.task_id`
-- UUIDv4(s) allocated at T-T1 inside Phase A. The body is persisted
-- ONCE at the B-T1 transaction commit and never rewritten at runtime.
-- The Gateway's gRPC handshake returns this body verbatim to the agent
-- in `HandshakeResult.toml_config` (`agent-beta.md §2.1.2`, `manifest-beta.md §2.3`).
-- See `manifest-beta.md` for the full body & delivery contract (INV-M1..INV-M8).


-- =====================================================================
-- 8. bindings
-- =====================================================================

CREATE TABLE bindings (
    binding_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alias               TEXT UNIQUE,                        -- e.g. 'BND-140'
    session_id          UUID NOT NULL REFERENCES sessions(session_id) ON DELETE RESTRICT,
    service_id          UUID NOT NULL REFERENCES services(service_id) ON DELETE RESTRICT,
    agent_id            UUID REFERENCES agents(agent_id) ON DELETE RESTRICT,  -- nullable since w4a_byo_infra: BYO-infra SEQ-1 Phase A creates the Binding before A-T1; gateway_consumer patches agent_id at Registration; B-T2 grace leaves it NULL on released rows
    workspace_id        UUID NOT NULL REFERENCES workspaces(workspace_id) ON DELETE RESTRICT,
    manifest_id         UUID NOT NULL REFERENCES manifests(manifest_id) ON DELETE RESTRICT,
    status              TEXT NOT NULL CHECK (status IN (
                                'pending', 'active', 'draining', 'releasing', 'released'
                            )),
    -- Aligned to `binding-beta.md §2.3.1` release_reason enum (Atlas precedence).
    -- Dropped (not written by any current FSM transition):
    --   'task_completed' (redundant with 'normal'),
    --   'drain'          (SEQ-5 concept, not written at Binding level in v0.1),
    --   'session_expired'(Session/Service-level concept; cascades to Binding
    --                     via B-T4 -> B-T6 / B-T7 which set normal/force/agent_lost),
    --   'delete_agent'   (SEQ-2 Delete uses 'operator_stop' instead).
    -- Added in v0.1-beta-2:
    --   'registration_grace_timeout' (B-T2 grace path - `bindings.pending_grace_ms`
    --                                 expired without a Registration arriving;
    --                                 BYO-infra path).
    release_reason      TEXT CHECK (release_reason IN (
                                'normal', 'operator_stop', 'force',
                                'agent_lost', 'task_rejected', 'task_failed',
                                'registration_grace_timeout'
                            )),
    -- migration 20260604000004: distinguishes a
    -- recoverable platform-drain `draining` Binding (SEQ-5 O-T6, RemoteAgent
    -- keeps running, SEQ-4 resumes it) from a delete-drain `draining`
    -- Binding (SEQ-2, headed for release). NULL unless status='draining'.
    draining_reason     TEXT CHECK (draining_reason IN (
                                'operator_stop', 'platform_drain'
                            )),
    pending_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    active_at           TIMESTAMPTZ,
    draining_at         TIMESTAMPTZ,
    releasing_at        TIMESTAMPTZ,
    released_at         TIMESTAMPTZ,
    container_id        TEXT,                               -- PlatformAgent DockerSpawner container handle (impl: 20260607000001_i5_binding_container_id)
    row_version         BIGINT NOT NULL DEFAULT 1
);

CREATE INDEX bindings_session_id_idx       ON bindings (session_id);
CREATE INDEX bindings_service_id_idx       ON bindings (service_id);
CREATE INDEX bindings_agent_id_idx         ON bindings (agent_id);
CREATE INDEX bindings_status_idx           ON bindings (status);
-- Service's in-flight Binding set query (supports INV-SV1 counts):
CREATE INDEX bindings_service_active_idx   ON bindings (service_id)
    WHERE status IN ('pending', 'active', 'draining', 'releasing');

-- Late FK from manifests.binding_id:
ALTER TABLE manifests
    ADD CONSTRAINT manifests_binding_id_fkey
    FOREIGN KEY (binding_id) REFERENCES bindings(binding_id) ON DELETE RESTRICT
    DEFERRABLE INITIALLY DEFERRED;


-- =====================================================================
-- 9. tasks
-- =====================================================================

CREATE TABLE tasks (
    task_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alias               TEXT UNIQUE,                        -- e.g. 'TSK-88'
    session_id          UUID NOT NULL REFERENCES sessions(session_id) ON DELETE RESTRICT,
    service_id          UUID NOT NULL REFERENCES services(service_id) ON DELETE RESTRICT,
    binding_id          UUID NOT NULL REFERENCES bindings(binding_id) ON DELETE RESTRICT,
    compute_slot_id     UUID NOT NULL REFERENCES compute_slots(compute_slot_id) ON DELETE RESTRICT,
    skill               TEXT NOT NULL CHECK (skill IN (
                                'ingest', 'sync', 'transform', 'emit', 'report'
                            )),
    task_spec           JSONB NOT NULL,
    -- Aligned to `task-beta.md §2.2.1` FSM states (Atlas precedence).
    -- Dropped (command-in-flight phases; atomic in the FSM driver, never persisted):
    --   'pausing', 'resuming', 'completing'.
    -- Renamed: 'submitted' -> 'pending' (FSM state name);
    --          'canceled'  -> 'rejected' (FSM terminal state via T-T2 / B-T10).
    -- Added:   'restarting', 'stopping' (real FSM states written by T-T8, T-T12).
    -- ('TASK_CANCEL' and 'TaskCanceled' on the wire have no matching FSM
    --  state; TASK_CANCEL resolves via T-T8 -> T-T9/T-T10.)
    status              TEXT NOT NULL CHECK (status IN (
                                'pending', 'accepted', 'running', 'paused',
                                'restarting', 'stopping', 'completed',
                                'failed', 'rejected'
                            )),
    failure_reason      TEXT,
    pending_at          TIMESTAMPTZ NOT NULL DEFAULT now(),   -- was submitted_at
    accepted_at         TIMESTAMPTZ,
    running_at          TIMESTAMPTZ,
    paused_at           TIMESTAMPTZ,                          -- T-T4 entry; NOT cleared by T-T5 resume (impl: 20260429000000_w4b_paused_at)
    stopping_at         TIMESTAMPTZ,                          -- T-T8 entry; drain-duration queries
    completed_at        TIMESTAMPTZ,
    failed_at           TIMESTAMPTZ,
    rejected_at         TIMESTAMPTZ,                          -- was canceled_at
    row_version         BIGINT NOT NULL DEFAULT 1
);

CREATE INDEX tasks_session_id_idx         ON tasks (session_id);
CREATE INDEX tasks_service_id_idx         ON tasks (service_id);
CREATE INDEX tasks_binding_id_idx         ON tasks (binding_id);
CREATE INDEX tasks_compute_slot_id_idx    ON tasks (compute_slot_id);
CREATE INDEX tasks_status_idx             ON tasks (status);


-- =====================================================================
-- 10. artifacts
--
-- Lineage-only Artifact rows. v0.1-beta-2 stores identity, lineage, and
-- pointer metadata for DataArtifact, LogsArtifact, ModelArtifact emitted
-- by Agents and ManifestArtifact emitted by the Overseer. Payload content
-- lives at the Sink (local Parquet, webapp TerminalSink buffer, archive
-- store); this table stores what is needed to join across Sinks and to
-- answer the use-case's "all Artifacts under SVC-18" lineage queries.
--
-- Agent-emitted wire format:   ArtifactFrame         (proto-catalog-beta.md §data.proto)
-- Overseer-emitted wire format: ManifestArtifactFrame (proto-catalog-beta.md §data.proto)
--
-- **Insertion path.** Agent-emitted Artifact rows are
-- written by the Overseer's `artifact.frames` Kafka consumer
-- (`atelier-overseer/src/queue/gateway_consumer.rs::consume_artifacts`)
-- on receipt of a metadata-only ArtifactFrame from the SDK. The Gateway
-- forwards the frame to Kafka via `build_envelope_json` which extracts
-- the lineage block. The consumer's INSERT is
-- idempotent on the partial unique index
-- `artifacts_task_epoch_sequence_idx (task_id, restart_epoch, sequence)
-- WHERE task_id IS NOT NULL` via `ON CONFLICT DO NOTHING` so duplicate
-- Kafka delivery from at-least-once semantics is a no-op.
-- ManifestArtifact rows (kind='manifest') are inserted by the Overseer
-- directly at T-T1 manifest archival; they don't traverse Kafka.
-- =====================================================================

CREATE TABLE artifacts (
    artifact_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id              UUID NOT NULL REFERENCES sessions(session_id) ON DELETE RESTRICT,
    service_id              UUID NOT NULL REFERENCES services(service_id) ON DELETE RESTRICT,
    -- task_id is NULL for kind='manifest' (Overseer-emitted, no Task scope)
    -- and NOT NULL for all Agent-emitted kinds per taxonomy §Artifacts
    -- ("Agent-produced Artifacts additionally carry a Task ID").
    task_id                 UUID REFERENCES tasks(task_id) ON DELETE RESTRICT,
    kind                    TEXT NOT NULL CHECK (kind IN (
                                'data', 'logs', 'model', 'manifest'
                            )),
    -- sink_id is left unconstrained: `sinks` remains a deferred table
    -- (workspaces.sinks JSONB is the authoritative Sink-set in beta).
    -- When `sinks` is promoted, a late FK can be added here.
    sink_id                 UUID,
    datatype                TEXT,                           -- nullable for kind='manifest'
    restart_epoch           INTEGER NOT NULL DEFAULT 0,     -- echoes Task.restart_epoch (§2.1.5)
    sequence                BIGINT NOT NULL DEFAULT 0,      -- per-(task_id, restart_epoch) monotone for Agent-emitted; 0 for kind='manifest'
    payload_schema_ref      TEXT,                           -- names the out-of-band payload schema (Parquet / Arrow / JSON / manifest format)
    payload_size_bytes      BIGINT,                         -- observability; NULL if unknown at emit time
    payload_uri             TEXT,                           -- optional Sink pointer (e.g. 's3://...', 'file:///data/binance/...')
    partial                 BOOLEAN NOT NULL DEFAULT false, -- set when flush exceeded stop_drain_timeout (taxonomy §Artifacts)
    emitted_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Pointer back to the archived Manifest row, only for kind='manifest'.
    archived_manifest_id    UUID REFERENCES manifests(manifest_id) ON DELETE RESTRICT,
    -- Field-fill consistency with kind. Defense-in-depth.
    CHECK (
        (kind = 'manifest' AND task_id IS NULL  AND archived_manifest_id IS NOT NULL)
     OR (kind IN ('data', 'logs', 'model')
                           AND task_id IS NOT NULL
                           AND archived_manifest_id IS NULL)
    )
);

CREATE INDEX artifacts_session_id_idx  ON artifacts (session_id);
CREATE INDEX artifacts_service_id_idx  ON artifacts (service_id);
CREATE INDEX artifacts_emitted_at_idx  ON artifacts (emitted_at);  -- time-range lineage scans (impl: 20260606000001_artifacts_emitted_at_idx)
CREATE INDEX artifacts_task_id_idx     ON artifacts (task_id)
    WHERE task_id IS NOT NULL;
-- Per-Task ordering and Recovery resume-from-epoch scans:
CREATE UNIQUE INDEX artifacts_task_epoch_sequence_idx
    ON artifacts (task_id, restart_epoch, sequence)
    WHERE task_id IS NOT NULL;
-- ManifestArtifact lookup by archived Manifest:
CREATE INDEX artifacts_archived_manifest_id_idx
    ON artifacts (archived_manifest_id)
    WHERE archived_manifest_id IS NOT NULL;

-- Late FK from manifests.archived_as_artifact_id -> artifacts.artifact_id:
ALTER TABLE manifests
    ADD CONSTRAINT manifests_archived_as_artifact_id_fkey
    FOREIGN KEY (archived_as_artifact_id) REFERENCES artifacts(artifact_id) ON DELETE RESTRICT
    DEFERRABLE INITIALLY DEFERRED;


-- =====================================================================
-- 11. commands
--
-- Durable request/ack log for every Command issued by the Overseer. Backs
-- `overseer-beta.md §1.7` reconciliation of stale `pending` Commands across
-- Overseer restart (step 2 of the reconciliation sequence: "Query
-- Persistent Storage for all Commands with status='pending'"). Also
-- supports audit, at-least-once re-delivery, and idempotency-on-retry
-- keyed by `command_id`.
--
-- Wire shape:  `Command` (`proto-catalog-beta.md §control.proto`) -
--              `CommandKind kind`, `oneof target { SessionTarget, ServiceTarget,
--              AgentTarget, BindingTarget, TaskTarget }`, `google.protobuf.Struct
--              params`. Target polymorphism is persisted as (`target_kind`,
--              `target_id`) - the target_id is the `{session|service|agent|
--              binding|task}_id` UUID from the oneof body.
-- =====================================================================

CREATE TABLE commands (
    command_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id          UUID NOT NULL REFERENCES sessions(session_id) ON DELETE RESTRICT,
    -- CommandKind mirrors `proto-catalog-beta.md §control.proto CommandKind`.
    -- 14 spec'd verbs in v0.1-beta-2; CHECK keeps persisted values
    -- aligned with the wire catalog.
    kind                TEXT NOT NULL CHECK (kind IN (
                            'session_renew', 'session_force_close',
                            'service_create', 'service_deploy',
                            'service_stop', 'service_archive',
                            'agent_drain', 'agent_restart', 'agent_terminate',
                            'binding_release',
                            'task_start', 'task_pause', 'task_resume',
                            'task_complete', 'task_cancel'
                        )),
    -- target is polymorphic per Command.oneof. Persist as (kind, id).
    target_kind         TEXT NOT NULL CHECK (target_kind IN (
                            'session', 'service', 'agent', 'binding', 'task'
                        )),
    target_id           UUID NOT NULL,
    params              JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- Command lifecycle. Separate from the ack outcome:
    --   pending  - persisted at issue, not yet acked
    --   acked    - CommandAck.Accepted received; Command ran on the target
    --   rejected - CommandAck.rejected received (Error carries ErrorKind)
    --   timeout  - `command_timeout` elapsed with no ack
    --                (set by `overseer-beta.md §1.7` step 2 for pre-crash Commands,
    --                 or by the dispatcher on a live timeout)
    --   failed   - internal dispatch failure (e.g., SPAWN_FAILED,
    --                CHANNEL_OPEN_FAILED) before the Command reached the target
    status              TEXT NOT NULL CHECK (status IN (
                            'pending', 'acked', 'rejected', 'timeout', 'failed'
                        )),
    -- Ack echo. Populated on terminal transitions.
    ack_error_kind      TEXT,                               -- mirrors ErrorKind name when status='rejected'
    ack_message         TEXT,                               -- free-form from Error.message; not a parse target
    correlation_id      UUID,                               -- envelope_id of the ack envelope, where known
    issued_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    dispatched_at       TIMESTAMPTZ,                        -- written on wire send (RemoteAgent) or in-process handoff (PlatformAgent)
    acked_at            TIMESTAMPTZ,                        -- set on entry to acked/rejected
    completed_at        TIMESTAMPTZ,                        -- set on entry to any terminal status
    row_version         BIGINT NOT NULL DEFAULT 1,
    -- Lifecycle consistency (defense-in-depth; primary enforcement in FSM driver).
    CHECK (
        (status = 'pending'   AND acked_at IS NULL AND completed_at IS NULL)
     OR (status = 'acked'     AND acked_at IS NOT NULL AND completed_at IS NOT NULL)
     OR (status = 'rejected'  AND acked_at IS NOT NULL AND completed_at IS NOT NULL
                              AND ack_error_kind IS NOT NULL)
     OR (status = 'timeout'   AND completed_at IS NOT NULL)
     OR (status = 'failed'    AND completed_at IS NOT NULL
                              AND ack_error_kind IS NOT NULL)
    )
);

CREATE INDEX commands_session_id_idx   ON commands (session_id);
CREATE INDEX commands_target_idx       ON commands (target_kind, target_id);
CREATE INDEX commands_status_idx       ON commands (status);
-- Reconciliation sweep (`overseer-beta.md §1.7` step 2) scans pending Commands:
CREATE INDEX commands_pending_issued_idx
    ON commands (issued_at)
    WHERE status = 'pending';

-- =====================================================================
-- TABLE 12: channels
--
-- Durable Channel identity + provisioning/drain state. Promoted from the
-- deferred list so that Channel identity, reliability
-- class, sequence high-water mark, and restart_epoch survive Overseer
-- restart (SEQ-4 Crash Recovery) and so that graceful Drain (SEQ-5) has a
-- durable target to walk through Draining -> Closed.
--
-- Scope note: `channel-beta.md §2.10` specifies Opening/Open as normative and
-- enumerates Draining/Backpressured/Error/Closed/Failed. Draining, Closed,
-- and Failed are normative (CH-T3, CH-T4, CH-T10) for the Drain/Recovery
-- path; Backpressured and Error remain enumerated-only. The CHECK below
-- admits the full set so a later
-- promotion of Backpressured/Error needs no migration.
--
-- Wire shape: Channels are transport-level; there is no single proto
-- message. Identity is (category, channel_id); reliability class per
-- `channel-beta.md §2.10.3`.
-- =====================================================================

CREATE TABLE channels (
    channel_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id          UUID NOT NULL REFERENCES sessions(session_id) ON DELETE RESTRICT,
    -- The Binding whose lifecycle scopes this Channel. Kept nullable for
    -- the Gateway-control Channel promotion path (later); every Channel
    -- in v0.1-beta-2 is opened under a Binding.
    binding_id          UUID REFERENCES bindings(binding_id) ON DELETE RESTRICT,
    agent_id            UUID REFERENCES agents(agent_id) ON DELETE RESTRICT,
    -- Channel category per taxonomy (HOW §Channels) / `channel-beta.md §2.10`.
    category            TEXT NOT NULL CHECK (category IN (
                            'command', 'manifest', 'telemetry', 'data', 'artifact'
                        )),
    -- Transport direction. ManifestChannel is embedded in CommandChannel
    -- (INV-CH6) but persisted as its own row for reliability accounting.
    direction           TEXT NOT NULL CHECK (direction IN (
                            'upstream', 'downstream', 'bidirectional', 'lateral', 'local'
                        )),
    -- Reliability class per `channel-beta.md §2.10.3`. Immutable after Open
    -- (INV-CH3).
    reliability_class   TEXT NOT NULL CHECK (reliability_class IN (
                            'at_least_once_ack',
                            'exactly_once_idempotency',
                            'best_effort_sequence',
                            'at_least_once_sequence_gap',
                            'sink_class'
                        )),
    -- Provisioning + drain lifecycle. Opening/Open normative since beta;
    -- Draining/Closed/Failed promoted to normative;
    -- Backpressured/Error enumerated-only (admitted for forward-compat).
    status              TEXT NOT NULL CHECK (status IN (
                            'opening', 'open',
                            'draining', 'closed', 'failed',
                            'backpressured', 'error'
                        )),
    -- exactly-once channels (ManifestChannel) reserve an idempotency key;
    -- NULL for other classes. UNIQUE-WHERE-NOT-NULL enforces the
    -- exactly-once reservation (INV-CH6).
    idempotency_key     UUID,
    -- restart_epoch backs INV-CH5: Gateway-persistent Channels survive
    -- A-T8 Restart without cycling transport; the epoch increments while
    -- the same Channel row + sequence continuation persists.
    restart_epoch       BIGINT NOT NULL DEFAULT 0,
    -- Sequence high-water mark for sequence-bearing classes (Telemetry,
    -- Data, Artifact-with-sequence). NULL for ack-only / idempotency
    -- classes. Backs INV-CH4 monotonicity and SEQ-4 resync.
    sequence_high       BIGINT,
    -- ArtifactChannel target Sink. Unconstrained while `sinks` stays a
    -- deferred table (mirrors the `workspaces.sinks` JSONB convention).
    sink_id             UUID,
    opened_at           TIMESTAMPTZ,                        -- set on entry to open (CH-T2)
    drain_started_at    TIMESTAMPTZ,                        -- set on entry to draining (CH-T3)
    closed_at           TIMESTAMPTZ,                        -- set on entry to closed/failed
    last_seen_at        TIMESTAMPTZ,                        -- updated per frame; SEQ-4 staleness probe
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    row_version         BIGINT NOT NULL DEFAULT 1,
    -- Lifecycle consistency (defense-in-depth; primary enforcement in FSM driver).
    CHECK (
        (status = 'opening'       AND opened_at IS NULL)
     OR (status IN ('open', 'backpressured', 'error')
                                  AND opened_at IS NOT NULL AND closed_at IS NULL)
     OR (status = 'draining'      AND opened_at IS NOT NULL
                                  AND drain_started_at IS NOT NULL AND closed_at IS NULL)
     OR (status IN ('closed', 'failed')
                                  AND closed_at IS NOT NULL)
    )
);

CREATE INDEX channels_session_id_idx   ON channels (session_id);
CREATE INDEX channels_binding_id_idx   ON channels (binding_id);
CREATE INDEX channels_agent_id_idx     ON channels (agent_id);
CREATE INDEX channels_status_idx       ON channels (status);
-- exactly-once idempotency-key reservation (INV-CH6 ManifestChannel):
CREATE UNIQUE INDEX channels_idempotency_key_uniq
    ON channels (idempotency_key)
    WHERE idempotency_key IS NOT NULL;
-- SEQ-4 Crash Recovery Stage 1 re-probes live (non-terminal) Channels:
CREATE INDEX channels_live_idx
    ON channels (binding_id)
    WHERE status IN ('opening', 'open', 'draining', 'backpressured', 'error');
-- SEQ-5 Drain walks Channels still draining past the grace window:
CREATE INDEX channels_draining_idx
    ON channels (drain_started_at)
    WHERE status = 'draining';
```

---

## Cross-table invariants (enforced by FSM driver)

- **INV-SV2** (Service refs Session in {active, expiring}) - asserted at SV-T1 via `SELECT ... FOR UPDATE` on `sessions` row.
- **INV-SN1** (Envelope atomicity backing IR-O4) - `SELECT ... FOR UPDATE` on `sessions` row wraps both the envelope check and the child row insert inside one transaction.
- **INV-SV1** (Service-Binding count consistency) - FSM driver transactions; `bindings_service_active_idx` supports the query.
- **INV-CS1** (1:1 Task <-> Slot runtime) - `compute_slots` CHECK constraint + `tasks.compute_slot_id` FK.
- **INV-CS3** (Pipeline single-activation, v0.1-beta-2 scope) - partial unique index `compute_slots_pipeline_single_activation`.
- **INV-CS7** (Field-fill consistency with state) - `compute_slots` CHECK constraint (defense-in-depth; primary enforcement in FSM driver).
- **INV-O5** (Reconciliation before Ready) - `overseer-beta.md §1.7` step 2 reads `commands` rows with `status='pending'` and resolves each to `acked` / `rejected` / `timeout` before the Overseer reaches `Ready`. Backed by `commands_pending_issued_idx`.
- **INV-M1** (`[[metadata.tasks]].task_id` in the persisted `manifests.body` is the canonical FK target for `artifacts.task_id`) - owned by `manifest-beta.md`; enforced agent-side at the UpstreamSink emit boundary in `atelier-sdk/atelier-connect` (canonical `task_id` flows from `HandshakeResult.toml_config` -> `parse_metadata_tasks` -> `UpstreamSinkConfig.task_id` -> `ArtifactLineage.task_id`). The schema-side anchor is `artifacts_task_id_fkey`: agent-emitted ArtifactFrames whose lineage carries any non-canonical UUID are rejected at INSERT.
- **INV-M3** (`accept_task` (T-T1) commits before `manifests.body` is persisted) - owned by `manifest-beta.md`; enforced by `Scheduler::deploy_service` ordering in `atelier-overseer`. The walker fires T-T1 for each `TaskSpec` in the composed Manifest BEFORE inserting the `manifests` row, so `manifests.body` carries the canonical `task_id`(s) in `[[metadata.tasks]]` from the moment of B-T1 commit. The schema-side observable: a SELECT on `manifests.body::jsonb -> 'metadata' -> 'tasks'` after Phase A commit yields a non-empty array whose `task_id` values FK-reach `tasks.task_id`.
- **INV-M4** (`manifests.body` carries the FULL augmented shape) - owned by `manifest-beta.md`; the row is composed-and-augmented atomically inside Phase A's transaction stack and never rewritten at runtime. Reads of `manifests.body` post-B-T1-commit always observe the augmented shape including `[metadata]` + `[[metadata.tasks]]`. This is the body the Gateway returns verbatim in the gRPC handshake.
- **INV-CH3** (Reliability class immutable after Open) - owned by `channel-beta.md §2.10`; the FSM driver never UPDATEs `channels.reliability_class` after the row leaves `opening`. A downgrade is a close + re-open (new `channel_id`).
- **INV-CH5** (Gateway-persistent Channels survive A-T8 Restart) - owned by `channel-beta.md §2.10`; A-T8 increments `channels.restart_epoch` (and `agents.restart_epoch`) WITHOUT transitioning `channels.status` out of `open` or resetting `sequence_high`. The schema-side observable: a Channel row that was `open` before A-T8 is still `open` after, with `restart_epoch` incremented and `sequence_high` non-decreasing. Backed by `channels_live_idx`.
- **INV-CH7** (Recovery re-probes live Channels) - owned by `overseer-beta.md §1.7` / SEQ-4; on boot the Overseer scans `channels` rows with `status IN ('opening','open','draining','backpressured','error')` per `binding_id` it reconciles (Stage 1, IR-CHO4) and resolves each to `open` (transport intact) or `failed` (transport gone, triggers B-T7 force-release). Backed by `channels_live_idx`. A Channel left in `draining` past `agent.reconnect_grace_ms` is force-closed to `failed` (SEQ-5 timeout branch), backed by `channels_draining_idx`.

---

## Migration layout

Forward-only files under `atelier-lakehouse/overseer-db/migrations/`. Core FSM-table creation order (timestamped prefixes):

```
20260424000100_sessions.sql
20260424000200_pipelines.sql
20260424000300_compute_slots.sql
20260424000400_workspaces.sql
20260424000500_services.sql
20260424000600_services_workspaces_fk.sql   -- late FK workspaces.service_id -> services
20260424000700_agents.sql
20260424000800_manifests.sql
20260424000900_bindings.sql
20260424001000_manifests_bindings_fk.sql    -- late FK manifests.binding_id -> bindings
20260424001100_tasks.sql
20260424001200_artifacts.sql
20260424001300_manifests_artifacts_fk.sql   -- late FK manifests.archived_as_artifact_id -> artifacts
20260424001400_commands.sql                 -- durable Command log, backs overseer-beta.md §1.7 step 2
20260604000001_i5_channels.sql              -- durable Channel state, backs SEQ-4 recovery + SEQ-5 drain
```

Later timestamped migrations apply the enum/column refinements already folded into the CHECKs above (e.g. `..._i4_4_skill_mismatch`, `..._i5_terminated_reason`, `..._i5_binding_draining_reason`, `..._w4b_paused_at`, `..._w4a_byo_infra`). No down-migrations in v0.1 - schema changes ship under a new tagged version.

---

## Deferred tables

Per pre-plan G1, reduced in v0.1-beta-2:

- **`sinks`** - promote `workspaces.sinks` JSONB to rows with state, reliability class, handshake time. Needed when the Sink FSM graduates from provisioning contract (§2.11) to full lifecycle.

**Promoted in v0.1-beta-2:**

- **`artifacts`** - now specified above as table 10 (lineage-only columns; payload content lives at the Sink). Backs the use-case's per-Service and per-Task Artifact lineage queries without introducing payload storage into Postgres.
- **`commands`** - now specified above as table 11. Durable request/ack log. Promoted so that `overseer-beta.md §1.7` step 2 (reconcile Commands with `status='pending'`) is a DB scan rather than a recover-from-memory gap across Overseer restart. In-memory tracking alone could not re-deliver or time out pre-crash Commands.

**Promoted to normative:**

- **`channels`** - now specified above as table 12. Durable Channel identity + provisioning/drain state. Promoted so that SEQ-4 Crash Recovery can re-probe live Channels by `binding_id` after restart, and SEQ-5 graceful Drain has a durable target to walk Draining -> Closed past the drain grace window. `restart_epoch` and `sequence_high` persistence make `restart_epoch` sufficient as the Artifact lineage discriminator across A-T8 Restart (INV-CH5) without an in-memory reconstruction step. The internal Channel states Draining/Closed/Failed are promoted to normative in `channel-beta.md §2.10` as part of this; Backpressured/Error remain enumerated-only (the CHECK admits them so a later promotion needs no migration).

When the remaining deferred tables are promoted, the `workspaces.sinks` JSONB becomes redundant and gets dropped in a follow-up migration. Until then, `workspaces.sinks` is the authoritative Sink-set representation (sufficient for SEQ-1 Deploy).

---

## Design notes

**Twelve tables, not eight.** Four promotions beyond the pre-plan's 8 (the fourth, `channels`, lands for Drain/Recovery durability - see the promotion note above). `compute_slots` is a per-activation state-bearing table - embedding it in `pipelines.topology` JSONB would make every activation a Pipeline row write, breaking the immutability guarantee around Pipeline topology (INV-CS4). A separate `compute_slots` table keeps Pipeline rows read-mostly. `artifacts` is a lineage-only table - it records *which run produced which Artifact at which Sink*, without storing payload content. The distinction matters: payloads live at the Sink (local Parquet, webapp TerminalSink buffer, archive ObjectSink) and can be tens of MB or more each; pulling them into Postgres would turn the DB into a payload store. Lineage rows are small, indexable by `(task_id, restart_epoch, sequence)`, and directly back the use-case's "complete lineage preserved under Service ID" guarantee (`../txy/txy-beta.md §6`). Payload-typed promotion into proto message bodies per `ArtifactKind` is deferred; the `payload_schema_ref` + out-of-band schema pattern is the beta contract. `commands` is a durability concession: the Overseer cannot safely enforce INV-O5 (Reconciliation before Ready) without durable Command records, because `§1.7` step 2 explicitly scans "all Commands with status='pending'" after restart. An in-memory-only Command registry would forget pre-crash Commands, turning re-delivery/timeout into a gap rather than a contract. The column set is deliberately narrow - target polymorphism is compressed to `(target_kind, target_id)` rather than five nullable FKs, `params` stays opaque JSONB mirroring the wire `google.protobuf.Struct`, and the lifecycle enum is limited to terminal states the Overseer actually writes.

**TEXT CHECK over ENUM.** Adding a state = one `ALTER TABLE ... DROP CONSTRAINT; ADD CONSTRAINT ...`. Removing or renaming a state = same. Postgres `ENUM` values cannot be removed at all and renaming is awkward; the ergonomic win of enum-typed columns is negligible at Atelier's scale.

**Row-level locking for envelope atomicity.** The FSM driver implements IR-O4 by opening a transaction, `SELECT * FROM sessions WHERE session_id = $1 FOR UPDATE`, reading `envelope_counters`, verifying the addition fits, inserting the child row, then updating `envelope_counters` and committing. Concurrent Deploys against the same Session serialize on this lock.

**`row_version` optimistic concurrency.** Present on tables where concurrent Overseer replicas may race (`services`, `bindings`, `tasks`, `agents`, `compute_slots`, `sessions`, `commands`). FSM driver UPDATEs include `WHERE row_version = $N`; 0 rows touched -> retry with fresh read. `commands` needs it because the reconciliation sweep (`overseer-beta.md §1.7` step 2) may race with a live CommandAck arriving for the same `command_id` during the boot window.

**Workspace is service-lifecycle-scoped.** `workspaces.service_id` is NOT NULL; a Workspace is destroyed when its Service reaches Stopped (SV-T4 / SV-T5 effects). Multi-Workspace-per-Service is a later version.

**Session state of `created`.** Per Session FSM §2.7.1, `S-SN1 Created` is transient - typically the Overseer writes `status='active'` directly after SN-T1 + SN-T2 in a single transaction. The CHECK permits the transient state in case SN-T1 -> SN-T2 is split by a failure window.

---

## Sources

- [overseer-beta.md - §1.4 Matrix, §1.6 IR-O4, §1.7 Recovery](overseer-beta.md)
- [agent-beta.md - §2.1 Agent](agent-beta.md)
- [task-beta.md - §2.2 Task](task-beta.md)
- [binding-beta.md - §2.3 Binding](binding-beta.md)
- [service-beta.md - §2.5 Service](service-beta.md)
- [session-beta.md - §2.7 Session](session-beta.md)
- [compute-slot-beta.md - §2.8 ComputeSlot](compute-slot-beta.md)
- [gateway-beta.md - §2.9 Gateway](gateway-beta.md)
- [channel-beta.md - §2.10 Channel](channel-beta.md)
- [sink-beta.md - §2.11 Sink](sink-beta.md)
- [../txy/txy-beta.md - Identifiers, Scopes](../txy/txy-beta.md)
