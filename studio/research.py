import re
from datetime import datetime, timezone
from urllib.parse import urlparse
from .common import ROOT, StudioError, download, digest, save_json


FEEDS = ["https://feeds.bbci.co.uk/news/world/rss.xml", "https://feeds.bbci.co.uk/news/business/rss.xml",
         "https://www.theguardian.com/world/rss", "https://www.aljazeera.com/xml/rss/all.xml",
         "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml"]


def words(text):
    return set(re.findall(r"[a-z]{3,}", text.lower())) - {"the", "and", "for", "with", "from", "that", "this", "has", "are", "was", "news", "why", "how"}


def similar(a, b):
    x, y = words(a), words(b)
    return len(x & y) / max(1, min(len(x), len(y)))


def discover(brain, history, cache):
    import feedparser
    candidates = []
    previous = [x.get("topic", "") for x in history.get("videos", [])][-80:]
    # Respect the original project history too; no channel/history reset.
    previous += history.get("legacy_titles", [])
    for i, url in enumerate(FEEDS):
        try:
            path = download(url, cache / f"feed_{i}.xml", 3_000_000)
            for item in feedparser.parse(path.read_bytes()).entries[:16]:
                dt = item.get("published_parsed")
                if not dt:
                    continue
                age = datetime.now(timezone.utc).timestamp() - __import__("calendar").timegm(dt)
                if not -3600 <= age <= 48 * 3600:
                    continue
                title = item.title
                if any(similar(title, old) > 0.73 for old in previous):
                    continue
                candidates.append({"title": title, "url": item.link, "published": item.get("published", "")})
        except Exception:
            continue
    if not candidates:
        raise StudioError("No fresh, non-repeating news candidates; no filler video generated")
    choice = brain.json("Choose ONE well-supported globally relevant documentary topic. Prefer a concrete event "
        "with an explainable mechanism, human stakes and available real visual material. Avoid rumor-only headlines. "
        "Do not force a US angle onto local stories. Return {candidate_index: integer, reason: string}.",
        {"candidates": candidates, "recent_topics": previous[-15:]})
    index = choice.get("candidate_index")
    if not isinstance(index, int) or not 0 <= index < len(candidates):
        raise StudioError("Invalid topic selection")
    return candidates[index]["title"], [candidates[index]["url"]]


def collect_sources(topic, seed_urls, cache, max_sources=8):
    from ddgs import DDGS
    import trafilatura
    urls = list(seed_urls)
    try:
        for query in [topic, topic + " official report data statement"]:
            urls += [r["href"] for r in DDGS(timeout=15).text(query, max_results=8)]
    except Exception:
        pass
    sources, seen = [], set()
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        try:
            path = download(url, cache / (digest(url) + ".html"), 5_000_000)
            doc = trafilatura.bare_extraction(path.read_bytes(), url=url, include_comments=False,
                                             include_tables=True, favor_precision=True)
            if not doc:
                continue
            def get(k):
                return doc.get(k) if isinstance(doc, dict) else getattr(doc, k, None)
            text = get("text") or ""
            if len(text.split()) < 160:
                continue
            sources.append({"id": f"S{len(sources)+1}", "url": url, "title": get("title") or topic,
                "published": str(get("date") or "unknown"), "domain": urlparse(url).hostname,
                "retrieved_utc": datetime.now(timezone.utc).isoformat(), "text": text[:18000]})
            if len(sources) >= max_sources:
                break
        except Exception:
            continue
    if len({s["domain"] for s in sources}) < 3:
        raise StudioError("Need full readable reporting from at least 3 domains; headlines alone are insufficient")
    save_json(cache / "sources.json", sources)
    return sources


def norm(text):
    return re.sub(r"\s+", " ", text).strip().casefold()


def validate_facts(facts, sources):
    source_map = {s["id"]: s for s in sources}
    ids = set()
    for f in facts:
        if not f.get("id") or f["id"] in ids:
            raise StudioError("Duplicate/missing fact ID")
        ids.add(f["id"])
        if not f.get("evidence") or not f.get("claim"):
            raise StudioError("Fact lacks evidence")
        for e in f["evidence"]:
            if e.get("source_id") not in source_map:
                raise StudioError("Fact references unknown source")
            quote = e.get("quote", "")
            if len(quote.split()) < 4 or len(quote.split()) > 45 or norm(quote) not in norm(source_map[e["source_id"]]["text"]):
                raise StudioError("Evidence excerpt does not occur verbatim in the fetched source")
    return facts


def research(topic, sources, brain):
    result = brain.json("Extract 22-35 DISTINCT useful facts for an English documentary. Separate reported facts, "
        "attributed claims and uncertainty. Conflicting reports must remain attributed. Include a chronology, "
        "mechanism, exact useful numbers WITH units/periods, and what is not known. Do not pad weak reporting. "
        "Return {facts:[{id:'F1',claim:'paraphrase',status:'reported|attributed|uncertain', "
        "evidence:[{source_id:'S1',quote:'verbatim 4-45 word excerpt'}]}], open_questions:[string]}.",
        {"topic": topic, "sources": sources})
    facts = validate_facts(result.get("facts", []), sources)
    if len(facts) < 16:
        raise StudioError("Research has too few supported facts for a full documentary")
    audit = brain.json("Independently audit EVERY claim against its excerpts. Reject exaggeration, missing "
        "attribution, inference presented as fact, contradictory numbers and dates. Return "
        "{accepted_ids:[fact IDs], rejected:[{id,reason}]}. An excerpt must actually support the claim.", {"facts": facts})
    accepted = set(audit.get("accepted_ids", []))
    facts = [f for f in facts if f["id"] in accepted]
    if len(facts) < 16:
        raise StudioError("Evidence audit rejected too many claims; publication blocked")
    return {"topic": topic, "facts": facts, "sources": sources, "open_questions": result.get("open_questions", []),
            "audit": audit}
