from shiny import Inputs, reactive, render, ui
from shinywidgets import render_widget

from ipyleaflet import Map, basemaps
from localtileserver import TileClient, get_leaflet_tile_layer

from shared import get_tif_path


def server_v5(input: Inputs):

    @reactive.calc
    def tile_client():
        path = get_tif_path(
            input.species(),
            input.region(),
            input.year(),
        )

        if not path.exists():
            return None

        return TileClient(str(path))

    @render_widget
    def map_widget():
        client = tile_client()

        if client is None:
            return ui.p("No data available")

        # Create leaflet map
        m = Map(
            center=client.center(), 
            zoom=4, 
            basemap=basemaps.CartoDB.Positron
        )

        # Add raster as tile layer
        tile_layer = get_leaflet_tile_layer(
            client,
            palette="viridis"
        )
        m.add_layer(tile_layer)

        return m