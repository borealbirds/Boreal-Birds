"""
Full re-download of bird photos for the Boreal Birds dashboard.

For every species in the master list this script wipes the existing folder
and downloads up to 12 photos:
  * sexually distinguishable species -> 6 male + 6 female
  * otherwise                        -> 12 photos labeled "unknown"

Metadata schema and the  {n}_{photo_id}.jpg / {n}_{photo_id}_metadata.json
naming convention are unchanged from the original download.

Usage (run from project root):
  python src/bird_photos/get_bird_photos.py                 # full re-download (all species)
  python src/bird_photos/get_bird_photos.py --species "Downy Woodpecker"
  python src/bird_photos/get_bird_photos.py --limit 5       # first 5 species (test run)
  python src/bird_photos/get_bird_photos.py --dupes-only    # only report cross-species dupes

Key correctness notes
----------------------
* iNaturalist controlled-term values are Female = 10, Male = 11.
* Searches resolve the scientific name to a verified Aves taxon_id and query
  by taxon_id (+ iconic_taxa="Aves"), so genus/name homonyms can't pull in
  insects or plants.
"""

import argparse
import csv
import json
import re
import time
import random
from pathlib import Path
from collections import defaultdict

import requests
import openpyxl

# -- Paths --------------------------------------------------------------
_SCRIPT_DIR   = Path(__file__).parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
SPECIES_FILE  = _PROJECT_ROOT / "src" / "bird_songs" / "docs" / "species_bam.tsv"
EXCEL_FILE    = _PROJECT_ROOT / "src" / "bird_songs" / "docs" / "12_BAMV5-results_noabundance.xlsx"
OUTPUT_DIR    = _PROJECT_ROOT / "app" / "img"

MB = 1024 * 1024; KB = 1024
INAT_API       = "https://api.inaturalist.org/v1"
INAT_SIZES     = ["medium", "large", "original"]
SIZE_CAP       = int(1.5 * MB)

# Target counts
PER_SEX        = 6     # 6 male + 6 female when distinguishable
TOTAL_UNKNOWN  = 12    # 12 total when sex is not distinguishable

# iNaturalist controlled-term value IDs for "Sex" (term_id 9): Female=10, Male=11.
TERM_SEX = 9; TERM_FEMALE = 10; TERM_MALE = 11
# "Alive or Dead" (term_id 17): Alive=18, Dead=19. Used to exclude dead birds.
TERM_ALIVE_DEAD = 17; TERM_ALIVE = 18; TERM_DEAD = 19
AVES_ICONIC = "Aves"

# Keyword screen for condition we can't filter structurally: dead/rehab birds and
# banded/tagged/transmitter-wearing birds. Matched as whole words/phrases against
# the observation description + tags + species_guess. Word boundaries keep this
# from tripping on names like "Ring-necked Duck" or "Banded"-prefixed plumage notes
# is unavoidable for a few, but candidate volume absorbs the occasional false drop.
EXCLUDE_PATTERNS = re.compile(
    r"\b("
    r"dead(?!\s+(?:tree|branch|snag|log|wood|leaf|leaves|grass|stump))|"
    r"deceased|carcass|roadkill|road[\s-]?killed|window[\s-]?strike|found\s+dead|"
    r"taxidermy|mount(?:ed)?\s+specimen|salvage[d]?|"
    r"rehab(?:ilitation|ilitated|bed)?|wildlife\s+center|raptor\s+center|"
    r"leg[\s-]?band(?:ed)?|colou?r[\s-]?band(?:ed)?|bird[\s-]?band(?:ed)?|"
    r"ring(?:ed|ing)|banded\s+bird|aluminum\s+band|usgs\s+band|"
    r"wing[\s-]?tag|patagial|transmitter|radio[\s-]?tag(?:ged)?|gps[\s-]?tag(?:ged)?|"
    r"geolocator|backpack\s+tag"
    r")\b",
    re.IGNORECASE,
)

# Plumage/morph outliers we also skip.
MORPH_TERMS = {"albino","leucistic","leucism","xanthochroism","melanistic",
               "partial albino","colour morph","color morph","white morph"}

# Species (by English common name) to always treat as NOT sex-distinguishable.
# Seed this from the dashboard's impossible_to_sex() list. Anything listed here
# skips the male/female split and downloads 12 "unknown" photos instead.
MONOMORPHIC = {
    # "Canada Jay",
    # "Blue Jay",
    # ...
}

