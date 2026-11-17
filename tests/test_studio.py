import copy
import math
import os
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch, MagicMock
import numpy as np
from studio.common import StudioError, Budget, public_url, config
from studio.director import validate_plan
from studio.research import validate_facts, similar
from studio.media import license_allowed, anchored
from studio.voice import inspect_audio, captions, Voice
from studio.quality import visual_gate, check_video
from studio.brain import parse_json
from studio.demo import fixture
from studio.render import Canvas


class EvidenceTests(unittest.TestCase):
    def setUp(self):self.plan,self.dossier=fixture()

    def test_valid_fixture(self):
        validate_facts(self.dossier["facts"],self.dossier["sources"])
        validate_plan(self.plan,self.dossier,minimum_words=1)

    def test_fabricated_excerpt_is_rejected(self):
        self.dossier["facts"][0]["evidence"][0]["quote"]="An invented sentence that never appeared in the source."
        with self.assertRaises(StudioError):validate_facts(self.dossier["facts"],self.dossier["sources"])

    def test_unknown_source_is_rejected(self):
        self.dossier["facts"][0]["evidence"][0]["source_id"]="S999"
        with self.assertRaises(StudioError):validate_facts(self.dossier["facts"],self.dossier["sources"])

    def test_chart_cannot_invent_number(self):
        self.plan["beats"][1]["visual"]["data"]["points"][0]["value"]=900
        with self.assertRaises(StudioError):validate_plan(self.plan,self.dossier,1)

    def test_chart_cannot_use_nan_or_boolean(self):
        for value in [float("nan"),float("inf"),True]:
            with self.subTest(value=value):
                self.plan["beats"][1]["visual"]["data"]["points"][0]["value"]=value
                with self.assertRaises(StudioError):validate_plan(self.plan,self.dossier,1)

    def test_short_must_be_contiguous(self):
        self.plan["short_beat_ids"]=["B01","B03"]
        with self.assertRaises(StudioError):validate_plan(self.plan,self.dossier,1)

    def test_no_uncited_narration(self):
        self.plan["beats"][0]["fact_ids"]=[]
        with self.assertRaises(StudioError):validate_plan(self.plan,self.dossier,1)

    def test_unsourced_narration_number_rejected(self):
        self.plan["beats"][0]["narration"]="This shipment allegedly cost 950 million dollars according to unspecified reports on the internet."
        with self.assertRaises(StudioError):validate_plan(self.plan,self.dossier,1)

    def test_short_script_not_padded(self):
        with self.assertRaises(StudioError):validate_plan(self.plan,self.dossier)

    def test_duplicate_beats_rejected(self):
        self.plan["beats"][1]["id"]="B01"
        with self.assertRaises(StudioError):validate_plan(self.plan,self.dossier,1)

    def test_no_arbitrary_3d_object(self):
        self.plan["beats"][0]["visual"]["data"]["object"]="missile"
        with self.assertRaises(StudioError):validate_plan(self.plan,self.dossier,1)


class MediaTests(unittest.TestCase):
    def test_licenses(self):
        for name in ["CC BY 4.0","CC BY-SA 3.0","Public domain","CC0","Pexels License"]:
            self.assertTrue(license_allowed(name))
        for name in ["","Fair use","CC BY-NC 4.0","CC BY-ND 4.0","All rights reserved","unknown"]:
            self.assertFalse(license_allowed(name))

    def test_wrong_country_anchor(self):
        self.assertFalse(anchored({"caption":"London parliament"},["India parliament"]))
        self.assertTrue(anchored({"caption":"A cargo-container at the port"},["cargo container"]))

    def test_still_images_do_not_count_as_real_video(self):
        cfg=config()
        beats=[{"duration":10,"asset":{"kind":"photo","license":"CC0"}}]*8
        result=visual_gate(beats,cfg)
        self.assertEqual(result["real_video_ratio"],0)
        self.assertFalse(result["passed"])

    def test_duration_weighted_media_gate(self):
        cfg=config()
        beats=[{"duration":1,"asset":{"kind":"footage","license":"CC0"}}]*10
        beats += [{"duration":90,"fallback":True}]
        self.assertFalse(visual_gate(beats,cfg)["passed"])

    def test_valid_media_mix(self):
        beats=[{"duration":30,"asset":{"kind":"footage","license":"CC0"}},
               {"duration":30,"asset":{"kind":"photo","license":"CC0"}},{"duration":40}]
        self.assertTrue(visual_gate(beats,config())["passed"])

    def test_private_source_blocked(self):
        with patch("socket.getaddrinfo",return_value=[(0,0,0,"",("127.0.0.1",80))]):
            with self.assertRaises(StudioError):public_url("http://localhost/secret")
        with self.assertRaises(StudioError):public_url("file:///etc/passwd")


