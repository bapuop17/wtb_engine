"""Offline renderer demo. Fictional data; no narration, no research, no upload."""
import wave
from pathlib import Path
from .common import ROOT, config, save_json


def fixture():
    facts=[{"id":"F1","claim":"This is a fictional design demonstration, not a report about a real event.",
            "status":"reported","evidence":[{"source_id":"S1","quote":"Fictional demo: North 120 and South 80 units."}]}]
    dossier={"topic":"The hidden journey of a shipment — fictional design demo","facts":facts,
             "sources":[{"id":"S1","title":"Fictional demo dataset","domain":"DEMO DATA / NOT NEWS",
                         "url":"https://example.com/demo","published":"fictional","text":"Fictional demo: North 120 and South 80 units."}],
             "open_questions":[]}
    def b(i,kind,headline,data,narration):
        return {"id":f"B{i:02}","chapter":"DESIGN DEMO / FICTIONAL DATA / NO NARRATION", "narration":narration,
                "fact_ids":["F1"],"visual":{"kind":kind,"headline":headline,"reason":"Renderer demonstration only","data":data}}
    beats=[
        b(1,"model3d","One shipment. Many moving parts.",{"object":"container"},
          "An original three dimensional container illustration explains a physical subject without pretending to be real event footage."),
        b(2,"chart","Show the comparison. Keep the scale.",{"unit":"Fictional units", "points":[
            {"label":"North", "value":120,"fact_id":"F1","evidence_text":"Fictional demo: North 120 and South 80 units."},
            {"label":"South", "value":80,"fact_id":"F1","evidence_text":"Fictional demo: North 120 and South 80 units."}]},
          "This chart uses invented demonstration data. Production charts require sourced values, matching units, and a zero baseline."),
        b(3,"timeline","A story should unfold in order.",{"events":[{"date":"DAY 01","label":"Departure","fact_id":"F1"},
            {"date":"DAY 04","label":"Inspection","fact_id":"F1"},{"date":"DAY 07","label":"Arrival","fact_id":"F1"}]},
          "This fictional sequence demonstrates how a documented chronology can appear as an animated timeline with clear event labels."),
        b(4,"diagram","Explain what connects the pieces.",{"steps":["Supplier","Port","Transit","Customer"]},
          "A simple mechanism diagram connects the supplier, the port, the journey and the customer without inventing numerical relationships."),
        b(5,"globe","Geography, with a clear purpose.",{"places":["Singapore"],"resolved_places":[
            {"name":"Singapore","lat":1.35,"lon":103.82,"source":"Demo coordinates"}]},
          "The schematic globe uses a projected sphere and a place marker. It is not an event map or an actual shipping route."),
        b(6,"evidence","Evidence comes before the effect.",{"fact_id":"F1"},
          "This preview demonstrates graphics only. A production documentary also needs readable research, relevant licensed footage and a working narrator.")]
    return {"title":"How the story becomes clear","thumbnail_text":"THE HIDDEN JOURNEY","summary":"Fictional graphics demonstration.",
            "title_alternatives":[],"tags":[],"beats":beats,"short_beat_ids":["B01","B02"]},dossier


def create_demo():
    from .render import Canvas, render_beat, concatenate, make_thumbnail
    from PIL import Image, ImageDraw
    out=ROOT/"output"/"design_demo";out.mkdir(parents=True,exist_ok=True)
    plan,dossier=fixture();cfg=config();cfg.update(preset="veryfast",crf=21)
    audio=out/"demo_silence.wav"
    # Intentional silence in a graphics-only demo; this path never enters publication/QC.
    with wave.open(str(audio),"wb") as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(48000);w.writeframes(b"\0\0"*48000*5)
    files=[];sheet=Image.new("RGB",(1440,1215),(12,19,30))
    for i,b in enumerate(plan["beats"]):
        b["duration"]=5
        poster=Canvas(b,dossier,960,540).frame(2,5)
        poster.save(out/(b["id"]+".jpg"),quality=92)
        sheet.paste(poster.resize((720,405)),((i%2)*720,(i//2)*405))
        path=out/(b["id"]+".mp4")
        print("Rendering offline graphics demo",b["id"],flush=True)
        render_beat(b,dossier,{"path":str(audio),"duration":5,"timings":[]},path,cfg)
        files.append(path)
    concatenate(files,out/"graphics_demo.mp4")
    sheet.save(out/"contact_sheet.jpg",quality=94)
    make_thumbnail(plan,dossier,out/"thumbnail.jpg")
    save_json(out/"demo_info.json",{"type":"fictional graphics-only demonstration","narration":False,"publishes":False,
        "dimensions":"1920x1080","duration_seconds":30,"data_is_fictional":True})
    return out
