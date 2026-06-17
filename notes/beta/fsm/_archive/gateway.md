# Atelier FSM Atlas - Gateway (§2.9)

Part of the **State Machine Atlas v0.1-beta-2**. See `fsm-main.md` for the reading guide, notation, §2.4 FSMs - scope status, and §3 Cross-FSM Sequences. Owns the `INV-GW*` invariant prefix. Cross-references: `overseer.md` (§1, §1.7 Recovery), `agent.md` (§2.1, §2.1.5), `channel.md` (§2.10). Participates in **SEQ-1 Deploy** (`sequences.md`) - GW-T2 Ready is a precondition; INV-GW1 (RemoteAgent soft-restart connection persistence) is the contract backing §2.1.5 and `channel.md §2.10` INV-CH5.

This FSM is specified at **minimal** depth: process-level lifecycle only. Per-connection state (per-Agent tunnel health, sequence numbers, reconnection bookkeeping) lives in the Channel FSM (§2.10) and in the SDK-side reconnection logic that v0.1-beta-2 does not re-specify.

---

## 2.9 Gateway FSM (minimal)

The Gateway is a System Process at the boundary between the Remote Domain and the Platform Domain. It authenticates RemoteAgent connections, multiplexes Command/Manifest/Telemetry/Data/Artifact channels over a single transport, and routes messages between RemoteAgents and the Overseer. PlatformAgents do not traverse the Gateway; their Channels are direct.

