All released 2020 prediction surfaces received four post-processing treatments:

1. **Extreme-density truncation.** Predictions were first limited using a species-specific upper density derived from observed counts and their detectability corrections. A second cap was applied at the 99.9th percentile of the species' mean predicted density surface.
2. **Species-range limitation.** Training detections were supplemented with qualifying eBird detections, spatially thinned, and used to estimate a smoothed probable maximum range. Predictions were limited to this supported range.
3. **Data-extent limitation.** Predictions were retained in areas with at least 450 surveys within 250 km. The resulting boundary was smoothed before being applied.
4. **Water masking.** Inland water was removed because the products model landbird density in terrestrial habitats.

These steps reduce extreme or unsupported predictions, but they do not eliminate all uncertainty near range boundaries or in sparsely sampled environments.
