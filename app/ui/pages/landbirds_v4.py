"""
Landbirds Version 4 historical model placeholder view template.

Acts as a structural interface mirror for legacy metrics, providing the 
front-end layout panels for future backend server wiring sprints.

Currently linking back to old website.
"""

from shiny import ui


def landbirds_v4_tab():
    """
    Generate a dynamic navigation item linking to the landbird v4 model results.

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
