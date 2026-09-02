"""Other BAM model products resource page."""

from shiny import ui

from shared.data_loading import read_md


def other_model_products_tab() -> ui.nav_panel:
    """Build the page linking to BAM model products hosted elsewhere."""
    return ui.nav_panel(
        "Other Model Products",
        ui.layout_columns(
            ui.card(
                ui.card_header("Explore Other BAM Model Products"),
                ui.markdown(read_md("other-model-products.md")),
                class_="other-model-products-card",
            ),
            col_widths=(-1, 10, -1),
        ),
    )