### 2.9.1 States

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  GATEWAY STATES                                                              │
│                                                                              │
│     Starting ──► Ready ◄─► Degraded ──► Stopping ──► Stopped                 │
│                                 ▲                                            │
│                                 └── (independent of Overseer mode)           │
│                                                                              │
│  Ready ↔ Degraded is bidirectional.                                          │
│  Stopped: absorbing terminal for this Gateway process instance.              │
└──────────────────────────────────────────────────────────────────────────────┘
```

**S-GW1: Starting.** The Gateway process has started; it is binding listening sockets, establishing its upstream Overseer session, and materializing its routing table from Overseer-known Binding topology. No client connections are accepted yet.

Entry: GW-T1 (process launch).
Exit: GW-T2 (ready to accept connections) or GW-T5 (operator stop during startup).

**S-GW2: Ready.** Steady state. Listeners are open; incoming RemoteAgent connections are authenticated (JWT-validated) and routed. All five Channel categories (Command, Manifest, Telemetry, Data, Artifact-to-platform) are multiplexed over the accepted transport. Platform-side event bus and persistent storage for audit are reachable.

Entry: GW-T2, GW-T4 (recovery from Degraded).
Exit: GW-T3 (subsystem dependency lost), GW-T5 (operator stop).

**S-GW3: Degraded.** The Gateway continues to route *existing connections* but is operating with a degraded dependency: typically the platform-side event bus is unreachable (so Telemetry delivery to the Overseer is buffered or dropped per reliability class), or the audit store is unreachable (so audit events are buffered). New RemoteAgent connections MAY still be accepted depending on which subsystem is degraded (policy detail; minimum: JWT validation must remain available, else connections are rejected with a retry-after hint).

Entry: GW-T3.
Exit: GW-T4 (subsystem recovered), GW-T5 (operator stop).

**S-GW4: Stopping.** Graceful shutdown in progress. The Gateway rejects new connections; existing connections are allowed to complete their in-flight request/reply exchanges; the Gateway signals shutdown to connected RemoteAgents so the SDK can initiate reconnect-against-another-Gateway (multi-Gateway deployment, out of scope for v0.1 but forward-compatible).

Entry: GW-T5.
Exit: GW-T6 (all existing connections closed, listeners torn down, resources released).

**S-GW5: Stopped.** Absorbing terminal for this Gateway process instance. A new Gateway process is a new FSM instance with its own state.

Entry: GW-T6.
Exit: none (terminal; a new process restart is a new FSM).

### 2.9.2 Transitions

```
GW-T1:  (creation) ──► Starting
        Trigger:  Gateway process launch.
        Guard:    Persistent storage reachable (to read Binding topology for
                  routing table materialization).
        Effects:  Initialize process; bind listening sockets (but do not start
                    accepting yet); load Binding topology from persistent
                    storage; establish Overseer-side session (the Gateway is
                    itself a client of the Overseer's system-process registry).

GW-T2:  Starting ──► Ready
        Trigger:  Listeners bound, routing table materialized, Overseer-side
                  session established and Overseer has ack'd GatewayReady.
        Guard:    All Gateway subsystems (JWT validation, persistent storage,
                  platform event bus) reachable.
        Effects:  Accept incoming connections; emit GatewayReady event.

GW-T3:  Ready ──► Degraded
        Trigger:  A subsystem dependency becomes unreachable: platform event bus
                  (telemetry delivery), persistent storage for audit, or any
                  non-critical dependency.
        Guard:    JWT validation is still available (else this is not Degraded -
                  it is Stopping pending recovery; out of scope for v0.1).
        Effects:  Persist Gateway status=degraded, degraded_at, degraded_subsystem;
                  continue routing existing connections;
                  emit GatewayDegraded event with subsystem detail.

GW-T4:  Degraded ──► Ready
        Trigger:  Previously-unavailable subsystem returns (re-probed or receives
                  a health signal).
        Guard:    All Gateway subsystems reachable.
        Effects:  Persist Gateway status=ready, recovered_at;
                  drain any buffered Telemetry / audit events;
                  emit GatewayReady event.

GW-T5:  {Ready, Degraded, Starting} ──► Stopping
        Trigger:  Operator Stop of the Gateway process; platform-level shutdown
                  signal (SIGTERM); host OS shutdown.
        Guard:    none (shutdown is always accepted).
        Effects:  Stop accepting new connections;
                  signal shutdown on each existing CommandChannel (so SDKs can
                    initiate reconnect-elsewhere if multi-Gateway);
                  emit GatewayStopping event;
                  set a shutdown deadline for forced close (config: gateway_
                    shutdown_deadline, default 30s).

GW-T6:  Stopping ──► Stopped
        Trigger:  All existing connections closed (either drained gracefully or
                  forced after shutdown_deadline) AND listeners torn down.
        Guard:    none.
        Effects:  Release resources; emit GatewayStopped event; process exits.
```

### 2.9.3 Invariants

**INV-GW1: RemoteAgent soft-restart connection persistence (per §2.1.5).**
Gateway does NOT close, cycle, or re-handshake a connection when the connected RemoteAgent fires A-T8 `{Ready, Bound} -> Restarting`. The Agent's process re-initializes in place on top of the existing transport. This is a contract the Gateway FSM honors in v0.1; it is not relaxable from the Gateway side without an Atlas revision.

**INV-GW2: JWT authentication at connect, not at every message.**
Connection-level JWT validation happens once at accept. Per-message auth is not performed in v0.1 (future work if needed). A connection remains authenticated until the transport closes; on transport close, re-authentication is required for a new connection.

**INV-GW3: No Gateway-initiated connections into the Remote Domain.**
Per taxonomy HOW §Domain boundary: the Gateway accepts connections from the Remote Domain but does not initiate. A-T9 / A-T10 (Agent connection loss / reconnect) drive reconnection from the Agent side; Gateway is passive in that direction.

**INV-GW4: Gateway routing state is derived, not authoritative.**
The Gateway's in-memory routing table is materialized from persistent storage (Binding topology) at GW-T1. It is updated incrementally via Overseer push for Binding creation/release during the Gateway's lifetime. On any inconsistency (e.g., an incoming message references an unknown binding_id), the Gateway rejects with `COMMAND_TARGET_UNKNOWN` and requests a routing-table refresh from the Overseer. The Gateway does not own Binding state; the Overseer does.

**INV-GW5: Gateway state is process-scoped, not persisted across restart.**
A new Gateway process is a new FSM instance. Recovery of connected RemoteAgents across Gateway restart is the SDK's responsibility (reconnect-with-same-JWT until JWT expires). This simplifies the v0.1 Gateway; a multi-Gateway HA deployment with state handoff is out of scope.

**INV-GW6: Overseer mode does not drive Gateway state.**
Overseer Drain (T6) does NOT cascade to Gateway Stopping. Overseer Degraded does NOT force Gateway Degraded. The Gateway operates its own subsystem observability. The only Overseer-driven Gateway influence is the push of routing updates (which happens while both are healthy).

### 2.9.4 Interaction Rules

**Gateway <-> Overseer (IR-GWO)**

- **IR-GWO1: Routing topology push.** Overseer pushes B-T1 (Binding created) and B-T8 (Binding released) events to Gateway, which updates its routing table. The push is idempotent; Gateway tolerates replay (it de-dupes by `(binding_id, version)`).
- **IR-GWO2: Telemetry to Overseer.** Gateway forwards TelemetryChannel messages (Agent -> Overseer) subject to platform event-bus reachability. When GW-T3 fires due to event-bus loss, Gateway buffers Telemetry up to a bounded size; overflow drops oldest (Telemetry reliability class is best-effort).
- **IR-GWO3: Gateway registers as a system process with Overseer.** Not a Binding (Gateway is not an Agent); a dedicated system-process registry row in persistent storage. Overseer uses this to address the Gateway for routing pushes.
- **IR-GWO4: Overseer restart does not close Gateway connections.** Per §1.7 Recovery and IR-SNO5 / INV-GW5 / INV-GW6: Overseer and Gateway are independent processes with independent lifecycles. An Overseer restart re-reads routing topology and pushes a fresh snapshot to the Gateway; the Gateway's connected RemoteAgents are unaffected.

**Gateway <-> Agent (IR-GWA)**

- **IR-GWA1: Accept = {JWT-valid, routing-known}.** An incoming connection presents its Session JWT and its declared `agent_id`. Gateway validates the JWT and looks up `agent_id` in its routing table. Rejection reasons: `JWT_INVALID`, `JWT_EXPIRED`, `AGENT_UNKNOWN`.
- **IR-GWA2: A-T8 Restart is transparent.** The Agent's Restart (A-T8) is a process-internal event; the Gateway does not observe any Channel-level signal and does not alter connection state. Per INV-GW1.
- **IR-GWA3: A-T12 Lost.** If the Gateway's transport layer observes a disconnect (socket close, TCP RST, keepalive failure) on a connection whose Agent was in {Bound, Restarting}, the Gateway emits a `ConnectionLost{agent_id}` event to the Overseer. The Overseer uses this to drive A-T12 (Ready/Bound -> Lost) or A-T13 (Restarting -> Lost) per `agent.md §2.1`.
- **IR-GWA4: A-T10 Reconnect.** A returning Agent connects fresh; Gateway accepts as in IR-GWA1. If the Agent's `agent_id` corresponds to a Binding still in `draining` (per Binding FSM §2.3 after an Overseer Drain), the Overseer reconciles (IR-O5) on receipt of the fresh CommandChannel heartbeat.

**Gateway <-> Channel (IR-GWC)**

- **IR-GWC1:** Channels (§2.10) between a RemoteAgent and the Overseer are multiplexed over the Gateway's accepted transport. The Gateway observes Channel-level open acks (Opening -> Open) and surfaces them as routing-ready signals to the Overseer.
- **IR-GWC2:** On Gateway Stopping (GW-T5), all Channels transition to their internal Draining state (§2.10 deferred detail); SDK-side reconnect logic handles re-establishment against a new Gateway process.

### 2.9.5 Notes

- **Multi-Gateway HA deferred.** v0.1 assumes a single Gateway process per deployment. Connection handoff between Gateways, state replication, and Gateway election are out of scope. The FSM is written to be forward-compatible with a multi-Gateway future (Stopping signals "reconnect-elsewhere" is a hint already, not a hard close).
- **JWT expiry mid-connection.** v0.1 treats JWT expiry lazily: the connection remains open until the Agent disconnects for independent reasons. Re-authentication happens on the next connect. A future version may enforce mid-connection re-auth on JWT expiry.
- **ArtifactChannel direction.** ArtifactChannels from RemoteAgents to platform Sinks traverse the Gateway (upstream). ArtifactChannels from RemoteAgents to client-local Sinks do NOT traverse the Gateway (local). Gateway routing table only carries routing for upstream ArtifactChannels.
- **`gateway_shutdown_deadline` config.** Lives in the timeout/config catalog.
- **Testability.** Every `INV-GW*` is asserted at its transition boundary or at Channel-level accept/forward time. `INV-GW1` is specifically tested by an integration test that fires A-T8 Restart on a RemoteAgent connected through the Gateway and asserts the Gateway-side connection object is unchanged (same socket, same sequence numbers). See the invariant testability convention in `fsm-main.md` preface.
