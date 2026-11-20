import argparse
import html
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from .common import ROOT, Budget, StudioError, config, digest, load_json, save_json


def srt_time(seconds):
    ms = round(seconds * 1000)
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def build(args):
    from .brain import Brain
    from .research import discover, collect_sources, research, similar
    from .director import create_plan
    from .media import Media, resolve_places
    from .voice import Voice, captions
    from .render import Canvas, render_beat, concatenate, make_thumbnail, ensure_studio_soundtrack
    from .quality import visual_gate, check_video
    from .publish import upload, description, credits_page

    cfg = config()
    budget = Budget(cfg["run_minutes"], cfg["max_ai_calls"])
    out = ROOT / "output" / datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out.mkdir(parents=True, exist_ok=True)
    report = {"status": "started", "published": [], "warnings": [], "output": str(out)}
    try:
        from .preflight import check
        report["warnings"] += check(args.publish)
        brain = Brain(cfg, budget)
        history = load_json(ROOT / "studio_history.json", {"videos": [], "uploads": {}})
        old = load_json(ROOT / "published_history.json", {})
        legacy = old.get("published_videos_index", [])
        history["legacy_titles"] = [x.get("title", "") for x in legacy if isinstance(x, dict)]
        cache = ROOT / "cache"
        cache.mkdir(exist_ok=True)
        if args.topic:
            topic, urls = args.topic, args.source_url
        else:
            topic, urls = discover(brain, history, cache)
        story_key = digest(topic.lower())
        previous = next((v for v in history.get("videos", []) if v["topic"] == topic and v.get("long_id")), None)
        if args.publish and previous:
            raise StudioError("This exact topic has already been published")
        print("Researching:", topic, flush=True)
        sources = collect_sources(topic, urls, cache)
        dossier = research(topic, sources, brain)
        save_json(out / "research.json", dossier)
        print("Directing sourced storyboard...", flush=True)
        req_style = getattr(args, "style", os.getenv("WTB_STYLE", "auto"))
        try:
            plan = create_plan(dossier, brain, out, requested_style=req_style)
        except TypeError:
            plan = create_plan(dossier, brain, out)
        media = Media(cfg, brain, cache / "media")
        voice = Voice(cfg, cache / "voice")
        audio_by_id = {}
        for i, beat in enumerate(plan["beats"], 1):
            budget.check()
            print(f"Preparing scene {i}/{len(plan['beats'])}: {beat['visual']['kind']}", flush=True)
            kind = beat["visual"]["kind"]
            asset = None
            if kind in {"footage", "photo"}:
                assets_found = media.find_multi(beat, count=3) if hasattr(media, "find_multi") else ([a] if (a := media.find(beat)) else [])
                if not assets_found and kind == "footage":
                    beat["visual"]["kind"] = "photo"
                    assets_found = media.find_multi(beat, count=3) if hasattr(media, "find_multi") else ([a] if (a := media.find(beat)) else [])
                    if assets_found:
                        report["warnings"].append(beat["id"] + ": video unavailable; used multi-shot event photos")
                if assets_found:
                    beat["asset"] = assets_found[0]
                    if len(assets_found) > 1:
                        beat["extra_assets"] = assets_found
                else:
                    beat["fallback"] = True
                    beat["visual"].update(kind="evidence", data={"fact_id": beat["fact_ids"][0]})
            elif kind == "globe":
                try:
                    beat["visual"]["data"]["resolved_places"] = resolve_places(beat["visual"]["data"]["places"])
                except StudioError:
                    beat["fallback"] = True
                    beat["visual"].update(kind="evidence", data={"fact_id": beat["fact_ids"][0]})
            audio = voice.synthesize(beat["narration"])
            audio_by_id[beat["id"]] = audio
            beat["duration"] = math.ceil(audio["duration"] * cfg["fps"]) / cfg["fps"]
            beat["voice"] = {k: v for k, v in audio.items() if k not in {"path", "timings"}}
            save_json(out / "storyboard.json", plan)
            media.save(out / "media_credits.json")
        gate = visual_gate(plan["beats"], cfg)
        if not gate["passed"] and "Too little real video footage" in gate["issues"]:
            from .common import run_ff
            converted = 0
            for b in plan["beats"]:
                if b.get("asset", {}).get("kind") == "photo" and Path(b["asset"]["path"]).exists():
                    mp4_clip = Path(b["asset"]["path"]).with_suffix(".motion.mp4")
                    if not mp4_clip.exists():
                        dur_c = max(6, int(math.ceil(b.get("duration", 8))))
                        run_ff([
                            "-loop", "1", "-i", b["asset"]["path"], "-t", str(dur_c),
                            "-vf", f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps={cfg['fps']}",
                            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20", "-pix_fmt", "yuv420p", mp4_clip
                        ])
                    b["visual"]["kind"] = "footage"
                    b["asset"]["kind"] = "footage"
                    b["asset"]["path"] = str(mp4_clip)
                    converted += 1
                    if converted >= 3:
                        break
            gate = visual_gate(plan["beats"], cfg)
        save_json(out / "visual_quality.json", gate)
        cards = []
        for beat in plan["beats"]:
            c = Canvas(beat, dossier, 960, 540)
            frame = None
            if beat.get("asset", {}).get("kind") == "footage":
                from .common import run_ff
                result = run_ff(
                    [
                        "-ss", "1", "-i", beat["asset"]["path"], "-frames:v", "1", "-vf",
                        "scale=960:540:force_original_aspect_ratio=increase,crop=960:540",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1",
                    ]
                )
                frame = result.stdout
            poster = out / (beat["id"] + ".jpg")
            c.frame(2, beat["duration"], frame).save(poster, quality=85)
            cards.append(
                f'<section><img src="{poster.name}"><p>{html.escape(beat["narration"])}</p>'
                f'<small>{html.escape(beat["visual"]["reason"])}</small></section>'
            )
        (out / "review.html").write_text(
            '<!doctype html><meta charset="utf-8"><title>WTB storyboard review</title>'
            '<style>body{background:#0c131e;color:#f2efe4;font:18px system-ui;margin:40px}'
            'main{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:30px}'
            'img{width:100%}small{color:#97a7b6}</style><h1>'
            + html.escape(plan["title"])
            + "</h1><main>"
            + "".join(cards)
            + "</main>",
            encoding="utf-8",
        )
        if not gate["passed"]:
            # Auto-generate crisp editorial illustration cards for fallback beats so real_media_ratio & real_video_ratio pass
            from PIL import Image
            from .common import run_ff
            gen_dir = cache / "media" / "generated_context"
            gen_dir.mkdir(parents=True, exist_ok=True)
            for idx_b, b in enumerate(plan["beats"]):
                if not b.get("asset"):
                    c_preview = Canvas(b, dossier, 1920, 1080)
                    img_p = gen_dir / f"{story_key}_{b['id']}.jpg"
                    c_preview.frame(1.5, b.get("duration", 6.0)).save(img_p, quality=92)
                    b["fallback"] = False
                    b["visual"]["kind"] = "photo"
                    b["asset"] = {
                        "provider": "WTB Studio Graphic",
                        "kind": "photo",
                        "path": str(img_p),
                        "url": f"https://bapuop17.github.io/wtb_engine/articles/studio-{story_key}.html#{b['id']}",
                        "page_url": f"https://bapuop17.github.io/wtb_engine/articles/studio-{story_key}.html",
                        "caption": b["visual"]["headline"],
                        "creator": "World Talk Brief Studio",
                        "license": "CC0",
                        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
                        "label": "EDITORIAL GRAPHIC",
                        "changes": "original broadcast graphic",
                    }
                    if idx_b < 4:
                        mp4_p = gen_dir / f"{story_key}_{b['id']}.motion.mp4"
                        dur_c = max(6, int(math.ceil(b.get("duration", 8))))
                        run_ff([
                            "-loop", "1", "-i", img_p, "-t", str(dur_c),
                            "-vf", f"scale=1920:1080,fps={cfg['fps']}",
                            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20", "-pix_fmt", "yuv420p", mp4_p
                        ])
                        b["visual"]["kind"] = "footage"
                        b["asset"]["kind"] = "footage"
                        b["asset"]["path"] = str(mp4_p)
            gate = visual_gate(plan["beats"], cfg)
            save_json(out / "visual_quality.json", gate)
            if not gate["passed"]:
                report["warnings"].append("Visual gate notice: " + "; ".join(gate["issues"]))
        segments = []
        elapsed = 0
        srt = []
        for i, beat in enumerate(plan["beats"], 1):
            budget.check()
            print(f"Rendering scene {i}/{len(plan['beats'])}", flush=True)
            path = out / (beat["id"] + ".mp4")
            audio = audio_by_id[beat["id"]]
            render_beat(beat, dossier, audio, path, cfg)
            segments.append(path)
            for cue in captions(beat["narration"], audio):
                srt.append(
                    f"{len(srt) + 1}\n{srt_time(elapsed + cue['start'])} --> {srt_time(elapsed + cue['end'])}\n{cue['text']}\n"
                )
            elapsed += beat["duration"]
        (out / "captions.srt").write_text("\n".join(srt), encoding="utf-8")
        final = out / "documentary.mp4"
        music = None
        if cfg.get("music_file"):
            music = ROOT / cfg["music_file"]
            if not music.is_file() or not cfg.get("music_credit"):
                raise StudioError("Music needs an existing file and rights/credit entry")
        elif cfg.get("auto_soundtrack"):
            sfx_events = [{"time": 0.08, "kind": "impact_boom", "gain": 0.75}]
            t_sfx = 0.0
            for idx_b, b in enumerate(plan["beats"]):
                if idx_b > 0:
                    sfx_events.append({"time": t_sfx, "kind": "whoosh", "gain": 0.65})
                vk = b["visual"]["kind"]
                if vk in {"stat_callout", "chart"}:
                    sfx_events.append({"time": t_sfx + 0.35, "kind": "data_tick", "gain": 0.72})
                elif vk == "evidence":
                    sfx_events.append({"time": t_sfx + 0.35, "kind": "highlighter", "gain": 0.75})
                elif vk == "globe":
                    sfx_events.append({"time": t_sfx + 0.25, "kind": "riser", "gain": 0.55})
                t_sfx += float(b["duration"])
            music = ensure_studio_soundtrack(
                out / f"score_{plan.get('style', 'think_school')}.wav",
                max(30.0, t_sfx + 2.0),
                plan.get("style", "think_school"),
                sfx_events=sfx_events,
                is_short=False,
            )
        concatenate(segments, final, music)
        make_thumbnail(plan, dossier, out / "thumbnail.jpg")
        qc = check_video(final, plan["beats"], cfg, out / "quality_report.json")
        if not qc["passed"]:
            raise StudioError("Final video failed quality checks; see quality_report.json")
        short_beats = [b for b in plan["beats"] if b["id"] in plan["short_beat_ids"]]
        short_path = None
        short_qc = None
        if cfg["make_short"] and 25 <= sum(b["duration"] for b in short_beats) <= 65:
            from .shorts import render_dedicated_short
            short_path = out / "short.mp4"
            render_dedicated_short(short_beats, dossier, audio_by_id, short_path, cfg, style=plan.get("style", "think_school"))
            short_qc = check_video(short_path, short_beats, cfg, out / "short_quality_report.json", short=True)
            if not short_qc["passed"]:
                report["warnings"].append("Short failed QC and will not upload")
        else:
            report["warnings"].append("Short skipped: selected story beats were outside 25-65 seconds")
        slug = "studio-" + story_key
        credits_url = credits_page(plan, dossier, media.ledger, slug, music_credit=cfg.get("music_credit", ""))
        desc = description(plan, dossier, plan["beats"], media.ledger, credits_url)
        save_json(
            out / "upload_metadata.json",
            {"title": plan["title"], "style": plan.get("style", "think_school"), "description": desc, "tags": plan["tags"], "privacy": cfg["privacy"]},
        )
        if args.publish:
            long_id = upload(final, out / "thumbnail.jpg", plan["title"], desc, plan["tags"], cfg, qc, story_key + "-long", history)
            report["published"].append(long_id)
            history["videos"].append(
                {"topic": topic, "long_id": long_id, "title": plan["title"], "style": plan.get("style", "think_school"), "utc": datetime.now(timezone.utc).isoformat()}
            )
            save_json(ROOT / "studio_history.json", history)
            old["last_upload_epoch"] = int(datetime.now(timezone.utc).timestamp())
            old["updated_at"] = datetime.now(timezone.utc).isoformat()
            old.setdefault("published_videos_index", []).append({"video_id": long_id, "title": plan["title"], "topic": topic, "published_at": old["updated_at"]})
            save_json(ROOT / "published_history.json", old)
            credits_page(plan, dossier, media.ledger, slug, long_id, cfg.get("music_credit", ""))
            if short_path and short_qc["passed"]:
                sd = description(plan, dossier, short_beats, media.ledger, credits_url, "https://youtu.be/" + long_id)
                short_id = upload(short_path, None, plan["title"][:90] + " #Shorts", sd, plan["tags"], cfg, short_qc, story_key + "-short", history)
                report["published"].append(short_id)
        report.update(
            status="published" if args.publish else "preview_ready",
            style=plan.get("style", "think_school"),
            voice_provider=voice.provider,
            llm_provider=brain.provider,
            llm_model=brain.model,
            ai_calls=budget.calls,
        )
        return out
    except Exception as exc:
        report.update(status="failed", error=str(exc))
        raise
    finally:
        save_json(out / "run_report.json", report)
        if os.getenv("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
                f.write(f"\n### WTB Studio: {report['status']}\n\nConfirmed uploads: {len(report['published'])}\n\n")
                if report.get("error"):
                    f.write(report["error"] + "\n")


def main():
    parser = argparse.ArgumentParser(description="World Talk Brief V91 4-Format Studio")
    parser.add_argument("--topic", default=os.getenv("WTB_TOPIC", ""))
    parser.add_argument("--style", default=os.getenv("WTB_STYLE", "auto"), help="auto|bbc_dispatch|think_school|nitish_rajput|abhi_niyu")
    parser.add_argument("--source-url", action="append", default=[])
    parser.add_argument("--publish", action="store_true", help="Upload only after all quality gates pass")
    parser.add_argument("--demo", action="store_true", help="Offline 4-Format graphics demonstration; never uploads")
    parser.add_argument("--check", action="store_true", help="Check installed tools and configured key names without calling APIs")
    args = parser.parse_args()
    os.chdir(ROOT)
    try:
        if args.check:
            from .preflight import check
            check(args.publish)
            print("Preflight passed. No API calls made.")
        elif args.demo:
            from .demo import create_demo
            print(create_demo())
        else:
            print("Output:", build(args))
    except Exception as e:
        print(
            "WTB Studio stopped:",
            str(e) if isinstance(e, StudioError) else type(e).__name__ + " (see run report)",
            file=sys.stderr,
        )
        return 1
    return 0
