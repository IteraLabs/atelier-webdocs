---
source_example: atelier-quant/examples/eg_hawkes_ob_arrivals.rs
sdk_version: "0.0.10"
sdk_commit: "(record this before cutover)"
---

# Fit a Hawkes process to orderbook arrivals

The quant payoff. Take a Parquet file of trades or orderbook
snapshots collected by [Tutorial 1](01-bybit-to-parquet.md), extract
event timestamps, fit a univariate Hawkes process via maximum
likelihood, and compare it against a Poisson baseline.

The end-to-end pipeline:

1. Load Parquet → event timestamps.
2. Sort, deduplicate, validate monotonicity, detect gaps.
3. Train/test split (80/20).
4. Fit Hawkes (`μ`, `α`, `β`) and Poisson (`λ`) on the training set.
5. Goodness-of-fit via time-rescaling residuals.
6. Forecast next N arrivals from each model.
7. Compare with AIC/BIC + likelihood ratio test + forecast error.

The example exists because the Hawkes hypothesis — that orderbook
arrivals are *self-exciting* (one event raises the probability of
the next) — is a quantitatively testable claim. Fitting both models
and reading the AIC/BIC/LR diagnostics tells you whether your data
*actually* supports it for a given symbol and time window.

!!! note "Source"
    Code lifted from
    [`atelier-quant/examples/eg_hawkes_ob_arrivals.rs`](https://github.com/IteraLabs/atelier-sdk/tree/main/atelier-quant/examples/eg_hawkes_ob_arrivals.rs)
    in atelier-sdk. The example is ~650 lines; this tutorial walks
    through the key sections. Run the original verbatim with
    `cargo run -p atelier_quant --example eg_hawkes_ob_arrivals`.

## What you need

A Parquet file from Tutorial 1 (or any compatible source). The
example's `parquet_path` defaults to:

```
datasets/collected/bybit/btcusdt/trades_bybit_20260218_181131.060.parquet
```

Adjust to whatever you collected. The script auto-detects whether
the file is trades or orderbook from the filename prefix.

## 1. Project setup

```toml
[package]
name = "hawkes-on-arrivals"
version = "0.1.0"
edition = "2024"

[dependencies]
atelier-types = "0.0.10"
atelier-io    = { version = "0.0.10", features = ["parquet"] }
atelier-quant = "0.0.11"
```

`atelier-quant` is at its own version (see the
[`atelier-quant`](../sdk/quant/index.md) page for why).

## 2. Load Parquet → timestamps

```rust
use std::path::Path;
use atelier_io::orderbooks::ob_parquet::load_parquet_to_ob;
use atelier_io::trades::read_trades_parquet;
use atelier_types::temporal::{self, TimeResolution};
use atelier_quant::arrivals::{
    extract_orderbook_timestamps, extract_trade_timestamps,
    compute_interarrivals, descriptive_stats,
};

let parquet_path = Path::new(
    "datasets/collected/bybit/btcusdt/trades_bybit_20260218_181131.060.parquet",
);

// Detect file type from filename prefix.
let filename = parquet_path
    .file_name().and_then(|f| f.to_str()).unwrap_or("");
let is_trades = filename.starts_with("trades_");

let (timestamps_ns, n_loaded) = if is_trades {
    let trades = read_trades_parquet(parquet_path)?;
    println!("Loaded {} trades", trades.len());
    (extract_trade_timestamps(&trades), trades.len())
} else {
    let books = load_parquet_to_ob(parquet_path)?;
    println!("Loaded {} orderbook snapshots", books.len());
    (extract_orderbook_timestamps(&books), books.len())
};

if n_loaded < 12 {
    anyhow::bail!("need at least 12 events (10 test + 2 train)");
}
```

The `extract_*_timestamps` helpers return a `Vec<u64>` of
nanoseconds. They're in
[`atelier_quant::arrivals`](https://docs.rs/atelier-quant/0.0.11/atelier_quant/arrivals/).

## 3. Sort, dedupe, validate

```rust
let mut timestamps_ns = timestamps_ns;
timestamps_ns.sort_unstable();
let before = timestamps_ns.len();
timestamps_ns.dedup();
if before > timestamps_ns.len() {
    println!("Removed {} duplicate timestamps", before - timestamps_ns.len());
}

// MLE requires strictly increasing event times.
for i in 1..timestamps_ns.len() {
    if timestamps_ns[i] <= timestamps_ns[i - 1] {
        anyhow::bail!("monotonicity violated at index {}", i);
    }
}

// Detect gaps > 5 seconds — likely feed disconnects.
let gap_threshold_ns = 5_000_000_000_u64;
for i in 1..timestamps_ns.len() {
    let gap = timestamps_ns[i] - timestamps_ns[i - 1];
    if gap > gap_threshold_ns {
        eprintln!("warn: gap {:.3}s at index {}", gap as f64 / 1e9, i - 1);
    }
}
```

Real exchange feeds will produce duplicate timestamps (multiple
trades in the same millisecond). Dedupe before the MLE — keeping
duplicates breaks the strict-increase requirement and either
poisons the fit or makes it crash.

## 4. Train/test split, descriptive stats

```rust
let n_total = timestamps_ns.len();
let n_test  = (n_total as f64 / 5.0) as usize;  // 20%
let n_train = n_total - n_test;
let train_ts = &timestamps_ns[..n_train];
let test_ts  = &timestamps_ns[n_train..];

let ia = compute_interarrivals(train_ts, TimeResolution::Milliseconds)?;
let stats = descriptive_stats(&ia.deltas_f64).unwrap();

println!("Mean (ms):       {:.6}", stats.mean);
println!("Std dev (ms):    {:.6}", stats.std_dev);
println!("CV (σ/μ):        {:.4}", stats.cv);
```

The **CV** (coefficient of variation, σ/μ) is the key diagnostic:

- **CV > 1** indicates clustering (super-Poisson), consistent with
  Hawkes excitation. **Fit Hawkes.**
- **CV ≈ 1** suggests near-Poisson (memoryless) arrivals. The Hawkes
  parameters will collapse toward Poisson — fit anyway, then check
  the LR test.
- **CV < 1** indicates regularity (sub-Poisson). Less common for
  LOB data; investigate before fitting.

## 5. Hawkes MLE

```rust
use atelier_quant::hawkes::{
    HawkesProcess,
    estimation::{HawkesEstimationConfig, estimate_hawkes_mle, time_rescaling_residuals},
};

// Convert to milliseconds, relative to the first event, to keep
// the optimizer's numbers in a reasonable range.
let t0_ns = train_ts[0];
let train_events_ms: Vec<f64> = train_ts.iter()
    .map(|&t| temporal::from_nanos(t - t0_ns, TimeResolution::Milliseconds))
    .collect();

let config = HawkesEstimationConfig {
    max_iter: 50_000,
    tol: 1e3,
    learning_rate: 1e-2,
    initial_params: None,  // use the heuristic
};

let mle = estimate_hawkes_mle(&train_events_ms, &config)?;

println!("μ̂ (ev/ms)         {:.8}", mle.mu);
println!("α̂                 {:.8}", mle.alpha);
println!("β̂ (1/ms)          {:.8}", mle.beta);
println!("Branching α̂/β̂     {:.6}", mle.branching_ratio);
println!("Log-likelihood    {:.4}", mle.log_likelihood);
println!("AIC               {:.4}", mle.aic);
println!("BIC               {:.4}", mle.bic);
println!("Converged         {}",     mle.converged);
```

Three numbers to read:

- **μ̂** — the baseline arrival rate, in events per millisecond.
- **α̂** — the excitation jump per event.
- **β̂** — the decay rate; `1/β̂` is the time scale of the excitation.

The **branching ratio α̂/β̂** is the key one to watch. It must be
strictly less than 1 for the process to be stationary (which the
fitter guarantees). Values close to 1 indicate strong self-excitation
and a regime where small perturbations are amplified; values close
to 0 indicate the process is near-Poisson.

## 6. Goodness-of-fit (time rescaling)

```rust
let residuals = time_rescaling_residuals(
    mle.mu, mle.alpha, mle.beta, &train_events_ms,
);
let rs = descriptive_stats(&residuals).unwrap();

println!("Residuals mean    {:.6}  (target ≈ 1.0)", rs.mean);
println!("Residuals std dev {:.6}  (target ≈ 1.0)", rs.std_dev);
```

Under correct specification, time-rescaling residuals are ~Exp(1):
mean and std dev should both be near 1.0. A residual mean of 0.7
or 1.4 is a strong hint that the model is mis-specified for this
dataset (try a different kernel, or accept that Poisson is enough).

## 7. Poisson baseline + AIC/BIC comparison

```rust
use atelier_quant::poisson::{
    PoissonProcess,
    estimation::{PoissonEstimationConfig, estimate_poisson_mle},
};

let pp_mle = estimate_poisson_mle(&train_events_ms, &PoissonEstimationConfig)?;

println!("λ̂ (ev/ms)         {:.8}", pp_mle.lambda);
println!("Hawkes  AIC       {:.4}", mle.aic);
println!("Poisson AIC       {:.4}", pp_mle.aic);

if mle.aic < pp_mle.aic {
    println!("→ AIC favors Hawkes (lower by {:.2})", pp_mle.aic - mle.aic);
} else {
    println!("→ AIC favors Poisson (lower by {:.2})", mle.aic - pp_mle.aic);
    println!("  Hawkes excitation is not justified for this data.");
}
```

Lower AIC is better. The 2-parameter penalty (Hawkes has 3 params,
Poisson has 1, so Hawkes pays an AIC penalty of 2×2 = 4 for the
extra freedom) means Hawkes only wins if the log-likelihood
improvement exceeds 2 in absolute terms. BIC is stricter still
(penalty grows with sample size).

## 8. Likelihood ratio test

A formal hypothesis test:

```rust
// H0: Poisson (λ),  H1: Hawkes (μ, α, β)
// LR = 2(ℓ_H − ℓ_P) ~ χ²(2) under H0
let lr_stat = 2.0 * (mle.log_likelihood - pp_mle.log_likelihood);
let chi2_critical_05 = 5.991;  // χ²(2), α = 0.05

println!("LR statistic        {:.4}", lr_stat);
println!("χ²(2) critical 5%   {:.3}", chi2_critical_05);

if lr_stat > chi2_critical_05 {
    println!("→ Reject H₀ at 5%. Hawkes excitation is significant.");
} else {
    println!("→ Fail to reject. Poisson is sufficient.");
}
```

This is the canonical test. If you can't reject at 5%, the data
doesn't support the Hawkes hypothesis for that symbol and time
window — accept the simpler model.

## 9. Forecast comparison

```rust
let last_train_ms = *train_events_ms.last().unwrap();
let hp = HawkesProcess::new(mle.mu, mle.alpha, mle.beta)?;
let pp = PoissonProcess::new(pp_mle.lambda)?;

let h_forecast = hp.generate_values(last_train_ms, n_test);
let p_forecast = pp.generate_values(last_train_ms, n_test);

// Compute MAE / RMSE against actual test arrivals.
let actual_ms: Vec<f64> = test_ts.iter()
    .map(|&t| temporal::from_nanos(t - t0_ns, TimeResolution::Milliseconds))
    .collect();

let (h_mae, h_rmse) = errors(&actual_ms, &h_forecast, last_train_ms);
let (p_mae, p_rmse) = errors(&actual_ms, &p_forecast, last_train_ms);

println!("           Hawkes        Poisson");
println!("MAE        {:>10.4}   {:>10.4}", h_mae, p_mae);
println!("RMSE       {:>10.4}   {:>10.4}", h_rmse, p_rmse);

fn errors(actual: &[f64], forecast: &[f64], t0: f64) -> (f64, f64) {
    let n = actual.len().min(forecast.len());
    let mut s_abs = 0.0; let mut s_sq = 0.0;
    for i in 0..n {
        let err = (actual[i] - t0) - (forecast[i] - t0);
        s_abs += err.abs(); s_sq += err * err;
    }
    (s_abs / n as f64, (s_sq / n as f64).sqrt())
}
```

Forecasting is harder than fitting. A model can have lower in-sample
AIC and still produce worse forecasts — that's overfitting, and
it's worth seeing.

## What success looks like

You're looking for *consistency*: AIC/BIC favor Hawkes, the LR test
rejects the Poisson null, the time-rescaling residuals look ~Exp(1),
**and** Hawkes beats Poisson on out-of-sample MAE. When all four
agree, the self-excitation hypothesis has real support for this
data.

If they disagree — say AIC favors Hawkes but the residuals look
non-Exp(1) — your model is fitting the data without truly
explaining it. That's the signal to try a different kernel or look
for regime changes within the window.

## Where to go next

- [`atelier-quant`](../sdk/quant/index.md) — full conceptual reference.
- The example's full source has additional sections (compensator
  diagnostics, formatted comparison tables, structured output) that
  this tutorial elides for length. Run the original directly:

  ```bash
  cargo run -p atelier_quant --example eg_hawkes_ob_arrivals
  ```

- [Tutorial 1: Bybit → Parquet](01-bybit-to-parquet.md) — collect
  fresh data to fit on.
- [Tutorial 2: multi-exchange sync](02-multi-exchange-sync.md) —
  natural follow-up: fit per-exchange Hawkes models on the same
  underlying asset and compare excitation parameters.
