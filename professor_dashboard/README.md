# Polymer AI Researcher Radar

A dependency-free, responsive dashboard for tracking professors, PIs and emerging researchers working at the intersection of artificial intelligence and polymer science.

## Features

- Search by researcher, institution or topic.
- Filter by tier, region and verification status.
- Responsive light/dark interface with no JavaScript framework or CDN dependency.
- Daily publication scan through the OpenAlex API.
- Conservative author disambiguation using name and institution signals.
- Automated unit tests before every deployment.
- GitHub Pages deployment on pushes and every day at 03:15 UTC (06:15 Asia/Riyadh).

## Data quality

The initial profile list was seeded from a user-supplied compilation. Current affiliations were corrected where reliable evidence was available. Ambiguous names and uncertain affiliations are visibly marked `Needs review`; they are not silently treated as verified.

The daily update feed is intended for discovery. OpenAlex records can contain author or venue metadata errors, so important items should be verified at the DOI or publisher page.

## Local preview

From the repository root:

```bash
python -m http.server 8000 --directory professor_dashboard
```

Open `http://localhost:8000`.

## Tests

```bash
python -m unittest discover -s professor_dashboard/tests -v
```

## Refresh the publication feed

```bash
python professor_dashboard/scripts/update_updates.py
```

The updater uses only Python's standard library and writes `professor_dashboard/data/updates.json`.

## Publishing

The included workflow deploys the `professor_dashboard` directory to GitHub Pages. In the repository settings, set **Pages → Build and deployment → Source** to **GitHub Actions** once if it is not already enabled.
