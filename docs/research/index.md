---
description: Research notes from IteraLabs — methodology, microstructure, and the quantitative machinery behind the Atelier platform.
---

# Research

Notes from the lab. Short, dated, authored pieces on market microstructure, point-process
modelling, deterministic replay, and the engineering that makes the [Atelier
SDK](../sdk/index.md) reproducible.

These are not marketing posts and not API docs — they are the **methodology** behind the
numbers: the testable claims we make about market data, how we validate them, and the cases
where the honest answer is "the simple model is enough." Every piece links to the exact code
that produced it, so results are reproducible rather than asserted.

!!! tip "Reproducibility"
    Each post names the SDK crate, example, and version it draws from. Where a result depends
    on data, the dataset and the command that generated it are stated inline — run it yourself.
