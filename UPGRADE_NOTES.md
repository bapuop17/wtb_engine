# Upgrade audit

Inspected `wtb_engine-main.zip` from the supplied local folder. Original source was about 20,000 lines; retained in `legacy/wtb_engine_pre_studio.py.txt` as inactive reference.

## Concrete original-code findings

- `VoiceAndSubtitleEngine.synthesize_with_word_boundaries`: gTTS fallback and `anullsrc` silence despite comments claiming a strict voice lock.
- `run_automatic_pre_upload_qc_gate`: exceptions returned `True`; audio verification defaulted to success; license audit was a fixed PASS message.
- `classify_special_visual_simulation_mode`: effects selected from word patterns and template cycling instead of explicit sourced graphic data.
- `ai_direct_complete_video_package`: forced a geopolitical narrative structure across topics; fact/source IDs were not attached to individual spoken claims.
- Uploading triggered old-video rehabilitation and token failover. Studio does not call those paths.
- README and actual workflow described different cadences. New docs reflect the actual schedule.

## Editorial references

Reviewed official catalogues and publicly available descriptions, not full frame-by-frame video playback. These inform general clarity, chronology, evidence and explanatory graphics; this is original WTB design, not a reproduction of these creators' production teams.

- Think School: https://thethinkschool.com/collab/
- Think School description/study-material presentation: https://www.youtube.com/watch?v=VzUmLAUPSQo
- Nitish Rajput official catalogue: https://www.nitishrajput.com/
- Abhi and Niyu documentary: https://www.youtube.com/watch?v=ueja-yAmpEs

## Official integration references

- Pexels: https://www.pexels.com/api/documentation/
- Wikimedia metadata: https://www.mediawiki.org/wiki/API:Imageinfo
- Deepgram: https://developers.deepgram.com/docs/tts-models
- ElevenLabs: https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps
- Gemini models: https://ai.google.dev/gemini-api/docs/models
- YouTube upload: https://developers.google.com/youtube/v3/docs/videos/insert
- Synthetic-content field: https://developers.google.com/youtube/v3/docs/videos

`contains_synthetic_media` is explicit configuration, false by default for neutral synthesized narration and visibly explanatory graphics. Set true if future content includes realistic altered/reconstructed events requiring disclosure. This version does not generate realistic fake event footage.
