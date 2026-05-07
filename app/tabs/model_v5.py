from shiny import ui
from shinywidgets import output_widget

def model_v5_tab():
    """
    Generate the UI layout for the Model V5 results tab.

    This function constructs a navigation panel containing a bird information 
    header and a multi-tabbed card interface. The card interface allows users 
    to toggle between a spatial map with band selection, land cover analytics, 
    and population size estimates.

    Returns
    -------
    shiny.ui
    """
    return ui.nav_panel(
        "Model V5",
        
        ui.output_ui("bird_info"),

        ui.navset_card_underline(
            ui.nav_panel(
                "Map",
                ui.input_radio_buttons(
                    "raster_band",
                    None,
                    choices={
                        1: "Mean Density (Male birds/hectare)",
                        2: "Standard Deviation",
                        3: "Mean Distance",
                    },
                    selected=1,
                    inline=True
                ),
                output_widget("map_widget"),
            ),
            ui.nav_panel(
                "Land Cover",
                ui.p("land_cover_placeholder"),
            ),
            ui.nav_panel(
                "Population Size",
                ui.p("population_size_placeholder"),
            ),
            title="Model Results",
        ),
    )