"""
Main entry point and UI layout for the BAM Shiny Dashboard.

This script assembles the global navbar layout, links static web assets, 
and coordinates the reactive server orchestration loops.

Attributes
----------
www_dir : Path
    Path to static frontend assets (CSS, images, favicons).
app_ui : page_navbar
    The main user interface navigation and layout structure.
app : App
    The instantiated Shiny application runtime object.
"""

from shiny import App, Inputs, Outputs, Session, ui

from assets.sounds import audio
from server.landbird_v5_server import landbird_v5_server
from shared.paths import WWW_DIR

from ui.components.contact import website, website_contact
from ui.components.layout import footer

from ui.pages.methods import methods_tab
from ui.pages.landbirds_v4 import landbirds_v4_tab
from ui.pages.landbirds_v5 import landbirds_v5_tab
from ui.pages.model_access import citing_tab, tools_tab
from ui.pages.welcome import welcome_tab


app_ui = ui.page_navbar(
    ui.head_content(
        ui.include_css(str(WWW_DIR / "styles.css")),
        ui.tags.link(rel="icon", href="img/favicon.png", type="image/x-icon"),
        audio(),
    ),
    ui.nav_spacer(),
    welcome_tab(),
    ui.nav_menu(
        "Models",
        landbirds_v5_tab(),
        landbirds_v4_tab(),
    ),
    ui.nav_menu(
        "Model Access",
        tools_tab(),
        citing_tab(),
    ),
    methods_tab(),
    ui.nav_menu(
        "Contact Us",
        website(),
        website_contact(),
    ),
    selected="Welcome",
    id="tabs",
    title=ui.tags.a(
        ui.tags.img(
            src="img/BAM-Logo-WhiteText.svg",
            alt="Boreal Avian Modelling Centre Dashboard",
            height="48"
        ),
        href="https://borealbirds.ca/",
        target="_blank",
    ),
    fillable=True,
    footer=footer()
)


def server(input: Inputs, output: Outputs, session: Session) -> None:
    """
    Root server coordinator for the Shiny application.

    Delegates the reactive session execution loop downstream to the 
    Version 5 analytical backend engine.

    Parameters
    ----------
    input : Inputs
        Reactive container for user interface input nodes.
    output : Outputs
        Reactive registry handling user interface output components.
    session : Session
        The active client connection and runtime execution session.

    Returns
    -------
    None
    """
    landbird_v5_server(input, output, session)


app = App(app_ui, server, static_assets=WWW_DIR)
