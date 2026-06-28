# `atelier-agent`

The Atelier remote-agent binary. A long-running Rust process that
connects to the Atelier Gateway over gRPC, accepts work assignments
(TOML manifests for data and market workers), spawns the workers,
and streams telemetry + artifacts back upstream.

The agent is **binary-only** (`publish = false`). It has no library
API and no [docs.rs](https://docs.rs) page. This page is the
canonical reference for operating it.

!!! note "Source"
    Quoted material is lifted from `atelier-agent/src/main.rs` in
    atelier-sdk at v0.0.10. If the agent's CLI surface or env-var
    contract changes upstream, this page needs to be regenerated
    against the new source.

## Identity model — the W4.A contract

Three identity fields shape every agent run:

| Field         | Where it comes from                                                                              |
|---------------|---------------------------------------------------------------------------------------------------|
| `binding_id`  | Embedded in the JWT, minted by the Overseer at deploy time                                        |
| `service_id`  | Embedded in the JWT                                                                              |
| `session_id`  | Embedded in the JWT                                                                              |
| `agent_id`    | Allocated by the **Gateway** at A-T1, returned in `RegistrationResponse.Accepted`                 |
| `agent_alias` | User-facing label, auto-generated as `RA-<uuid>` if not provided                                  |

The agent **consumes a pre-issued JWT** — it does not self-sign.
`binding_id`, `service_id`, and `session_id` are extracted from the
token's claims and are *not* separate environment variables. The
authoritative `agent_id` is the Gateway's, not anything the operator
provides.

## Environment variables

| Env var                | CLI flag         | Default                          | Required |
|------------------------|------------------|----------------------------------|----------|
| `ATELIER_GATEWAY_URL`  | `--gateway-url`  | `http://localhost:50051`         | no       |
| `ATELIER_TOKEN`        | `--token`        | —                                | **yes**  |
| `AGENT_ALIAS`          | `--agent-alias`  | auto-generated `RA-<uuid>`       | no       |
| `RUST_LOG`             | —                | `info`                           | no       |

!!! warning "`AGENT_ID` is not read"
    Earlier iterations of the agent accepted an `AGENT_ID` env var.
    That has been removed (W1-1 in the source). The Gateway allocates
    the authoritative `agent_id` and returns it in the registration
    response. Setting `AGENT_ID` has no effect.

## CLI flags

```
atelier-agent [OPTIONS]

OPTIONS:
      --gateway-url <URL>      Gateway gRPC URL
                               [env: ATELIER_GATEWAY_URL]
                               [default: http://localhost:50051]

      --token <JWT>            Pre-issued JWT (the `token` field from the
                               webapp's deploy response).
                               [env: ATELIER_TOKEN]
                               (required — agent does not self-sign)

      --agent-alias <NAME>     User-facing label; auto-generated if omitted.
                               Never load-bearing — Gateway-allocated
                               agent_id is authoritative.
                               [env: AGENT_ALIAS]

      --json-logs              Emit structured JSON logs (recommended in
                               production).

  -h, --help                   Print help
  -V, --version                Print version
```

## Typical invocations

**Minimum**, JWT via env var:

```bash
ATELIER_TOKEN=eyJhbGc... atelier-agent
```

**Full configuration** via CLI flags:

```bash
atelier-agent \
  --gateway-url http://gateway:50051 \
  --token eyJhbGc...
```

**Production** with structured logs:

```bash
atelier-agent --json-logs
```

`RUST_LOG=info,atelier_connect=debug` is a common debug filter.

## Where the JWT comes from

The webapp's "Deploy agent" UI (the Spawn Modal's credential panel)
returns a JWT minted by the Overseer at B-T1. Operators copy that
token into the `ATELIER_TOKEN` env var on the host where the agent
will run. The token's claims include `binding_id`, `service_id`, and
`session_id` — the agent extracts them at startup via
`extract_claims_unverified`.

The Overseer's signing key is shared with the Gateway, which verifies
the token's signature on every connection attempt. The agent does
not have, and does not need, the signing key.

## Lifecycle

