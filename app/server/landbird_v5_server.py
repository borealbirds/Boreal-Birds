"""
Backend analytical server for the current Landbird Density & Habitat product (v5).

Orchestrates reactive pipeline computations, updates filtering ranges, 
handles asynchronous TiTiler spatial metadata statistics collections, and 
renders localized chart widgets, audio tracks, image grids, and datasets.
"""

import io
import json
import warnings
from datetime import date
from pathlib import Path

import requests
import altair as alt
import polars as pl
import xlsxwriter

from ipywidgets import Button, HTML, Layout
from ipyleaflet import (
    basemap_to_tiles,
    basemaps,
    FullScreenControl,
    LayersControl,
    Map,
    ScaleControl,
    TileLayer,
    WidgetControl,
)

from shiny import Inputs, Outputs, Session, reactive, render, ui, req
from shinywidgets import render_altair, render_widget

from assets.images import *
from assets.icons import *
from assets.sounds import *

from domain.birds import *
from domain.charts import *
from domain.map import *

from shared.data_loading import *
from shared.paths import url_exists, get_tif_path
from utils.titiler import *

# alt.data_transformers.enable("vegafusion")

warnings.filterwarnings(
    "ignore",
    category=RuntimeWarning,
    module="numpy.ma.core"
)


def _pretty_license(value: str) -> str:
    """Normalize a license string (CC URL or short code) to a clean label.

    Examples
    --------
    'https://creativecommons.org/licenses/by-nc-sa/4.0/' -> 'CC BY-NC-SA 4.0'
    'cc-by-nc'                                            -> 'CC BY-NC'
    ''                                                    -> ''
    """
    if not value:
        return ""
    v = value.strip()
    low = v.lower()
    if "creativecommons.org" in low:
        if "publicdomain" in low or "/zero/" in low:
            return "CC0"
        # pull the ".../licenses/<code>/<version>/" segment
        parts = [p for p in low.split("creativecommons.org/licenses/", 1)[-1].split("/") if p]
        if parts:
            label = "CC " + "-".join(t.upper() for t in parts[0].split("-"))
            if len(parts) > 1 and parts[1].replace(".", "").isdigit():
                label += " " + parts[1]
            return label
        return "Creative Commons"
    if low.startswith("cc"):
        return "CC " + "-".join(t.upper() for t in v.split("-")[1:]) if "-" in v else v.upper()
    return v


def _source_label(url: str) -> str:
    """Human-readable link label derived from the source URL."""
    low = (url or "").lower()
    if "inaturalist" in low:
        return "iNaturalist ↗"
    if "xeno-canto" in low or "xeno_canto" in low:
        return "Xeno-Canto ↗"
    return "Source ↗"

# log in terminal
print(f"\n\n\nTitiler API Health Status: \n\tTitiler is healthy: {tiler_is_healthy()}\n\n\n")

birds = load_species_metadata()
abundances = load_abundance_data()
covariates = load_covariate_metadata()
importance = load_importance_data()
regions = load_region_data()
IMPOSSIBLE_TO_SEX = impossible_to_sex()

# ── HELPER FUNCTIONS (Non-reactive) -----───────────────────────────

def _format_population_value(pop_df: pl.DataFrame) -> str:
    """
    Extract and format a population estimate numeric value as a clean string.

    Parameters
    ----------
    pop_df : pl.DataFrame
        Filtered data row containing the target population metric column.

    Returns
    -------
    str
        Formatted decimal representation, or an em-dash if missing.
    """
    pop_raw = pop_df.item(0, 'population_estimate') if len(pop_df) > 0 else None
    if pop_raw is None:
        return "—"
    elif round(pop_raw, 2) == 0.0:
        return f"{pop_raw:.3f}"
    return f"{pop_raw:.2f}"

# ── MAIN SERVER LOGIC ──────────────────────────────────────────────

