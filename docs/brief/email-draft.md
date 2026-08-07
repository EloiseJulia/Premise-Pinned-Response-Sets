Subject: Pilot on premise-pinned response sets for LLM judges

Hi Professor Holstein,

I read *Validating LLM-as-a-Judge Systems under Rating Indeterminacy* and built
a small follow-up around its open construct-validity question: instead of asking
a judge to directly self-report every reasonable rating, I ask it to surface
unstated scoring premises and then rerun the rating under one counterfactually
pinned premise value at a time.

[Insert Figure 1.] In the frozen three-task/four-judge panel,
`beta_self` and `beta_pin` [insert result and interval].

[Insert one-sentence H2/H3 result.] The complete `pi`/`tau` surfaces, placebo,
prompt-leakage audit, and both SummEval polarity conventions are included in the
linked brief rather than selecting a favorable threshold.

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
