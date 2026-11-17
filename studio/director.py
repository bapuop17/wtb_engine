"""4-Format Auto-Director: BBC Dispatch, Think School Case Study, Nitish Rajput Investigation & Abhi-Niyu Impact Explainer."""
import json
import math
import re
from .common import StudioError, save_json

KINDS = {
    "footage", "photo", "evidence", "chart", "timeline", "diagram",
    "globe", "model3d", "actor_split", "evidence_board", "stat_callout"
}

SHOW_STYLES = {
    "bbc_dispatch": {
        "label": "BBC GLOBAL DISPATCH",
        "badge": "LIVE GLOBAL DISPATCH",
        "min_words": 520,
        "target_words": "600-850",
        "beats_range": "22-32",
        "voice_edge": "en-GB-RyanNeural",
        "structure": (
            "Structure (BBC World News Broadcast Style): urgent breaking dateline cold open -> what is confirmed "
            "by official sources right now -> on-the-ground mechanism & map context -> reactions from key capitals "
            "-> what remains unverified -> next 48-hour outlook. Tone: crisp, neutral, authoritative broadcast journalism."
        ),
    },
    "think_school": {
        "label": "THINK SCHOOL CASE STUDY",
        "badge": "GEOPOLITICAL & ECONOMIC CASE STUDY",
        "min_words": 760,
        "target_words": "900-1200",
        "beats_range": "30-42",
        "voice_edge": "en-US-ChristopherNeural",
        "structure": (
            "Structure (Think School Geopolitical & Business Strategy Style): sharp strategic paradox cold open -> "
            "the 3 core questions this case study answers -> walk the map (geography & chokepoints) -> follow the money "
            "and hard numbers -> head-to-head strategic comparison (actor_split) -> winners, losers & long-term leverage."
        ),
    },
    "nitish_rajput": {
        "label": "NITISH RAJPUT INVESTIGATION",
        "badge": "FORENSIC DOSSIER & TIMELINE",
        "min_words": 760,
        "target_words": "950-1250",
        "beats_range": "32-44",
        "voice_edge": "en-US-GuyNeural",
        "structure": (
            "Structure (Nitish Rajput Forensic Investigation Style): dramatic documented incident cold open -> "
            "chronological Day-1 to Present timeline reconstruction -> the evidence board (connecting actors, "
            "operations, and documented proof) -> side-by-side claims vs counter-claims -> what official records prove."
        ),
    },
    "abhi_niyu": {
        "label": "ABHI & NIYU IMPACT EXPLAINER",
        "badge": "WHY THIS MATTERS • HUMAN IMPACT",
        "min_words": 650,
        "target_words": "750-1050",
        "beats_range": "26-36",
        "voice_edge": "en-US-AndrewNeural",
        "structure": (
            "Structure (Abhi and Niyu Human Impact & Solution Style): relatable human-scale hook ('Why should you care?') -> "
            "the hidden domino chain connecting a global event to everyday citizens (food, energy, jobs, security) -> "
            "big clear stat callouts -> what the real-world solution or safeguard looks like."
        ),
    },
}


def detect_show_style(topic, dossier=None, requested="auto"):
    req = str(requested or "auto").strip().lower()
    if req in SHOW_STYLES:
        return req
    text = (str(topic or "") + " " + " ".join(
        f.get("claim", "") for f in (dossier or {}).get("facts", [])[:10]
    )).lower()
    if re.search(r"\b(plot|assassinat|mossad|cia|irgc|cyber|hack|breach|spy|espionage|investigat|dossier|secret|leaked|forensic|raid)\b", text):
        return "nitish_rajput"
    if re.search(r"\b(supermarket|food|price|inflation|consumer|citizen|health|climate|water|electricity|jobs|workers|everyday|household|fridge)\b", text):
        return "abhi_niyu"
    if re.search(r"\b(summit|talks|minister|diplomat|ceasefire|vote|election|announces|warns|blasts|breaking|urgent|council|unsc)\b", text):
        return "bbc_dispatch"
    return "think_school"


