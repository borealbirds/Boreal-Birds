Version 5.0 provides several spatial diagnostics to help users evaluate model support. These diagnostics describe different aspects of support and should not be interpreted as statistical uncertainty.

**Species detection distance.** Each species prediction raster includes the mean distance to the nearest held-out detection of that species across the 32 bootstrap samples. Larger values indicate that a prediction is farther from observations confirming the species' presence.

**Sampling-folder rasters.** Separate region-and-year rasters contain three bands:

1. **Environmental extrapolation:** the proportion of bootstrap samples for which the environmental conditions at a pixel were outside those represented in the training data.
2. **Training sampling density:** the mean number of training observations within 20 km of each pixel.
3. **Testing sampling density:** the mean number of held-out testing observations within 20 km of each pixel.

For the sampling-density layers, observation years were assigned to the nearest five-year interval and results were averaged across the 32 bootstrap samples. These layers are available for individual modelling regions and the broad-scale mosaics.

The extrapolation layer is an interpretive diagnostic only. It was not used to select, remove, or weight regional predictions in the final workflow.
