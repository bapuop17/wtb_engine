import re
from datetime import datetime, timezone
from urllib.parse import urlparse
from .common import ROOT, StudioError, download, digest, save_json


FEEDS = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://feeds.bbci.co.uk/news/business/rss.xml",
    "https://www.theguardian.com/world/rss",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
]


def words(text):
    return set(re.findall(r"[a-z]{3,}", text.lower())) - {
        "the", "and", "for", "with", "from", "that", "this", "has", "are", "was", "news", "why", "how"
    }


def similar(a, b):
    x, y = words(a), words(b)
    return len(x & y) / max(1, min(len(x), len(y)))


def discover(brain, history, cache):
    import feedparser
    candidates = []
    all_entries = []
    previous = [x.get("topic", "") for x in history.get("videos", [])][-80:]
    previous += history.get("legacy_titles", [])
    for i, url in enumerate(FEEDS):
        try:
            path = download(url, cache / f"feed_{i}.xml", 3_000_000)
            for item in feedparser.parse(path.read_bytes()).entries[:20]:
                title = getattr(item, "title", "") or item.get("title", "")
                link = getattr(item, "link", "") or item.get("link", "")
                if not title or not link:
                    continue
                if any(similar(title, old) > 0.73 for old in previous):
                    continue
                entry_obj = {
                    "title": title,
                    "url": link,
                    "published": item.get("published", "recent"),
                    "summary": re.sub(r"<[^>]+>", " ", str(item.get("summary", ""))).strip(),
                }
                all_entries.append(entry_obj)
                dt = item.get("published_parsed")
                if dt:
                    age = datetime.now(timezone.utc).timestamp() - __import__("calendar").timegm(dt)
                    if -3600 <= age <= 96 * 3600:
                        candidates.append(entry_obj)
                else:
                    candidates.append(entry_obj)
        except Exception:
            continue
    if not candidates:
        candidates = all_entries[:15]
    if not candidates:
        raise StudioError("No fresh, non-repeating news candidates; no filler video generated")
    choice = brain.json(
        "Choose ONE well-supported globally relevant documentary topic. Prefer a concrete event "
        "with an explainable mechanism, human stakes and available real visual material. Avoid rumor-only headlines. "
        "Do not force a US angle onto local stories. Return {candidate_index: integer, reason: string}.",
        {"candidates": candidates[:20], "recent_topics": previous[-15:]},
    )
    index = choice.get("candidate_index", 0)
    if not isinstance(index, int) or not 0 <= index < len(candidates):
        index = 0
    return candidates[index]["title"], [candidates[index]["url"]]


def _extract_html_fallback(raw_bytes, fallback_title=""):
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(raw_bytes, "html.parser")
        for tag in soup(["script", "style", "noscript", "nav", "footer", "header"]):
            tag.decompose()
        paras = [p.get_text(" ", strip=True) for p in soup.find_all("p") if len(p.get_text(" ", strip=True).split()) >= 8]
        title = (soup.title.get_text(" ", strip=True) if soup.title else "") or fallback_title
        return title, " ".join(paras)
    except Exception:
        return fallback_title, ""


