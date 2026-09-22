"""
Methods and modeling methodologies layout views.

Loads statistical methodology disclosures from an external YAML manifest to 
dynamically assemble an interactive user interface layout panel.
"""

from shiny import ui

from shared.data_loading import read_md, read_yaml

methods_sections = read_yaml("methods/methods-sections.yaml")

methods_accordion = ui.accordion(
    *[
        ui.accordion_panel(
            section["section"],
            ui.markdown(read_md(section["file"])),
        )
        for section in methods_sections
    ],
    open=None # opens the first section by default
)


def methods_tab() -> ui.nav_panel:
    """
    Build the methods interface container layout.

    Arranges introductory markdown sheets alongside an interactive accordion grid
    with responsive grid-column widths optimized for varying viewport break-points.

    Returns
    -------
    shiny.ui.nav_panel
        The completed user interface tab panel holding methodology records.
    """
    return ui.nav_panel(
        "Methods",
        ui.layout_columns(
            ui.card(
                ui.card_header("Landbird Density & Habitat Models — Version 5.0"),
                ui.markdown(read_md("methods/methods-intro.md")),
                class_="methods-info"
            ),
            ui.card(
                methods_accordion,
                class_="methods-accordion",
            ),
            col_widths={
                "xs": (12, 12),
                "sm": (12, 12),
                "md": (12, 12),
                "lg": (12, 12),
                "xl": (5, 7),
                "xxl": (5, 7),
            }
        ),
    )
