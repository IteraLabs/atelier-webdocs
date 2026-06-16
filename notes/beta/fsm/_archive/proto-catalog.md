# FSM Atlas v0.1-beta-2 - Proto Message Catalog

The single wire-format source of truth for v0.1-beta-2. Used verbatim on the CommandChannel and TelemetryChannel between SDK (RemoteAgent) / Overseer (PlatformAgent) and the Gateway / Overseer, and on the internal backend event bus.

Target codegen: `prost` + `tonic` from a Rust crate `atelier-proto`. Package `atelier.v0_1_beta_2`. Proto3.

**Design stance.** There is no separate "event" catalog. Every FSM transition that crosses a boundary (SDK <-> platform, or backend internal bus) is an `Event` variant in this catalog. This keeps the wire surface and the observability surface in lockstep - when a state is added to an FSM, exactly one new event variant is added here.

## Layout

```
atelier-proto/
├── proto/
│   └── atelier/
│       └── v0_1_beta_2/
│           ├── common.proto           # Envelope, Error, IDs
│           ├── control.proto          # Registration, Command, Manifest, Acks
│           ├── telemetry.proto        # Heartbeat, TaskTelemetry, AgentStatus
│           ├── data.proto             # ArtifactFrame
│           ├── events.proto           # Event oneof + all variants
│           └── services.proto         # gRPC service definitions
├── build.rs                           # tonic-build config
└── src/lib.rs                         # re-exports of codegen'd modules
```

---

## `common.proto`

