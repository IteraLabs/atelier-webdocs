# Operations

Operator-facing material: how to run the binary components of the
Atelier platform, how the docs site itself is built and deployed,
and the runbooks for production-affecting operations like the
docs-cutover atomic swap.

- [atelier-agent](agent.md) — the remote-agent binary: CLI flags,
  environment variables, the gateway/JWT handshake, and (eventually)
  the published Docker image.
- [Cutover runbook](cutover-runbook.md) — atomic-swap procedure for
  moving `/atelier/docs/` from the webapp container to the standalone
  docs container.
