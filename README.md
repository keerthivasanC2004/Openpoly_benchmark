# AI for Polymers — Researcher Radar

A clean, responsive dashboard for tracking professors, principal investigators, and emerging researchers working at the intersection of artificial intelligence and polymer science.

## Live dashboard

After GitHub Pages is enabled, the site is published at:

**https://keerthivasanc2004.github.io/AI-for-polymers/**

## Features

- Search by researcher, institution, or topic.
- Filter by influence tier, region, and verification status.
- Responsive light/dark interface with no JavaScript framework or CDN dependency.
- Daily publication discovery through the OpenAlex API.
- Conservative author disambiguation using researcher names and institutional signals.
- Automated tests before every deployment.
- GitHub Pages deployment on every relevant push and daily at 03:15 UTC (06:15 Asia/Riyadh).

## Data quality

The initial researcher list was seeded from a user-supplied compilation and reviewed where reliable evidence was available. Ambiguous identities and uncertain affiliations are explicitly marked **Needs review** instead of being silently presented as verified.

The daily feed is intended for discovery. OpenAlex metadata can contain author, affiliation, or venue errors, so important records should be confirmed at the DOI or publisher page.

## Local preview

```bash
python -m http.server 8000
```

Then open `http://localhost:8000`.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Refresh the publication feed

```bash
python scripts/update_updates.py --lookback-days 120 --per-author 3 --max-items 60
```

The updater uses only Python's standard library and writes `data/updates.json`.

## Publishing

The workflow in `.github/workflows/pages.yml` validates the updater, refreshes the publication feed, and deploys the repository root to GitHub Pages.

In the repository settings, select **Pages → Build and deployment → Source → GitHub Actions** if it is not already enabled.
