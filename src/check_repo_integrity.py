"""Validate local modules, content files, and paired media assets."""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path


REPO_DIR = Path(__file__).resolve().parent.parent
APP_DIR = REPO_DIR / "app"
CONTENT_DIR = APP_DIR / "content"
IMG_DIR = APP_DIR / "www" / "img"
AUDIO_DIR = APP_DIR / "www" / "audio"
META_SUFFIX = "_metadata.json"


def module_exists(module: str) -> bool:
    """Return whether a local import or Quartodoc module exists."""
    if module == "app":
        return (APP_DIR / "app.py").is_file()

    relative = Path(*module.split("."))
    return (APP_DIR / relative).with_suffix(".py").is_file() or (
        APP_DIR / relative / "__init__.py"
    ).is_file()


def check_python(errors: list[str]) -> None:
    """Check local imports and literal content-loader targets."""
    local_roots = {
        path.name for path in APP_DIR.iterdir() if path.is_dir()
    } | {"app"}

    for source in APP_DIR.rglob("*.py"):
        relative_source = source.relative_to(REPO_DIR)
        try:
            tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        except SyntaxError as exc:
            errors.append(f"{relative_source}:{exc.lineno}: invalid Python syntax: {exc.msg}")
            continue

        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                modules = [node.module]

            for module in modules:
                if module.split(".", 1)[0] in local_roots and not module_exists(module):
                    errors.append(
                        f"{relative_source}:{node.lineno}: missing local module {module}"
                    )

            if not isinstance(node, ast.Call) or not node.args:
                continue
            if not isinstance(node.func, ast.Name) or node.func.id not in {
                "read_md",
                "read_yaml",
            }:
                continue
            filename = node.args[0]
            if isinstance(filename, ast.Constant) and isinstance(filename.value, str):
                target = CONTENT_DIR / filename.value
                if not target.is_file():
                    errors.append(
                        f"{relative_source}:{node.lineno}: missing content file "
                        f"{target.relative_to(REPO_DIR)}"
                    )

    manifest = CONTENT_DIR / "methods" / "methods-sections.yaml"
    for line_number, line in enumerate(
        manifest.read_text(encoding="utf-8").splitlines(), start=1
    ):
        match = re.match(r"\s*file:\s*(.+?)\s*$", line)
        if match:
            target = CONTENT_DIR / match.group(1).strip("\"'")
            if not target.is_file():
                errors.append(
                    f"{manifest.relative_to(REPO_DIR)}:{line_number}: "
                    f"missing content file {target.relative_to(REPO_DIR)}"
                )


def check_quartodoc(errors: list[str]) -> None:
    """Check that every module configured for Quartodoc exists."""
    config = REPO_DIR / "docs" / "_quarto.yml"
    in_quartodoc = False
    for line_number, line in enumerate(
        config.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if line == "quartodoc:":
            in_quartodoc = True
        if not in_quartodoc:
            continue
        match = re.match(r"\s{8}-\s+([A-Za-z_]\w*(?:\.\w+)*)\s*$", line)
        if match and not module_exists(match.group(1)):
            errors.append(
                f"{config.relative_to(REPO_DIR)}:{line_number}: "
                f"missing Quartodoc module {match.group(1)}"
            )


def check_images(errors: list[str]) -> None:
    """Check species photo/metadata pairs and local_file references."""
    for photo in IMG_DIR.rglob("*.jpg"):
        if photo.parent == IMG_DIR:
            continue
        metadata = photo.with_name(f"{photo.stem}{META_SUFFIX}")
        if not metadata.is_file():
            errors.append(
                f"{photo.relative_to(REPO_DIR)}: missing metadata sidecar "
                f"{metadata.name}"
            )

    for metadata in IMG_DIR.rglob(f"*{META_SUFFIX}"):
        try:
            values = json.loads(metadata.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{metadata.relative_to(REPO_DIR)}: invalid JSON: {exc}")
            continue
        local_file = values.get("local_file")
        if local_file and not (metadata.parent / local_file).is_file():
            errors.append(
                f"{metadata.relative_to(REPO_DIR)}: local_file does not exist: "
                f"{local_file}"
            )


def check_audio(errors: list[str]) -> None:
    """Check audio files and metadata using the dashboard's matching rules."""
    for directory in sorted(path for path in AUDIO_DIR.iterdir() if path.is_dir()):
        audio_files = list(directory.glob("*.mp3"))
        metadata_files = list(directory.glob(f"*{META_SUFFIX}"))
        metadata_keys = {
            metadata: metadata.name[: -len(META_SUFFIX)]
            for metadata in metadata_files
        }

        for audio_file in audio_files:
            if not any(
                audio_file.stem == key or audio_file.stem.startswith(key)
                for key in metadata_keys.values()
            ):
                errors.append(
                    f"{audio_file.relative_to(REPO_DIR)}: missing matching metadata"
                )

        for metadata, key in metadata_keys.items():
            if not any(
                audio_file.stem == key or audio_file.stem.startswith(key)
                for audio_file in audio_files
            ):
                errors.append(
                    f"{metadata.relative_to(REPO_DIR)}: missing matching audio file"
                )


def check_static_assets(errors: list[str]) -> None:
    """Check layout assets and embedded vignettes referenced by the app."""
    paths = (
        "img/favicon.png",
        "img/BAM-Logo-WhiteText.svg",
        "img/BAM-OurWork-BaltimoreOriole.jpg",
        "vignettes/BAMexploreR_1_intro.html",
        "vignettes/BAMexploreR_2_access.html",
        "vignettes/BAMexploreR_3_distribution.html",
        "vignettes/BAMexploreR_4_habitat.html",
    )
    for relative in paths:
        target = APP_DIR / "www" / relative
        if not target.is_file():
            errors.append(f"{target.relative_to(REPO_DIR)}: missing static asset")


def main() -> int:
    """Run all checks and return a process exit code."""
    errors: list[str] = []
    check_python(errors)
    check_quartodoc(errors)
    check_images(errors)
    check_audio(errors)
    check_static_assets(errors)

    if errors:
        print("Repository integrity check failed:")
        for error in sorted(set(errors)):
            print(f"- {error}")
        return 1

    print("Repository integrity check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
