---
date: 2026-06-16
slug: self-exciting-arrivals
authors:
  - iteralabs
categories:
  - Microstructure
  - Methodology
description: >
  A Hawkes process claims order arrivals are self-exciting. Here is the discipline we use
  to test that claim — and the cases where the honest answer is "Poisson is enough."
---

# When are crypto order arrivals self-exciting?

A Hawkes process makes a sharp, falsifiable claim about market data: that one event raises
the probability of the next. It is a seductive model — order flow *looks* clustered, and a
self-exciting process reproduces that clustering almost by construction. Which is exactly why
fitting one and declaring victory proves nothing. This note is about the discipline that
separates a real finding from a plausible-looking fit.

<!-- more -->

## The claim, stated precisely

A univariate Hawkes process has a conditional intensity

```
λ(t) = μ + Σ_{tᵢ < t} α·e^(−β(t − tᵢ))
```

— a baseline rate **μ**, bumped by **α** at every past event, decaying at rate **β**. Set
α = 0 and it collapses to a homogeneous Poisson process with rate μ. So "arrivals are
self-exciting" is precisely the statement **α > 0, and significantly so**. The Poisson
process is the null hypothesis sitting inside the Hawkes model as a boundary case, which is
what makes the comparison clean.

The quantity that matters most is the **branching ratio α/β** — the expected number of
events directly triggered by a single event. It must be strictly below 1 for the process to
be stationary; values near 1 describe a market where small perturbations are amplified, and
values near 0 describe one that is effectively memoryless.

## The wrong way to answer it

Fit a Hawkes process, observe α̂ > 0, ship the conclusion. This fails for two reasons. First,
MLE will almost always return α̂ > 0 on real data — noise alone produces apparent excitation.
Second, in-sample fit quality says nothing about whether the extra parameters *earn their
keep* or whether the model will generalise. A model can fit beautifully in-sample and
forecast worse than the one-parameter Poisson it replaced. That is not a corner case; it is
the default failure mode of flexible models.

## The method: four diagnostics that must agree

The Atelier approach is to make the self-excitation claim survive **four independent checks**,
each of which can kill it. We only report self-excitation when all four point the same way.

| # | Diagnostic | "Supports Hawkes" looks like |
|---|------------|------------------------------|
| 1 | **Coefficient of variation** (σ/μ of interarrivals) | CV > 1 — super-Poisson clustering, a *precondition* not a proof |
| 2 | **Model selection** (AIC / BIC) | Hawkes AIC below Poisson AIC by more than the parameter penalty |
| 3 | **Likelihood-ratio test** | LR = 2(ℓ_H − ℓ_P) exceeds χ²(2) critical value (5.991 at 5%) |
| 4 | **Goodness-of-fit** (time-rescaling residuals) | Residuals ~ Exp(1): mean and std dev both ≈ 1.0 |

And then a fifth, out-of-sample, as the tie-breaker that in-sample statistics cannot fake:

| # | Diagnostic | "Supports Hawkes" looks like |
|---|------------|------------------------------|
| 5 | **Forecast error** (MAE / RMSE on held-out arrivals) | Hawkes beats Poisson on data it was not fit to |

### 1 — Pre-screen with the coefficient of variation

Before fitting anything, compute the CV of the interarrival times. A Poisson process has
CV = 1 by construction. **CV > 1 indicates clustering** consistent with excitation; **CV ≈ 1**
means the Hawkes parameters will collapse toward Poisson anyway; **CV < 1** indicates
regularity and is a reason to stop and investigate before fitting. The CV is cheap and it
tells you whether the rest of the pipeline is even worth running.

```rust
let ia = compute_interarrivals(train_ts, TimeResolution::Milliseconds)?;
let stats = descriptive_stats(&ia.deltas_f64).unwrap();
println!("CV (σ/μ): {:.4}", stats.cv);   // > 1 ⇒ proceed
```