# Force the scientific name for species whose name resolution is unreliable.
# Searching by an unambiguous binomial avoids fuzzy common-name collisions
# (e.g. "Canada Jay" fuzzily matching Canada Goose). Keyed by English common name.
SCI_OVERRIDE = {
    "Canada Jay": "Perisoreus canadensis",
    "Gray Jay":   "Perisoreus canadensis",
    "Spruce Grouse": "Falcipennis canadensis",
}

# -- Session ------------------------------------------------------------
session = requests.Session()
session.headers.update({"User-Agent": "BorealBirds-Dashboard/1.0"})

# -- Master species list ------------------------------------------------
def load_id_lookup():
    """Return {english_common_name: {"id": code, "scientific": name}} from Excel."""
    if not EXCEL_FILE.exists():
        return {}
    try:
        wb      = openpyxl.load_workbook(EXCEL_FILE, read_only=True, data_only=True)
        ws      = wb["species"]
        rows    = list(ws.iter_rows(values_only=True))
        wb.close()
        headers = [str(h).strip() if h is not None else "" for h in rows[0]]
        id_idx  = headers.index("id")
        en_idx  = headers.index("english")
        sci_idx = headers.index("scientific")
        min_len = max(id_idx, en_idx, sci_idx) + 1
        result = {}
        for row in rows[1:]:
            if len(row) >= min_len and row[id_idx] and row[en_idx]:
                result[str(row[en_idx]).strip()] = {
                    "id":         str(row[id_idx]).strip(),
                    "scientific": str(row[sci_idx]).strip() if row[sci_idx] else "",
                }
        return result
    except Exception as e:
        print(f"  [warn] Could not load Excel: {e}")
        return {}

def load_scientific_from_tsv(common_name: str) -> str:
    """Fallback scientific-name lookup in the TSV by common name."""
    ALIASES = {"Canada Jay": "Gray Jay", "Gray Jay": "Canada Jay"}
    try:
        with SPECIES_FILE.open("r", encoding="utf-8") as f:
            for row in csv.DictReader(f, delimiter="\t"):
                name = row.get("common_name", "").strip()
                if name == common_name or name == ALIASES.get(common_name, ""):
                    return row.get("scientific_name", "").strip()
    except Exception:
        pass
    return ""

# -- iNaturalist ---------------------------------------------------------
def resolve_bird_taxon_id(name: str):
    """
    Resolve a scientific name (species or genus) to an iNat taxon_id,
    restricted to birds. Returns (taxon_id, matched_name) or (None, None).
    Searching by a verified Aves taxon_id is what prevents insect/plant hits.
    """
    try:
        r = session.get(
            f"{INAT_API}/taxa",
            params={"q": name, "rank": "species,genus", "per_page": 30},
            timeout=30,
        )
        r.raise_for_status()
        results = r.json().get("results", [])
    except Exception as e:
        print(f"  [taxon lookup error] {e}")
        return None, None

    aves = [t for t in results if t.get("iconic_taxon_name") == AVES_ICONIC]
    if not aves:
        return None, None
    # Always prefer an exact name match (case-insensitive).
    for t in aves:
        if t.get("name", "").lower() == name.lower():
            return t.get("id"), t.get("name")
    # No exact match. For a multi-word binomial, refuse to guess — a fuzzy
    # first result is how wrong species slip in (e.g. Canada Goose for
    # "Canada Jay"). Only fall back to the top Aves hit for a bare genus.
    if len(name.split()) > 1:
        print(f"  [warn] No exact Aves match for '{name}' — not guessing")
        return None, None
    return aves[0].get("id"), aves[0].get("name")

def get_annotations(obs):
    result = {}
    for ann in obs.get("annotations", []):
        attr = ann.get("controlled_attribute", {}).get("label", "")
        val  = ann.get("controlled_value", {}).get("label", "")
        if attr and val:
            result[attr] = val
    return result

