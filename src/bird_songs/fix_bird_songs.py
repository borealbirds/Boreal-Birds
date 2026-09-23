"""
Targeted song fix script — downloads missing Xeno-Canto songs for species
that were skipped in the original run.

Missing species (same list as fix_bird_photos.py):
  BWWA CAJA DUNL RBWO RHWO ROSA SPGR WITU

Folder format matches what the dashboard expects:
  app/www/audio/{SPECIES_ID}_{Common_Name}/

Run from project root:
  python src/bird_photos/fix_bird_songs.py
"""

import json
import re
import time
import random
from pathlib import Path

import requests

# ── Paths ──────────────────────────────────────────────────────────────
_SCRIPT_DIR   = Path(__file__).parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
AUDIO_DIR     = _PROJECT_ROOT / "app" / "www" / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# ── Missing species: code → (common_name, scientific_name) ────────────
# Scientific names verified against XC / Birds of the World
MISSING = {
    "BWWA": ("Blue-winged Warbler",   "Vermivora cyanoptera"),
    "CAJA": ("Canada Jay",            "Perisoreus canadensis"),
    "DUNL": ("Dunlin",                "Calidris alpina"),
    "RBWO": ("Red-bellied Woodpecker","Melanerpes carolinus"),
    "RHWO": ("Red-headed Woodpecker", "Melanerpes erythrocephalus"),
    "ROSA": ("Rock Sandpiper",        "Calidris ptilocnemis"),
    "SPGR": ("Spruce Grouse",         "Canachites canadensis"),
    "WITU": ("Wild Turkey",           "Meleagris gallopavo"),
}

# Settings (mirrors download_bird_songs.py)
MAX_RECORDINGS           = 2
MAX_RECORDINGS_LONG_TIER = 1
INAT_API                 = "https://api.inaturalist.org/v1"


# ── Helpers ───────────────────────────────────────────────────────────
def duration_to_seconds(duration):
    if not duration:
        return None
    parts = duration.strip().split(":")
    try:
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except ValueError:
        pass
    return None


def quality_rank(q):
    return {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5}.get(str(q).upper(), 99)


def select_recordings(recordings):
    valid = []
    for rec in recordings:
        secs = duration_to_seconds(rec.get("length"))
        if secs is None:
            continue
        rec["_secs"] = secs
        valid.append(rec)

    sort_key = lambda r: (quality_rank(r.get("q")), r["_secs"])
    selected, seen = [], set()

    for max_secs, cap in [(7,MAX_RECORDINGS),(10,MAX_RECORDINGS),(15,MAX_RECORDINGS),(20,MAX_RECORDINGS)]:
        for r in sorted([x for x in valid if x["_secs"] <= max_secs and x.get("id") not in seen], key=sort_key):
            if len(selected) >= cap: break
            selected.append(r); seen.add(r.get("id"))
        if len(selected) >= MAX_RECORDINGS: break

    if selected:
        return selected

    for max_secs in [25, 30]:
        for r in sorted([x for x in valid if x["_secs"] <= max_secs and x.get("id") not in seen], key=sort_key):
            if len(selected) >= MAX_RECORDINGS_LONG_TIER: break
            selected.append(r); seen.add(r.get("id"))
        if selected: break

    return selected


def fetch_inat_sounds(scientific_name):
    try:
        r = requests.get(f"{INAT_API}/observations",
            params={"taxon_name": scientific_name, "sounds": "true",
                    "quality_grade": "research", "per_page": 20, "order_by": "votes"},
            timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"  [iNat error] {e}"); return []
    results = []
    for obs in r.json().get("results", []):
        for snd in obs.get("sounds", []):
            url = snd.get("file_url") or snd.get("file")
            if url:
                results.append({
                    "id": f"inat_{obs.get('id')}_{snd.get('id')}",
                    "file_url": url,
                    "recordist": obs.get("user", {}).get("login", "unknown"),
                    "date": obs.get("observed_on", ""),
                    "country": obs.get("place_guess", ""),
                    "obs_url": f"https://www.inaturalist.org/observations/{obs.get('id')}",
                })
    return results