def landbird_v5_server(input: Inputs, output: Outputs, session: Session):
    """
    Execute reactive data flow for the current Landbird Density & Habitat panel (v5).

    Manages calculations across distinct application pipelines including Leaflet 
    map view instances, dynamic dataset slicing using Polars, reactive chart rendering 
    via Altair, media galleries, and workbook extraction routines.

    Parameters
    ----------
    input : Inputs
        Reactive session input dictionary container mapping active interface selections.
    output : Outputs
        Reactive renderer object registry controlling interface output nodes.
    session : Session
        The current active browser runtime and communication link execution loop.

    Returns
    -------
    None
    """

    # Reactive Calcs

    @reactive.calc
    def current_bird_meta() -> pl.DataFrame:
        """
        [@reactive.calc] Slice global metadata for the selected bird species.

        Returns
        -------
        pl.DataFrame
            A single-row data slice matching the current active English common name.
        """
        return birds.filter(pl.col("english") == input.species_v5())

    @reactive.calc
    def population_data() -> pl.DataFrame:
        """
        [@reactive.calc] Extract regional abundance data filtered by species.

        Returns
        -------
        pl.DataFrame
            Complete temporal and regional abundance rows for the selected species.
        """
        return abundances.filter(
            (pl.col("english") == input.species_v5()) & (pl.col("year") == str(input.year_v5()))
        )

    @reactive.calc
    def current_population_slice() -> pl.DataFrame:
        """
        [@reactive.calc] Extract a single population row for specific filters.

        Filters the collection by active species, selected region, and year inputs.

        Returns
        -------
        pl.DataFrame
            The unique intersection data record matching all active layout nodes.
        """
        return abundances.filter(
            (pl.col("english") == input.species_v5()) &
            (pl.col("region")  == input.region_v5()) &
            (pl.col("year")    == str(input.year_v5()))
        )

    @reactive.calc
    def file_url() -> str:
        """
        [@reactive.calc] Resolve the absolute remote URL for the target COG.

        Returns
        -------
        str or None
            The structured HTTP URL to the target cloud-optimized GeoTIFF, or None.
        """
        bird = current_bird_meta()
        species_id = bird.item(0, "id") if len(bird) > 0 else None
        region = input.region_v5()
        year = input.year_v5()

        if not species_id or not region or not year:
            return None
        return get_tif_path(species_id, region, int(year))

    @reactive.calc
    def raster_info() -> dict:
        """
        [@reactive.calc] Query min/max data stats from the remote TiTiler metadata API.

        Returns
        -------
        dict
            Status payload dictionary containing 'status' strings and min/max bounds.
        """
        url = file_url()
        if url is None:
            return {"status": "loading"}
        if not url or not url_exists(url):
            return {"status": "missing"}
        if not tiler_is_healthy():
            return {"status": "tiler_unavailable"}

        try:
            encoded_cog = requests.utils.quote(url, safe="")
            stats_url = f"{PRODUCTION_TILER_BASE}/cog/statistics?url={encoded_cog}"
            res = requests.get(stats_url, timeout=5)
            res.raise_for_status()

            stats = res.json()
            band_key = next(iter(stats), None)
            if not band_key:
                return {"status": "error"}

            band = stats[band_key]
            return {
                "status": "ready",
                "min": float(band.get("min", 0)),
                "max": float(band.get("max", 1))
            }
        except Exception as e:
            print(f"Statistics request failed: {e}")
            return {"status": "tiler_starting"}


    # UI updates

    @reactive.effect
    def _set_map_default():
        """[@reactive.effect] Enforce default 'map' radio view selection on initial connection."""
        ui.update_radio_buttons("view_toggle", selected="map")

    @reactive.effect
    @reactive.event(input.model_access_link)
    def _open_model_access():
        """Open the Access & Tools page from the Download tab link."""
        ui.update_navs("tabs", selected="Access & Tools")

    @reactive.effect
    def update_bcr_filter() -> list:
        """
        Changes the selection of BCR's based on user selected covariate and bird species

        Returns
        -------
        List
            List of applicable BCR's for a selected bird species and covariate
        """

        req(input.covariate_filter())

        covariate_code = input.covariate_filter()
        bird_code = (
            birds
            .filter(pl.col("english") == input.species_v5())
            .item(0, "id")
        )

        file_url, _ = select_covariate_file(covariate_code)

        fx_df = pl.read_csv(file_url).filter(
            (pl.col("species") == bird_code)
        )

        bcr_list = fx_df.get_column("bcr").unique().to_list()

        bcr_choices = dict(
            regions.filter(pl.col("region").is_in(bcr_list))
            .select("region", "name_adj")
            .sort("name_adj")
            .iter_rows()
        )

        ui.update_select(
            "bcr_filter",
            choices=bcr_choices,
            selected=list(bcr_choices.keys())[0] if bcr_choices else None,
        )

    # Bird info UI

    @render.ui
    def selected_bird()-> ui.tags:
        """[@render.ui] Render the header component displaying names and active population bounds."""
        bird = current_bird_meta()
        pop_df = current_population_slice()
        pop_value = _format_population_value(pop_df)
        region = input.region_v5()

        return ui.div(
            ui.div(
                ui.span(bird.item(0, "english"), class_="bird-name"),
                ui.span(bird.item(0, "french"),  class_="bird-french"),
                class_="bird-names",
            ),
            ui.div(
                ui.span("Population Estimate (male birds) ", class_="bird-pop-label"),
                ui.span(region, class_="bird-region-label"),
                ui.span(f" {pop_value}", class_="bird-pop-value"),
                ui.tooltip(
                    question_circle_fill,
                    "Population estimate in millions of male birds for the selected region and year.",
                    placement="right",
                ),
                class_="bird-pop",
            ),
            class_="bird-header-content",
        )

    @render.ui
    def sidebar_bird_image_v5()-> ui.tags:
        """[@render.ui] Render the sidebar profile picture for the active species if it exists."""
        bird = current_bird_meta()
        if len(bird) == 0:
            return ui.span()
            
        img_info = get_sidebar_image_path(bird.item(0, "id"), bird.item(0, "english"))
        if img_info:
            src_path, folder_name = img_info
            return ui.tags.img(
                src=src_path,
                class_="bird-image-sidebar",
                alt=bird.item(0, "english"),
                onerror="this.style.display='none'",
            )
        return ui.span()


    # Map Rendering
    
    REGION_LAYERS = {
        "Canada": build_region_layer("Canada"),
        "Lower48": build_region_layer("Lower48"),
        "Alaska": build_region_layer("Alaska"),
    }

    @render_widget
    def map_widget() -> Map:
        """
        [@render_widget] Build an interactive Ipyleaflet Map map layout object.

        Fetches dynamic PNG tiles from Titiler API, draws boundaries, hooks up
        hover listener tooltips, and binds click-to-zoom matrix overrides.

        Returns
        -------
        Map
            The fully configured interactive geospatial visualization frame instance.
        """
        info = raster_info()
        if info["status"] != "ready":
            return get_map_error_html(info["status"])

        url = file_url()
        encoded_cog = requests.utils.quote(url, safe="")
        region = input.region_v5()
        
        # Basemaps Setup
        positron = basemap_to_tiles(basemaps.CartoDB.Positron)
        positron.base, positron.name = True, "Positron (minimal)"

        osm = basemap_to_tiles(basemaps.OpenStreetMap.Mapnik)
        osm.base, osm.name = True, "Open Street Map (default)"
        
        esri = basemap_to_tiles(basemap=basemaps.Esri.WorldImagery)
        esri.base, esri.name = True, "World Imagery (satellite)"

        # initialize map
        map_center = REGION_CENTERS.get(region, [60.0, -110.0])
        m = Map(layers=[esri, positron, osm], center=map_center, zoom=4, scroll_wheel_zoom=True)

        # generate legend using stats from titiler
        rmin, rmax = info["min"], info["max"]
        legend = WidgetControl(
            widget=HTML(f"""
            <div class="map-legend">
                <div class="map-legend-title">
                    <b>Mean density (male birds/ha)</b><br>
                    <b>{rmin:.4f} → {rmax:.4f}</b>
                </div>
                <div class="map-legend-gradient"></div>
            </div>
            """),
            position="bottomright"
        )

        # request tiles from the titiler API gateway
        tile_string = (
            f"{PRODUCTION_TILER_BASE}"
            f"/cog/tiles/{{z}}/{{x}}/{{y}}.png"
            f"?url={encoded_cog}"
            f"&colormap_name=ylgn"
            f"&rescale={rmin},{rmax}"
        )

        mean_density = TileLayer(url=tile_string, name="Mean density (male birds/ha)")
        m.add(mean_density)
        m.add(legend)

        if region in REGION_LAYERS:
            region_layer, hover_card, hover_control = REGION_LAYERS[region]
            default_center = REGION_CENTERS.get(region, [60, -110])
            default_zoom = 4

            # hover
            def update_hover(event=None, feature=None, **kwargs):

                props = feature.get("properties", {})
                bcr = props.get("bcr", "Unknown")

                hover_card.value = f"""
                <div style="
                    padding:8px 10px;
                    background:white;
                    border-radius:6px;
                    box-shadow:0 1px 4px rgba(0,0,0,0.25);
                    font-size:13px;
                    min-width:160px;
                ">
                    <div>
                        {REGION_DICT[bcr]['name_adj']}
                    </div>
                </div>
                """

            # click on region to zoom
            def zoom_to_bcr(event=None, feature=None, **kwargs):
                props = feature.get("properties", {})
                center = props.get("_center")
                spanx, spany = props.get("_spanx"), props.get("_spany")

                if center and spanx and spany:
                    m.center = center
                    m.zoom = zoom_from_span(spanx, spany)

            region_layer.on_hover(update_hover)
            region_layer.on_click(zoom_to_bcr)

            # reset zoom button
            reset_btn = Button(
                description="Reset Zoom",
                layout=Layout(width="120px")
            )

            def reset_zoom(btn):
                m.center = default_center
                m.zoom = default_zoom

            reset_btn.on_click(reset_zoom)
            reset_control = WidgetControl(
                widget=reset_btn,
                position="bottomleft"
            )

            # add to map
            m.add(region_layer)
            m.add(hover_control)

        # controls
        m.add(FullScreenControl())
        m.add(LayersControl(collapsed=False, position="topright"))
        m.add(reset_control)
        m.add(ScaleControl(position="bottomleft"))

        return m


    # ── TABULAR DATA ───────────────────────────────────────────────────

    @render.data_frame
    def population_size()-> render.DataGrid:
        """
        [@render.data_frame] Output sorted tabular records using an analytical grid component.

        Returns
        -------
        shiny.render.DataGrid
            Sorted metrics collection with active background rows highlighted.
        """
        region = input.region_v5()
        year = int(input.year_v5())

        if not region:
            return render.DataGrid(pl.DataFrame(), selection_mode="rows")


        df = population_data().filter(pl.col("year") == str(year))
        df = df.select([
            "year",
            "region", 
            "population_estimate", 
            "population_lower", 
            "population_upper", 
            "density_estimate", 
            "density_lower", 
            "density_upper"
        ])

        df = df.with_columns(
            (pl.col("region") == region).alias("selected_region")
        ).sort("selected_region", "population_estimate", descending=[True, True])

        region_row_number = df.select(pl.arg_where(pl.col("region") == region)).to_series().to_list()

        selected_style = [
            {
                "rows": region_row_number,
                "style": {
                    "background-color": "#A9DC67FF",
                    "height": "50px",
                },
            }
        ]

        display_df = df.select(pl.exclude("selected_region")).rename({
            "year": "Year",
            "region": "Region",
            "population_estimate": "Population estimate (millions of male birds)",
            "population_lower": "Population lower bound (millions of male birds)",
            "population_upper": "Population upper bound (millions of male birds)",
            "density_estimate": "Density estimate (male birds/ha)",
            "density_lower": "Density lower bound (male birds/ha)",
            "density_upper": "Density upper bound (male birds/ha)",
        })

        return render.DataGrid(display_df, selection_mode="rows", styles=selected_style)

    # ── INFO TAB ───────────────────────────────────────────────────────

    @render.ui
    def species_info()-> ui.tags:
        """[@render.ui] Render taxonomic info strings alongside contextual search hyperlinks."""
        bird = current_bird_meta()
        common_name = bird.item(0, "english")
        species_id = bird.item(0, "id")
        scientific = bird.item(0, "scientific")
        french = bird.item(0, "french")
        family = bird.item(0, "family")

        def info_row(label, value, italic=False):
            return ui.div(
                ui.span(label, class_="info-label"),
                ui.span(ui.tags.em(value) if italic else value, class_="info-value"),
                class_="info-row",
            )

        return ui.div(
            info_row("Scientific Name", scientific, italic=True),
            info_row("French Name",     french),
            info_row("Family",          family),
            info_row("Species Code",    species_id),
            ui.div(
                ui.span("More Information", class_="info-label"),
                ui.div(
                    ui.tags.a("eBird ↗", href=f"https://ebird.org/search?q={scientific.replace(' ', '+')}", target="_blank", class_="info-link"),
                    ui.tags.a("NatureCounts ↗", href=f"https://naturecounts.ca/nc/socb-epoc/search.jsp?qstr={common_name}", target="_blank", class_="info-link"),
                    ui.tags.a("Wikipedia ↗", href=f"https://en.wikipedia.org/wiki/{scientific.replace(' ', '_')}", target="_blank", class_="info-link"),
                    ui.tags.a("Xeno-Canto ↗", href=f"https://xeno-canto.org/species/{scientific.replace(' ', '-')}", target="_blank", class_="info-link"),
                ),
                class_="info-row info-row-links",
            ),
            class_="species-info-card",
        )

    # ── IMAGES TAB ─────────────────────────────────────────────────────

    @render.ui
    def species_images()-> ui.tags:
        """[@render.ui] Assemble a masonry layout grid sorted by biological sex categories."""
        bird = current_bird_meta()
        species_id = bird.item(0, "id")
        common_name = bird.item(0, "english")
        french_name = bird.item(0, "french")
        try:
            scientific_name = bird.item(0, "scientific")
        except Exception:
            scientific_name = ""
        folder_name = f"{species_id}_{common_name.replace(' ', '_')}"
        img_dir = Path(__file__).parent.parent / "www" / "img" / folder_name

        if not img_dir.exists():
            return ui.p("No images available for this species.", class_="text-muted p-3")

        photos = []
        for jpg in sorted(img_dir.glob("*.jpg")):
            meta_path = img_dir / f"{jpg.stem}_metadata.json"
            sex, attribution, obs_url, license = "unknown", "", "", ""
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text())
                    sex = meta.get("sex", "unknown")
                    attribution = meta.get("attribution", "")
                    obs_url = meta.get("obs_url", "")
                    license = meta.get("license", "")
                except Exception:
                    pass
            photos.append({
                "file": jpg.name, 
                "sex": sex, 
                "attribution": attribution, 
                "obs_url": obs_url, 
                "license": license
            })

        if not photos:
            return ui.p("No images found.", class_="text-muted p-3")

        SEX_SYMBOL = {"male": "♂", "female": "♀", "unknown": "?"}

        def photo_grid(items, with_badges=False):
            if not items:
                return ui.p("No photos in this category.", class_="text-muted p-2")
            return ui.div(
                *[
                    ui.div(
                        ui.tags.img(
                            src=f"img/{folder_name}/{p['file']}",
                            class_="species-photo",
                            loading="lazy",
                            onclick="openSpeciesLightbox(this)",
                            data_sex=p["sex"],
                            data_attribution=p.get("attribution",""),
                            data_obs_url=p.get("obs_url",""),
                            data_license=p.get("license",""),
                            data_common=common_name,
                            data_french=french_name,
                            data_scientific=scientific_name,
                        ),
                        ui.span(
                            SEX_SYMBOL.get(p["sex"], "?"),
                            class_=f"sex-badge sex-{p['sex']}"
                        ) if with_badges and common_name not in IMPOSSIBLE_TO_SEX else ui.span(),
                        class_="photo-cell",
                    ) for p in items
                ],
                class_="photo-grid",
            )

        male_photos = [p for p in photos if p["sex"] == "male" and common_name not in IMPOSSIBLE_TO_SEX]
        female_photos = [p for p in photos if p["sex"] == "female" and common_name not in IMPOSSIBLE_TO_SEX]

        return ui.div(
            lightbox_script(),
            ui.HTML("""
                <label class="tag-toggle-floating">
                    <input type="checkbox"
                        onchange="this.closest('.images-tab-wrapper').classList.toggle('show-sex-tags', this.checked)">
                    ♂♀ labels
                </label>
            """) if common_name not in IMPOSSIBLE_TO_SEX else None,
            ui.navset_tab(
                ui.nav_panel(f"All ({len(photos)})", photo_grid(photos, with_badges=True)),
                *( [ui.nav_panel(f"Male ({len(male_photos)})", photo_grid(male_photos))] if male_photos else []),
                *( [ui.nav_panel(f"Female ({len(female_photos)})", photo_grid(female_photos))] if female_photos else []),
            ),
            class_="images-tab-wrapper species-images-container",
        )

    # ── SOUNDS TAB ──────────────────────────────────────────────────────

    @render.ui
    def species_songs()-> ui.tags:
        """[@render.ui] Construct an audio player layout linked to client-side WaveSurfer timelines."""
        bird = current_bird_meta()
        species_id = bird.item(0, "id")
        common_name = bird.item(0, "english")
        scientific_name = bird.item(0, "scientific") if "scientific" in bird.columns else ""
        
        folder_name = f"{species_id}_{common_name.replace(' ', '_')}"
        audio_dir = Path(__file__).parent.parent / "www" / "audio" / folder_name

        if not audio_dir.exists():
            return ui.p("No sounds available for this species.", class_="text-muted p-3")

        audio_files = sorted(audio_dir.glob("*.mp3"))[:5]
        if not audio_files:
            return ui.p("No audio files found.", class_="text-muted p-3")

        # Index sidecars by stem (filename minus the _metadata.json suffix).
        # mp3 and sidecar share a prefix but the suffix differs by source:
        #   XC:   2_1087236_qA_0-07.mp3        <-> 2_1087236_metadata.json
        #   iNat: inat_2_inat_77774398_213707.mp3 <-> ..._213707_metadata.json
        _META_SUFFIX = "_metadata.json"
        meta_index = {
            mf.name[: -len(_META_SUFFIX)]: mf
            for mf in audio_dir.glob("*_metadata.json")
        }

        def _meta_for(mp3):
            stem = mp3.stem
            if stem in meta_index:                       # exact match (iNat-style)
                return meta_index[stem]
            cands = [k for k in meta_index if stem.startswith(k)]  # XC-style prefix
            return meta_index[max(cands, key=len)] if cands else None

        songs = []
        for i, f in enumerate(audio_files, 1):
            m = {}
            mf = _meta_for(f)
            if mf:
                try:
                    m = json.loads(mf.read_text())
                except Exception:
                    pass
            source_url = (m.get("xeno_canto_url", "")
                          or m.get("inat_url", "")
                          or m.get("obs_url", ""))
            songs.append({
                "wsId": f"ws-{species_id}-{i}",
                "specId": f"spec-{species_id}-{i}",
                "metaId": f"meta-{species_id}-{i}",
                "btnId": f"btn-{species_id}-{i}",
                "src": f"/audio/{folder_name}/{f.name}",
                "label": f"Sound {i}",
                "commonName": common_name,
                "scientificName": scientific_name,
                "recordist": m.get("recordist", ""),
                "country": m.get("country", ""),
                "date": m.get("date", ""),
                "quality": m.get("quality", ""),
                "license": _pretty_license(m.get("license", "")),
                "xc_url": source_url,
                "sourceLabel": _source_label(source_url),
            })

        song_blocks = [
            ui.div(
                ui.div(
                    ui.span(s["label"], class_="song-label"),
                    ui.tags.button("▶  Play", id=s["btnId"], class_="play-btn"),
                    class_="song-controls",
                ),
                ui.div(
                    ui.HTML('<div class="ws-loading">Loading waveform…</div>'),
                    id=s["wsId"],
                    class_="waveform-container",
                ),
                ui.div(id=s["specId"], class_="spectrogram-container"),
                ui.div(id=s["metaId"], class_="sound-meta"),
                class_="song-block",
            ) for s in songs
        ]

        sounds_json = json.dumps(songs)

        return ui.div(
            *song_blocks,
            sound_script(sounds_json),
            class_="songs-container",
        )
    
    # ── Chart details ───────────────────────────────────────────────────────

    @render_altair
    def population_chart()-> alt.Chart:
        return population_altair(population_data(), input.species_v5())


    @render_altair
    def density_chart()-> alt.Chart:
        return density_altair(population_data(), input.species_v5())

    # ── COVARIATE FILTER & MARGINAL EFFECTS ───────────────────────────

    @render.text
    def covariate_desc() -> str:
        """
        [@render.text] Outputs simple text containing the covariate definition based on covariate filter.

        Returns
        -------
        Text
            Covariate Definition
        """
        req(input.covariate_filter())

        cov_desc = covariates.filter(pl.col("variable") == input.covariate_filter()).item(0, "definition")

        return f"Definition: {cov_desc}"


    @render.data_frame
    def importance_metrics() -> render.DataTable:
        """
        [@render.data_frame] Output sorted tabular records using an analytical grid component.

        Returns
        -------
        DataGrid
            Sorted metrics collection with active background rows highlighted.
        """

        req(covariates is not None and not covariates.is_empty())

        importance_data = importance.filter(
            pl.col("english") == input.species_v5()
            ).sort(
                "importance_mean", descending=True
            ).select(
                ["variable", "region", "importance_mean"]
            ).head().join(
                covariates.select(["variable", "name"]),
                on="variable",
                how="left",
            )
        
        importance_data = importance_data.with_columns(
            pl.col("importance_mean").round(1),
            pl.coalesce(["name", "variable"]).alias("predictor_name"),
        ).select(
            ["predictor_name", "region", "importance_mean"]
        )
        
        importance_data = importance_data.rename({
            "predictor_name": "Predictor",
            "region": "BCR",
            "importance_mean": "Score"
        })


        return render.DataTable(importance_data, height="210px")
    
    @render.ui
    def marginal_fx_filter()-> ui.tags:
        """[@render.ui] Render variable select dropdown constraints for covariate analyses."""
        
        bird = current_bird_meta().item(0, "english")
        cov_choices = dict(
            covariates.select(
                key=pl.col("variable"),
                value=pl.concat_str(
                    [pl.col("name"), pl.lit(": "), pl.col("variable")]
                )
            )
            .sort("value")
            .iter_rows()
        )
        bcr_choices = []

        return ui.layout_columns(
            ui.layout_columns(
                ui.input_select(
                    id="covariate_filter",
                    label="Select Predictor",
                    choices=cov_choices,
                ),
                # ui.output_text("covariate_desc"),
                ui.input_select(
                    id="bcr_filter",
                    label="Select BCR (Multi-Select)",
                    choices=bcr_choices,
                    multiple=True,
                ),
                col_widths=(12, 12, 12)
            ),
            ui.card(
                ui.markdown(f"Predictor Importance for {bird}"),
                ui.output_data_frame("importance_metrics"),
                fillable=True,
                full_screen=True
            ),
            col_widths=(12, 12)
        )
    
    @render_altair
    def marginal_fx_chart()-> alt.Chart:     
        return covariate_chart(
            input.covariate_filter(),
            input.species_v5(),
            input.bcr_filter(),
        )

    # ── Download ───────────────────────────

    @lru_cache(maxsize=1)
    def get_workbook_bytes() -> bytes:
        """
        Download the master workbook from the configured HTTPS endpoint.

        The downloaded file is cached in memory to avoid repeated network
        requests during the lifetime of the application process.

        Returns
        -------
        bytes
            Raw binary contents of the Excel workbook.
        """
        response = requests.get(LANDBIRD_V5_RESULTS, timeout=30,)
        response.raise_for_status()
        return response.content

    @render.download(
        filename=lambda: (
            f"{date.today().isoformat()}_"
            "BAM_Landbird-Density-Habitat_v5_all-results.xlsx"
        )
    )
    def downloadAll():
        """
        Stream the complete master workbook to the client.

        The workbook is retrieved from the configured HTTPS endpoint and served
        directly to the user without creating a temporary file on the local
        filesystem.

        Yields
        ------
        bytes
            Binary content of the Excel workbook.

        Notes
        -----
        The underlying workbook download is cached by ``get_workbook_bytes()``,
        reducing repeated network requests for subsequent downloads within the
        same application process.
        """
        yield get_workbook_bytes()

    @render.download(
        filename=lambda: (
            f"{date.today().isoformat()}_"
            f"BAM_Landbird-Density-Habitat_v5_{input.species_v5()}_results.xlsx"
        )
    )
    def downloadFiltered():
        """
        Generate a filtered multi-sheet workbook in memory.

        The source workbook is downloaded from the configured HTTPS endpoint,
        filtered according to the selected species and year inputs, and written
        to a new Excel workbook without using intermediate files on disk.

        Yields
        ------
        bytes
            Binary content of the generated Excel workbook.

        Notes
        -----
        The source workbook is cached in memory by ``get_workbook_bytes()`` to
        avoid repeated network requests while the application process is active.
        """

        workbook_bytes = get_workbook_bytes()
        metadata = pl.read_excel(io.BytesIO(workbook_bytes), sheet_name="metadata")
        species = pl.read_excel(io.BytesIO(workbook_bytes), sheet_name="species").filter(
            pl.col("english") == input.species_v5()
        )
        regions = pl.read_excel(io.BytesIO(workbook_bytes), sheet_name="regions")
        variables = pl.read_excel(io.BytesIO(workbook_bytes), sheet_name="variables")
        importance = pl.read_excel(io.BytesIO(workbook_bytes), sheet_name="importance").filter(
            pl.col("english") == input.species_v5()
        )
        validation = pl.read_excel(io.BytesIO(workbook_bytes), sheet_name="validation").filter(
            pl.col("english") == input.species_v5()
        )
        abundances = pl.read_excel(io.BytesIO(workbook_bytes), sheet_name="abundances").filter(
            (pl.col("english") == input.species_v5())
            & (pl.col("year") == str(input.year_v5()))
        )

        with io.BytesIO() as buffer:
            workbook = xlsxwriter.Workbook(buffer, {'in_memory': True})
            metadata.write_excel(workbook=workbook, worksheet="metadata", autofilter=False, autofit=True)
            species.write_excel(workbook=workbook, worksheet="species", autofilter=False, autofit=True)
            regions.write_excel(workbook=workbook, worksheet="regions", autofilter=False, autofit=True)
            variables.write_excel(workbook=workbook, worksheet="variables", autofilter=False, autofit=False)
            importance.write_excel(workbook=workbook, worksheet="importance", autofilter=False, autofit=True)
            validation.write_excel(workbook=workbook, worksheet="validation", autofilter=False, autofit=True)
            abundances.write_excel(workbook=workbook, worksheet="abundances", autofilter=False, autofit=True)
            workbook.close()
            yield buffer.getvalue()

    @render.ui
    def download_filtered_btn()-> ui.tags:
        """[@render.ui] Render a custom contextual export execution trigger button for the bird model."""
        species = input.species_v5()

        return ui.download_button(
            "downloadFiltered",
            f"Download {species} Results"
        )
