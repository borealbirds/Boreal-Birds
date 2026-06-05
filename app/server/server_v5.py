import io
import json
import warnings
from datetime import date
from functools import lru_cache
from pathlib import Path

import requests
import altair as alt
import polars as pl
import xlsxwriter
from shapely.geometry import shape

from ipywidgets import Button, HTML, Layout
from ipyleaflet import (
    basemap_to_tiles,
    basemaps,
    FullScreenControl,
    GeoJSON,
    LayersControl,
    Map,
    ScaleControl,
    TileLayer,
    WidgetControl,
)

from shiny import Inputs, Outputs, Session, reactive, render, ui, req
from shinywidgets import render_altair, render_widget

from icons import question_circle_fill
from shared import (
    available_regions,
    available_years,
    get_tif_path,
    get_cov_fx_data,
    load_abundance_data,
    load_region_data,
    load_species_metadata,
    load_subregion_boundaries,
    load_covariate_metadata,
)

# alt.data_transformers.enable("vegafusion")

warnings.filterwarnings(
    "ignore",
    category=RuntimeWarning,
    module="numpy.ma.core"
)

birds = load_species_metadata()
abundances = load_abundance_data()
subregions = load_subregion_boundaries()
region_dict = load_region_data().rows_by_key(key="region", named=True, unique=True)
covariates = load_covariate_metadata()

# Live Posit Connect Cloud dynamic map tiler base domain address
PRODUCTION_TILER_BASE = "https://019e4735-507f-07a0-1ae5-b96da68b058b.share.connect.posit.cloud"

# Hardcoded fallback center metrics for geographic bounding contexts
REGION_CENTERS = {
    "Alaska": [64, -149],
    "Canada": [58, -103],
    "Lower48": [47.0, -97.0]
}

def url_exists(url: str) -> bool:
    """
    Ensure url for the file exists in the data host server
    """
    try:
        r = requests.head(url, timeout=10)
        return r.status_code == 200
    except Exception:
        return False

def get_region_gdf(region: str):
    gdf = subregions
    alaska_bcr = ["usa2", "usa41423", "usa43", "usa40", "usa5"]

    if region == "Canada":
        return gdf[gdf["bcr"].str.startswith("can")]

    if region == "Lower48":
        return gdf[
            gdf["bcr"].str.startswith("usa") &
            ~gdf["bcr"].isin(alaska_bcr)
        ]

    if region == "Alaska":
        return gdf[gdf["bcr"].isin(alaska_bcr)]

    return gdf

def build_region_layer(region_name: str):

    region_gdf = get_region_gdf(region_name)

    geojson_data = json.loads(
        region_gdf.to_json(drop_id=True)
    )

    # precompute zoom/centering for each feature
    for feature in geojson_data["features"]:

        geom = shape(feature["geometry"])
        minx, miny, maxx, maxy = geom.bounds

        # center of each bcr
        cx, cy = geom.centroid.x, geom.centroid.y

        feature["properties"]["_center"] = [cy, cx]
        feature["properties"]["_bounds"] = [[miny, minx], [maxy, maxx]]

        spanx = maxx - minx
        spany = maxy - miny
        feature["properties"]["_spanx"] = spanx
        feature["properties"]["_spany"] = spany

    layer = GeoJSON(
        data=geojson_data,
        style={
            "color": "black",
            "weight": 1.25,
            "fillColor": "white", 
            "fillOpacity": 0, 
            "opacity": 0.2,
        },
        hover_style={
            "color": "#00FFFF",
            "weight": 3,
            "fillColor": "white", 
            "fillOpacity": 0, 
            "opacity": 1, 
        },
        name="Subregion Boundaries"
    )

    # floating info card
    hover_card = HTML(
        value="""
        <div style="
            padding:8px 10px;
            background:white;
            border-radius:6px;
            box-shadow:0 1px 4px rgba(0,0,0,0.25);
            font-size:13px;
            min-width:140px;
        ">
            Hover over a subregion
        </div>
        """,
        layout=Layout(margin="0px")
    )

    hover_control = WidgetControl(
        widget=hover_card,
        position="bottomleft"
    )

    return layer, hover_card, hover_control

