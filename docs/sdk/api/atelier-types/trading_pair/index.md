# `atelier_types::trading_pair`

Canonical trading pair representation
Canonical trading pair representation.

`TradingPair` decomposes a trading pair into its base and quote
assets, providing format conversions for every exchange and a
canonical `"BASE/QUOTE"` form that serves as the universal join key
across the atelier ecosystem.

# Exchange formats

| Exchange  | Wire format      | Example       |
|-----------|------------------|---------------|
| Bybit     | `BASEQUOTE`      | `SOLUSDT`     |
| Binance   | `basequote`      | `solusdt`     |
| Coinbase  | `BASE-QUOTE`     | `SOL-USD`     |
| Kraken    | `BASE/QUOTE`     | `SOL/USDT`    |

The canonical form matches the backend DB `pair` column convention
(`SOL/USDT`, slash-separated, uppercase).

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_types::trading_pair`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-types/latest/atelier_types/trading_pair/).

## Structs

| Item | Summary |
| --- | --- |
| [`TradingPair`](https://docs.rs/atelier-types/latest/atelier_types/trading_pair/struct.TradingPair.html) | Canonical trading pair — base and quote stored separately, uppercase. |
