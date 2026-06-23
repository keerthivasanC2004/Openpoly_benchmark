#!/usr/bin/env python3
"""Build the dashboard's recent-publication feed from OpenAlex.

The script intentionally uses only Python's standard library so the scheduled
GitHub Pages build has no package-install step and fewer failure modes.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESEARCHERS = ROOT / "data" / "researchers-meta.json"
DEFAULT_OUTPUT = ROOT / "data" / "feed.json"
OPENALEX = "https://api.openalex.org"
POLITE_EMAIL = "keerthivasan.chinnasamy@kaust.edu.sa"

RELEVANCE_TERMS = {
    "polymer": 5, "polymers": 5, "polymeric": 5, "macromolecule": 4,
    "plastic": 3, "elastomer": 4, "membrane": 2, "mechanophore": 4,
    "machine learning": 3, "deep learning": 3, "artificial intelligence": 3,
    "informatics": 3, "generative": 2, "autonomous": 2, "self-driving": 3,
    "high-throughput": 2, "property prediction": 3, "materials discovery": 2,
}


def normalize(text: str | None) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def json_request(path: str, params: dict[str, Any], retries: int = 2, timeout: int = 15) -> dict[str, Any]:
    query = urllib.parse.urlencode({**params, "mailto": POLITE_EMAIL}, doseq=True)
    url = f"{OPENALEX}{path}?{query}"
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": f"PolymerAIRadar/1.0 (mailto:{POLITE_EMAIL})"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.load(response)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            if attempt == retries - 1:
                raise RuntimeError(f"OpenAlex request failed after {retries} attempts: {url}") from exc
            time.sleep(1.5 * (attempt + 1))
    raise AssertionError("unreachable")


def candidate_score(researcher: dict[str, Any], candidate: dict[str, Any]) -> int:
    target = normalize(researcher.get("name")); display = normalize(candidate.get("display_name")); score = 0
    if display == target: score += 12
    elif target and (target in display or display in target): score += 7
    score += len(set(target.split()) & set(display.split())) * 2
    tokens = [normalize(x) for x in researcher.get("institution_tokens", [])]
    institutions = [normalize(x.get("display_name")) for x in candidate.get("last_known_institutions") or []]
    for affiliation in candidate.get("affiliations") or []:
        institution = affiliation.get("institution") or {}
        institutions.append(normalize(institution.get("display_name")))
    for token in tokens:
        if token and any(token in institution for institution in institutions): score += 5
    if candidate.get("works_count", 0) >= 10: score += 1
    return score


def select_author(researcher: dict[str, Any], candidates: Iterable[dict[str, Any]]) -> tuple[dict[str, Any] | None, int]:
    ranked = sorted(((candidate_score(researcher, c), c) for c in candidates), key=lambda x: x[0], reverse=True)
    if not ranked or ranked[0][0] < 10: return None, ranked[0][0] if ranked else 0
    return ranked[0][1], ranked[0][0]


def text_for_work(work: dict[str, Any]) -> str:
    concepts = " ".join(x.get("display_name", "") for x in work.get("concepts") or [])
    topics = " ".join(x.get("display_name", "") for x in work.get("topics") or [])
    return normalize(" ".join([work.get("title") or "", concepts, topics]))


def relevance_score(work: dict[str, Any]) -> int:
    text = text_for_work(work)
    return sum(weight for term, weight in RELEVANCE_TERMS.items() if normalize(term) in text)


def work_url(work: dict[str, Any]) -> str:
    doi = work.get("doi")
    if doi: return doi if doi.startswith("http") else f"https://doi.org/{doi}"
    return (work.get("primary_location") or {}).get("landing_page_url") or work.get("id") or "https://openalex.org"


def venue_name(work: dict[str, Any]) -> str:
    source = ((work.get("primary_location") or {}).get("source") or {})
    return source.get("display_name") or work.get("type_crossref") or work.get("type") or "Publication"


def author_label(work: dict[str, Any]) -> str:
    names = [(a.get("author") or {}).get("display_name") for a in work.get("authorships") or []]
    names = [x for x in names if x]
    return ", ".join(names[:3]) + (" et al." if len(names) > 4 else "")


def fetch_researcher_updates(researcher: dict[str, Any], since: str, per_author: int) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    if researcher.get("verification") == "needs_review" and not researcher.get("institution_tokens"):
        return [], {"researcher_id": researcher["id"], "name": researcher["name"], "reason": "identity or affiliation requires review"}
    author_payload = json_request("/authors", {"search": researcher["name"], "per-page": 6})
    author, score = select_author(researcher, author_payload.get("results") or [])
    if not author:
        return [], {"researcher_id": researcher["id"], "name": researcher["name"], "reason": f"author disambiguation score too low ({score})"}
    author_id = str(author.get("id", "")).rsplit("/", 1)[-1]
    work_payload = json_request("/works", {"filter": f"authorships.author.id:{author_id},from_publication_date:{since}", "sort": "publication_date:desc", "per-page": max(10, min(50, per_author * 4))})
    selected = []
    for work in work_payload.get("results") or []:
        score_value = relevance_score(work)
        if score_value < 5: continue
        selected.append({"researcher_id": researcher["id"], "author": author_label(work) or researcher["name"], "title": work.get("title") or "Untitled publication", "publication_date": work.get("publication_date") or str(work.get("publication_year") or ""), "venue": venue_name(work), "url": work_url(work), "relevance": f"Automated polymer/AI relevance score: {score_value}", "confidence": "high" if score >= 15 else "medium", "openalex_author_id": author_id, "openalex_work_id": str(work.get("id", "")).rsplit("/", 1)[-1]})
        if len(selected) >= per_author: break
    return selected, None


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle: return json.load(handle)


def build_feed(researchers_path: Path, output_path: Path, lookback_days: int, per_author: int, max_items: int) -> dict[str, Any]:
    profile_data = load_json(researchers_path)
    researchers = profile_data.get("researchers") or []
    if not researchers:
        researchers = []
        for chunk_path in sorted(researchers_path.parent.glob("researchers-[0-9]*.json")):
            researchers.extend(load_json(chunk_path).get("researchers") or [])
    since = (dt.date.today() - dt.timedelta(days=lookback_days)).isoformat()
    items, unresolved, failures = [], [], []
    try: json_request("/works", {"per-page": 1}, retries=1, timeout=10)
    except RuntimeError as exc:
        failures.append(f"OpenAlex health check failed: {exc}")
        previous = load_json(output_path) if output_path.exists() else {}
        payload = {"generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"), "status": "fallback" if previous.get("items") else "degraded", "source": "OpenAlex API", "lookback_days": lookback_days, "unresolved": [], "failures": failures, "items": previous.get("items", [])}
        output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"); return payload
    for researcher in researchers:
        try:
            found, unresolved_item = fetch_researcher_updates(researcher, since, per_author); items.extend(found)
            if unresolved_item: unresolved.append(unresolved_item)
        except RuntimeError as exc: failures.append(f"{researcher.get('name')}: {exc}")
        time.sleep(0.08)
    unique = {}
    for item in items:
        key = item.get("openalex_work_id") or normalize(item.get("title"))
        if key not in unique or item.get("confidence") == "high": unique[key] = item
    items = sorted(unique.values(), key=lambda x: x.get("publication_date") or "", reverse=True)[:max_items]
    previous = load_json(output_path) if output_path.exists() else {}
    status = "live" if items else "degraded"
    if not items and previous.get("items"): items, status = previous["items"], "fallback"
    payload = {"generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"), "status": status, "source": "OpenAlex API", "lookback_days": lookback_days, "unresolved": unresolved, "failures": failures, "items": items}
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"); return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--researchers", type=Path, default=DEFAULT_RESEARCHERS); parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--lookback-days", type=int, default=120); parser.add_argument("--per-author", type=int, default=3); parser.add_argument("--max-items", type=int, default=60)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.lookback_days < 1 or args.per_author < 1 or args.max_items < 1: raise SystemExit("Numeric arguments must be positive.")
    payload = build_feed(args.researchers, args.output, args.lookback_days, args.per_author, args.max_items)
    print(f"Wrote {len(payload['items'])} updates to {args.output} ({payload['status']})."); return 0


if __name__ == "__main__": raise SystemExit(main())