def zoom_from_span(span_x, span_y):
    if not span_x or not span_y:
        return 4
    # map height / map width (roughly)
    aspect = 4 / 9
    # normalize vertical span into width-equivalent span
    span_y_normalized = span_y / aspect
    span = max(span_x, span_y_normalized)

    if span > 30:
        zoom = 4.2
    elif span > 25:
        zoom = 4.5
    elif span > 23:
        zoom = 4.7
    elif span > 16:
        zoom = 5.2
    elif span > 10:
        zoom = 5.5
    elif span > 8:
        zoom = 6
    else:
        zoom = 6.5
    print("\n\nspan ", span, " zoom ", zoom)
    return zoom

def server_v5(input: Inputs, output: Outputs, session: Session):
    """
    Main server logic for the Model V5 tab, managing reactive data flow 
    and spatial visualization.
    """

    @reactive.effect
    def _set_map_default():
        """Force MAP view on session init."""
        ui.update_radio_buttons("view_toggle", selected="map")

    @render.ui
    def selected_bird():
        bird   = birds.filter(pl.col("english") == input.species_v5())
        region = input.region_v5() or ""
        year   = int(input.year_v5())

        pop_df = abundances.filter(
            (pl.col("english") == input.species_v5()) &
            (pl.col("region")  == region) &
            (pl.col("year") == str(year))
        )
        pop_raw   = pop_df.item(0, 'population_estimate') if len(pop_df) > 0 else None
        if pop_raw is None:
            pop_value = "—"
        elif round(pop_raw, 2) == 0.0:
            pop_value = f"{pop_raw:.3f}"
        else:
            pop_value = f"{pop_raw:.2f}"

        return ui.div(
            ui.div(
                ui.span(bird.item(0, "english"), class_="bird-name"),
                ui.span(bird.item(0, "french"),  class_="bird-french"),
                class_="bird-names",
            ),
            ui.div(
                ui.span("Population Estimate ", class_="bird-pop-label"),
                ui.span(region, class_="bird-region-label"),
                ui.span(f" {pop_value}", class_="bird-pop-value"),
                ui.tooltip(
                    question_circle_fill,
                    "Population estimate (millions) for the selected region and year",
                    placement="right",
                ),
                class_="bird-pop",
            ),
            class_="bird-header-content",
        )

    @render.ui
    def sidebar_bird_image_v5():
        bird        = birds.filter(pl.col("english") == input.species_v5())
        species_id  = bird.item(0, "id")
        common_name = bird.item(0, "english")
        folder_name = f"{species_id}_{common_name.replace(' ', '_')}"
        img_dir     = Path(__file__).parent.parent / "www" / "img" / folder_name
        if img_dir.exists():
            jpgs = sorted(img_dir.glob("*.jpg"))
            if jpgs:
                return ui.tags.img(
                    src=f"img/{folder_name}/{jpgs[0].name}",
                    class_="bird-image-sidebar",
                    alt=common_name,
                    onerror="this.style.display='none'",
                )
        return ui.span()

    @reactive.effect
    def _update_regions():
        """Update the region dropdown choices dynamically based on species availability."""
        species_id = birds.filter(pl.col("english") == input.species_v5()).item(0, "id")

        if not species_id:
            ui.update_select("region_v5", choices=[], selected=None)
            return

        regions = available_regions(species_id)

        ui.update_select(
            "region_v5",
            choices=regions,
            selected=(
                "Canada" if regions and "Canada" in regions else (
                    regions[0] if regions else None
                )
            ),
        )

    @reactive.effect
    def _update_year_range():
        """Update the slider range and default value based on available temporal data."""
        species_id = birds.filter(pl.col("english") == input.species_v5()).item(0, "id")
        region = input.region_v5()

        if not species_id or not region:
            return

        years = available_years(species_id, region)

        if not years:
            return

        ui.update_slider(
            "year_v5",
            min=min(years),
            max=max(years),
            value=max(years),
        )
    
    @reactive.calc
    def file_url():
        """Construct the remote URL string path for the selected raster."""
        species_id = birds.filter(
            pl.col("english") == input.species_v5()
        ).item(0, "id")

        region = input.region_v5()
        year = int(input.year_v5())

        if not species_id or not region or not year:
            return None

        return get_tif_path(species_id, region, int(year))

    @reactive.calc
    def raster_statistics():
        """Query min/max data statistics remotely using the TiTiler metadata API."""
        url = file_url()
        if not url or not url_exists(url):
            return {"min": 0.0, "max": 1.0}
            
        try:
            encoded_cog = requests.utils.quote(url, safe="")
            # Query the statistics endpoint exposed by the tiler
            stats_url = f"{PRODUCTION_TILER_BASE}/cog/statistics?url={encoded_cog}"
            res = requests.get(stats_url, timeout=5).json()
            
            band_key = list(res.keys())[0] if res else None
            if band_key:
                band_stats = res[band_key]
                return {
                    "min": float(band_stats.get("min", 0.0)),
                    "max": float(band_stats.get("max", 1.0))
                }
            return {"min": 0.0, "max": 1.0}
        except Exception as e:
            print(f"Error fetching TiTiler statistics: {e}")
            return {"min": 0.0, "max": 1.0}
    
    REGION_LAYERS = {
        "Canada": build_region_layer("Canada"),
        "Lower48": build_region_layer("Lower48"),
        "Alaska": build_region_layer("Alaska"),
    }

    @render_widget
    def map_widget():
        """Generate the interactive map widget leveraging the remote cloud tiler engine."""
        url = file_url()

        if not url:
            return HTML("<p>Loading / No data available</p>")

        if not url_exists(url):
            return HTML("<p>Raster not found on data server</p>")

        encoded_cog = requests.utils.quote(url, safe="")
        
        # center on the selected region
        map_center = REGION_CENTERS.get(input.region_v5(), [60.0, -110.0])

        # Basemaps
        positron = basemap_to_tiles(basemaps.CartoDB.Positron)
        positron.base = True
        positron.name = "Positron (minimal)"
        
        osm = basemap_to_tiles(basemaps.OpenStreetMap.Mapnik)
        osm.base = True
        osm.name = "Open Street Map (default)"
        
        esri = basemap_to_tiles(basemap=basemaps.Esri.WorldImagery)
        esri.base = True
        esri.name = "World Imagery (satellite)"

        # Initialize core map interface
        m = Map(layers=[esri, positron, osm], center=map_center, zoom=4, scroll_wheel_zoom=True)

        # generate legend utilizing remote data calculations
        stats = raster_statistics()
        rmin = stats["min"]
        rmax = stats["max"]

        legend = WidgetControl(
            widget=HTML(f"""
            <div class="map-legend">
                <div class="map-legend-title">
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

        mean_density = TileLayer(
            url=tile_string,
            name="Mean Density",
        )

        m.add(mean_density)
        m.add(legend)

        region = input.region_v5()

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
                        {region_dict[bcr]['name_adj']}
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

    @reactive.calc
    def population_data():
        return abundances.filter(
            (pl.col("english") == input.species_v5())
        )

    @render.data_frame
    def population_size():
        region = input.region_v5()
        year   = int(input.year_v5())

        if not region:
            return render.DataGrid(pl.DataFrame(), selection_mode="rows")

        df = abundances.filter(
            (pl.col("english") == input.species_v5()) &
            # (pl.col("region")  == region) &
            (pl.col("year")    == str(year))
        )

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
        ).sort("population_estimate", "selected_region", descending=[True, True])

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

        return render.DataGrid(df.select(pl.exclude("selected_region")), selection_mode="rows", styles=selected_style)

    # ── INFO TAB ───────────────────────────────────────────────────────

    @render.ui
    def species_info():
        bird        = birds.filter(pl.col("english") == input.species_v5())
        species_id  = bird.item(0, "id")
        scientific  = bird.item(0, "scientific")
        french      = bird.item(0, "french")
        family      = bird.item(0, "family")

        ebird_url = f"https://ebird.org/species/{species_id.lower()}"
        bow_url   = f"https://birdsoftheworld.org/bow/species/{species_id.lower()}"

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
                    ui.tags.a("eBird ↗",       href=f"https://ebird.org/search?q={scientific.replace(' ', '+')}", target="_blank", class_="info-link"),
                    ui.tags.a("Xeno-Canto ↗",  href=f"https://xeno-canto.org/species/{scientific.replace(' ', '-')}", target="_blank", class_="info-link"),
                    ui.tags.a("Wikipedia ↗",   href=f"https://en.wikipedia.org/wiki/{scientific.replace(' ', '_')}", target="_blank", class_="info-link"),
                ),
                class_="info-row info-row-links",
            ),
            class_="species-info-card",
        )

    # ── IMAGES TAB ─────────────────────────────────────────────────────

    @render.ui
    def species_images():
        bird            = birds.filter(pl.col("english") == input.species_v5())
        species_id      = bird.item(0, "id")
        common_name     = bird.item(0, "english")
        french_name     = bird.item(0, "french")
        try:
            scientific_name = bird.item(0, "scientific")
        except Exception:
            scientific_name = ""
        folder_name = f"{species_id}_{common_name.replace(' ', '_')}"
        img_dir     = Path(__file__).parent.parent / "www" / "img" / folder_name

        if not img_dir.exists():
            return ui.p("No images available for this species.", class_="text-muted p-3")

        photos = []
        for jpg in sorted(img_dir.glob("*.jpg")):
            meta_path = img_dir / f"{jpg.stem}_metadata.json"
            sex, attribution = "unknown", ""
            if meta_path.exists():
                try:
                    meta        = json.loads(meta_path.read_text())
                    sex         = meta.get("sex", "unknown")
                    attribution = meta.get("attribution", "")
                except Exception:
                    pass
            obs_url = ""
            license = ""
            if meta_path.exists():
                try:
                    m2       = json.loads(meta_path.read_text())
                    obs_url  = m2.get("obs_url", "")
                    license  = m2.get("license", "")
                except Exception:
                    pass
            photos.append({"file": jpg.name, "sex": sex, "attribution": attribution,
                           "obs_url": obs_url, "license": license})

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
                            class_=f"sex-badge sex-{p['sex']}",
                        ) if with_badges else ui.span(),
                        class_="photo-cell",
                    )
                    for p in items
                ],
                class_="photo-grid",
            )

        male_photos   = [p for p in photos if p["sex"] == "male"]
        female_photos = [p for p in photos if p["sex"] == "female"]

        lightbox_js = ui.HTML("""
<script>
if (!document.getElementById('species-lightbox')) {
    document.body.insertAdjacentHTML('beforeend', `
        <div id="species-lightbox" class="lb-overlay" onclick="if(event.target===this)closeLb()">
            <button class="lb-close" onclick="closeLb()">✕</button>
            <button class="lb-arrow lb-prev" onclick="lbNav(-1)">&#8249;</button>
            <div class="lb-content">
                <img id="lb-img" class="lb-main-img">
                <div id="lb-counter" class="lb-counter"></div>
                <div id="lb-meta" class="lb-meta"></div>
            </div>
            <button class="lb-arrow lb-next" onclick="lbNav(1)">&#8250;</button>
        </div>
    `);
    document.addEventListener('keydown', e => {
        const lb = document.getElementById('species-lightbox');
        if (lb && lb.style.display !== 'none') {
            if (e.key === 'ArrowLeft')  lbNav(-1);
            if (e.key === 'ArrowRight') lbNav(1);
            if (e.key === 'Escape')     closeLb();
        }
    });
}

window.openSpeciesLightbox = function(el) {
    const grid = el.closest('.photo-grid');
    const imgs = Array.from(grid.querySelectorAll('.species-photo'));
    window._lbPhotos = imgs.map(i => ({
        src:         i.src,
        sex:         i.dataset.sex || '',
        attribution: i.dataset.attribution || '',
        obsUrl:      i.dataset.obsUrl || '',
        license:     i.dataset.license || '',
        common:      i.dataset.common || '',
        french:      i.dataset.french || '',
        scientific:  i.dataset.scientific || '',
    }));
    window._lbIdx = imgs.indexOf(el);
    updateLb();
    document.getElementById('species-lightbox').style.display = 'flex';
};

window.lbNav = function(dir) {
    window._lbIdx = (window._lbIdx + dir + window._lbPhotos.length) % window._lbPhotos.length;
    updateLb();
};

window.closeLb = function() {
    document.getElementById('species-lightbox').style.display = 'none';
};

function updateLb() {
    const p   = window._lbPhotos[window._lbIdx];
    const SEX = { male: '♂ Male', female: '♀ Female', unknown: '' };
    document.getElementById('lb-img').src     = p.src;
    document.getElementById('lb-counter').textContent =
        (window._lbIdx + 1) + ' – ' + window._lbPhotos.length;

    const sexTag  = SEX[p.sex] || '';
    const license = p.license  ? ' · ' + p.license : '';
    const link    = p.obsUrl   ? '<a href="' + p.obsUrl + '" target="_blank" class="lb-link">iNaturalist ↗</a>' : '';
    document.getElementById('lb-meta').innerHTML =
        '<div class="lb-species-row">' +
            (p.common     ? '<span class="lb-common">'     + p.common     + '</span>' : '') +
            (p.scientific ? '<em  class="lb-scientific">'  + p.scientific + '</em>'   : '') +
            (sexTag       ? '<span class="lb-sex-label">'  + sexTag       + '</span>' : '') +
        '</div>' +
        '<div class="lb-attr-row">' +
            (p.attribution ? '© ' + p.attribution + license : '') +
            (link          ? '&nbsp;&nbsp;' + link : '') +
        '</div>';
}
</script>
""")

        return ui.div(
            lightbox_js,
            ui.HTML("""
                <label class="tag-toggle-floating">
                    <input type="checkbox"
                        onchange="this.closest('.images-tab-wrapper').classList.toggle('show-sex-tags', this.checked)">
                    ♂♀ labels
                </label>
            """),
            ui.navset_tab(
                ui.nav_panel(f"All ({len(photos)})",          photo_grid(photos, with_badges=True)),
                ui.nav_panel(f"Male ({len(male_photos)})",    photo_grid(male_photos)),
                ui.nav_panel(f"Female ({len(female_photos)})", photo_grid(female_photos)),
            ),
            class_="images-tab-wrapper species-images-container",
        )

    # ── SONGS TAB ──────────────────────────────────────────────────────

    @render.ui
    def species_songs():
        bird        = birds.filter(pl.col("english") == input.species_v5())
        species_id  = bird.item(0, "id")
        common_name = bird.item(0, "english")
        folder_name = f"{species_id}_{common_name.replace(' ', '_')}"
        audio_dir   = Path(__file__).parent.parent / "www" / "audio" / folder_name

        if not audio_dir.exists():
            return ui.p("No songs available for this species.", class_="text-muted p-3")

        audio_files = sorted(audio_dir.glob("*.mp3"))[:5]
        if not audio_files:
            return ui.p("No audio files found.", class_="text-muted p-3")

        songs = [
            {
                "wsId":  f"ws-{species_id}-{i}",
                "specId": f"spec-{species_id}-{i}",
                "btnId":  f"btn-{species_id}-{i}",
                "src":    f"/audio/{folder_name}/{f.name}",
                "label":  f"Song {i}",
            }
            for i, f in enumerate(audio_files, 1)
        ]

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
                ui.div(
                    ui.HTML('<div class="ws-loading ws-loading-spec">Computing spectrogram…</div>'),
                    id=s["specId"],
                    class_="spectrogram-container",
                ),
                ui.tags.button(
                    "⤢  Expand spectrogram",
                    id=f"expand-{s['specId']}",
                    class_="spec-expand-btn",
                    onclick=f"toggleSpec('{s['specId']}', this)",
                ),
                class_="song-block",
            )
            for s in songs
        ]

        songs_json = json.dumps(songs)

        init_script = f"""
<script>
(async function() {{
    try {{
        await new Promise(r => setTimeout(r, 200));
        const {{ default: WaveSurfer }}  = await import('https://unpkg.com/wavesurfer.js@7/dist/wavesurfer.esm.js');
        const {{ default: Spectrogram }} = await import('https://unpkg.com/wavesurfer.js@7/dist/plugins/spectrogram.esm.js');

        window.toggleSpec = function(specId, btn) {{
            const el = document.getElementById(specId);
            const expanded = el.classList.toggle('spec-expanded');
            btn.textContent = expanded ? '⤡  Collapse spectrogram' : '⤢  Expand spectrogram';
        }};

        const songs = {songs_json};
        for (const song of songs) {{
            const wsEl   = document.getElementById(song.wsId);
            const specEl = document.getElementById(song.specId);
            const btn    = document.getElementById(song.btnId);
            if (!wsEl || !specEl) continue;
            if (wsEl._ws) {{ try {{ wsEl._ws.destroy(); }} catch(e) {{}} }}

            const ws = WaveSurfer.create({{
                container:     wsEl,
                waveColor:     'rgba(59,82,139,0.8)',
                progressColor: '#153B40',
                cursorColor:   '#ff4444',
                cursorWidth:   2,
                height:        56,
                normalize:     true,
                plugins: [
                    Spectrogram.create({{
                        container:    specEl,
                        labels:       true,
                        height:       200,
                        frequencyMax: 10000,
                        fftSamples:   1024,
                    }})
                ],
            }});
            ws.load(song.src);
            wsEl._ws = ws;

            // Remove loading placeholders once ready
            ws.on('decode', () => {{
                wsEl.querySelector('.ws-loading')?.remove();
                specEl.querySelector('.ws-loading')?.remove();
            }});

            if (btn) {{
                btn.addEventListener('click', () => ws.playPause());
                ws.on('play',   () => btn.textContent = '⏸  Pause');
                ws.on('pause',  () => btn.textContent = '▶  Play');
                ws.on('finish', () => btn.textContent = '▶  Play');
            }}

            specEl.style.position = 'relative';
            const cursor = document.createElement('div');
            cursor.style.cssText = 'position:absolute;top:0;left:0;width:2px;height:100%;background:rgba(255,68,68,0.85);pointer-events:none;z-index:10;';
            specEl.appendChild(cursor);
            ws.on('timeupdate', t => {{
                const dur = ws.getDuration();
                if (dur) cursor.style.left = (t/dur*100)+'%';
            }});
        }}
    }} catch(e) {{ console.error('WaveSurfer init error:', e); }}
}})();
</script>"""

        return ui.div(
            *song_blocks,
            ui.HTML(init_script),
            class_="songs-container",
        )
    
    # ── Chart details ───────────────────────────────────────────────────────
    @render_altair
    def population_chart():

        df = population_data()

        points = alt.Chart(df).mark_point(
            filled=True,
        ).encode(
            alt.X("population_estimate:Q")
                .title("Abundance (M males)")
                .scale(type="symlog"),
            alt.Y("region_name:N")
                .title(None)
                .sort(
                    field="population_estimate",
                    order="descending",
                )
                .axis(labelLimit=0),
            alt.Color(
                "country_name:N",
                legend=alt.Legend(title="Country")
            ),
        ).transform_calculate(
            region_name=f"{region_dict}[datum.region].name_adj",
            country_name=f"{region_dict}[datum.region].country"
        )

        nearest = alt.selection_point(
            nearest=True,
            on="pointerover",
            fields=["population_estimate"],
            empty=False
        )
        when_near = alt.when(nearest)

        highlight = points.mark_point(
            size=50,
            stroke="#153B40FF",
        ).encode(
            opacity=when_near.then(alt.value(1)).otherwise(alt.value(0))
        )

        rules = alt.Chart(df).mark_rule(
            color="#153B40FF",
        ).encode(
            x="population_estimate:Q",
            opacity=alt.when(nearest)
                .then(alt.value(0.5))
                .otherwise(alt.value(0)),
            tooltip=[
                alt.Tooltip("population_estimate:Q", title="Population Estimate"),
                alt.Tooltip("population_lower:Q", title="Lower Estimate"),
                alt.Tooltip("population_upper:Q", title="Upper Estimate"),
        ]
        ).add_params(nearest)

        error_bars = points.mark_rule().encode(
            x="population_lower:Q",
            x2="population_upper:Q",
        )

        return (points + error_bars + rules + highlight).properties(
            title=alt.Title(
                f"Regional Population Estimates for the {input.species_v5()}",
                subtitle="Intervals represent 5th and 95th percentile of the bootstrap distribution"
            ),
            width="container",
            height=750
        )

    @render_altair
    def density_chart():

        df = population_data()

        points = alt.Chart(df).mark_point(
            filled=True,
        ).encode(
            alt.X("density_estimate:Q")
                .title("Density (males/ha)"),
            alt.Y("region_name:N")
                .title(None)
                .sort(
                    field="density_estimate",
                    order="descending",
                )
                .axis(labelLimit=0),
            alt.Color(
                "country_name:N",
                legend=alt.Legend(title="Country")
            ),
        ).transform_calculate(
            region_name=f"{region_dict}[datum.region].name_adj",
            country_name=f"{region_dict}[datum.region].country"
        )

        nearest = alt.selection_point(
            nearest=True,
            on="pointerover",
            fields=["density_estimate"],
            empty=False
        )
        when_near = alt.when(nearest)

        highlight = points.mark_point(
            size=50,
            stroke="#153B40FF",
        ).encode(
            opacity=when_near.then(alt.value(1)).otherwise(alt.value(0))
        )

        rules = alt.Chart(df).mark_rule(
            color="#153B40FF",
        ).encode(
            x="density_estimate:Q",
            opacity=alt.when(nearest)
                .then(alt.value(0.5))
                .otherwise(alt.value(0)),
            tooltip=[
                alt.Tooltip("density_estimate:Q", title="Density Estimate"),
                alt.Tooltip("density_lower:Q", title="Lower Estimate"),
                alt.Tooltip("density_upper:Q", title="Upper Estimate"),
        ]
        ).add_params(nearest)

        error_bars = points.mark_rule().encode(
            x="density_lower:Q",
            x2="density_upper:Q",
        )

        return (points + error_bars + rules + highlight).properties(
            title=alt.Title(
                f"Regional Density Estimates for {input.species_v5()}",
                subtitle="Intervals represent 5th and 95th percentile of the bootstrap distribution"
            ),
            width="container",
            height=750
        )
    
    @render.ui
    def marginal_fx_filter():
        
        cov_choices = sorted(covariates.get_column("name").unique().to_list())
        # cov_choices.append("year")
        res_choices = covariates.get_column("prediction_resolution").unique().to_list()
        bcr_choices = ['can40', 'can72','can13','usa2','can14','can70','can12', 'can5', 'can9',
                       'can61','can60','can3','can11','usa41423','can82',
                       'can71','can81','can41','can80','usa43', 'usa40','can10']

        return ui.layout_columns(
            ui.input_select(
                id="covariate_filter",
                label="Select Covariate",
                choices=cov_choices
            ),
            ui.input_select(
                id="resolution_filter",
                label="Select Resolution",
                choices=res_choices
            ),
            ui.input_select(
                id="bcr_filter",
                label="Select BCR",
                choices=bcr_choices
            ),
            col_widths=(12, 12)
        )

    @reactive.Calc
    def covariate_df():
        req(input.covariate_filter())
        req(input.resolution_filter())
        req(input.species_v5())
        
        bird_code = birds.filter(pl.col("english") == input.species_v5()).item(0,"id")

        return get_cov_fx_data(
            covariates.filter(
                (pl.col("name") == input.covariate_filter()) & (pl.col("prediction_resolution") == input.resolution_filter())
            ).get_column("variable").to_list()
        ).filter(pl.col("species") == bird_code)

    @render_altair
    def marginal_fx_chart():
        req(input.covariate_filter())
        req(input.resolution_filter())
        req(input.species_v5())
        req(input.bcr_filter())
        
        bird_code = birds.filter(pl.col("english") == input.species_v5()).item(0,"id")

        fx_df = get_cov_fx_data(
                covariates.filter(
                    (pl.col("name") == input.covariate_filter()) & (pl.col("prediction_resolution") == input.resolution_filter())
                ).get_column("variable").to_list()
            ).filter((pl.col("species") == bird_code) & (pl.col("bcr") == input.bcr_filter()))
        

        #viz_df = fx_df.with_columns(pl.col("x").round(2)).group_by(["bcr", "x"]).agg(pl.col("y").mean().alias("mean_y"))

        # points = alt.Chart(fx_df).mark_point().encode(
        #     alt.X("x:N")
        #         .title(f"Covariate: {input.covariate_filter()}")
        #         .bin(maxbins=20),
        #     alt.Y("mean_y:Q")
        #         .title("Marginal Effect on Density")
        #         .axis(labelLimit=0),
        #     alt.Color(
        #         "bcr:N",
        #         legend=alt.Legend(title="BCR")
        #     ),
        # )

        # # trendline = points.transform_regression(
        # #     'x', 'y'
        # # ).mark_line(size=3)

        # return (points)
        chart = alt.Chart(fx_df).mark_line().encode(
            alt.X("x")
                .title(f"Covariate: {input.covariate_filter()}"),
            alt.Y("fit"),
            alt.Color("bcr")
        ).properties(
            width="container",
            height="container"
        )

        band = alt.Chart(fx_df).mark_errorband().encode(
            alt.X("x"),
            alt.Y(
                "lwr",
                title="Marginal effect on denisty (birds/ha)"
            ),
            alt.Y2("upr"),
        )
        return (band + chart)


    @render.download(filename=lambda: f"{date.today().isoformat()}_BAMV5-results.xlsx")
    def downloadAll():

        return str(Path(__file__).parent.parent.parent / "data" / "model_v5" / "12_BAMV5-results.xlsx")

    @render.download(filename=lambda: f"{date.today().isoformat()}_{input.species_v5()}_model-results.xlsx")
    def downloadFiltered():

        model_results = str(Path(__file__).parent.parent.parent / "data" / "model_v5" / "12_BAMV5-results.xlsx")
        metadata = pl.read_excel(model_results, sheet_name="metadata")
        species = pl.read_excel(model_results, sheet_name="species").filter(pl.col("english") == input.species_v5())
        regions = pl.read_excel(model_results, sheet_name="regions")
        variables = pl.read_excel(model_results, sheet_name="variables")
        importance = pl.read_excel(model_results, sheet_name="importance").filter(pl.col("english") == input.species_v5())
        validation = pl.read_excel(model_results, sheet_name="validation").filter(pl.col("english") == input.species_v5())
        abundances = pl.read_excel(model_results, sheet_name="abundances").filter(
            (pl.col("english") == input.species_v5()) & (pl.col("year") == str(input.year_v5()))
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
    def download_filtered_btn():
        species = input.species_v5()

        return ui.download_button(
            "downloadFiltered",
            f"Download {species} Results"
        )
