#!/usr/bin/env python3
"""Build the MayBeDex static site from a LetsDive prefab catalog export.

Expected input mirrors the contents of LetsDive/PrefabPreviews/Synty:

catalog-source/
  _lookup.tsv
  _catalog.json                 (optional)
  PolygonMilitary/...jpg
  PolygonParticleFX/...jpg
  _ai/...jpg.b64

The generated _site/ directory is suitable for GitHub Pages. Public URLs use
Unity GUIDs so moving or renaming a prefab in Unity does not break links.
"""

from __future__ import annotations

import base64
import csv
import html
import json
import os
import re
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "catalog-source"
LOOKUP = SOURCE / "_lookup.tsv"
SITE_SOURCE = ROOT / "site-src"
SITE = ROOT / "_site"
BASE_URL = "https://maybetallgames.github.io/MayBeDex"
EXPORT_PREFIX = "PrefabPreviews/Synty/"
SCHEMA_VERSION = 1


def clean_site() -> None:
    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir(parents=True)
    shutil.copy2(SITE_SOURCE / "index.html", SITE / "index.html")
    shutil.copytree(SITE_SOURCE / "assets", SITE / "assets")
    (SITE / ".nojekyll").write_text("", encoding="utf-8")


def parse_int(value: str) -> int:
    try:
        return int(value or 0)
    except ValueError:
        return 0


def parse_bounds(value: str) -> List[float]:
    output: List[float] = []
    for part in (value or "").split(",")[:3]:
        try:
            output.append(float(part))
        except ValueError:
            output.append(0.0)
    while len(output) < 3:
        output.append(0.0)
    return output


def export_relative(value: str) -> Path:
    normalized = (value or "").replace("\\", "/").lstrip("/")
    if normalized.startswith(EXPORT_PREFIX):
        normalized = normalized[len(EXPORT_PREFIX):]
    return Path(*[part for part in normalized.split("/") if part not in ("", ".", "..")])


def slug(value: str) -> str:
    result = re.sub(r"[^A-Za-z0-9._-]+", "-", value or "Unknown").strip("-._")
    return result or "Unknown"


def tokens(*values: str) -> List[str]:
    text = " ".join(value or "" for value in values)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    bits = re.split(r"[^A-Za-z0-9]+", text.lower())
    stop = {"assets", "synty", "prefab", "prefabs", "models", "model"}
    return sorted({bit for bit in bits if len(bit) >= 2 and bit not in stop})


def read_rows() -> List[Dict[str, str]]:
    if not LOOKUP.exists():
        raise SystemExit(f"Missing lookup file: {LOOKUP}")
    with LOOKUP.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    return [row for row in rows if row.get("guid") and row.get("name")]


def copy_full_image(row: Dict[str, str], guid: str) -> str:
    source_path = SOURCE / export_relative(row.get("imagePath", ""))
    if not source_path.is_file():
        return ""
    destination = SITE / "images" / f"{guid}.jpg"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, destination)
    return f"images/{guid}.jpg"


def write_thumbnail(row: Dict[str, str], guid: str, fallback_image: str) -> str:
    sidecar = SOURCE / export_relative(row.get("aiPreviewPath", ""))
    destination = SITE / "thumbs" / f"{guid}.jpg"
    destination.parent.mkdir(parents=True, exist_ok=True)

    if sidecar.is_file():
        try:
            raw = base64.b64decode(sidecar.read_text(encoding="utf-8").strip(), validate=True)
            destination.write_bytes(raw)
            return f"thumbs/{guid}.jpg"
        except Exception as exc:  # Build should still succeed if one sidecar is corrupt.
            print(f"warning: could not decode {sidecar}: {exc}")

    if fallback_image:
        source = SITE / fallback_image
        if source.is_file():
            shutil.copy2(source, destination)
            return f"thumbs/{guid}.jpg"
    return ""


def make_entry(row: Dict[str, str]) -> Dict[str, object]:
    guid = row["guid"].strip()
    components = [part.strip() for part in (row.get("componentHints") or "").split(",") if part.strip()]
    image = copy_full_image(row, guid)
    thumbnail = write_thumbnail(row, guid, image)
    item_tags = tokens(
        row.get("name", ""),
        row.get("pack", ""),
        row.get("kind", ""),
        row.get("assetPath", ""),
        row.get("componentHints", ""),
    )
    search_text = " ".join(
        [row.get("name", ""), row.get("pack", ""), row.get("kind", ""), row.get("assetPath", "")]
        + components
        + item_tags
    ).lower()

    return {
        "guid": guid,
        "name": row.get("name", ""),
        "pack": row.get("pack", ""),
        "kind": row.get("kind", "") or "prefab",
        "assetPath": row.get("assetPath", ""),
        "page": f"prefabs/{guid}/",
        "thumbnail": thumbnail,
        "image": image,
        "particles": parse_int(row.get("particles", "0")),
        "renderers": parse_int(row.get("renderers", "0")),
        "skinned": parse_int(row.get("skinned", "0")),
        "lods": parse_int(row.get("lods", "0")),
        "colliders": parse_int(row.get("colliders", "0")),
        "bounds": parse_bounds(row.get("boundsXYZ", "")),
        "dependencyHash": row.get("dependencyHash", ""),
        "components": components,
        "tags": item_tags,
        "searchText": search_text,
    }


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def tsv_cell(value: object) -> str:
    if isinstance(value, list):
        value = ",".join(str(item) for item in value)
    return str(value if value is not None else "").replace("\t", " ").replace("\r", " ").replace("\n", " ")