DIRECTOR = """Write an ORIGINAL, thoughtful English World Talk Brief production for a global audience.
Use conversational American/International English, precise names and short spoken sentences. No fake quotes,
invented suspense, invented 'what happens next', verbal filler or imitations of named creators.
Structure: concrete cold open -> central question -> necessary background -> mechanism -> evidence
and counter-evidence -> consequences -> what is known/unknown. Let evidence determine length.
Target 900-1200 spoken words, 32-44 beats, 6-8 chapters. Every beat is ONE visual idea and 18-45 spoken
words; avoid splitting a sentence between beats. Write for the ear. Pronunciation stays natural.
Each beat references only the supplied facts it uses. Every factual clause needs evidence.
Return this EXACT JSON structure:
{
 "style":"think_school|bbc_dispatch|nitish_rajput|abhi_niyu",
 "title":"specific, honest, compelling title under 95 characters",
 "title_alternatives":["2 further honest alternatives"],
 "thumbnail_text":"2-5 concrete words, no unproven claims",
 "summary":"two concise sentences", "tags":["up to 8 relevant tags"],
 "beats":[{"id":"B01", "chapter":"The question", "narration":"spoken words",
  "fact_ids":["F1"], "visual":{"kind":"footage", "headline":"one concise takeaway",
    "query":"precise visual subject search", "must_include":["specific subject or named entity"],
    "reason":"why this image helps explain THIS narration", "data":{}}}],
 "short_beat_ids":["B01","B02","B03"]
}
Choose 3-5 consecutive beats making a self-contained 30-60s trailer, without a misleading cutoff.
Visual rules:
- footprint is editorial, restrained, cinematic: footage and photos provide real context.
- Aim for 45-65% footage/photo beats, never force that where evidence cannot support it.
- Footage/photo query must describe visible nouns actually discussed; must_include contains 1-3
  literal entity/subject phrases that the asset caption should contain. Do not use abstract rhetoric.
- Real event footage is never assumed available. Search material will be labeled ARCHIVE / CONTEXT
  or STOCK / ILLUSTRATION. Never say 'look at this actual incident' without verified event material.
- Chart ONLY to compare at least 2 supported numbers with SAME unit and compatible periods.
  data={"unit":"USD billion", "points":[{"label":"2023", "value":12.4,
  "fact_id":"F3","evidence_text":"exact verbatim excerpt containing that number"},...]}
  No estimated decorative data. Values must appear as the same digits in the excerpts.
- stat_callout ONLY when highlighting 1-3 key verified numbers from the beat's cited facts.
  data={"metrics":[{"value":"8 TONS","label":"Payload Capacity"},{"value":"1,550 MI","label":"Tactical Range"}]}
- actor_split ONLY when comparing two named sides, nations, leaders or doctrines.
  data={"left_title":"MOROCCO C295W","left_points":["Agile desert airlift","8-ton tactical payload"],
        "right_title":"ALGERIA S-400","right_points":["Fixed SAM umbrella","Long-range radar lock"]}
- evidence_board ONLY when connecting 2-4 documented nodes in an investigation or network.
  data={"nodes":[{"tag":"NODE 01","title":"Actor / Origin","detail":"Short verified role"},...]}
- Timeline ONLY for an actual dated sequence. data={"events":[{"date":"2024-01-02",
  "label":"short event", "fact_id":"F4"},...]} 2-4 events; dates must appear in facts/evidence.
- Diagram ONLY for a supported mechanism; data={"steps":["Mine","Refine","Manufacture"]}.
  2-4 short labels, no invented quantitative relationships. Label is conceptual.
- Globe ONLY if geography matters. data={"places":["Exact Wikipedia place name",...]} max 3.
  Engine resolves real coordinates. Do not put invented coordinates in the plan.
- model3d ONLY when a shipment/container process is explained. data={"object":"container"}.
  A restrained rotating perspective container illustration, NOT a reconstruction of a real incident.
- evidence: data={"fact_id":"F1"}. Displays sourced paraphrase, not a fake newspaper or quote.
- Never choose a chart merely because the narration contains a number; don't force 3D into all topics.
- Never use 'image', 'photo', 'source says' as filler. Visual headlines maximum 9 words.
"""