def download_species(code, common_name, scientific_name, api_key):
    safe        = common_name.replace(" ", "_")
    folder      = AUDIO_DIR / f"{code}_{safe}"
    folder.mkdir(parents=True, exist_ok=True)

    # Already has songs?
    if any(folder.glob("*.mp3")):
        print(f"  [skip] {common_name} — already has songs")
        return

    print(f"\n=== {common_name} ({scientific_name}) ===")

    # ── XC query ──────────────────────────────────────────────────────
    parts = scientific_name.split()
    query = f"gen:{parts[0]} sp:{parts[1]} type:song" if len(parts) >= 2 else scientific_name

    try:
        r = requests.get("https://xeno-canto.org/api/3/recordings",
                         params={"query": query, "key": api_key}, timeout=60)
        r.raise_for_status()
        recordings = r.json().get("recordings", [])
    except Exception as e:
        print(f"  [XC error] {e}"); recordings = []

    selected = select_recordings(recordings) if recordings else []
    source   = "XC"

    # ── iNaturalist fallback ───────────────────────────────────────────
    if not selected:
        print(f"  No XC results — trying iNaturalist…")
        inat_recs = fetch_inat_sounds(scientific_name)
        if not inat_recs:
            print(f"  ✗ No audio found on XC or iNaturalist for {common_name}")
            return
        source = "iNaturalist"
        for i, rec in enumerate(inat_recs[:MAX_RECORDINGS], 1):
            file_url = rec["file_url"]
            filename = f"{i}_inat_{rec['id']}.mp3"
            outpath  = folder / filename
            try:
                audio = requests.get(file_url, timeout=120)
                audio.raise_for_status()
                outpath.write_bytes(audio.content)
                meta = {
                    "common_name": common_name, "scientific_name": scientific_name,
                    "source": "iNaturalist", "recordist": rec.get("recordist",""),
                    "date": rec.get("date",""), "country": rec.get("country",""),
                    "obs_url": rec.get("obs_url",""), "local_audio_file": filename,
                }
                (folder / f"{i}_inat_{rec['id']}_metadata.json").write_text(
                    json.dumps(meta, indent=2), encoding="utf-8")
                print(f"  ✓ {filename}  (iNaturalist)")
                time.sleep(random.uniform(1.0, 2.5))
            except Exception as e:
                print(f"  ✗ Download error: {e}")
        return

    print(f"  {len(recordings)} XC recordings found → downloading {len(selected)}")

    for i, rec in enumerate(selected, 1):
        file_url = rec.get("file", "")
        if file_url.startswith("//"): file_url = "https:" + file_url
        if not file_url: continue

        rec_id   = rec.get("id", "unknown")
        quality  = rec.get("q", "?")
        length   = rec.get("length", "?")
        safe_len = str(length).replace(":", "-")
        filename = f"{i}_{rec_id}_q{quality}_{safe_len}.mp3"
        outpath  = folder / filename

        try:
            audio = requests.get(file_url, timeout=120)
            audio.raise_for_status()
            outpath.write_bytes(audio.content)
            meta = {
                "common_name": common_name, "scientific_name": scientific_name,
                "source": "Xeno-Canto",
                "xeno_canto_recording_id": rec_id,
                "xeno_canto_url": f"https://xeno-canto.org/{rec_id}",
                "xeno_canto_english_name": rec.get("en",""),
                "recordist": rec.get("rec",""), "country": rec.get("cnt",""),
                "location": rec.get("loc",""), "date": rec.get("date",""),
                "length": length, "duration_seconds": rec.get("_secs"),
                "quality": quality, "type": rec.get("type",""),
                "license": rec.get("lic",""), "local_audio_file": filename,
            }
            (folder / f"{i}_{rec_id}_metadata.json").write_text(
                json.dumps(meta, indent=2), encoding="utf-8")
            print(f"  ✓ {filename}  (quality {quality}, {length})")
            time.sleep(random.uniform(1.0, 2.5))
        except Exception as e:
            print(f"  ✗ Download error: {e}")


# ── Run ────────────────────────────────────────────────────────────────
API_KEY = input("Paste your Xeno-Canto API key: ").strip()
if not API_KEY:
    raise RuntimeError("No API key provided.")

print(f"\nDownloading songs for {len(MISSING)} species → {AUDIO_DIR}\n")

for code, (common_name, scientific_name) in MISSING.items():
    download_species(code, common_name, scientific_name, API_KEY)

print("\n✓ Song fix complete.")
