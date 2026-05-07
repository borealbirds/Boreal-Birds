from pathlib import Path

from tabs.about import about_tab
from tabs.model_v4 import model_v4_tab
from tabs.model_v5 import model_v5_tab
from tabs.methods import methods_tab
from server.server_v5 import server_v5

from sidebar import sidebar

import polars as pl
from shiny import App, Inputs, reactive, render, ui

from content.methods_content import methods_sections

app_ui = ui.page_navbar(
    ui.nav_spacer(),
    model_v5_tab(),
    model_v4_tab(),
    methods_tab(),
    about_tab(),
    sidebar=sidebar(),
    id="tabs",
    title="Boreal Birds Dashboard",
    fillable=True,
    header=ui.tags.style(
        """
        :root {
            --bb-primary: rgb(21, 59, 64);
            --bb-secondary: rgb(30, 80, 85);
            --bb-surface: rgb(237, 245, 243);
            --bb-sidebar: rgb(228, 239, 236);
            --bb-card: rgb(241, 248, 246);
        }

        html,
        body {
            background-color: var(--bb-surface);
        }

        .navbar {
            background-color: var(--bb-primary) !important;
        }

        .navbar .navbar-brand,
        .navbar .nav-link {
            color: white !important;
        }

        .navbar .nav-link.active,
        .navbar .nav-link[aria-current="page"] {
            font-weight: 700 !important;
        }

        .sidebar {
            background-color: var(--bb-sidebar);
        }

        .card {
            background-color: var(--bb-card);
            border: 1px solid rgba(21, 59, 64, 0.08);
            border-radius: 8px;
        }

        .card-header {
            background-color: rgb(230, 241, 238);
            color: var(--bb-secondary) !important;
        }

        .form-select,
        .form-control {
            border-color: rgba(21, 59, 64, 0.12);
        }

        .form-check-input:checked {
            background-color: var(--bb-secondary);
            border-color: var(--bb-secondary);
        }
        """
    ),
)


def server(input: Inputs):

    # Register Model V5 outputs
    server_v5(input)

img_dir = Path(__file__).parent / "img"

app = App(app_ui, server, static_assets={"/img": str(img_dir)})