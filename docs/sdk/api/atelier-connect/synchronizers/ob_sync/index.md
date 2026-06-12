# `atelier_connect::synchronizers::ob_sync`

src/syncrhonizers/ob_sync.rs

Time-synchronized orderbook snapshot sampling.

Produces uniformly-spaced `Orderbook` snapshots from an irregular stream
of full-book updates by selecting the most recent snapshot at each discrete
grid point.

# Model

```text
  stream:  S₁  S₂     S₃  S₄  S₅        S₆   S₇
  time: ───┼───┼───────┼───┼───┼──────────┼────┼──→
  grid: ───────|───────────|───────────|───────────|
           t₀         t₁         t₂         t₃

  output:       S₂          S₅          S₇
               (@ t₁)      (@ t₂)      (@ t₃ via finalize)
```

At each grid boundary, the **last snapshot received before the crossing**
is emitted with its `orderbook_ts` reassigned to the grid-aligned
nanosecond timestamp. Gaps (periods with no updates) are forward-filled
from the previous snapshot.

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_connect::synchronizers::ob_sync`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-connect/latest/atelier_connect/synchronizers/ob_sync/).

## Structs

| Item | Summary |
| --- | --- |
| [`ObSynchronizer`](https://docs.rs/atelier-connect/latest/atelier_connect/synchronizers/ob_sync/struct.ObSynchronizer.html) | Produces uniformly-spaced `Orderbook` snapshots from an irregular update stream. |

## Functions

| Item | Summary |
| --- | --- |
| [`capture_levels`](https://docs.rs/atelier-connect/latest/atelier_connect/synchronizers/ob_sync/fn.capture_levels.html) | Extract the current book state from an `OrderbookDelta` as `Vec<Level>` pairs. |