class VoiceQualityTests(unittest.TestCase):
    def wav(self,path,samples):
        with wave.open(str(path),"wb") as w:
            w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(samples.astype("<i2").tobytes())

    def test_silence_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"silent.wav";self.wav(path,np.zeros(32000))
            with self.assertRaises(StudioError):inspect_audio(path)

    def test_clipping_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"clip.wav";self.wav(path,np.full(32000,32767))
            with self.assertRaises(StudioError):inspect_audio(path)

    def test_test_tone_passes_audio_integrity_only(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"tone.wav";self.wav(path,np.sin(np.arange(32000)*.1)*3000)
            self.assertAlmostEqual(inspect_audio(path),2)

    def test_provider_timing_preserved(self):
        a={"duration":3,"timings":[{"text":"Hello","start":.3,"end":.8},{"text":"world","start":1,"end":2}]}
        c=captions("Hello world",a)[0]
        self.assertEqual((c["start"],c["end"]),(.3,2))

    def test_auto_uses_existing_deepgram(self):
        with tempfile.TemporaryDirectory() as td,patch.dict(os.environ,{"DEEPGRAM_API_KEY":"test"},clear=True):
            self.assertEqual(Voice(config(),Path(td)).provider,"deepgram")

    def test_qc_probe_exception_blocks_upload(self):
        with tempfile.TemporaryDirectory() as td,patch("studio.quality.inspect_video",side_effect=RuntimeError("probe unavailable")):
            report=check_video("missing.mp4",[],config(),Path(td)/"qc.json")
            self.assertFalse(report["passed"])
            self.assertTrue((Path(td)/"qc.json").exists())

    def test_missing_audio_blocks_upload(self):
        with tempfile.TemporaryDirectory() as td,patch("studio.quality.inspect_video",return_value={"streams":[{"codec_type":"video"}]}):
            self.assertFalse(check_video("v.mp4",[],config(),Path(td)/"qc.json")["passed"])


class RendererTests(unittest.TestCase):
    def test_all_graphics_landscape_and_portrait(self):
        p,d=fixture()
        for size in [(640,360),(360,640)]:
            for b in p["beats"]:
                with self.subTest(kind=b["visual"]["kind"],size=size):
                    c=Canvas(b,d,*size);im=c.frame(2,5)
                    self.assertEqual(im.size,size)
                    self.assertGreater(np.asarray(im).std(),10)

    def test_container_moves(self):
        p,d=fixture();c=Canvas(p["beats"][0],d,640,360)
        self.assertGreater(np.mean(np.abs(np.asarray(c.frame(.5,5)).astype(float)-np.asarray(c.frame(3,5)))),1)

    def test_chart_supports_zero_and_negative(self):
        p,d=fixture();b=p["beats"][1]
        for vals in [(0,0),(-20,80),(-30,-10)]:
            for v,point in zip(vals,b["visual"]["data"]["points"]):point["value"]=v
            self.assertEqual(Canvas(b,d,640,360).frame(2,5).size,(640,360))


class GeneralTests(unittest.TestCase):
    def test_empty_provider_timings_not_mutated(self):
        audio={"duration":3,"timings":[]}
        captions("These timing estimates must stay labeled as estimates.",audio)
        self.assertEqual(audio["timings"],[])

    def test_pending_upload_blocks_duplicate(self):
        from studio.publish import upload
        with patch.dict(os.environ,{"YOUTUBE_TOKEN_JSON_B64":"dummy"}):
            with self.assertRaises(StudioError):
                upload("v",None,"title","description",[],config(),{"passed":True},"key",
                       {"uploads":{"key":{"status":"uploading"}}})

    def test_confirmed_upload_is_not_reinserted(self):
        from studio.publish import upload
        with patch.dict(os.environ,{"YOUTUBE_TOKEN_JSON_B64":"dummy"}):
            result=upload("v",None,"title","description",[],config(),{"passed":True},"key",
                          {"uploads":{"key":{"video_id":"existing"}}})
            self.assertEqual(result,"existing")

    def test_upload_without_qc_is_rejected(self):
        from studio.publish import upload
        with self.assertRaises(StudioError):
            upload("v",None,"title","description",[],config(),{},"key",{})

    def test_budget_enforced(self):
        b=Budget(max_calls=1);b.spend()
        with self.assertRaises(StudioError):b.spend()

    def test_json_parse_rejects_arrays(self):
        self.assertEqual(parse_json('```json\n{"ok":true}\n```'),{"ok":True})
        with self.assertRaises(StudioError):parse_json('[]')

    def test_topic_similarity(self):
        self.assertGreater(similar("Singapore port faces shipping delays","Shipping delays at Singapore port"),.7)


if __name__=="__main__":unittest.main()
