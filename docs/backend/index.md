# Backend reference

The Atelier backend exposes three transport layers:

- **REST** at `:8000` for synchronous resource operations (subscriptions, dashboard stats, worker spawn/control).
- **WebSocket** at `/ws/live` for real-time fleet telemetry.
- **gRPC** at `:50051` for high-throughput data queries against the bronze layer.

This page documents all three. For the SDK that wraps them, see the
[SDK reference](../sdk/index.md).

## Authentication

All `/api/*` routes require a JWT bearer token in the `Authorization` header.

```
Authorization: Bearer <token>
```

The JWT payload carries the following claims:

| Claim   | Type       | Description           |
|---------|------------|-----------------------|
| `sub`   | UUID       | User ID               |
| `email` | string     | User email            |
| `exp`   | unix timestamp | Token expiration  |
| `iat`   | unix timestamp | Issued-at         |

> **Dev bypass** — set `AUTH_DEV_BYPASS=true`. The literal token `dev-token` is then accepted
> without JWT validation and resolves to a hardcoded identity
> (`00000000-0000-0000-0000-000000000001` / `dev@atelier.local`).

Health-check and WebSocket routes are **unauthenticated**.

## Error responses

Every REST error body follows a single shape:

```json
{ "error": "<human-readable message>" }
```

| Variant       | Status | Meaning                          |
|---------------|--------|----------------------------------|
| `Validation`  | 400    | Malformed or invalid input       |
| `Unauthorized`| 401    | Missing or invalid token         |
| `Forbidden`   | 403    | Valid token, insufficient access |
| `NotFound`    | 404    | Resource does not exist          |
| `Conflict`    | 409    | Duplicate or state conflict      |
| `Database`    | 500    | Internal persistence failure     |
| `Internal`    | 500    | Catch-all server error           |
| `Kafka`       | 503    | Event-bus unavailable            |

---

## REST API

### Health

These routes are **unauthenticated** and sit outside the `/api` prefix.

#### `GET /health`

Liveness probe. Always `200 OK`.

**Response:**

```json
{
  "status": "ok",
  "timestamp": "2025-04-13T12:00:00Z"
}
```

---

#### `GET /health/ready`

Readiness probe. Checks PostgreSQL and Kafka connectivity.

**Response `200`** (all healthy) **or `503`** (degraded):

```json
{
  "status": "ok",
  "postgres": true,
  "kafka": true,
  "timestamp": "2025-04-13T12:00:00Z"
}
```

`status` is `"ok"` when both dependencies are reachable, `"degraded"` otherwise.

---

### Subscriptions

#### `POST /api/subscriptions`

Create a market-data subscription.

**Headers:** `Authorization: Bearer <token>`, `Content-Type: application/json`

**Request body:**

| Field      | Type   | Required | Rules |
|------------|--------|----------|-------|
| `exchange` | string | yes | One of `bybit`, `binance`, `coinbase`, `kraken`. Case-insensitive; stored lowercase. |
| `pair`     | string | yes | Format `XXX/YYY`, each symbol 2–10 ASCII-alpha chars. Case-insensitive; stored uppercase. |
| `user_id`  | UUID   | yes | — |

