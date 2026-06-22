"""
Sidebar navigation controls and reactive inputs for model tabs.

Dynamically extracts validated species catalog definitions to construct 
consistent dashboard filtering sidebars across distinct framework versions.
"""

from shiny import ui
from shared.data_loading import load_species_metadata


def sidebar(model_version: str, year_slider: bool = True) -> ui.sidebar:
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
        If False, disable the slider from sidebar

    Returns
    -------
    shiny.ui.sidebar
        The configured layout panel object containing the filter controls.
    """
    species_choices = sorted(load_species_metadata().get_column("english").to_list())

    sidebar_elements = [
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
    ]

    # include year slider if year_slider = True
    if year_slider:
        sidebar_elements.append(
            ui.input_slider(
                f"year_{model_version}",
                "Year",
                min=1990,
                max=2020,
                value=2020,
                step=5,
                ticks=True,
                sep=''
            )
        )

    return ui.sidebar(*sidebar_elements, width=375)