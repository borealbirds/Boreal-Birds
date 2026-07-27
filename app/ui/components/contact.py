"""
UI contact components for the BAM dashboard.

Provides reusable contact components including website, email, and issues.
"""

from shiny import ui


def website() -> ui.nav_control:
    """
    Generate a dynamic navigation item linking to the core BAM project web portal.

    Returns
    -------
    shiny.ui.nav_control
        A navigation controller containing an external anchor element configuration.
    """
    return ui.nav_control(
            ui.a(
                "Our Website",
                href="https://borealbirds.ca/",
                target="_blank",
            ),
        )


def website_contact() -> ui.nav_control:
    """
    Generate a navigation layout button mapping to the official team directory page.

    Returns
    -------
    shiny.ui.nav_control
        A web component mapping directly to external communication infrastructure.
    """
    return ui.nav_control(
        ui.a(
            "Contact Us",
            href="https://borealbirds.ca/contact/",
            target="_blank",
            ),
        )


def email() -> ui.nav_control:
    """
    Generate an interface interaction gateway linking to default mail applications.

    Returns
    -------
    shiny.ui.nav_control
        An operational interface anchor using mailto address routing actions.
    """
    return ui.nav_control(
        ui.a(
            "Email Us",
            href="mailto:bamp@ualberta.ca",
            target="_blank",
            ),
        )


def report_issue() -> ui.nav_control:
    """
    Generate an issue-tracking shortcut pointing to repository management layers.

    Returns
    -------
    shiny.ui.nav_control
        A link asset to log defects, structural feature requests, or application bugs.
    """
    return ui.nav_control(
            ui.a(
                "Report an Issue",
                href="https://github.com/borealbirds/Boreal-Birds/issues",
                target="_blank",
            ),
        )