def inat_search(taxon_id, per_page=50, sex_term_value=None):
    """Research-grade, non-captive, adult, alive bird photos for a taxon_id.

    Photos are ordered by community faves (best available proxy for image
    quality), dead birds are excluded at the API level, and a keyword screen
    drops obvious dead/rehab/banded/tagged observations.
    """
    params = {
        "taxon_id":            taxon_id,
        "iconic_taxa":         AVES_ICONIC,
        "photos":              "true",
        "quality_grade":       "research",
        "captive":             "false",
        "without_term_value_id": TERM_DEAD,   # drop anything annotated "Dead"
        "per_page":            per_page,
        "order_by":            "votes",       # faves first -> better photos
        "order":               "desc",
    }
    if sex_term_value is not None:
        params["term_id"]       = TERM_SEX
        params["term_value_id"] = sex_term_value
    try:
        r = session.get(f"{INAT_API}/observations", params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"  [iNat error] {e}")
        return []

    photos = []
    seen   = set()
    for obs in data.get("results", []):
        if obs.get("taxon", {}).get("iconic_taxon_name") not in (None, AVES_ICONIC):
            continue
        ann        = get_annotations(obs)
        life_stage = ann.get("Life Stage", "")
        alive_dead = ann.get("Alive or Dead", "")
        if life_stage and life_stage != "Adult": continue
        if alive_dead and alive_dead != "Alive": continue   # belt-and-suspenders vs. Dead
        # Keyword screen across description + tags + species_guess.
        blob = " ".join([
            obs.get("description") or "",
            " ".join(obs.get("tags", [])),
            obs.get("species_guess") or "",
        ])
        if EXCLUDE_PATTERNS.search(blob): continue
        if any(t in blob.lower() for t in MORPH_TERMS): continue
        obs_url  = f"https://www.inaturalist.org/observations/{obs.get('id')}"
        obs_date = obs.get("observed_on", "")
        user     = obs.get("user", {}).get("login", "")
        for photo in obs.get("photos", []):
            pid = photo.get("id")
            if pid in seen: continue
            seen.add(pid)
            photos.append({
                "id":          pid,
                "square_url":  photo.get("url", ""),
                "attribution": photo.get("attribution", ""),
                "license":     photo.get("license_code", ""),
                "obs_url":     obs_url,
                "obs_date":    obs_date,
                "user":        user,
            })
    return photos

def select_url(photo):
    for size in INAT_SIZES:
        url = photo["square_url"].replace("square", size)
        if not url: continue
        if size == "original":
            try:
                r = session.head(url, timeout=10, allow_redirects=True)
                length = r.headers.get("Content-Length")
                if length and int(length) >= SIZE_CAP: continue
            except Exception:
                continue
        return url, (150*KB if size == "medium" else 450*KB if size == "large" else 800*KB)
    return None