### 2 & 3 — Make the extra parameters earn their keep

Fit both models by maximum likelihood on the **training split**, then compare. AIC and BIC
penalise the Hawkes model for its two extra parameters: Hawkes only wins if its
log-likelihood improvement clears the penalty (BIC's penalty grows with sample size, so it is
the stricter referee). The likelihood-ratio test formalises this: under the Poisson null,
2(ℓ_H − ℓ_P) is χ²-distributed with 2 degrees of freedom, so an LR statistic above **5.991**
rejects Poisson at the 5% level.

```rust
let lr_stat = 2.0 * (mle.log_likelihood - pp_mle.log_likelihood);
if lr_stat > 5.991 {
    println!("Reject Poisson at 5% — excitation is significant.");
}
```

If you cannot reject the null, you are done: the data does not support the Hawkes hypothesis
for that symbol and window, and the simpler model is the correct one to report.

### 4 — Check that the model actually explains the data

Passing model selection means Hawkes fits *better* — not that it fits *well*. The
**time-rescaling theorem** gives the test: under a correctly specified point process, the
rescaled interarrival times are i.i.d. Exp(1). Compute the residuals and check that their
mean and standard deviation are both near 1.0. A residual mean of 0.7 or 1.4 is a model that
is fitting the data without explaining it — usually a sign the exponential kernel is wrong
for this regime, or that there is a structural break inside the window.

### 5 — The out-of-sample tie-breaker

Finally, forecast the held-out test arrivals from each fitted model and compare MAE / RMSE.
This is the check that in-sample statistics cannot game. A Hawkes model with lower AIC that
nonetheless forecasts *worse* than Poisson is overfit, and seeing that happen is worth more
than any single in-sample number.

## When the diagnostics disagree

The interesting cases are the disagreements, because they are diagnostic in themselves:

- **AIC favours Hawkes, residuals are not Exp(1).** The model is over-parameterised for the
  data — it is absorbing structure it cannot reproduce. Try a different kernel, or look for a
  regime change splitting the window.
- **LR rejects Poisson, out-of-sample MAE is worse.** Classic overfit. The in-sample
  excitation is real but not stable enough to forecast — report it as fragile, not as signal.
- **CV > 1 but Hawkes loses on AIC.** The clustering is there but an exponential-kernel
  Hawkes is the wrong shape for it. The clustering may be exogenous (news, liquidations)
  rather than endogenous self-excitation.

The point of demanding agreement across five checks is not statistical theatre. It is that
each check fails in a *different* way, so consensus among them is hard to fake — the same
adversarial-verification discipline we apply everywhere else on the platform.

## Reproduce it

Everything above runs end-to-end against a Parquet file of real arrivals. Collect data with
[Tutorial 1](../../guides/01-bybit-to-parquet.md), then:

```bash
cargo run -p atelier_quant --example eg_hawkes_ob_arrivals
```

The full walk-through — including the gap detection and monotonicity validation that real
exchange feeds make necessary — is in [Fit a Hawkes process to orderbook
arrivals](../../guides/03-hawkes-on-arrivals.md). The modelling machinery lives in
[`atelier-quant`](../../sdk/quant/index.md): Ogata-thinning simulation, the `Kernel` trait,
MLE with Armijo line search, and the AIC/BIC and goodness-of-fit diagnostics used here.

!!! quote "Cite this note"
    ```bibtex
    @misc{iteralabs2026selfexciting,
      title  = {When are crypto order arrivals self-exciting?},
      author = {IteraLabs Research},
      year   = {2026},
      note   = {Atelier SDK research notes},
      url    = {https://www.iteralabs.xyz/atelier/docs/research/self-exciting-arrivals/}
    }
    ```

---

*Drawn from `atelier-quant` v0.0.11 (`examples/eg_hawkes_ob_arrivals.rs`) in
[`atelier-sdk`](https://github.com/IteraLabs/atelier-sdk).*
