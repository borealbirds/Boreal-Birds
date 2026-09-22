The distributed prediction rasters contain mean predicted density in male birds per hectare and the standard deviation across 32 bootstrap predictions. Standard deviation is provided as a single uncertainty band to limit file size. It describes variation among bootstrap predictions but does not represent every source of ecological, observation, or model uncertainty.

Population and regional density summaries are calculated directly from the 32 bootstrap estimates. They report the median and the 5th and 95th percentiles of the bootstrap distribution.

Each bootstrap model was evaluated using observations not selected for that bootstrap's training sample. Observations that occurred only in a region's 100-km buffer were excluded from region-level validation. Reported metrics include:

- **Area under the receiver operating characteristic curve (AUC):** discrimination between detections and non-detections
- **Poisson deviance-based pseudo-R²:** improvement in fit relative to the offset-only model
- **Overall concordance correlation coefficient (OCCC):** agreement among completed bootstrap predictions, including precision and accuracy components
