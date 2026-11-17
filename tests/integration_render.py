"""Explicit FFmpeg integration test; run separately from quick unit tests."""
import copy
import os
import tempfile
import unittest
import wave
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path
import numpy as np
from studio.common import config, run_ff
from studio.demo import fixture
from studio.render import render_beat, concatenate
from studio.quality import inspect_video, check_video


class RenderIntegration(unittest.TestCase):
    def test_preview_pipeline_with_fixture_providers(self):
        """Exercise real orchestration, rendering, metadata and QC without remote calls."""
        from studio.pipeline import build
        from PIL import Image
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);cfg=config();cfg.update(width=640,height=360,fps=12,crf=26,preset="ultrafast",minimum_long_seconds=1,make_short=False)
            plan,dossier=fixture();plan["beats"]=plan["beats"][:3];plan["short_beat_ids"]=[]
            video=root/"source.mp4";photo=root/"photo.jpg";wav=root/"voice.wav"
            Image.new("RGB",(1280,720),(40,110,140)).save(photo)
            run_ff(["-f","lavfi","-i","testsrc2=size=1280x720:rate=12","-t","2","-c:v","libx264","-pix_fmt","yuv420p",video])
            run_ff(["-f","lavfi","-i","sine=frequency=330:sample_rate=48000","-t","1","-c:a","pcm_s16le",wav])
            for b,kind in zip(plan["beats"][1:],["photo","footage"]):
                b["visual"].update(kind=kind,query="fixture",must_include=["fixture"])
            class FakeBrain:
                provider="fixture";model="no remote calls"
                def __init__(self,*args):pass
            class FakeMedia:
                def __init__(self,*args):self.ledger=[]
                def find(self,b):
                    kind=b["visual"]["kind"]
                    a={"kind":kind,"path":str(photo if kind=="photo" else video),"label":"TEST FIXTURE",
                       "creator":"Tests","license":"CC0","license_url":"https://example.com/license",
                       "url":"https://example.com/"+kind,"page_url":"https://example.com/"+kind,
                       "caption":"Fixture media","changes":"Test render"}
                    self.ledger.append(a);return a
                def save(self,path):
                    from studio.common import save_json
                    save_json(path,self.ledger)
            class FakeVoice:
                provider="fixture"
                def __init__(self,*args):pass
                def synthesize(self,text):return {"path":str(wav),"duration":1,"timings":[],"provider":"fixture","voice":"test signal"}
            with patch("studio.pipeline.ROOT",root),patch("studio.publish.ROOT",root),patch("studio.pipeline.config",return_value=cfg),\
                 patch("studio.preflight.check",return_value=[]),patch("studio.brain.Brain",FakeBrain),\
                 patch("studio.research.collect_sources",return_value=dossier["sources"]),\
                 patch("studio.research.research",return_value=dossier),patch("studio.director.create_plan",return_value=plan),\
                 patch("studio.media.Media",FakeMedia),patch("studio.voice.Voice",FakeVoice):
                out=build(SimpleNamespace(topic="Fixture preview only",source_url=[],publish=False))
            from studio.common import load_json
            self.assertEqual(load_json(out/"run_report.json")["status"],"preview_ready")
            self.assertTrue(load_json(out/"quality_report.json")["passed"])
            for name in ["documentary.mp4","thumbnail.jpg","review.html","captions.srt","upload_metadata.json"]:
                self.assertTrue((out/name).is_file(),name)

    def test_graphics_photo_and_actual_video_decode(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);cfg=config();cfg.update(width=640,height=360,fps=12,crf=26,preset="ultrafast",minimum_long_seconds=1)
            plan,dossier=fixture()
            wav=root/"test_signal.wav"
            with wave.open(str(wav),"wb") as w:
                w.setnchannels(1);w.setsampwidth(2);w.setframerate(48000)
                a=(np.sin(np.arange(48000)*2*np.pi*220/48000)*2500).astype("<i2")
                w.writeframes(a.tobytes())
            audio={"path":str(wav),"duration":1,"timings":[]}
            source=root/"source.mp4"
            run_ff(["-f","lavfi","-i","testsrc2=size=1280x720:rate=12","-t","2","-c:v","libx264","-pix_fmt","yuv420p",source])
            image=root/"still.jpg";Image.new("RGB",(1280,720),(45,130,180)).save(image)
            beats=[copy.deepcopy(plan["beats"][0]) for _ in range(3)]
            for i,b in enumerate(beats):b["id"]=f"I{i}";b["duration"]=1
            for b,kind,path in [(beats[1],"photo",image),(beats[2],"footage",source)]:
                b["visual"]["kind"]=kind
                b["asset"]={"kind":kind,"path":str(path),"label":"TEST FIXTURE","creator":"Unit test",
                            "license":"CC0"}
            clips=[]
            for i,b in enumerate(beats):
                out=root/f"part{i}.mp4";render_beat(b,dossier,audio,out,cfg);clips.append(out)
            final=root/"final.mp4";concatenate(clips,final)
            meta=inspect_video(final)
            self.assertAlmostEqual(float(meta["format"]["duration"]),3,delta=.2)
            report=check_video(final,beats,cfg,root/"quality.json")
            self.assertTrue(report["passed"],report)

    def test_native_portrait_layout_and_audio(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);plan,dossier=fixture();cfg=config();cfg.update(fps=12,preset="ultrafast",crf=27)
            wav=root/"tone.wav"
            run_ff(["-f","lavfi","-i","sine=frequency=330:sample_rate=48000","-t","1","-c:a","pcm_s16le",wav])
            out=root/"portrait.mp4"
            render_beat(plan["beats"][3],dossier,{"path":str(wav),"duration":1,"timings":[]},out,cfg,portrait=True)
            info=inspect_video(out);v=next(s for s in info["streams"] if s["codec_type"]=="video")
            self.assertEqual((v["width"],v["height"]),(1080,1920))
            self.assertTrue(any(s["codec_type"]=="audio" for s in info["streams"]))


if __name__=="__main__":unittest.main()
