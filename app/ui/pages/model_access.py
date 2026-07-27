"""
Model access layout views, R package vignettes, and citation components.

Constructs dedicated panels for documentation workflows, embedding localized 
vignette HTML files via iframe modules and parsing reference citations.
"""

from shiny import ui

from shared.data_loading import read_md


def _vignette_panel(title: str, src: str) -> ui.nav_panel:
    """
    Create a navigation panel with an embedded iframe for a vignette.

    Parameters
    ----------
    title: str
        Title of the vignette navigation panel.
    src: str
        Relative file path or external web address pointing to the HTML document.

    Returns
    -------
    shiny.ui.nav_panel
        A Shiny UI component containing a navigation panel with an embedded iframe of the vignette.
    """
    return ui.nav_panel(
        title,
        ui.tags.iframe(
            src=src,
            style="""
                width: 100%;
                height: 60vh;
                border: none;
                display: block;
            """
        ),
    )


def vignettes_tab() -> ui.nav_panel:
    """
    Build the standalone tab panel housing the complete package vignette collection.

    Returns
    -------
    shiny.ui.nav_panel
        The completed user interface view wrapping structured package documentation.
    """
    return ui.nav_panel(
        "Vignettes",
        ui.layout_columns(
            ui.navset_card_underline(
                ui.nav_spacer(),
                _vignette_panel("Introduction", "vignettes/BAMexploreR_1_intro.html"),
                _vignette_panel("Access", "vignettes/BAMexploreR_2_access.html"),
                _vignette_panel("Distribution", "vignettes/BAMexploreR_3_distribution.html"),
                _vignette_panel("Habitat", "vignettes/BAMexploreR_4_habitat.html"),
                title="Vignettes",
                ),
            col_widths=(-1, 10, -1),
        ),
    )


def tools_tab()-> ui.nav_panel:
    """
    Build the tooling resources layout tab view.

    Renders the model-access resources and package-vignette links maintained
    in the tools Markdown content.

    Returns
    -------
    shiny.ui.nav_panel
        The constructed interface view holding available developer guidelines.
    """
    return ui.nav_panel(
        "Access & Tools",
        ui.layout_columns(
            ui.card(
                ui.card_header("Use Landbird Density & Habitat Models"),
                ui.markdown(read_md("tools.md")),
                class_="tools-card"
            ),
            col_widths=(-1, 10, -1),
        ),
    )


def citing_tab()-> ui.nav_panel:
    """
    Build the citation view interface container.

    Pulls and renders markdown blocks stating data reuse rights, permissions,
    and official project referencing guidelines.

    Returns
    -------
    shiny.ui.nav_panel
        A dedicated user interface tab wrapping formal citation documentation.
    """
    return ui.nav_panel(
        "Citation",
        ui.layout_columns(
            ui.card(
                ui.card_header("How to Cite BAM Model Results"),
                ui.markdown(read_md("citing.md")),
                fill=False,
                class_="citing-card"
            ),
            col_widths=(-1, 10, -1),
        ),
    )