```json
{
  "exchange": "binance",
  "pair": "SOL/USDT",
  "user_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response `201 Created`:**

```json
{
  "id": "a1b2c3d4-...",
  "exchange": "binance",
  "pair": "SOL/USDT",
  "status": "active",
  "created_at": "2025-04-13T12:00:00Z"
}
```

> **Side effect:** publishes a Kafka event to `dataset.subscriptions` (partition key `{exchange}:{pair}`).

---

#### `GET /api/subscriptions`

List all subscriptions for a user.

**Headers:** `Authorization: Bearer <token>`

**Query parameters:**

| Param     | Type | Required |
|-----------|------|----------|
| `user_id` | UUID | yes      |

**Response `200`:**

```json
{
  "subscriptions": [
    {
      "id": "a1b2c3d4-...",
      "exchange": "binance",
      "pair": "SOL/USDT",
      "status": "active",
      "created_at": "2025-04-13T12:00:00Z"
    }
  ]
}
```

---

#### `DELETE /api/subscriptions/{id}`

Delete a subscription.

**Headers:** `Authorization: Bearer <token>`

**Path parameters:**

| Param | Type | Description       |
|-------|------|-------------------|
| `id`  | UUID | Subscription ID   |

**Response `200`:**

```json
{ "id": "a1b2c3d4-...", "status": "deleted" }
```

> **Side effect:** publishes a Kafka event to `dataset.unsubscriptions`.

---

### Dashboard

#### `GET /api/dashboard/stats`

Aggregated trade statistics for a given exchange/pair.

**Headers:** `Authorization: Bearer <token>`

**Query parameters:**

| Param      | Type   | Required |
|------------|--------|----------|
| `exchange` | string | yes      |
| `pair`     | string | yes      |

**Response `200`:**

```json
{
  "exchange": "binance",
  "pair": "SOL/USDT",
  "trade_count_1h": 42,
  "trade_count_24h": 1200,
  "latest_price": "123.45",
  "avg_trade_size_1h": "0.5",
  "latest_trade_at": "2025-04-13T12:00:00Z",
  "update_timestamp": "2025-04-13T12:00:00Z"
}
```

| Field              | Type              | Nullable |
|--------------------|-------------------|----------|
| `trade_count_1h`   | integer           | no       |
| `trade_count_24h`  | integer           | no       |
| `latest_price`     | decimal (string)  | yes      |
| `avg_trade_size_1h`| decimal (string)  | yes      |
| `latest_trade_at`  | ISO 8601 datetime | yes      |
| `update_timestamp` | ISO 8601 datetime | no       |

---

### Workers

#### `GET /api/workers`

List all active workers with telemetry.

**Headers:** `Authorization: Bearer <token>`

**Response `200`:**

```json
{
  "counts": { "total": 5, "active": 4, "paused": 1 },
  "workers": [
    {
      "id": "binance:BTCUSDT:0",
      "exchange": "Binance",
      "symbol": "BTCUSDT",
      "market_type": "Spot",
      "mode": "Producer",
      "connection_state": "Connected",
      "messages_per_sec": 10.5,
      "total_events": 50000,
      "reconnect_count": 2,
      "uptime_secs": 3600.0
    }
  ]
}
```

| Worker field       | Type    | Description                     |
|--------------------|---------|---------------------------------|
| `id`               | string  | Composite key `exchange:symbol:index` |
| `exchange`         | string  | Exchange name                   |
| `symbol`           | string  | Trading pair without `/`        |
| `market_type`      | string  | `Spot`, `Futures`, etc.         |
| `mode`             | string  | `Producer`, etc.                |
| `connection_state` | string  | `Connected`, `Disconnected`, …  |
| `messages_per_sec` | float   | Current throughput              |
| `total_events`     | integer | Lifetime event count            |
| `reconnect_count`  | integer | Number of reconnections         |
| `uptime_secs`      | float   | Seconds since spawn             |

---

#### `POST /api/workers`

Spawn one or more workers from a TOML manifest.

**Headers:** `Authorization: Bearer <token>`, `Content-Type: application/json`

**Request body:**

| Field           | Type   | Required | Description |
|-----------------|--------|----------|-------------|
| `kind`          | string | yes      | `"data"` or `"market"` |
| `manifest_toml` | string | yes      | Raw TOML content (native atelier-sdk config format) |

When `kind` is `"data"`, the TOML is parsed as a `DataWorkerManifest`. When `"market"`, as a `MarketWorkerManifest`. Each manifest can define multiple `[[workers]]` entries; all are spawned in one call.

**Example — spawn data workers:**

```bash
curl -X POST http://localhost:8000/api/workers \
  -H "Authorization: Bearer dev-token" \
  -H "Content-Type: application/json" \
  -d '{
    "kind": "data",
    "manifest_toml": "[collect]\nexchange = \"binance\"\n\n[collect.datatypes.orderbook]\nenabled = true\ndepth = 20\n\n[collect.datatypes.trades]\nenabled = true\n\n[[collect.output]]\ntype = \"channel\"\n\n[[collect.output]]\ntype = \"terminal\"\n\n[[workers]]\nsymbol = \"ETHUSDC\"\n\n[[workers]]\nsymbol = \"BTCUSDC\"\n\n[session]\nduration_hours = 0.05"
  }'