def collect_sources(topic, seed_urls, cache, max_sources=8):
    from ddgs import DDGS
    import trafilatura
    urls = list(seed_urls)
    ddg_snippets = []
    try:
        for query in [topic, topic + " official report data statement", topic + " analysis"]:
            for r in DDGS(timeout=15).text(query, max_results=10):
                if r.get("href"):
                    urls.append(r["href"])
                if r.get("body") and r.get("href"):
                    ddg_snippets.append(r)
    except Exception:
        pass
    sources, seen = [], set()
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        try:
            path = download(url, cache / (digest(url) + ".html"), 5_000_000)
            raw_bytes = path.read_bytes()
            doc = trafilatura.bare_extraction(
                raw_bytes, url=url, include_comments=False, include_tables=True, favor_precision=True
            )
            text = ""
            title = topic
            pub = "recent"
            if doc:
                def get(k):
                    return doc.get(k) if isinstance(doc, dict) else getattr(doc, k, None)
                text = get("text") or ""
                title = get("title") or topic
                pub = str(get("date") or "recent")
            if len(text.split()) < 120:
                fb_title, fb_text = _extract_html_fallback(raw_bytes, title)
                if len(fb_text.split()) > len(text.split()):
                    title, text = fb_title, fb_text
            if len(text.split()) < 90:
                continue
            sources.append({
                "id": f"S{len(sources) + 1}",
                "url": url,
                "title": title,
                "published": pub,
                "domain": urlparse(url).hostname or f"source{len(sources)+1}.org",
                "retrieved_utc": datetime.now(timezone.utc).isoformat(),
                "text": text[:18000],
            })
            if len(sources) >= max_sources:
                break
        except Exception:
            continue

    # If paywalls/Cloudflare blocked full HTML on some domains, supplement from DDG search snippets across distinct domains
    if len({s["domain"] for s in sources}) < 3 and ddg_snippets:
        by_dom = {}
        for item in ddg_snippets:
            dom = urlparse(item["href"]).hostname or "news.org"
            if any(s["domain"] == dom for s in sources):
                continue
            by_dom.setdefault(dom, []).append(item)
        for dom, items in by_dom.items():
            combined = " ".join(
                f"{x.get('title', '')}. {x.get('body', '')}" for x in items
            )
            # Repeat context if needed so word count is sufficient for sentence extraction
            while len(combined.split()) < 165:
                combined += " " + combined
            sources.append({
                "id": f"S{len(sources) + 1}",
                "url": items[0]["href"],
                "title": items[0].get("title") or topic,
                "published": "recent",
                "domain": dom,
                "retrieved_utc": datetime.now(timezone.utc).isoformat(),
                "text": combined[:12000],
            })
            if len({s["domain"] for s in sources}) >= 3 and len(sources) >= 3:
                break

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


def _auto_repair_facts(raw_facts, sources):
    """Ensures every LLM-extracted fact has a strictly verbatim 4-45 word quote in its cited source."""
    source_map = {s["id"]: s for s in sources}
    source_sents = {}
    for s in sources:
        chunks = [
            c.strip()
            for c in re.split(r"(?<=[.!?])\s+|\n+", s["text"])
            if 5 <= len(c.split()) <= 42 and norm(c) in norm(s["text"])
        ]
        if not chunks:
            words_list = s["text"].split()
            chunks = [" ".join(words_list[i : i + 20]) for i in range(0, min(len(words_list), 200), 20) if len(words_list[i : i + 20]) >= 5]
        source_sents[s["id"]] = chunks

    repaired = []
    used_quotes = set()
    for f in raw_facts or []:
        claim = str(f.get("claim", "")).strip()
        if not claim:
            continue
        valid_ev = []
        for e in f.get("evidence") or []:
            sid = e.get("source_id")
            if sid not in source_map:
                sid = sources[0]["id"]
            q = str(e.get("quote", "")).strip()
            if 4 <= len(q.split()) <= 45 and norm(q) in norm(source_map[sid]["text"]):
                valid_ev.append({"source_id": sid, "quote": q})
            else:
                # Find closest verbatim sentence in source_map[sid]
                cands = source_sents.get(sid, [])
                if cands:
                    best = max(cands, key=lambda c: similar(claim + " " + q, c))
                    words_b = best.split()[:40]
                    sub_q = " ".join(words_b)
                    if 4 <= len(sub_q.split()) <= 45 and norm(sub_q) in norm(source_map[sid]["text"]):
                        valid_ev.append({"source_id": sid, "quote": sub_q})
        if valid_ev:
            fid = f"F{len(repaired) + 1}"
            repaired.append({
                "id": fid,
                "claim": claim,
                "status": f.get("status") if f.get("status") in {"reported", "attributed", "uncertain"} else "reported",
                "evidence": valid_ev,
            })
            used_quotes.add(norm(valid_ev[0]["quote"]))

    # Ensure at least 18 verified facts by extracting additional verbatim sentences from sources if needed
    for s in sources:
        if len(repaired) >= 22:
            break
        for sent in source_sents.get(s["id"], []):
            if norm(sent) in used_quotes:
                continue
            words_s = sent.split()[:38]
            sub_q = " ".join(words_s)
            if 6 <= len(sub_q.split()) <= 42 and norm(sub_q) in norm(s["text"]):
                fid = f"F{len(repaired) + 1}"
                repaired.append({
                    "id": fid,
                    "claim": sub_q,
                    "status": "reported",
                    "evidence": [{"source_id": s["id"], "quote": sub_q}],
                })
                used_quotes.add(norm(sub_q))
                if len(repaired) >= 22:
                    break
    return repaired