```proto
syntax = "proto3";

package atelier.v0_1_beta_2;

import "google/protobuf/timestamp.proto";

// -------- IDs --------
// All IDs are UUIDv4 strings. Aliases (e.g. 'RA-17') are carried separately
// where useful, never as identity.
// Naming convention: the *_id field is authoritative; *_alias is optional.
//
// Wire representation (NORMATIVE, v0.1-beta-2): IDs are carried as FLAT
// `string` fields on every message - e.g. `string agent_id = 1;`,
// `string binding_id = 1;`. Wrapper-message identifier patterns such as
// `message AgentId { string value = 1; }` are NON-CONFORMANT and MUST NOT
// appear in `atelier-proto/atelier/v0_1_beta_2/*.proto`. The wrapper
// pattern was considered and rejected: it adds a decode layer on every
// field without adding any compile-time discipline at the wire - only
// language-local post-decode wrapping can do that.
//
// Language-layer newtype discipline is the RIGHT place to enforce
// cross-domain ID safety. In the Rust SDK/backend crates, each ID domain
// SHOULD be a distinct newtype (`AgentId(Uuid)`, `BindingId(Uuid)`,
// `TaskId(Uuid)`, ...) so that passing a `BindingId` where an `AgentId`
// is expected is a compile error. That discipline is implemented in
// `atelier-sdk/atelier-types` (or its rename) and in
// `atelier-backend/atelier-overseer/models`; it does NOT change the wire
// shape. The wire stays flat strings; the Rust layer wraps on decode
// and unwraps on encode.

// -------- Envelope --------
// Every cross-boundary message is wrapped in an Envelope. The Envelope carries
// the per-frame metadata; the payload is the typed body.
//
// Used on:
//   - CommandChannel (bidirectional gRPC stream, at-least-once)
//   - TelemetryChannel (upstream gRPC stream, best-effort-with-sequence)
//   - Internal backend bus (as-is, no rewrap)

message Envelope {
    string                    envelope_id   = 1;  // UUIDv4, unique per envelope
    google.protobuf.Timestamp emitted_at    = 2;
    string                    session_id    = 3;  // UUIDv4; empty only on pre-session frames (Registration)
    string                    sender_id     = 4;  // agent_id | overseer_id | gateway_id
    uint64                    sequence      = 5;  // per-(channel, sender) monotonic
    uint32                    restart_epoch = 6;  // echoes Agent.restart_epoch; 0 if N/A

    oneof payload {
        Registration          registration          = 10;
        RegistrationResponse  registration_response = 11;
        Manifest              manifest              = 12;
        ManifestAck           manifest_ack          = 13;
        Command               command               = 14;
        CommandAck            command_ack           = 15;

        Heartbeat             heartbeat             = 20;
        TaskTelemetry         task_telemetry        = 21;
        AgentStatus           agent_status          = 22;

        ArtifactFrame         artifact_frame          = 30;
        ManifestArtifactFrame manifest_artifact_frame = 31;

        Event                 event                 = 40;

        Error                 error                 = 90;
    }
}

// -------- Errors --------

enum ErrorKind {
    ERROR_KIND_UNSPECIFIED            = 0;

    // Auth / identity
    UNAUTHENTICATED                   = 1;
    SESSION_EXPIRED                   = 2;
    SESSION_REVOKED                   = 3;
    PLAN_REVOKED                      = 4;

    // Envelope / quota
    ENVELOPE_EXCEEDED                 = 10;   // IR-O4 atomicity rejection
    QUOTA_DENIED                      = 11;

    // Agent / registration
    REGISTRATION_INVALID              = 20;
    REGISTRATION_EXPIRED              = 21;
    AGENT_NOT_FOUND                   = 22;
    AGENT_LOST                        = 23;
    DUPLICATE_AGENT_ID                = 24;

    // Manifest
    MANIFEST_REJECTED                 = 30;
    SKILL_MISMATCH                    = 31;
    SPEC_INVALID                      = 32;
    MANIFEST_IDEMPOTENCY_COLLISION    = 33;

    // Command / target
    COMMAND_TARGET_NOT_FOUND          = 40;
    COMMAND_TARGET_WRONG_STATE        = 41;
    COMMAND_UNSUPPORTED               = 42;
    UPDATE_NOT_SUPPORTED              = 43;   // v0.1-beta-2: Service update is explicitly unsupported
    DISPATCH_TIMEOUT                  = 44;

    // Binding / Task
    BINDING_ALREADY_RELEASED          = 50;
    TASK_ALREADY_TERMINAL             = 51;
    SPAWN_FAILED                      = 52;

    // Transport
    GATEWAY_UNAVAILABLE               = 60;
    CHANNEL_OPEN_FAILED               = 61;
    SINK_OPEN_FAILED                  = 62;
    SINK_UNAVAILABLE                  = 63;

    // Subsystem degradation
    SUBSYSTEM_LOSS_PERSISTENT_STORAGE = 70;
    SUBSYSTEM_LOSS_MESSAGE_DELIVERY   = 71;
    SUBSYSTEM_LOSS_PROCESS_SPAWNING   = 72;
    SUBSYSTEM_LOSS_EVENT_BROADCAST    = 73;

    // Generic
    INTERNAL                          = 90;
    NOT_IMPLEMENTED                   = 91;
    TEMPORARILY_UNAVAILABLE           = 92;
}

message Error {
    ErrorKind kind           = 1;
    string    message        = 2;   // free-form, human-readable; not a parse target
    string    correlation_id = 3;   // envelope_id of the offending request (where applicable)
    bool      retryable      = 4;
    uint32    retry_after_ms = 5;
}
```

---

## `control.proto`

```proto
syntax = "proto3";

package atelier.v0_1_beta_2;

import "atelier/v0_1_beta_2/common.proto";
import "google/protobuf/timestamp.proto";
import "google/protobuf/struct.proto";

// -------- Registration (A-T1) --------

message Registration {
    string agent_alias                   = 1;   // optional, user-facing
    AgentType agent_type                 = 2;
    repeated string skills               = 3;   // Skill trait names: 'ingest', 'sync', 'transform', 'emit', 'report'
    google.protobuf.Struct host_identity = 4;   // opaque claims
    string target_session_id             = 5;
}

enum AgentType {
    AGENT_TYPE_UNSPECIFIED = 0;
    AGENT_TYPE_REMOTE      = 1;
    AGENT_TYPE_PLATFORM    = 2;
}

message RegistrationResponse {
    oneof outcome {
        Accepted accepted = 1;
        Error    rejected = 2;
    }

    message Accepted {
        string agent_id                             = 1;
        string agent_alias                          = 2;
        string session_id                           = 3;
        google.protobuf.Timestamp registered_at     = 4;
    }
}

// -------- Manifest (B-T1) --------
// Transmitted on ManifestChannel (embedded in CommandChannel per INV-CH6).
// Reliability: exactly-once via idempotency_key.
//
// v0.1-beta-2 status: under the BYO-infra deploy path the Manifest body
// is delivered to the agent via the gRPC handshake response
// (`Gateway.Handshake -> HandshakeResult.toml_config`), NOT over a
// separate ManifestChannel. The Overseer composes + augments the body
// during Phase A (SEQ-1 step 4, `sequences.md §3.1.1`); the persisted
// `manifests.body` already carries the canonical `[[metadata.tasks]]`
// block (INV-M3 / INV-M4, `manifest.md §4`). The Gateway's handshake
// handler returns that persisted body verbatim. No `ManifestAck`
// round-trip is needed because the canonical IDs are already in the
// body the agent receives.
//
// The Overseer additionally publishes the augmented body to Kafka topic
// `control.manifests` (compacted, keyed on binding_id) during Phase A.
// This publish is server-internal and not load-bearing for v0.1-beta-2
// - preserved for Iteration 5+ uses (boot reconciler republish, cross-
// replica coordination, future Gateway federation). See `manifest.md
// §2.4` and §6.
//
// The gRPC `Manifest` / `ManifestAck` messages defined here are reserved
// for the post-beta gRPC `ManifestChannel` path; both shapes carry
// equivalent payload - see `manifest.md §7` for the correspondence table.

message Manifest {
    string manifest_id                      = 1;
    string idempotency_key                  = 2;
    string service_id                       = 3;
    string agent_ref                        = 4;
    string workspace_ref                    = 5;

    repeated TaskSpec tasks                 = 6;
    repeated SinkAssignment sinks           = 7;
    google.protobuf.Timestamp composed_at   = 8;
}

message TaskSpec {
    string task_id                    = 1;      // may be platform-assigned on Ack
    Skill  skill                      = 2;
    google.protobuf.Struct params     = 3;
    repeated string datatypes         = 4;
    repeated string sink_ids          = 5;
}

enum Skill {
    SKILL_UNSPECIFIED = 0;
    SKILL_INGEST      = 1;
    SKILL_SYNC        = 2;
    SKILL_TRANSFORM   = 3;
    SKILL_EMIT        = 4;
    SKILL_REPORT      = 5;
}

message SinkAssignment {
    string sink_id                = 1;
    SinkType type                 = 2;
    google.protobuf.Struct config = 3;
}

enum SinkType {
    SINK_TYPE_UNSPECIFIED = 0;
    SINK_TYPE_OBJECT      = 1;
    SINK_TYPE_DB          = 2;
    SINK_TYPE_TERMINAL    = 3;
}

message ManifestAck {
    string manifest_id                      = 1;
    google.protobuf.Timestamp acked_at      = 2;
    oneof outcome {
        Accepted accepted = 3;
        Error    rejected = 4;
    }

    message Accepted {
        string binding_id              = 1;
        repeated AssignedTask tasks    = 2;
    }

    message AssignedTask {
        string manifest_task_id   = 1;
        string task_id            = 2;
    }
}

// -------- TaskRejectionReason --------
// Task-FSM-local catalog naming *why a single Task was rejected* during
// ManifestAck dispatch. Distinct from `ErrorKind` (common.proto), which is
// the wire-level, cross-cutting error enum carried by the `Error` message
// everywhere. `TaskRejectionReason` is narrow and local to `ManifestAck`;
// its first three members overlap semantically with ErrorKind values
// SKILL_MISMATCH (31), SPEC_INVALID (32), and INTERNAL (90) but are kept
// in a separate enum so the post-beta multi-Task `ManifestAck` shape can
// carry per-Task rejection reasons without bloating `ErrorKind` with
// Task-local variants.
//
// Under the v0.1-beta-2 single-Task Manifest restriction
// (taxonomy §Tasks / beta scope; enforced at `binding.md §2.3.2 B-T1`),
// `TASK_REJECTION_PEER_REJECTED` is dormant: it is reachable only when a
// Manifest carries multiple Tasks and one sibling rejection cascades to
// the remaining accepted siblings via `binding.md IR-BT2`. The value is
// preserved so that lifting the beta restriction does not require a
// proto schema bump.
//
// See `errors.md` preface for the `ErrorKind` vs `TaskRejectionReason`
// boundary, and `task.md §2.2.2 T-T2`, `binding.md §2.3.2 B-T10` for
// transition-level use.

enum TaskRejectionReason {
    TASK_REJECTION_UNSPECIFIED      = 0;
    TASK_REJECTION_SKILL_MISMATCH   = 1;
    TASK_REJECTION_SPEC_INVALID     = 2;
    TASK_REJECTION_INTERNAL_ERROR   = 3;
    TASK_REJECTION_PEER_REJECTED    = 4;  // dormant in v0.1-beta-2; reachable post-beta (multi-Task)
}

// -------- Command --------
// Reliability: at-least-once with ack by command_id.

message Command {
    string command_id = 1;
    CommandKind kind  = 2;

    oneof target {
        SessionTarget   session     = 10;
        ServiceTarget   service     = 11;
        AgentTarget     agent       = 12;
        BindingTarget   binding     = 13;
        TaskTarget      task        = 14;
    }

    google.protobuf.Struct params = 20;
}

enum CommandKind {
    COMMAND_KIND_UNSPECIFIED   = 0;

    SESSION_RENEW              = 1;
    SESSION_FORCE_CLOSE        = 2;

    SERVICE_CREATE             = 10;
    SERVICE_DEPLOY             = 11;
    SERVICE_STOP               = 12;
    SERVICE_ARCHIVE            = 13;

    AGENT_DRAIN                = 20;
    AGENT_RESTART              = 21;
    AGENT_TERMINATE            = 22;

    BINDING_RELEASE            = 30;
    TASK_START                 = 40;
    TASK_PAUSE                 = 41;
    TASK_RESUME                = 42;
    TASK_COMPLETE              = 43;
    TASK_CANCEL                = 44;
}

message SessionTarget { string session_id = 1; }
message ServiceTarget { string service_id = 1; }
message AgentTarget   { string agent_id   = 1; }
message BindingTarget { string binding_id = 1; }
message TaskTarget    { string task_id    = 1; }

message CommandAck {
    string command_id                 = 1;
    google.protobuf.Timestamp acked_at = 2;
    oneof outcome {
        Accepted accepted = 3;
        Error    rejected = 4;
    }

    message Accepted {
        google.protobuf.Struct result = 1;
    }
}
```

---

## `telemetry.proto`

```proto
syntax = "proto3";

package atelier.v0_1_beta_2;

import "atelier/v0_1_beta_2/common.proto";
import "google/protobuf/timestamp.proto";
import "google/protobuf/struct.proto";

message Heartbeat {
    string agent_id              = 1;
    google.protobuf.Timestamp ts = 2;
    uint32 restart_epoch         = 3;
    AgentStatus.Phase phase      = 4;
}

message AgentStatus {
    string agent_id                        = 1;
    google.protobuf.Timestamp ts           = 2;
    uint32 restart_epoch                   = 3;
    Phase  phase                           = 4;
    repeated string active_binding_ids     = 5;
    repeated string active_task_ids        = 6;

    enum Phase {
        PHASE_UNSPECIFIED  = 0;
        PHASE_REGISTERED   = 1;
        PHASE_READY        = 2;
        PHASE_BOUND        = 3;
        PHASE_RESTARTING   = 4;
        PHASE_LOST         = 5;
        PHASE_DRAINING     = 6;
        PHASE_TERMINATED   = 7;
    }
}

message TaskTelemetry {
    string agent_id                        = 1;
    google.protobuf.Timestamp ts           = 2;
    repeated TaskProgress tasks            = 3;

    message TaskProgress {
        string task_id                     = 1;
        TaskPhase phase                    = 2;
        uint64 artifacts_emitted           = 3;
        uint64 artifacts_failed            = 4;
        google.protobuf.Struct metrics     = 5;
    }

    enum TaskPhase {
        TASK_PHASE_UNSPECIFIED = 0;
        TASK_PHASE_SUBMITTED   = 1;
        TASK_PHASE_ACCEPTED    = 2;
        TASK_PHASE_RUNNING     = 3;
        TASK_PHASE_PAUSING     = 4;
        TASK_PHASE_PAUSED      = 5;
        TASK_PHASE_RESUMING    = 6;
        TASK_PHASE_COMPLETING  = 7;
        TASK_PHASE_COMPLETED   = 8;
        TASK_PHASE_FAILED      = 9;
        TASK_PHASE_CANCELED    = 10;
    }
}
```

---

## `data.proto`

```proto
syntax = "proto3";

package atelier.v0_1_beta_2;

import "atelier/v0_1_beta_2/common.proto";
import "google/protobuf/timestamp.proto";

// -------- Artifact envelopes --------
//
// The wire carries two Artifact envelopes in v0.1-beta-2:
//
//   - ArtifactFrame          - Agent-emitted. Kinds: DATA, LOGS, MODEL.
//                              Carries ArtifactLineage (service/experiment +
//                              task + restart_epoch + sequence) as a first-
//                              class submessage so consumers can join on
//                              lineage without decoding the payload.
//   - ManifestArtifactFrame  - Overseer-emitted (taxonomy §Artifacts).
//                              Separate message: no Task ID, distinct sink
//                              path (archive store), distinct producer.
//
// The payload body itself stays opaque: Artifact payloads in beta are
// Parquet / Arrow IPC / JSON / log-line formats whose schemas are not
// Protocol Buffers. `payload_schema_ref` names an out-of-band schema the
// payload bytes MUST conform to. Promotion of payload bodies to typed
// proto messages per ArtifactKind is deferred post-beta.

enum ArtifactKind {
    ARTIFACT_KIND_UNSPECIFIED = 0;
    ARTIFACT_KIND_DATA        = 1;  // DataArtifact    - primary or derived datasets
    ARTIFACT_KIND_LOGS        = 2;  // LogsArtifact    - operational logs, traces, diagnostics
    ARTIFACT_KIND_MODEL       = 3;  // ModelArtifact   - trained models, fitted parameters
}

// ArtifactLineage identifies *which run* produced this Artifact, independent
// of the payload. Hoisted into its own submessage so lineage joins across
// Sinks, Recovery resume-from-epoch queries, and per-Task ordering scans do
// not have to decode the payload.
//
// v0.1-beta-2 emits only `service_id` (Experiment activation is deferred per
// taxonomy §Activation Modes). The oneof is present so post-beta Experiment
// traffic can land without a wire-format break.

message ArtifactLineage {
    string artifact_id      = 1;
    string task_id          = 2;
    uint32 restart_epoch    = 3;   // echoes Task.restart_epoch per §2.1.5
    uint64 sequence         = 4;   // per-(task_id, restart_epoch) monotone

    oneof activation {
        string service_id    = 10;
        string experiment_id = 11;  // reserved for post-beta
    }
}

// **Iteration 4.5.4 - payload contract.**
// `ArtifactFrame` has two conformant emission shapes, picked per-Agent at
// per-Task sink-build time:
//
//   * **Lineage-only (preferred when a local Sink is configured).** The
//     local Sink (e.g. `ParquetSnapshotFlusher` writing to `[output.parquet]`)
//     IS the artifact; the upstream frame carries identity + lineage +
//     pointer metadata (`sink_id`, `datatype`, `partial`) only. `payload`
//     is empty bytes; `payload_schema_ref` is empty string. The Overseer's
//     `artifact.frames` consumer inserts the lineage row into
//     `schema.md §10 artifacts`. `payload_schema_ref` is NOT required in
//     this shape - it would point at out-of-band content the upstream
//     never carries. Iteration 4.5.1 / 4.5.2 / 4.5.3 land this path
//     end-to-end for the BYO-infra use case.
//
//   * **Payload-bearing (no-Sink fallback).** The Agent has no local
//     Sink configured; the upstream frame is the only artifact in
//     existence. `payload` carries the bytes; `payload_schema_ref` MUST
//     be set so consumers can decode out-of-band. Used as a debug /
//     dashboard fallback.
//
// The platform decides the shape per-worker by inspecting the manifest's
// `[[collect.output]]` entries: presence of any `type = "parquet"` flips
// the agent into lineage-only mode for that worker.

message ArtifactFrame {
    ArtifactKind    kind                 = 1;
    ArtifactLineage lineage              = 2;
    string sink_id                       = 3;
    string datatype                      = 4;
    google.protobuf.Timestamp emitted_at = 5;
    bool   partial                       = 6;   // set when flush exceeded stop_drain_timeout (taxonomy §Artifacts)

    bytes  payload                       = 10;  // empty in lineage-only mode (Iteration 4.5.4)
    string payload_schema_ref            = 11;  // out-of-band schema pointer; MUST be set when payload non-empty, empty in lineage-only mode
}

// ManifestArtifact is Overseer-emitted (taxonomy §Artifacts): it archives
// the Manifest body for audit and reproducibility. It carries no Task ID
// and does not participate in Task-lineage. `manifest_id` references the
// originating Manifest row in persistence (`schema.md manifests`).

message ManifestArtifactFrame {
    string artifact_id                   = 1;
    string service_id                    = 2;   // or experiment_id post-beta
    string manifest_id                   = 3;
    google.protobuf.Timestamp emitted_at = 4;

    string sink_id                       = 5;   // typically an archive ObjectSink
    bytes  manifest_body                 = 10;  // canonicalized serialized Manifest
    string manifest_schema_ref           = 11;  // pins the serialization format
}
```

---

## `events.proto`

```proto
syntax = "proto3";

package atelier.v0_1_beta_2;

import "atelier/v0_1_beta_2/common.proto";
import "google/protobuf/timestamp.proto";

// Event is emitted at every FSM transition that crosses a boundary.
// Exactly one variant per state-change that matters.

message Event {
    string event_id                 = 1;
    google.protobuf.Timestamp ts    = 2;
    string transition_id            = 3;   // e.g. 'A-T2', 'SV-T2', 'B-T3'
    string session_id               = 4;

    oneof body {
        // --- Overseer (FSM §1) ---
        OverseerReady          overseer_ready          = 10;
        OverseerDegraded       overseer_degraded       = 11;
        OverseerRecovered      overseer_recovered      = 12;
        OverseerDraining       overseer_draining       = 13;

        // --- Agent (FSM §2.1) ---
        AgentRegistered        agent_registered        = 20;
        AgentReady             agent_ready             = 21;
        AgentBound             agent_bound             = 22;
        AgentRestarting        agent_restarting        = 23;
        AgentLost              agent_lost              = 24;
        AgentDraining          agent_draining          = 25;
        AgentTerminated        agent_terminated        = 26;

        // --- Task (FSM §2.2) ---
        TaskAccepted           task_accepted           = 30;
        TaskRunning            task_running            = 31;
        TaskPaused             task_paused             = 32;
        TaskResumed            task_resumed            = 33;
        TaskCompleted          task_completed          = 34;
        TaskFailed             task_failed             = 35;
        TaskCanceled           task_canceled           = 36;
        TaskRestarted          task_restarted          = 37;

        // --- Binding (FSM §2.3) ---
        BindingCreated         binding_created         = 40;
        BindingActive          binding_active          = 41;
        BindingDraining        binding_draining        = 42;
        BindingReleasing       binding_releasing       = 43;
        BindingReleased        binding_released        = 44;

        // --- Service (FSM §2.5) ---
        ServiceProvisioning    service_provisioning    = 50;
        ServiceDeploying       service_deploying       = 51;
        ServiceActive          service_active          = 52;
        ServiceStopping        service_stopping        = 53;
        ServiceStopped         service_stopped         = 54;
        ServiceArchived        service_archived        = 55;

        // --- Session (FSM §2.7) ---
        SessionCreated         session_created         = 60;
        SessionActive          session_active          = 61;
        SessionRenewed         session_renewed         = 62;
        SessionExpiring        session_expiring        = 63;
        SessionExpired         session_expired         = 64;
        SessionClosed          session_closed          = 65;

        // --- ComputeSlot (FSM §2.8) ---
        ComputeSlotReserved    compute_slot_reserved   = 70;
        ComputeSlotOccupied    compute_slot_occupied   = 71;
        ComputeSlotReleasing   compute_slot_releasing  = 72;
        ComputeSlotVacant      compute_slot_vacant     = 73;
        ComputeSlotRetired     compute_slot_retired    = 74;

        // --- Gateway (FSM §2.9) ---
        GatewayReady           gateway_ready           = 80;
        GatewayDegraded        gateway_degraded        = 81;
        GatewayStopping        gateway_stopping        = 82;
        GatewayStopped         gateway_stopped         = 83;

        // --- Channel / Sink provisioning (§2.10 / §2.11) ---
        ChannelOpening         channel_opening         = 90;
        ChannelOpen            channel_open            = 91;
        SinkIdle               sink_idle               = 100;
        SinkReady              sink_ready              = 101;
    }
}

// --- Overseer ---
message OverseerReady     { string overseer_id = 1; }
message OverseerDegraded  {
    string overseer_id            = 1;
    repeated SubsystemLoss losses = 2;
}
message OverseerRecovered {
    string overseer_id             = 1;
    repeated SubsystemLoss cleared = 2;
}
message OverseerDraining  { string overseer_id = 1; }

enum SubsystemLoss {
    SUBSYSTEM_LOSS_UNSPECIFIED       = 0;
    SUBSYSTEM_PERSISTENT_STORAGE     = 1;
    SUBSYSTEM_MESSAGE_DELIVERY       = 2;
    SUBSYSTEM_PROCESS_SPAWNING       = 3;
    SUBSYSTEM_EVENT_BROADCAST        = 4;
}

// --- Agent ---
message AgentRegistered  { string agent_id = 1; AgentType agent_type = 2; repeated string skills = 3; }
message AgentReady       { string agent_id = 1; uint32 restart_epoch = 2; }
message AgentBound       { string agent_id = 1; string binding_id = 2; }
message AgentRestarting  { string agent_id = 1; uint32 restart_epoch = 2; }
message AgentLost        { string agent_id = 1; google.protobuf.Timestamp last_heartbeat_at = 2; }
message AgentDraining    { string agent_id = 1; string reason = 2; }
message AgentTerminated  { string agent_id = 1; string terminated_reason = 2; }

// --- Task ---
message TaskAccepted   { string task_id = 1; string binding_id = 2; string compute_slot_id = 3; }
message TaskRunning    { string task_id = 1; }
message TaskPaused     { string task_id = 1; string reason = 2; }
message TaskResumed    { string task_id = 1; }
message TaskCompleted  { string task_id = 1; uint64 artifacts_emitted = 2; }
message TaskFailed     { string task_id = 1; Error error = 2; }
message TaskCanceled   { string task_id = 1; string reason = 2; }
message TaskRestarted  { string task_id = 1; uint32 restart_epoch = 2; }

// --- Binding ---
message BindingCreated   { string binding_id = 1; string service_id = 2; string agent_id = 3; string manifest_id = 4; }
message BindingActive    { string binding_id = 1; }
message BindingDraining  { string binding_id = 1; string reason = 2; }
message BindingReleasing { string binding_id = 1; }
message BindingReleased  { string binding_id = 1; string release_reason = 2; }

// --- Service ---
message ServiceProvisioning { string service_id = 1; string pipeline_id = 2; AgentType agent_type = 3; }
message ServiceDeploying    { string service_id = 1; }
message ServiceActive       { string service_id = 1; }
message ServiceStopping     { string service_id = 1; string stopped_reason_intent = 2; }
message ServiceStopped      { string service_id = 1; string stopped_reason = 2; }
message ServiceArchived     { string service_id = 1; }

// --- Session ---
message SessionCreated  { string session_id = 1; string identity_id = 2; }
message SessionActive   { string session_id = 1; }
message SessionRenewed  { string session_id = 1; google.protobuf.Timestamp ttl_at = 2; }
message SessionExpiring { string session_id = 1; google.protobuf.Timestamp expired_at_scheduled = 2; }
message SessionExpired  { string session_id = 1; string expire_reason = 2; }
message SessionClosed   { string session_id = 1; }

// --- ComputeSlot ---
message ComputeSlotReserved   { string compute_slot_id = 1; string activation_id = 2; }
message ComputeSlotOccupied   { string compute_slot_id = 1; string task_id = 2; string binding_id = 3; }
message ComputeSlotReleasing  { string compute_slot_id = 1; }
message ComputeSlotVacant     { string compute_slot_id = 1; }
message ComputeSlotRetired    { string compute_slot_id = 1; }

// --- Gateway ---
message GatewayReady    { string gateway_id = 1; }
message GatewayDegraded { string gateway_id = 1; }
message GatewayStopping { string gateway_id = 1; }
message GatewayStopped  { string gateway_id = 1; }

// --- Channel / Sink (provisioning only) ---
message ChannelOpening { string channel_id = 1; string category = 2; }
message ChannelOpen    { string channel_id = 1; string category = 2; string reliability_class = 3; }
message SinkIdle       { string sink_id = 1; SinkType type = 2; }
message SinkReady      { string sink_id = 1; SinkType type = 2; string reliability_class = 3; }
```

---

## `services.proto`

```proto
syntax = "proto3";

package atelier.v0_1_beta_2;

import "atelier/v0_1_beta_2/common.proto";

service Gateway {
    // CommandChannel. Bidirectional stream. Carries Registration (first frame),
    // then Manifest, Command, Ack variants, and outbound Command frames from the
    // Overseer side. ManifestChannel is embedded (INV-CH6).
    rpc CommandChannel(stream Envelope) returns (stream Envelope);

    // TelemetryChannel. Upstream-only. Best-effort-with-sequence.
    rpc TelemetryChannel(stream Envelope) returns (Ack);

    // EventBus subscription (Overseer -> SDK). Optional.
    rpc EventSubscribe(EventSubscribeRequest) returns (stream Envelope);
}

message Ack {
    google.protobuf.Timestamp received_at = 1;
}

message EventSubscribeRequest {
    string  session_id              = 1;
    repeated string transition_ids  = 2;   // empty = all
}
```

---

## Wire -> FSM cross-reference

| Event variant | Transition | FSM section |
|---|---|---|
| AgentRegistered | A-T1 | agent.md §2.1 |
| AgentReady | A-T2 | agent.md §2.1 |
| AgentBound | A-T4 | agent.md §2.1 |
| AgentRestarting | A-T8 (entry) | agent.md §2.1 |
| AgentLost | A-T5 | agent.md §2.1 |
| AgentDraining | A-T6 / A-T7 | agent.md §2.1 |
| AgentTerminated | A-T7 / A-T15 / A-T16 | agent.md §2.1 |
| TaskAccepted | T-T2 | task.md §2.2 |
| TaskRunning | T-T3 | task.md §2.2 |
| TaskPaused / Resumed | T-T4 / T-T5 | task.md §2.2 |
| TaskCompleted | T-T7 | task.md §2.2 |
| TaskFailed | T-T8 | task.md §2.2 |
| TaskCanceled | T-T9 | task.md §2.2 |
| TaskRestarted | post A-T8 resync | agent.md §2.1.5 |
| BindingCreated | B-T1 | binding.md §2.3 |
| BindingActive | B-T3 | binding.md §2.3 |
| BindingDraining | B-T4 | binding.md §2.3 |
| BindingReleasing | B-T5 | binding.md §2.3 |
| BindingReleased | B-T6 | binding.md §2.3 |
| ServiceProvisioning | SV-T1 | service.md §2.5 |
| ServiceDeploying | SV-T2 | service.md §2.5 |
| ServiceActive | SV-T2 end | service.md §2.5 |
| ServiceStopping | SV-T3 / SV-T4 | service.md §2.5 |
| ServiceStopped | SV-T4 end | service.md §2.5 |
| ServiceArchived | SV-T5 | service.md §2.5 |
| SessionCreated | SN-T1 | session.md §2.7 |
| SessionActive | SN-T2 | session.md §2.7 |
| SessionRenewed | SN-T5 | session.md §2.7 |
| SessionExpiring | SN-T3 | session.md §2.7 |
| SessionExpired | SN-T4 / SN-T6 | session.md §2.7 |
| SessionClosed | SN-T7 | session.md §2.7 |
| ComputeSlotReserved | CS-T1 | compute-slot.md §2.8 |
| ComputeSlotOccupied | CS-T2 | compute-slot.md §2.8 |
| ComputeSlotReleasing | CS-T3 | compute-slot.md §2.8 |
| ComputeSlotVacant | CS-T4 | compute-slot.md §2.8 |
| ComputeSlotRetired | CS-T6 | compute-slot.md §2.8 |
| GatewayReady | GW-T2 | gateway.md §2.9 |
| GatewayDegraded | GW-T3 | gateway.md §2.9 |
| GatewayStopping | GW-T5 | gateway.md §2.9 |
| GatewayStopped | GW-T6 | gateway.md §2.9 |
| ChannelOpening | CH-T1 | channel.md §2.10 |
| ChannelOpen | CH-T2 | channel.md §2.10 |
| SinkIdle | SK-T1 | sink.md §2.11 |
| SinkReady | SK-T2 | sink.md §2.11 |
| OverseerReady | O-T1 | overseer.md §1.3 |
| OverseerDegraded | O-T2 | overseer.md §1.3 |
| OverseerRecovered | O-T3 | overseer.md §1.3 |
| OverseerDraining | O-T4 | overseer.md §1.3 |

---

## Invariants (wire-level)

**INV-P1: Envelope wraps every cross-boundary message.** No bare payload appears on any stream. This keeps `envelope_id`, `sequence`, and `restart_epoch` uniformly available to middleware.

**INV-P2: `session_id` is required on every post-registration Envelope.** The only exception is `Registration` itself (which carries `target_session_id` in its body). Enforcement: Gateway rejects `session_id`-less Envelopes post-Registration with `ERROR_KIND = UNAUTHENTICATED`.

**INV-P3: One Event variant per boundary-crossing transition.** Adding a state to an FSM requires adding exactly one Event variant and one entry in the Wire -> FSM cross-reference.

**INV-P4: `restart_epoch` propagates.** Any Envelope emitted *because of* an Agent that has a non-zero `restart_epoch` carries that epoch (`AgentStatus`, `Heartbeat`, `TaskTelemetry`, `ArtifactFrame`). Consumers use the epoch for lineage disambiguation per §2.1.5.

**INV-P5: `transition_id` on Event is stable.** The string `'A-T2'` means A-T2 forever within the v0.1-beta-2 major version. Renaming or renumbering a transition requires a catalog version bump.

**INV-P6: Event delivery is Session-scoped.** Every `Event` envelope delivered through `Gateway.EventSubscribe` (`§services.proto`) MUST carry `Envelope.session_id` equal to the subscriber's authenticated `session_id`. Two enforcement points:

- At subscribe time: the Gateway MUST reject any `EventSubscribeRequest` whose `session_id` does not match the transport-authenticated session, with `ErrorKind = UNAUTHENTICATED` (bare `session_id`-mismatch) or `ErrorKind = SESSION_EXPIRED / SESSION_REVOKED` (session-lifetime miss). An unauthenticated subscribe MUST be rejected - no anonymous `/ws/live` consumer is permitted.
- At emit time: the Gateway MUST drop every `Event` whose `Envelope.session_id` does not equal the subscriber's `session_id` before it is placed on the subscriber's stream.

There is no cross-Session fan-out and no broadcast channel. Events that logically span Sessions (none in v0.1-beta-2) would require an explicit operator-scoped subscription variant.

*Testability:*
- **Negative (subscribe):** a subscriber authenticated to `SES-A` attempts `EventSubscribeRequest { session_id = SES-B }` and MUST receive `Error { kind = UNAUTHENTICATED }` on the first frame.
- **Negative (emit):** given two subscribers authenticated to `SES-A` and `SES-B`, emit an `Event` with `Envelope.session_id = SES-A`; assert exactly one subscriber observes it and the `SES-B` stream receives zero frames for that `event_id`.
- **Positive:** a subscriber authenticated to `SES-A` with `EventSubscribeRequest { session_id = SES-A, transition_ids = [...] }` observes every matching `Event` emitted under `SES-A`.

Closes the multi-tenant leak where `GET /ws/live` would broadcast Service/Binding/Worker events across the whole platform (divergence report §7.2). Required for Wave 3.2 (`/ws/live` consumes `EventSubscribeRequest` rather than a session-less HTTP upgrade).

---

## Design notes

**Opaque `google.protobuf.Struct` for future-typed payloads.** `Command.params`, `TaskSpec.params`, `Registration.host_identity`, and `TaskTelemetry.TaskProgress.metrics` are typed post-beta. `Struct` keeps them on the proto wire while preserving JSON-shape flexibility; lower conversion cost than a bytes-wrapped JSON blob and no separate serde layer on the SDK side.

**No `EventPayload` outer wrapper.** Considered and rejected. Wrapping every event variant in an outer `EventPayload` carrying transition metadata, with `Event.body` as `bytes`, costs a nested decode and loses strong typing on consumers. The current shape (outer `Event` with oneof + common fields, slim variants) is both wire-efficient and ergonomic.

**`target` oneof in `Command`.** Enforces exactly-one-target at codegen time and keeps the `Command` message slim compared to five optional fields.

**`ErrorKind = 0` is `UNSPECIFIED`.** Mandatory proto3 convention. Validators at parse boundaries reject `UNSPECIFIED` in practice.

**Backpressure / flow control** is a Channel transport concern (gRPC flow control + ack queues per reliability class), not an application-level frame. Channel FSM §2.10 enumerates Backpressured as a deferred state; the proto catalog need not model it.

**Spec vs. `.proto` files.** This document is the contract; the six `.proto` files listed in Layout are the implementation. A generator-check pass in CI keeps them in sync (deferred tooling).

---

## Sources

- [fsm-v0.1-beta-2/fsm-main.md - preface](fsm-main.md)
- [fsm-v0.1-beta-2/overseer.md - §1.3 Overseer states, §1.4 Matrix, §1.6 IR-O4](overseer.md)
- [fsm-v0.1-beta-2/agent.md - §2.1 Agent, incl. §2.1.5 restart lineage](atelier/atelier-notes/fsm-v0.1-beta-2/agent.md)
- [fsm-v0.1-beta-2/task.md - §2.2 Task](task.md)
- [fsm-v0.1-beta-2/binding.md - §2.3 Binding](binding.md)
- [fsm-v0.1-beta-2/service.md - §2.5 Service](service.md)
- [fsm-v0.1-beta-2/session.md - §2.7 Session](session.md)
- [fsm-v0.1-beta-2/compute-slot.md - §2.8 ComputeSlot](compute-slot.md)
- [fsm-v0.1-beta-2/gateway.md - §2.9 Gateway](gateway.md)
- [fsm-v0.1-beta-2/channel.md - §2.10 Channel](channel.md)
- [fsm-v0.1-beta-2/sink.md - §2.11 Sink](sink.md)
- [fsm-v0.1-beta-2/schema.md - persistence schema referenced by wire types](schema.md)
- [txy-v0.1-beta-2/txy-main.md - Skills, Channels, Sinks taxonomies](../txy-v0.1-beta-2/txy-main.md)
