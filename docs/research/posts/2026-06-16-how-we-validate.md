---
date: 2026-06-16
slug: how-we-validate
authors:
  - iteralabs
categories:
  - Methodology
description: >
  Claims about a research platform should be earned the same way claims about data are —
  by adversarial verification against a source of truth. Here is the discipline.
---

# How we validate the Atelier platform

A research platform makes two kinds of claims: claims about *data* ("these arrivals are
self-exciting") and claims about *itself* ("the system does what the spec says"). We hold both
to the same standard — a claim survives only if it is **verified against a source of truth by
an adversary trying to break it**. This note is about how that standard is applied to the
platform itself.

<!-- more -->

## The spec is the source of truth

A system validated against its own code is validated against nothing: bugs are consistent with
themselves. So correctness is defined *outside* the implementation, in a canonical
specification with two legs:

- a **Taxonomy** — the nouns: every identifier, scope, and operation the platform may name; and
- an **FSM Atlas** — the dynamics: the states, transitions, guards, and invariants every
  subsystem must obey.

The spec is the yardstick. Code is measured against it — never the other way around. When the
two disagree, that is a finding, and the finding names which side is wrong.

## Two independent streams of evidence

A claim of compliance is only as good as the evidence behind it, so we gather two kinds that
fail differently:

### 1 — Live deployment evidence

The control plane is **built from source, booted as the full stack, and driven through the
platform's fully-specified end-to-end sequences** — deploy and delete — on real
infrastructure. At each gate we check observed behavior against the spec: health endpoints,
the exact state a deploy pauses at, the state-machine transitions it drives, the wire and
event flow on the bus, and the schema in the database. This is the evidence that a system
*actually runs to spec*, not that it compiles.

### 2 — Static multi-agent audit

In parallel, **independent agents audit each subsystem against the spec** — one set scoped to
the ownership boundaries of each state machine, another checking every repository against the
Taxonomy. Because each agent sees only its slice, no single reviewer's blind spot becomes the
audit's blind spot. Breadth comes from fan-out; depth comes from scoping.

## Adversarial verification is the gate

Finding something is not the same as it being true. So **every load-bearing finding must
survive independent, skeptical re-checks before it is accepted** — verifiers are tasked with
*refuting* the claim, and a finding that cannot be confirmed is discarded rather than
reported. Only findings that survive the attempt to break them count.

This is the same discipline as the five-diagnostic consistency check in
[When are crypto order arrivals self-exciting?](2026-06-16-self-exciting-arrivals.md): there,
a Hawkes claim must survive CV, model selection, a likelihood-ratio test, goodness-of-fit,
*and* out-of-sample forecasting; here, a compliance claim must survive live evidence, an
independent audit, and an adversary. In both cases consensus across checks that fail
differently is what makes a result hard to fake.

## Why it matters

The gap between "we believe it works" and "we drove it end-to-end and adversarially verified
every claim" is the whole difference between a demo and infrastructure. Publishing the
*methodology* — not just the conclusions — is how a lab earns the benefit of the doubt: you
can see exactly how a claim was tested, and what would have falsified it.

!!! quote "Cite this note"
    ```bibtex
    @misc{iteralabs2026validate,
      title  = {How we validate the Atelier platform},
      author = {IteraLabs Research},
      year   = {2026},
      note   = {Atelier SDK research notes},
      url    = {https://www.iteralabs.xyz/atelier/docs/research/how-we-validate/}
    }
    ```
