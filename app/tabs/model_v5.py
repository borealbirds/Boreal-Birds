from shiny import ui
from shinywidgets import output_widget

def model_v5_tab():

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