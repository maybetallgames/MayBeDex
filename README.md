# MayBeDex

Public, machine-readable Synty prefab catalog for the MayBeTall Games Unity project.

This repository is generated from prefab preview/catalog data produced by the private `LetsDive` project. It intentionally contains only generated asset metadata, thumbnails, preview images, and static-site files — never game source code.

## Stable endpoints

Once GitHub Pages is enabled, the site is intended to expose:

- `/catalog.json` — complete machine-readable catalog
- `/catalog.tsv` — compact lookup-first catalog
- `/packs/<pack>.json` — per-pack indexes
- `/prefabs/<guid>/` — one crawlable page per prefab
- `/thumbs/<guid>.jpg` — small AI/search thumbnail
- `/images/<guid>.jpg` — higher-quality preview

The Unity-side generator should use each prefab's Unity GUID as the permanent public identifier so asset renames and folder moves do not break URLs.
