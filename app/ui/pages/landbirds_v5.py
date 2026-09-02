"""
Layout for the current Landbird Density & Habitat product (v5).

Assembles the primary model dashboard tab utilizing a conditional view toggle 
to alternate between geospatial model output mappings and qualitative species briefs.
"""

from shiny import ui
from shinywidgets import output_widget

from assets.icons import question_circle_fill
from ui.layout.sidebar import sidebar


def landbirds_v5_tab() -> ui.nav_panel:
    """
    This function constructs a navigation panel containing a bird information 
    header and a multi-tabbed card interface. The card interface allows users 
    to toggle between a spatial map with band selection, land cover analytics, 
    and population size estimates.

    Landbird Density & Habitat tab — compact bird header with MAP/INFO toggle.
    MAP view: interactive map, land cover, population, density, download.
    INFO view: species info, photo gallery, sounds.

    Returns
    -------
    shiny.ui.nav_panel
        The operational grid environment mapping layout rows and view toggles.
    """
    return ui.nav_panel(
        "Landbird Density & Habitat",
        ui.layout_sidebar(
            sidebar("v5"),

            # ── Compact bird header + MAP/INFO toggle ──────────────────
                ui.layout_columns(
                    ui.output_ui("selected_bird"),
                    ui.div(
                        ui.input_radio_buttons(
                            "view_toggle",
                            None,
                            choices={
                                "map": "Map", 
                                "info": "Info"
                            },
                            selected="map",
                            inline=True,
                        ),
                        class_="toggle-wrapper",
                    ),
                    col_widths=(9, 3),
                    max_height="80px",
                    class_="bird-header-row",
                ),

            # ── MAP view ───────────────────────────────────────────────
            ui.panel_conditional(
                "input.view_toggle === 'map'",
                ui.navset_card_underline(
                    ui.nav_spacer(),
                    ui.nav_panel(
                        "Map",
                        output_widget("map_widget"),
                    ),
                    ui.nav_panel(
                        "Population",
                        ui.card(output_widget("population_chart"), full_screen=True),
                    ),
                    ui.nav_panel(
                        "Density",
                        ui.card(output_widget("density_chart"), full_screen=True),
                    ),
                    ui.nav_panel(
                        "Covariates",
                        ui.layout_columns(
                            ui.markdown("""
                            **Explore how each environmental predictor is associated with predicted density of male birds per hectare.**
                            'Species' filter applies.
                            """),
                            ui.layout_columns(
                                ui.card(output_widget("marginal_fx_chart"), full_screen=True),
                                ui.card(ui.output_ui("marginal_fx_filter")),
                                col_widths=(8, 4)
                            ),
                            col_widths=(12, 12),
                            row_heights=["auto", "1fr"],
                        ),
                    ),
                    ui.nav_panel(
                        "Download",
                        ui.layout_columns(
                            ui.markdown("""
                            **Landbird Density & Habitat downloads** include population and density estimates,
                            as well as model metadata, species taxonomy, regions, variables, importance, and validation.

                            For additional ways to access and use these models, please see the **Use Models** menu.
                            """),
                            ui.card(
                                ui.download_button("downloadAll", "Download All Results"),
                                ui.output_ui("download_filtered_btn"),
                                fill=False,
                            ),
                            ui.card(ui.output_data_frame("population_size"), full_screen=True),
                            col_widths=(7, 5, 12),
                        ),
                    ),
                    title=ui.tooltip(
                        ui.span("Landbird Density & Habitat Results ", question_circle_fill),
                        "Population size is estimated by summing predicted male density across each region and is reported in millions of male birds.",
                        placement="right",
                        id="results_tooltip",
                        class_="results_tooltip",
                    ),
                ),
                class_="fill-remaining-space",
            ),

            # ── INFO view ──────────────────────────────────────────────
            ui.panel_conditional(
                "input.view_toggle === 'info'",
                ui.navset_card_underline(
                    ui.nav_spacer(),
                    ui.nav_panel("Info",   ui.output_ui("species_info")),
                    ui.nav_panel("Images", ui.output_ui("species_images")),
                    ui.nav_panel("Sounds",  ui.output_ui("species_songs")),
                    title="Species Info",
                ),
            ),
        )
    )
