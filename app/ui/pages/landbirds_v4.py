"""
External navigation for the archived Landbird Density & Habitat product (v4).

Links users to the archived model website in a new browser tab.
"""

from shiny import ui


def landbirds_v4_tab():
    """
    Generate a navigation item linking to the archived v4 model results.

    Returns
    -------
    shiny.ui.nav_control
        A navigation controller containing an external anchor element configuration.
    """
    return ui.nav_control(
            ui.a(
                "Landbird Density & Habitat (v4 archive)",
                href="https://borealbirds.github.io/",
                target="_blank",
            ),
        )