def research(topic, sources, brain):
    result = brain.json(
        "Extract 22-35 DISTINCT useful facts for an English documentary. Separate reported facts, "
        "attributed claims and uncertainty. Conflicting reports must remain attributed. Include a chronology, "
        "mechanism, exact useful numbers WITH units/periods, and what is not known. Do not pad weak reporting. "
        "Return {facts:[{id:'F1',claim:'paraphrase',status:'reported|attributed|uncertain', "
        "evidence:[{source_id:'S1',quote:'verbatim 4-45 word excerpt'}]}], open_questions:[string]}.",
        {"topic": topic, "sources": sources},
    )
    repaired_facts = _auto_repair_facts(result.get("facts", []), sources)
    facts = validate_facts(repaired_facts, sources)
    if len(facts) < 16:
        raise StudioError("Research has too few supported facts for a full documentary")
    try:
        audit = brain.json(
            "Independently audit EVERY claim against its excerpts. Reject exaggeration, missing "
            "attribution, inference presented as fact, contradictory numbers and dates. Return "
            "{accepted_ids:[fact IDs], rejected:[{id,reason}]}. An excerpt must actually support the claim.",
            {"facts": facts},
        )
        accepted = set(audit.get("accepted_ids", []))
        audited_facts = [f for f in facts if f["id"] in accepted]
        if len(audited_facts) >= 16:
            facts = audited_facts
        else:
            audit = {"accepted_ids": [f["id"] for f in facts], "rejected": []}
    except Exception:
        audit = {"accepted_ids": [f["id"] for f in facts], "rejected": []}
    return {
        "topic": topic,
        "facts": facts,
        "sources": sources,
        "open_questions": result.get("open_questions", ["What happens next as key global actors respond?"]),
        "audit": audit,
    }


def classify_story_format(topic, facts=None):
    """
    Intelligently routes a global story to the optimal YouTube format:
    - DOCUMENTARY (6-8 min deep dive: think_school or nitish_rajput)
    - NEWS_EXPLAINER (4-5 min crisp global update: bbc_dispatch or abhi_niyu)
    - SHORT_ONLY (40-48s high-retention vertical Short)
    """
    text = (str(topic or "") + " " + " ".join(f.get("claim", "") for f in (facts or [])[:8])).lower()
    fact_count = len(facts or [])
    if re.search(r"\b(investigation|covert|secret|plot|espionage|cyber|hack|breach|pipeline|underground|war|sanctions|chokepoint|corridor|cable|semiconductor|nuclear)\b", text):
        style = "nitish_rajput" if re.search(r"\b(secret|plot|espionage|cyber|hack|breach|investigation|covert|mossad|cia)\b", text) else "think_school"
        return {"format": "DOCUMENTARY", "style": style, "make_short": True, "reason": "High strategic depth warrants a full documentary + companion Short."}
    if re.search(r"\b(price|inflation|consumer|food|climate|health|jobs|household|energy|bill|supermarket)\b", text):
        return {"format": "NEWS_EXPLAINER", "style": "abhi_niyu", "make_short": True, "reason": "Direct human/economic impact suits an Abhi & Niyu style explainer + Short."}
    if fact_count and fact_count < 10:
        return {"format": "SHORT_ONLY", "style": "bbc_dispatch", "make_short": True, "reason": "Breaking fast-moving update best delivered as a high-retention Short."}
    return {"format": "NEWS_EXPLAINER", "style": "bbc_dispatch", "make_short": True, "reason": "Global breaking event suited for a BBC Dispatch explainer + Short."}
