"""
Sidebar navigation controls and reactive inputs for model tabs.

Dynamically extracts validated species catalog definitions to construct 
consistent dashboard filtering sidebars across distinct framework versions.
"""

import polars as pl
from shiny import ui
from shared.data_loading import load_cog_species, load_importance_data, load_species_metadata
from shared.paths import PREDICTION_YEAR

#def sidebar(model_version: str, year_slider: bool = True) -> ui.sidebar:
def sidebar(model_version: str) -> ui.sidebar:
    """
    Initialize the standardized filtering sidebar layout for bird model views.

    Populates a core dropdown selection input using verified English common names 
    sourced directly from active species metadata collections.

    Parameters
    ----------
    model_version : str
        The version string identifier ('v4' or 'v5') used to namespace 
        the reactive interface components.
    year_slider : bool, default True
        If True, includes a slider input for years between 1990 and 2020.
        If False, disables the slider from sidebar in favour of a dropdown
        menu that can be used to limit options to select years.
    Returns
    -------
    shiny.ui.sidebar
        The configured layout panel object containing the filter controls.
    """
        

    # only species with at least one density raster in the cloud cog_species folder
    species_choices = sorted(load_cog_species().get_column("english").to_list())

    # Predictors tab: species with importance results; id converted to common name from the species sheet
    predictor_species_choices = sorted(
        load_importance_data().select("id", "english")
        .unique()
        .join(
            load_species_metadata().select("id", pl.col("english").alias("common")),
            on="id",
            how="left",
        )
        .select(pl.coalesce(["common", "english"]))
        .to_series()
        .to_list()
    )

    # the Predictors tab shows its own species list; all other tabs show species and region
    predictors_tab = "input.view_toggle === 'map' && input.results_tabs === 'Predictors'"

    sidebar_elements = [
        ui.panel_conditional(
            predictors_tab,
            ui.output_ui("sidebar_bird_image_predictors"),
            ui.input_select(
                "predictor_species",
                "Species",
                choices=predictor_species_choices,
                size=4
            ),
        ),
        ui.panel_conditional(
            f"!({predictors_tab})",
            ui.output_ui(f"sidebar_bird_image_{model_version}"),
            ui.input_select(
                f"species_{model_version}",
                "Species",
                choices=species_choices,
                size=4
            ),
            ui.input_select(
                f"region_{model_version}",
                "Region",
                choices=["Canada", "Alaska", "Lower48"],
            ),
        ),
    #]
    #
    # include year slider if year_slider = True
    #if year_slider:
    #    sidebar_elements.append(
    #        ui.input_slider(
    #            f"year_{model_version}",
    #            "Year",
    #            min=1990,
    #            max=2020,
    #            value=2020,
    #            step=5,
    #            ticks=True,
    #            sep=''
    #        )
    #    )
    #else:
    #    sidebar_elements.append(
    #        ui.input_select(
    #            f"year_{model_version}",
    #            "Year",
    #            choices=["2020"],
    #            selected=["2020"]
    #        )
    #    )

        ui.p(
            f"Predictions represent {PREDICTION_YEAR} conditions. "
            "Predictions for 1990–2015 are available upon request.",
            class_="text-muted small",
        ),
    ]

    return ui.sidebar(*sidebar_elements, width=375, open="open")
