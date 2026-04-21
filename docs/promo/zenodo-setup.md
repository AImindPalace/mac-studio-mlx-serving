# Enable Zenodo DOI for this repo

Your sister repo (`dgx-spark-nvfp4-serving`) already has a Zenodo DOI (`10.5281/zenodo.19673102`), but the new one doesn't — because **Zenodo integration is per-repo**, not per-account. You have to toggle it on individually.

## Why nothing archived from the v0.1.0 release

Zenodo's GitHub integration uses a **webhook** on each repo. The webhook fires on every GitHub release and Zenodo mints a new DOI version. Since we published v0.1.0 **before** enabling the webhook, that release isn't archived. Fixing that means cutting a new release (v0.1.1) after enabling the integration.

## Exact steps

1. Go to **https://zenodo.org/account/settings/github/**
2. Sign in if prompted (use the same GitHub account you used for the Spark repo — `AImindPalace`)
3. You'll see a list of your GitHub repos. Find **`AImindPalace/mac-studio-mlx-serving`** — it may say "Sync now" if it's new
4. Flip the toggle from off → **on**
5. Tell me when done. I'll cut a `v0.1.1` release on the Mac repo which will trigger Zenodo to mint a DOI

## After it's done

Zenodo will assign two DOIs:
- **Concept DOI** — always points at the latest version (use this in papers / permanent links)
- **Version DOI** — specific to v0.1.1

I'll add both to `CITATION.cff` and the README badge row, mirroring the Spark repo's layout.

## Linking the two DOIs

Once both repos have DOIs, we add a `related-identifiers` entry in each `CITATION.cff` pointing at the other. The Spark repo already does this (pointing at the Mac repo DOI after we add it). Standard way to express "these two artifacts are companions" in the scholarly-metadata world.
