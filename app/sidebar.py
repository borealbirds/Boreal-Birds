from shiny import ui
from shared import available_species


def sidebar():
    species_choices = available_species()

    initial_species = species_choices[0] if species_choices else None

    return ui.sidebar(
        ui.input_select(
            "species",
            "Species",
            choices=species_choices,
            selected=initial_species,
        ),
        ui.input_select(
            "region",
            "Region",
            choices=[],
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
