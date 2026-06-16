
# Clean
---

Remove, if existing, all the services.

```bash
cd ~/git/iteralabs/atelier-infra
docker compose -f docker-compose.beta.yml down -v --remove-orphans
for r in atelier-proto atelier-sdk atelier-backend atelier-webapp; do
  (cd ~/git/iteralabs/$r && cargo clean)
done
```

# From 0 to Service
---

Build all that is in the docker-compose.yml

```bash
cd ~/git/iteralabs/atelier-infra
docker compose -f docker-compose.beta.yml up --build -d
```

# Launch Service
---

Create the Manifest and the curl post to create a service

```bash
MANIFEST_TOML='[collect]
exchange = "binance"
[collect.datatypes.orderbook]
enabled = true
depth = 50
[collect.datatypes.trades]
enabled = false
[collect.datatypes.liquidations]
enabled = false
[collect.datatypes.funding_rates]
enabled = false
[collect.datatypes.open_interest]
enabled = false
[collect.sync]
sync_mode = "on_time"
flush_threshold = 40
[collect.sync.update_frequency]
value = 250
unit = "Millis"
[[collect.output]]
type = "parquet"
dir = "datasets/collected/binance/"
[[collect.output]]
type = "terminal"
[[workers]]
symbol = "BTCUSDT"'

RESP=$(curl -s -X POST http://localhost:8000/api/services \
  -H "Authorization: Bearer dev-token" -H "Content-Type: application/json" \
  -d "$(jq -n --arg toml "$MANIFEST_TOML" '{kind:"data", manifest_toml:$toml}')")

echo "$RESP" | jq
export TOKEN_JWT=$(echo "$RESP" | jq -r '.token')
export BINDING_ID=$(echo "$RESP" | jq -r '.binding_id')
export SERVICE_ID=$(echo "$RESP" | jq -r '.service_id')
```

Run the agent and attach it to the previously generated service

```bash
docker run --rm -d --name atelier-agent \
  -v "$HOME/atelier-data:/home/agent" \
  -e ATELIER_GATEWAY_URL="http://host.docker.internal:50443" \
  -e ATELIER_TOKEN="$TOKEN_JWT" \
  -e RUST_LOG=info \
  ghcr.io/iteralabs/atelier-agent:latest-arm64
```





Load Environment Variables

```bash
source .env
```


Build the agent's image (optionally)

```bash
docker build -f ~/git/iteralabs/atelier-infra/dockerfiles/agent.Dockerfile \
    -t iteralabs/atelier-agent:latest ~/git/iteralabs
```

Optionally, the GHCR image can be used:

```bash
ghcr.io/iteralabs/atelier-agent:latest-arm64
```