def build_director_prompt(style_key):
    meta = SHOW_STYLES.get(style_key, SHOW_STYLES["think_school"])
    return (
        DIRECTOR
        + f"\nSelected Production Format: {meta['label']} ({style_key}).\n"
        + f"{meta['structure']}\n"
        + f"Target {meta['target_words']} spoken words across {meta['beats_range']} beats. "
        + f"Set top-level \"style\": \"{style_key}\"."
    )


def validate_plan(plan, dossier, minimum_words=760):
    facts = {f["id"]: f for f in dossier["facts"]}
    beats = plan.get("beats", [])
    if not beats or len(beats) > 70:
        raise StudioError("Invalid number of storyboard beats")
    if not 8 <= len(plan.get("title", "")) <= 95:
        raise StudioError("Invalid title")
    ids, total = set(), 0
    for b in beats:
        if not b.get("id") or b["id"] in ids:
            raise StudioError("Duplicate/missing beat ID")
        ids.add(b["id"])
        n = b.get("narration", "")
        if not 8 <= len(n.split()) <= 65:
            raise StudioError(f"{b['id']}: narration is not one manageable visual beat")
        total += len(n.split())
        if not b.get("fact_ids") or not set(b["fact_ids"]) <= facts.keys():
            raise StudioError("Narration references missing evidence")
        evidence_text = " ".join(
            facts[fid]["claim"] + " " + " ".join(e["quote"] for e in facts[fid]["evidence"])
            for fid in b["fact_ids"]
        )
        evidence_nums = set(re.findall(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?", evidence_text.replace(",", "")))
        narration_nums = set(re.findall(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?", n.replace(",", "")))
        if not narration_nums <= evidence_nums:
            raise StudioError("Narration contains a numeric claim absent from cited evidence")
        v = b.get("visual", {})
        if v.get("kind") not in KINDS or not v.get("reason"):
            raise StudioError("Invalid visual direction")
        if not v.get("headline") or len(v["headline"].split()) > 12:
            raise StudioError("Visual headline too long/missing")
        data = v.get("data", {})
        if v["kind"] in {"photo", "footage"}:
            if not v.get("query") or not 1 <= len(v.get("must_include", [])) <= 3:
                raise StudioError("Unanchored media search")
        elif v["kind"] == "chart":
            points = data.get("points", [])
            if not data.get("unit") or not 2 <= len(points) <= 5:
                raise StudioError("Chart requires a common unit and 2-5 data points")
            for point in points:
                value = point.get("value")
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise StudioError("Chart has a non-finite/non-numeric value")
                if point.get("fact_id") not in b["fact_ids"]:
                    raise StudioError("Chart data is not cited in this beat")
                evidence = " ".join(e["quote"] for e in facts[point["fact_id"]]["evidence"])
                excerpt = point.get("evidence_text", "")
                if not excerpt or excerpt.casefold() not in evidence.casefold():
                    raise StudioError("Chart has an invented evidence excerpt")
                nums = [float(x.replace(",", "")) for x in re.findall(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?", excerpt)]
                if value not in nums:
                    raise StudioError("Chart value does not occur in its source excerpt")
        elif v["kind"] == "timeline":
            if not 2 <= len(data.get("events", [])) <= 4:
                raise StudioError("Timeline requires 2-4 events")
            for event in data["events"]:
                if event.get("fact_id") not in b["fact_ids"] or not event.get("date") or not event.get("label"):
                    raise StudioError("Timeline event lacks evidence/date")
        elif v["kind"] == "diagram":
            if not 2 <= len(data.get("steps", [])) <= 4:
                raise StudioError("Mechanism requires 2-4 steps")
        elif v["kind"] == "globe":
            if not 1 <= len(data.get("places", [])) <= 3:
                raise StudioError("Globe requires 1-3 actual place names")
        elif v["kind"] == "model3d":
            if data.get("object") != "container" or not re.search(r"ship|cargo|container|freight|logistics|supply", n, re.I):
                raise StudioError("3D container is unrelated to narration")
        elif v["kind"] == "actor_split":
            if not data.get("left_title") or not data.get("right_title"):
                raise StudioError("actor_split requires left_title and right_title")
        elif v["kind"] == "evidence_board":
            if not 2 <= len(data.get("nodes", [])) <= 4:
                raise StudioError("evidence_board requires 2-4 nodes")
        elif v["kind"] == "stat_callout":
            if not 1 <= len(data.get("metrics", [])) <= 4:
                raise StudioError("stat_callout requires 1-4 metrics")
        elif v["kind"] == "evidence" and data.get("fact_id") not in b["fact_ids"]:
            raise StudioError("Evidence graphic references an unrelated fact")
    if not minimum_words <= total <= 1700:
        raise StudioError(f"Script has {total} words; required {minimum_words}-1700. No padding permitted.")
    short = plan.get("short_beat_ids", [])
    indexes = [i for i, b in enumerate(beats) if b["id"] in short]
    if not short or not indexes or len(set(short)) != len(short) or not set(short) <= ids or indexes != list(range(min(indexes), max(indexes) + 1)):
        raise StudioError("Short must select a contiguous sequence of existing beats")
    return plan


def create_plan(dossier, brain, out, requested_style="auto"):
    style_key = detect_show_style(dossier.get("topic", ""), dossier, requested_style)
    style_meta = SHOW_STYLES[style_key]
    prompt = build_director_prompt(style_key)
    material = {
        "topic": dossier["topic"],
        "selected_style": style_key,
        "style_badge": style_meta["badge"],
        "facts": dossier["facts"],
        "open_questions": dossier["open_questions"],
    }
    plan = brain.json(prompt, material)
    plan.setdefault("style", style_key)
    for b in plan.get("beats", []):
        b.setdefault("style", plan["style"])
    min_w = style_meta["min_words"]
    for attempt in range(3):
        problems = []
        try:
            validate_plan(plan, dossier, minimum_words=min_w)
        except (StudioError, TypeError, KeyError) as e:
            problems.append(str(e))
        audit = brain.json(
            "Audit this complete script and ALL visual data against the supplied facts. "
            "Check every clause, title/thumbnail claim, timeline date, chart label/unit/period/scale, "
            "diagram causality, photo query alignment and trailer coherence. Require explicit attribution "
            "for allegations and contested reporting. No unsourced precise claims. Check story repetition. "
            "Return {passed:boolean, issues:[{beat_id,reason}], notes:string}. Be strict, not polite.",
            {"facts": dossier["facts"], "plan": plan},
        )
        if audit.get("passed") is True and not audit.get("issues") and not problems:
            plan["editorial_audit"] = audit
            plan.setdefault("style", style_key)
            for b in plan.get("beats", []):
                b.setdefault("style", plan["style"])
            save_json(out / "storyboard.json", plan)
            (out / "narration.txt").write_text("\n\n".join(b["narration"] for b in plan["beats"]), encoding="utf-8")
            return plan
        if attempt < 2:
            plan = brain.json(
                prompt + " Revise the supplied plan to correct ALL listed failures.",
                {**material, "previous_plan": plan, "validation_errors": problems, "editorial_audit": audit},
            )
            plan.setdefault("style", style_key)
            for b in plan.get("beats", []):
                b.setdefault("style", plan["style"])
    save_json(out / "rejected_storyboard.json", {"plan": plan, "validation_errors": problems, "audit": audit})
    raise StudioError("Storyboard failed evidence/editorial review after 2 repairs; upload blocked")