```mermaid
sequenceDiagram
    autonumber
    participant Op as Operator (you)
    participant Web as Webapp UI
    participant Over as Overseer
    participant Gate as Gateway
    participant Ag as atelier-agent

    Op->>Web: "Deploy agent"
    Web->>Over: Mint JWT (B-T1)
    Over-->>Web: token
    Web-->>Op: token

    Op->>Ag: ATELIER_TOKEN=… atelier-agent

    Ag->>Gate: Register (gRPC) (A-T1)
    Gate-->>Ag: agent_id, manifest

    Ag->>Ag: Spawn workers per manifest
    loop streaming
      Ag->>Gate: Telemetry envelopes
      Ag->>Gate: Artifact envelopes
    end

    Gate->>Ag: Lifecycle command (pause / resume / stop / restart)
    Ag->>Ag: Apply
    Ag->>Gate: Acknowledge

    Op->>Ag: SIGINT (Ctrl-C)
    Ag->>Gate: Final report + close
```

## Lifecycle commands the Gateway can send

| Command   | Effect                                                                                              |
|-----------|-----------------------------------------------------------------------------------------------------|
| `pause`   | Workers stop emitting events but keep their connections alive.                                       |
| `resume`  | Workers resume emission.                                                                            |
| `stop`    | Workers shut down cleanly. Agent exits.                                                              |
| `restart` | Workers shut down and respawn from the same manifest.                                                |

These mirror the REST `POST /api/workers/{id}/command` action set
documented on the [Backend reference](../backend/index.md) page.

## Telemetry channel

The agent streams a single unified upstream `Envelope` channel that
multiplexes telemetry samples and artifact bytes (Wave 2 unification).
Buffer capacity defaults to 256 envelopes, which absorbs both
metric-burst peaks and artifact flushes without backpressuring the
worker loop. The `RemoteAgentConfig::telemetry_buffer` field is
exposed for tuning if necessary.

The metric vocabulary itself is from
[`atelier-telemetry`](../sdk/telemetry/index.md): `MESSAGES_RECEIVED`,
`EVENT_LATENCY_MS`, `WORKER_CONNECTION_STATE`, `SINK_QUEUE_DEPTH`.

## Deployment — Docker

!!! info "Image not yet published"
    The agent's Docker image is **planned** at
    `ghcr.io/iteralabs/atelier-agent` once the agent is published as
    a deployment artifact. This section will be filled in with the
    actual image tag, supported architectures, recommended resource
    limits, and the Docker Compose wiring at that time. For the
    beta, run the agent natively from a `cargo build --release`.

Sketch of the eventual deployment shape:

```bash
docker run -d \
  --name atelier-agent-prod \
  -e ATELIER_GATEWAY_URL=https://gateway.iteralabs.xyz:50051 \
  -e ATELIER_TOKEN=... \
  -e RUST_LOG=info \
  --restart unless-stopped \
  ghcr.io/iteralabs/atelier-agent:0.0.10
```

The agent runs as a long-lived container managed by Docker Compose
in `atelier-infra` (`docker-compose.beta.yml`), with `ATELIER_TOKEN`
supplied from the environment.

## Common operational issues

**The agent exits with `error: registration rejected`.**
The Gateway rejected the JWT. Causes: token expired, token not minted
against the Gateway's current signing key, `binding_id` already in
use by another active agent. Resolution: mint a fresh token from the
webapp's Spawn Modal.

**The agent connects but spawns no workers.**
The manifest the Gateway sent has no `[[workers]]` entries, or all
entries failed to resolve. Check the agent's logs for
`workers.spawn_failed` events.

**Telemetry envelopes back up.**
The upstream Envelope channel is full (default 256 capacity). Either
the Gateway is consuming slowly or worker output is bursty. Bump
`RemoteAgentConfig::telemetry_buffer` and rebuild, or investigate
Gateway-side ingestion latency via the
[`atelier-telemetry`](../sdk/telemetry/index.md) `SINK_QUEUE_DEPTH`
metric.

## Related material

- [Backend reference](../backend/index.md) — the REST/WebSocket/gRPC
  API the Gateway exposes.
- [`atelier-connect`](../sdk/connect/index.md) — the worker
  primitives the agent spawns from manifests.
- [`atelier-telemetry`](../sdk/telemetry/index.md) — metric vocabulary
  the agent populates upstream.
