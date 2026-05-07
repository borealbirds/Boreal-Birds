from shiny import Inputs, reactive, ui
from shinywidgets import render_widget
from ipywidgets import HTML
from ipyleaflet import Map, basemaps, WidgetControl
from localtileserver import TileClient, get_leaflet_tile_layer

from shared import get_tif_path, available_regions, available_years


def server_v5(input: Inputs):

    @reactive.effect
    def _update_regions():
        species = input.species()

        if not species:
            ui.update_select("region", choices=[], selected=None)
            return

        regions = available_regions(species)

        ui.update_select(
            "region",
            choices=regions,
            selected=regions[0] if regions else None,
        )

    @reactive.effect
    def _update_year_range():
        species = input.species()
        region = input.region()

        if not species or not region:
            return

        years = available_years(species, region)

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
        species = input.species()
        region = input.region()
        year = input.year()

        if not species or not region or not year:
            return None

        path = get_tif_path(
            species,
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
            client,
            colormap="ylgn",
            indexes=[input.raster_band()]
        )

        m.add_layer(tile_layer)
        legend = HTML(
            value="""
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
            """
        )

        m.add_control(
            WidgetControl(
                widget=legend,
                position="bottomright",
            )
        )

        return m
