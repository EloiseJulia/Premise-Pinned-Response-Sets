Subject: Pilot on premise-pinned response sets for LLM judges

Hi Professor Holstein,

I read *Validating LLM-as-a-Judge Systems under Rating Indeterminacy* and built
a small follow-up around its open construct-validity question: instead of asking
a judge to directly self-report every reasonable rating, I ask it to surface
unstated scoring premises and then rerun the rating under one counterfactually
pinned premise value at a time.

[Insert Figure 1.] In the frozen three-task/four-judge panel,
`beta_self` and `beta_pin` correlated at `r=0.439` (95% bootstrap CI
`[0.306, 0.871]`), so my preregistered weak-correlation prediction was not
supported.

The premise intervention nevertheless exposed a large stable-sampling blind
spot: 80.69% of valid item-judge cells had `H_seed <= 0.5` but `H_ctx > 0`
(95% CI `[78.72%, 82.63%]`), with real-pin entropy 0.922 bits versus 0.190 for
matched placebo. Distribution matching was mixed: PPRS improved MNLI and
SummEval but worsened SNLI, so H3 failed overall. The complete `pi`/`tau`
surfaces and both SummEval polarity conventions are included rather than
selecting a favorable specification.

The boundaries are important: the task panel is small; SummEval has only eight
human ratings per item versus one hundred for ChaosNLI; model-disclosed premises
have not been validated as the same construct as human reasoning; and the
commercial service IDs limit exact numeric reproducibility. I therefore view
this as evidence that the failure mode [exists/was not detected] in this frozen
panel, not an estimate of deployment prevalence.

Repository: [link]  
Four-page technical brief: [link]

Best,
Eloise Julia
