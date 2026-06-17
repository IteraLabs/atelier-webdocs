---
description: End-to-end, task-oriented walkthroughs for the Atelier SDK — collection, synchronization, and model fitting.
---

# Tutorials

Task-oriented, end-to-end walkthroughs. Each starts from a clean project and ends with a
runnable result you can inspect. New to the SDK? Read
[Getting started](../sdk/getting-started.md) first.

<div class="grid cards" markdown>

-   __1 · Bybit → Parquet__

    ---

    Connect to a single exchange, stream live order-book and trade data, and persist it to Parquet.

    [Open tutorial →](01-bybit-to-parquet.md)

-   __2 · Multi-exchange sync__

    ---

    Run synchronized collection across multiple exchanges on the same asset, aligned to a common grid.

    [Open tutorial →](02-multi-exchange-sync.md)

-   __3 · Hawkes on arrivals__

    ---

    Fit a Hawkes process to real orderbook arrivals via MLE and test it against a Poisson baseline.

    [Open tutorial →](03-hawkes-on-arrivals.md)

</div>

Want the methodology behind tutorial 3 — when self-excitation is real and when it is not? See
[When are crypto order arrivals self-exciting?](../research/posts/2026-06-16-self-exciting-arrivals.md)
in Research.

Have a workflow you'd like documented? Open an issue in
[`atelier-webdocs`](https://github.com/IteraLabs/atelier-webdocs/issues).
