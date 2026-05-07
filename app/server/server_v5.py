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
    def _update_years():
        species = input.species()
        region = input.region()

        if not species or not region:
            ui.update_select("year", choices=[], selected=None)
            return

        years = available_years(species, region)

        ui.update_select(
            "year",
            choices=years,
            selected=years[-1] if years else None,
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
        )

        m.add_layer(tile_layer)
        legend = HTML(
            value="""
            <div style="
                background: white;
                padding: 8px 10px;
                border-radius: 4px;
                font-size: 12px;
                box-shadow: 0 1px 4px rgba(0,0,0,0.2);
            ">
                <div style="margin-bottom: 4px;"><b>Relative abundance</b></div>
                <div style="
                    width: 140px;
                    height: 12px;
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
                <div style="
                    display: flex;
                    justify-content: space-between;
                    margin-top: 2px;
                ">
                    <span>Low</span>
                    <span>High</span>
                </div>
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
