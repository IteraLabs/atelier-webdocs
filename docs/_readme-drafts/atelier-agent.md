# atelier-agent

The Atelier remote-agent binary. Connects to the Atelier Gateway over
a JWT-authenticated channel, accepts work assignments, spawns workers,
streams telemetry and artifacts back upstream.

This crate is **binary-only** — there is no library API and no docs.rs
page.

## Documentation

- **Operator reference (CLI flags, env vars, JWT contract, deployment):**
  [www.iteralabs.xyz/atelier/docs/operations/agent/](https://www.iteralabs.xyz/atelier/docs/operations/agent/)

## License

Apache-2.0 — part of the [atelier-sdk](https://github.com/IteraLabs/atelier-sdk) workspace.
