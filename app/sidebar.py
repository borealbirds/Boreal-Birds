from shiny import ui

def sidebar():

    return ui.sidebar(
        ui.input_select(
                "species",
                "Species",
                choices=[
                    "CAWA",
                    "CCSP"
                ],
            ),
        ui.input_select(
            "region",
            "Region",
            choices=[
                "Canada",
                "Alaska",
                "US (lower 48)"
            ],
        ),
        ui.input_slider(
            "year",
            "Year",
            min=1990,
            max=2020,
            value=2020,
            step=5,
        ),
    )