def save_photos(photos, sex_label, folder, scientific_name, common_name,
                start_count, limit, skip_ids):
    """Download up to `limit` NEW photos (skipping any id in skip_ids).

    skip_ids is mutated with each saved id so the same iNat photo is never
    fetched twice across passes or against what's already on disk.
    Returns (saved_filenames, next_count).
    """
    saved = []
    photo_count = start_count
    for photo in photos:
        if len(saved) >= limit: break
        if photo["id"] in skip_ids: continue          # already on disk or just saved
        result = select_url(photo)
        if not result: continue
        url, size_bytes = result
        photo_count += 1
        filename = f"{photo_count}_{photo['id']}.jpg"
        outpath  = folder / filename
        try:
            img = session.get(url, timeout=60)
            img.raise_for_status()
            outpath.write_bytes(img.content)
            meta = {
                "common_name": common_name, "scientific_name": scientific_name,
                "sex": sex_label, "life_stage": "adult", "captive": False,
                "photo_id": photo["id"], "attribution": photo.get("attribution",""),
                "license": photo.get("license",""), "obs_url": photo.get("obs_url",""),
                "obs_date": photo.get("obs_date",""), "recorded_by": photo.get("user",""),
                "download_url": url, "size_kb": round(size_bytes/KB, 1), "local_file": filename,
            }
            (folder / f"{photo_count}_{photo['id']}_metadata.json").write_text(
                json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
            saved.append(filename)
            skip_ids.add(photo["id"])
            print(f"    OK {filename}  ({sex_label}, {size_bytes/KB:.0f} KB)")
            time.sleep(random.uniform(0.5, 1.2))
        except Exception as e:
            print(f"    FAIL download error: {e}")
    return saved, photo_count

def scan_existing(folder):
    """
    Inspect a species folder already on disk.

    Returns dict with:
      ids        -> set of iNat photo_ids already present
      counts     -> {"male": n, "female": n, "unknown": n}
      max_index  -> highest numeric filename prefix (for continued numbering)
      total      -> number of jpgs present
    """
    ids       = set()
    counts    = {"male": 0, "female": 0, "unknown": 0}
    max_index = 0
    total     = 0
    if not folder.exists():
        return {"ids": ids, "counts": counts, "max_index": 0, "total": 0}

    for jpg in folder.glob("*.jpg"):
        total += 1
        # numeric prefix for continued numbering
        prefix = jpg.stem.split("_")[0]
        if prefix.isdigit():
            max_index = max(max_index, int(prefix))
        meta_file = folder / f"{jpg.stem}_metadata.json"
        sex = "unknown"
        if meta_file.exists():
            try:
                m = json.loads(meta_file.read_text())
                pid = m.get("photo_id")
                if pid is not None:
                    ids.add(pid)
                sex = m.get("sex", "unknown")
            except Exception:
                pass
        counts[sex if sex in counts else "unknown"] += 1
    return {"ids": ids, "counts": counts, "max_index": max_index, "total": total}

def download_species(species_code, common_name, scientific_name, force=False):
    """
    Ensure the species folder holds the target set of photos.

    Incremental by default: existing files are kept, and only the deficit is
    downloaded (6 male + 6 female when distinguishable, else 12 unknown).
    A folder that already meets target is skipped without any API calls.
    Pass force=True to wipe and re-download from scratch.

    Returns the total number of jpgs in the folder afterward.
    """
    safe   = common_name.replace(" ", "_")
    folder = OUTPUT_DIR / f"{species_code}_{safe}"
    folder.mkdir(parents=True, exist_ok=True)

    if force:
        for f in folder.iterdir():
            f.unlink()

    existing = scan_existing(folder)
    skip_ids = set(existing["ids"])
    start    = existing["max_index"]
    counts   = existing["counts"]

    # Determine the plan from what's already there (unless empty/forced).
    has_sexed   = counts["male"] > 0 or counts["female"] > 0
    has_unknown = counts["unknown"] > 0

    # Empty (or forced) -> decide distinguishability from iNat, full download.
    if existing["total"] == 0:
        taxon_id = _resolve_or_skip(scientific_name)
        if not taxon_id:
            return existing["total"]
        forced_mono = common_name in MONOMORPHIC
        male_photos = female_photos = []
        if not forced_mono:
            male_photos   = inat_search(taxon_id, sex_term_value=TERM_MALE)
            female_photos = inat_search(taxon_id, sex_term_value=TERM_FEMALE)
        if (not forced_mono) and male_photos and female_photos:
            print(f"  Fresh, distinguishable — {len(male_photos)}m / {len(female_photos)}f candidates")
            _, start = save_photos(male_photos, "male", folder, scientific_name,
                                   common_name, start, PER_SEX, skip_ids)
            _, start = save_photos(female_photos, "female", folder, scientific_name,
                                   common_name, start, PER_SEX, skip_ids)
        else:
            reason = "monomorphic override" if forced_mono else "no both-sex annotations"
            print(f"  Fresh, not distinguishable ({reason}) — {TOTAL_UNKNOWN} unknown")
            photos = inat_search(taxon_id, sex_term_value=None)
            _, start = save_photos(photos, "unknown", folder, scientific_name,
                                   common_name, start, TOTAL_UNKNOWN, skip_ids)
        return scan_existing(folder)["total"]

    # Non-empty -> top up using the existing labeling scheme.
    if has_sexed:
        need_m = max(0, PER_SEX - counts["male"])
        need_f = max(0, PER_SEX - counts["female"])
        if need_m == 0 and need_f == 0:
            print(f"  Complete ({counts['male']}m / {counts['female']}f) — skipping")
            return existing["total"]
        taxon_id = _resolve_or_skip(scientific_name)
        if not taxon_id:
            return existing["total"]
        print(f"  Topping up — have {counts['male']}m/{counts['female']}f, "
              f"need +{need_m}m/+{need_f}f")
        if need_m:
            photos = inat_search(taxon_id, sex_term_value=TERM_MALE)
            _, start = save_photos(photos, "male", folder, scientific_name,
                                   common_name, start, need_m, skip_ids)
        if need_f:
            photos = inat_search(taxon_id, sex_term_value=TERM_FEMALE)
            _, start = save_photos(photos, "female", folder, scientific_name,
                                   common_name, start, need_f, skip_ids)
    else:  # only unknowns present
        need = max(0, TOTAL_UNKNOWN - counts["unknown"])
        if need == 0:
            print(f"  Complete ({counts['unknown']} unknown) — skipping")
            return existing["total"]
        taxon_id = _resolve_or_skip(scientific_name)
        if not taxon_id:
            return existing["total"]
        print(f"  Topping up — have {counts['unknown']} unknown, need +{need}")
        photos = inat_search(taxon_id, sex_term_value=None)
        _, start = save_photos(photos, "unknown", folder, scientific_name,
                               common_name, start, need, skip_ids)

    return scan_existing(folder)["total"]

def _resolve_or_skip(scientific_name):
    """Resolve to an Aves taxon_id (species then genus), or print + return None."""
    taxon_id, _ = resolve_bird_taxon_id(scientific_name)
    if not taxon_id:
        genus = scientific_name.split()[0] if scientific_name else ""
        if genus:
            taxon_id, _ = resolve_bird_taxon_id(genus)
            if taxon_id:
                print(f"  Species not found as a bird; using genus '{genus}' (taxon {taxon_id})")
    if not taxon_id:
        print(f"  [warn] Could not resolve '{scientific_name}' to an Aves taxon — skipping")
    return taxon_id

# -- Cross-species duplicate detection ----------------------------------
def detect_duplicates():
    photo_id_map = defaultdict(list)
    for meta_file in OUTPUT_DIR.rglob("*_metadata.json"):
        try:
            m   = json.loads(meta_file.read_text())
            pid = str(m.get("photo_id", ""))
            if pid:
                photo_id_map[pid].append(
                    (meta_file.parent.name, meta_file.stem.rsplit("_metadata", 1)[0] + ".jpg"))
        except Exception:
            pass
    dupes = {pid: locs for pid, locs in photo_id_map.items() if len(locs) > 1}
    if dupes:
        print(f"\nWARNING {len(dupes)} duplicate photo ID(s) across species:")
        for pid, locs in dupes.items():
            print(f"  iNat photo {pid}:")
            for folder, filename in locs:
                print(f"    {folder}/{filename}")
    else:
        print("\nOK No cross-species duplicate photo IDs found.")
    return dupes

# -- CLI ----------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--species", help="Limit to one species (English common name)")
    parser.add_argument("--limit", type=int, help="Only process the first N species (test run)")
    parser.add_argument("--force", action="store_true",
                        help="Wipe and re-download each species instead of topping up")
    parser.add_argument("--dupes-only", action="store_true", help="Only run duplicate detection")
    args = parser.parse_args()

    id_lookup = load_id_lookup()

    if args.dupes_only:
        detect_duplicates()
        return

    if not id_lookup:
        print("[error] Could not load species master list from Excel — aborting.")
        return

    items = list(id_lookup.items())
    if args.species:
        items = [(en, info) for en, info in items if en.lower() == args.species.lower()]
        if not items:
            print(f"[error] '{args.species}' not found in species list.")
            return
    if args.limit:
        items = items[:args.limit]

    mode = "Re-downloading (force)" if args.force else "Updating (incremental)"
    print(f"\n-- {mode}: {len(items)} species, target 12 each -----------")
    summary = []
    for english, info in items:
        sci = (SCI_OVERRIDE.get(english)
               or info.get("scientific")
               or load_scientific_from_tsv(english))
        if not sci:
            print(f"  [warn] No scientific name for {english} — skipping")
            summary.append((english, 0))
            continue
        print(f"\n=== {info['id']}  {english} ({sci}) ===")
        total = download_species(info["id"], english, sci, force=args.force)
        summary.append((english, total))

    print("\n-- Cross-species duplicate detection ----------------------")
    detect_duplicates()

    # Summary, surfacing anything short of 12 so you can spot-check.
    print("\n-- Summary ------------------------------------------------")
    short = [(en, n) for en, n in summary if n < 12]
    print(f"  {len(summary)} species processed; {len(short)} below 12 photos")
    for en, n in short:
        print(f"    {n:2d}  {en}")
    print("\nOK Done.")

if __name__ == "__main__":
    main()