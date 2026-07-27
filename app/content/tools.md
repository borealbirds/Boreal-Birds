`BAMexploreR` is an R package for downloading and analyzing landbird density models produced by the Boreal Avian Modelling Centre (BAM). Additional options for model access are also listed below.

1. **[BAMexploreR](https://github.com/borealbirds/BAMexploreR)** - access the R package GitHub page.
2. **[BAMexploreR Shiny app](https://borealbirds.shinyapps.io/bam_landbird_viewer_dev95/)** - download and analyze rasters with a graphical user interface.
3. **[Google Earth Engine viewer](https://borealbirds-gee.projects.earthengine.app/view/landbirdmodels)** - view and explore the version 5 Canada-wide models and uncertainty over Google imagery.
4. **[BAM model website](https://borealbirds.github.io/)** - view predictions and metadata for the version 4 Canada-wide models.

The BAM landbird density models are species-specific predictions of the density of breeding male birds per hectare at a 1km resolution across Canada. They are produced with a generalized analytical approach to model landbird species density in relation to environmental predictors, using in-person or ARU point-count surveys and widely available spatial predictors.

We developed separate models for each geographic region (bird conservation regions) based on predictors such as tree species biomass (local and landscape scale), forest age, topography, land use, and climate. We used machine learning to allow for predictor interactions and non-linear responses while avoiding time-consuming species-by-species parameterization. We applied cross-validation to avoid overfitting and bootstrap resampling to estimate uncertainty associated with our density estimates.
