"""
Welcome tab layout and announcement sub-components for the dashboard.

Constructs the landing interface view, pulling text content and dynamic 
updates out of localized markdown utility assets.
"""
from pathlib import Path

from shiny import ui

from shared.data_loading import read_md
from ui.components.announcements import announcements_card


def welcome_tab() -> ui.nav_panel:
    """
    Build the primary interface landing tab panel layout view.

    Returns
    -------
    NavPanel
        The completed layout container housing cards and project briefs.
    """
    return ui.nav_panel(
        "Home",
        ui.div(
            {"id": "welcome-panel"},
            ui.layout_columns(
                announcements_card(display=True),
                ui.card(
                    ui.card_header("A Boreal Avian Modelling Project"),
                    ui.markdown(read_md("welcome.md")),
                    class_="welcome-card"
                ),
                col_widths=(
                    -1, 10, -1, # announcement card
                    -1, 10, -1, # welcome card
                ),
                row_heights=["auto", 1]
            ),
        ),
    )
