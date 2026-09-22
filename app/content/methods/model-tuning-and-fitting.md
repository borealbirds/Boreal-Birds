Separate Poisson boosted regression tree models were fitted for each eligible species and modelling region. Unusually large observed counts were capped at the species-specific 99.9th percentile before fitting to improve model convergence.

Predictors were screened in two stages:

1. Initial collinearity screening used a variance inflation factor threshold of 10.
2. Predictors contributing less than 0.1% relative influence in the tuned model were removed. Survey year and survey method were retained regardless of relative influence.

Models used an interaction depth of 3. Learning rates were adjusted between **0.00001 and 0.01** to target 1,000–10,000 trees. Tuning was conducted using the first bootstrap sample for each species–region combination, and the selected settings were then applied across all 32 bootstrap samples.
