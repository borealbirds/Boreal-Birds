from shiny import Inputs, reactive, ui, render
from shinywidgets import render_widget
from ipywidgets import HTML
from ipyleaflet import Map, basemaps, WidgetControl
from localtileserver import TileClient, get_leaflet_tile_layer

import polars as pl

from shared import (
    get_tif_path,
    available_regions,
    available_years,
    load_species_metadata,
    get_species_image,
)


def server_v5(input: Inputs):

    @reactive.calc
    def species_info():
        df = load_species_metadata()

        species_id = input.species()

        if not species_id:
            return None

        row = df.filter(pl.col("id") == species_id)

        if row.height == 0:
            return None

        r = row.row(0)

        return {
            "english": r[2],
            "french": r[3],
            "scientific": r[1],
            "family": r[4],
        }

    @render.ui
    def bird_info():
        info = species_info()

        if info is None:
            return ui.p("No species selected")

        species_id = input.species()
        img_path = get_species_image(species_id)
        img_src = (
            f"/img/{species_id}.jpg"
            if img_path and img_path.exists()
            else "https://placehold.co/200x150?text=No+Image"
        )

        return ui.div(
            ui.div(
                ui.img(
                    id="species_img",
                    src=img_src,
                    # style=(
                    #     "width: 200px; height: 150px; object-fit: cover; "
                    #     "border-radius: 6px; cursor: pointer;"
                    #     "display: block;"
                    # ),
                    style="width:200px; height:150px; object-fit:cover; border:1px solid #ddd;",
                ),
                ui.div(
                    ui.h4(info["english"], style="margin-bottom: 4px;"),
                    ui.p(
                        f"{info['french']} · {info['scientific']} · Family {info['family']}",
                        style="margin: 0;",
                    ),
                    style="padding-left: 12px;",
                ),
                style="display: flex; align-items: center;",
            ),
        )

    @reactive.effect
    def _update_regions():
        species_id = input.species()

        if not species_id:
            ui.update_select("region", choices=[], selected=None)
            return

        regions = available_regions(species_id)

        ui.update_select(
            "region",
            choices=regions,
            selected=regions[0] if regions else None,
        )

    @reactive.effect
    def _update_year_range():
        species_id = input.species()
        region = input.region()

        if not species_id or not region:
            return

        years = available_years(species_id, region)

        if not years:
            return

        ui.update_slider(
            "year",
            min=min(years),
            max=max(years),
            value=max(years),
        )

    @reactive.calc
    def tile_client():
        species_id = input.species()
        region = input.region()
        year = input.year()

        if not species_id or not region or not year:
            return None

        path = get_tif_path(
            species_id,
            region,
            int(year),
        )

        if not path.exists():
            return None

        return TileClient(str(path))

    @render_widget
    def map_widget():
        client = tile_client()

        if client is None:
            return ui.p("No data available")

        m = Map(
            center=client.center(),
            zoom=4,
            basemap=basemaps.CartoDB.Positron,
        )

        tile_layer = get_leaflet_tile_layer(
            client, colormap="ylgn", indexes=[input.raster_band()]
        )

        m.add_layer(tile_layer)
        legend = HTML(value="""
            <div style="
                background: white;
                padding: 5px 6px;
                border-radius: 3px;
                font-size: 10px;
                line-height: 1.1;
                box-shadow: 0 1px 3px rgba(0,0,0,0.15);
            ">
                <div style="margin-bottom: 3px;"><b>Low → High</b></div>
                <div style="
                    width: 90px;
                    height: 8px;
                    background: linear-gradient(
                        to right,
                        #ffffe5,
                        #d9f0a3,
                        #addd8e,
                        #78c679,
                        #31a354,
                        #006837
                    );
                    border: 1px solid #999;
                "></div>
            </div>
            """)

        m.add_control(
            WidgetControl(
                widget=legend,
                position="bottomright",
            )
        )

        return m