def write_public_tsv(path: Path, entries: Iterable[Dict[str, object]]) -> None:
    columns = ["guid", "name", "pack", "kind", "assetPath", "page", "thumbnail", "image", "particles", "renderers", "components"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(columns)
        for item in entries:
            writer.writerow([tsv_cell(item.get(column, "")) for column in columns])


def prefab_page(item: Dict[str, object]) -> str:
    name = html.escape(str(item["name"]))
    pack = html.escape(str(item["pack"]))
    kind = html.escape(str(item["kind"]))
    asset_path = html.escape(str(item["assetPath"]))
    guid = html.escape(str(item["guid"]))
    components = html.escape(", ".join(item.get("components", [])) or "—")
    tags = html.escape(", ".join(item.get("tags", [])) or "—")
    bounds = html.escape(" × ".join(f"{value:g}" for value in item.get("bounds", [0, 0, 0])))
    image_html = ""
    if item.get("image"):
        image_html = f'<a href="../../{html.escape(str(item["image"]))}"><img class="prefab-image" src="../../{html.escape(str(item["image"]))}" alt="{name} prefab preview"></a>'
    elif item.get("thumbnail"):
        image_html = f'<img class="prefab-image" src="../../{html.escape(str(item["thumbnail"]))}" alt="{name} prefab preview">'

    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="description" content="{name} — {pack} Synty prefab in MayBeDex.">
  <title>{name} — MayBeDex</title>
  <link rel="stylesheet" href="../../assets/styles.css">
</head>
<body>
  <main class="prefab-page">
    <nav class="prefab-nav"><a href="../../">← MayBeDex</a> · <a href="../../packs/{slug(str(item['pack']))}.json">pack JSON</a></nav>
    <p class="eyebrow">{pack} · {kind}</p>
    <h1>{name}</h1>
    <div class="prefab-layout">
      <div>{image_html}</div>
      <dl class="meta">
        <dt>Unity GUID</dt><dd><code>{guid}</code></dd>
        <dt>Pack</dt><dd>{pack}</dd>
        <dt>Kind</dt><dd>{kind}</dd>
        <dt>Asset path</dt><dd><code>{asset_path}</code></dd>
        <dt>Particles</dt><dd>{item['particles']}</dd>
        <dt>Renderers</dt><dd>{item['renderers']}</dd>
        <dt>Skinned</dt><dd>{item['skinned']}</dd>
        <dt>LOD groups</dt><dd>{item['lods']}</dd>
        <dt>Colliders</dt><dd>{item['colliders']}</dd>
        <dt>Bounds</dt><dd>{bounds}</dd>
        <dt>Components</dt><dd>{components}</dd>
        <dt>Search tags</dt><dd>{tags}</dd>
      </dl>
    </div>
  </main>
</body>
</html>
'''


def build() -> None:
    clean_site()
    rows = read_rows()
    entries = [make_entry(row) for row in rows]
    entries.sort(key=lambda item: (str(item["pack"]).lower(), str(item["name"]).lower(), str(item["guid"])))

    write_json(SITE / "catalog.json", {"schemaVersion": SCHEMA_VERSION, "entries": entries})
    write_public_tsv(SITE / "catalog.tsv", entries)

    by_pack: Dict[str, List[Dict[str, object]]] = defaultdict(list)
    for item in entries:
        by_pack[str(item["pack"])].append(item)
        page_dir = SITE / "prefabs" / str(item["guid"])
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir / "index.html").write_text(prefab_page(item), encoding="utf-8")

    pack_index = []
    for pack_name, pack_entries in sorted(by_pack.items(), key=lambda pair: pair[0].lower()):
        pack_slug = slug(pack_name)
        write_json(SITE / "packs" / f"{pack_slug}.json", {"pack": pack_name, "entries": pack_entries})
        write_public_tsv(SITE / "packs" / f"{pack_slug}.tsv", pack_entries)
        pack_index.append({"pack": pack_name, "slug": pack_slug, "count": len(pack_entries)})
    write_json(SITE / "packs" / "index.json", pack_index)

    generated = datetime.now(timezone.utc).isoformat()
    source_info = {}
    source_info_path = SOURCE / "_catalog.json"
    if source_info_path.is_file():
        try:
            source_info = json.loads(source_info_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    version = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedUtc": generated,
        "prefabCount": len(entries),
        "packCount": len(by_pack),
        "baseUrl": BASE_URL,
        "sourceRevision": os.environ.get("GITHUB_SHA", "local"),
        "unityCatalog": source_info,
    }
    write_json(SITE / "version.json", version)

    sitemap_urls = [f"{BASE_URL}/"] + [f"{BASE_URL}/{item['page']}" for item in entries]
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sitemap += "".join(f"  <url><loc>{html.escape(url)}</loc></url>\n" for url in sitemap_urls)
    sitemap += "</urlset>\n"
    (SITE / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    (SITE / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}/sitemap.xml\n", encoding="utf-8")

    total_bytes = sum(path.stat().st_size for path in SITE.rglob("*") if path.is_file())
    print(f"Built MayBeDex: {len(entries)} prefabs, {len(by_pack)} packs, {total_bytes / 1024 / 1024:.1f} MiB")
    if total_bytes > 900 * 1024 * 1024:
        print("warning: generated site exceeds 900 MiB and is approaching the GitHub Pages 1 GiB published-site limit")


if __name__ == "__main__":
    build()