```

**Response `200`:**

```json
{ "worker_ids": ["binance:ETHUSDC:0", "binance:BTCUSDC:0"] }
```

---

#### `POST /api/workers/{id}/command`

Send a lifecycle command to a running worker.

**Headers:** `Authorization: Bearer <token>`, `Content-Type: application/json`

**Path parameters:**

| Param | Type   | Description                          |
|-------|--------|--------------------------------------|
| `id`  | string | Worker ID (e.g. `binance:BTCUSDT:0`) |

**Request body:**

| Field    | Type   | Required | Allowed values                       |
|----------|--------|----------|--------------------------------------|
| `action` | string | yes      | `pause`, `resume`, `stop`, `restart` |

**Response `200`:**

```json
{ "status": "ok", "worker_id": "binance:BTCUSDT:0", "action": "pause" }
```

---

## WebSocket API

### `GET /ws/live`

Upgrades the connection to a WebSocket. **No authentication required.**

### Connection lifecycle

1. Client opens a standard WebSocket handshake to `/ws/live`.
2. Server immediately sends a `fleet_snapshot` event with the full current state.
3. Server continuously pushes events as they occur.
4. Client may send commands back over the same socket.
5. Either side closing the connection terminates the session.

### Server-to-client events

Every frame is a JSON object with a `"type"` discriminator.

#### `fleet_snapshot`

Sent once on connect. Contains the full worker fleet state so the client doesn't need to wait for individual updates.

```json
{
  "type": "fleet_snapshot",
  "workers": [
    {
      "id": "binance:BTCUSDT:0",
      "exchange": "Binance",
      "symbol": "BTCUSDT",
      "market_type": "Spot",
      "mode": "Producer",
      "connection_state": "Connected",
      "messages_per_sec": 10.5,
      "total_events": 50000,
      "reconnect_count": 2,
      "uptime_secs": 3600.0
    }
  ]
}
```

#### `worker_status`

Periodic telemetry snapshot for a single worker. Same fields as each entry in `fleet_snapshot.workers`.

```json
{
  "type": "worker_status",
  "id": "binance:BTCUSDT:0",
  "exchange": "Binance",
  "symbol": "BTCUSDT",
  "connection_state": "Connected",
  "messages_per_sec": 10.5,
  "total_events": 50000,
  "reconnect_count": 2,
  "uptime_secs": 3600.0
}
```

#### `sink_statuses`

Output-sink health update for a worker.

```json
{
  "type": "sink_statuses",
  "worker_id": "binance:BTCUSDT:0",
  "sinks": [
    {
      "name": "kafka-sink",
      "state": "Active",
      "events_emitted": 50000,
      "bytes_written": 5242880,
      "queue_depth": 100,
      "queue_capacity": 1000
    }
  ]
}
```

| Sink field       | Type             | Nullable | Description                 |
|------------------|------------------|----------|-----------------------------|
| `name`           | string           | no       | Sink identifier             |
| `state`          | string           | no       | Current state               |
| `events_emitted` | integer          | no       | Total events pushed         |
| `bytes_written`  | integer          | yes      | Total bytes written         |
| `queue_depth`    | integer          | yes      | Current backpressure depth  |
| `queue_capacity` | integer          | yes      | Max queue size              |

#### `log`

Engine or manager log entry.

```json
{
  "type": "log",
  "worker_id": "binance:BTCUSDT:0",
  "level": "info",
  "message": "Connected to wss://stream.binance.com"
}
```

`level` is one of `info`, `warn`, `error`.

#### `worker_finished`

Emitted when a worker exits cleanly (e.g. session duration elapsed).

```json
{
  "type": "worker_finished",
  "worker_id": "binance:BTCUSDT:0",
  "report_summary": "Collected 12340 events in 180s"
}
```

### Client-to-server commands

Send a JSON object to control a worker:

```json
{
  "action": "pause",
  "worker_id": "binance:BTCUSDT:0"
}
```

| Field       | Type   | Required | Allowed values                       |
|-------------|--------|----------|--------------------------------------|
| `action`    | string | yes      | `pause`, `resume`, `stop`, `restart` |
| `worker_id` | string | yes      | Target worker ID                     |

---

## gRPC API

Service: `atelier.data.v1.DataService` — binds on port `50051` by default.

Proto source: `proto/atelier/data/v1/data_service.proto` in the backend repo.

### `GetRawTrades`

Fetch raw trades from the PostgreSQL bronze layer.

**Request — `GetRawTradesRequest`:**

| Field            | Type                          | Required | Default     | Constraints |
|------------------|-------------------------------|----------|-------------|-------------|
| `exchange`       | string                        | yes      | —           |             |
| `pair`           | string                        | yes      | —           |             |
| `from_timestamp` | `google.protobuf.Timestamp`   | no       | now − 1 hour|             |
| `to_timestamp`   | `google.protobuf.Timestamp`   | no       | now         |             |
| `limit`          | int32                         | no       | 1000        | max 10000   |

**Response — `GetRawTradesResponse`:**

```protobuf
repeated RawTrade trades = 1;
```

| `RawTrade` field | Type                        | Description                   |
|------------------|-----------------------------|-------------------------------|
| `id`             | string                      | Trade UUID                    |
| `exchange`       | string                      | Exchange name                 |
| `pair`           | string                      | Trading pair                  |
| `timestamp`      | `google.protobuf.Timestamp` | Trade timestamp               |
| `price`          | string                      | Decimal as string (precision) |
| `size`           | string                      | Decimal as string (precision) |
| `side`           | string                      | `"buy"` or `"sell"`           |
| `trade_id`       | string                      | Exchange-native trade ID      |

> **Planned:** `QueryArrow` RPC for streaming Arrow RecordBatches (not yet implemented).

---

## Configuration

### Environment variables

| Variable                  | Required | Default                                     | Description                               |
|---------------------------|----------|---------------------------------------------|-------------------------------------------|
| `REST_HOST`               | no       | `0.0.0.0`                                   | REST server bind host                     |
| `REST_PORT`               | no       | `8000`                                      | REST server bind port                     |
| `GRPC_PORT`               | no       | `50051`                                     | gRPC server bind port                     |
| `DATABASE_URL`            | **yes**  | —                                           | PostgreSQL connection string              |
| `DATABASE_MAX_CONNECTIONS`| no       | `10`                                        | Connection pool size                      |
| `KAFKA_BROKERS`           | **yes**  | —                                           | Kafka broker addresses                    |
| `KAFKA_GROUP_ID`          | no       | `atelier-backend`                           | Kafka consumer group ID                   |
| `JWT_SECRET`              | no       | `dev-secret-not-for-production`             | JWT signing/validation secret             |
| `AUTH_DEV_BYPASS`         | no       | `false`                                     | Accept `dev-token` without JWT validation |
| `RUST_LOG`                | no       | `atelier_backend=debug,tower_http=debug`    | Tracing/logging filter                    |

### Middleware stack

| Layer    | Scope          | Description                              |
|----------|----------------|------------------------------------------|
| CORS     | all routes     | Permissive — allows all origins, methods, headers |
| Tracing  | all routes     | Tower HTTP trace layer for request logging |
| Auth     | `/api/*` only  | JWT validation; injects claims into request extensions |


### Manual CURL

```bash
 curl -X POST http://localhost:8000/api/workers \
  -H "Authorization: Bearer dev-token" \
  -H "Content-Type: application/json" \
  -d '{
    "kind": "data",
    "manifest_toml": "[collect]\nexchange = \"binance\"\n\n[collect.datatypes.orderbook]\nenabled = true\ndepth = 20\n\n[collect.datatypes.trades]\nenabled = true\n\n[collect.datatypes.liquidations]\nenabled = false\n\n[collect.datatypes.funding_rates]\nenabled = false\n\n[collect.datatypes.open_interest]\nenabled = false\n\n[[collect.output]]\ntype = \"channel\"\n\n[[collect.output]]\ntype = \"terminal\"\n\n[[workers]]\nsymbol = \"ETHUSDC\"\n\n[[workers]]\nsymbol = \"BTCUSDC\"\n\n[session]\nduration_hours = 0.05"
  }'
```
