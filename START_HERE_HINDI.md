# पहले यह पढ़ो — WTB Studio Upgrade

यह तुम्हारे `wtb_engine` प्रोजेक्ट का नया version है। पुराना history और website files रखे हैं। उसी GitHub repository में डालोगे तो पुरानी Secrets वहीं रहेंगी।

## GitHub में लगाना

1. ZIP extract करो। अंदर `wtb_engine` folder की **सारी files और folders** उसी repository के root में रखो। केवल ZIP file को repository में upload करने से code update नहीं होता।
2. पुरानी `wtb_engine.py`, `README.md`, `.github/workflows/test_and_run.yml` replace करो। नया `studio/`, `tests/`, `requirements.txt`, `studio_config.json` और `.github/workflows/validate.yml` भी जरूरी हैं। `.github` folder छूटना नहीं चाहिए।
3. Settings → Secrets and variables → Actions में तुम्हारी `YOUTUBE_TOKEN_JSON_B64` और AI keys पहले जैसी रहेंगी। कम से कम एक writing key चाहिए: Gemini, Groq या OpenRouter।
4. अच्छी voice के लिए मौजूदा `DEEPGRAM_API_KEY` इस्तेमाल होगी। Optional: `ELEVENLABS_API_KEY` + `ELEVENLABS_VOICE_ID`। Paid usage हो सकता है।
5. Real stock videos के लिए `PEXELS_API_KEY` बहुत उपयोगी है। इसके बिना Commons से video खोजेगा; सही footage कम मिले तो upload रोक देगा।
6. Actions → **WTB Studio - Documentary Production** → Run workflow → पहली बार **preview** चुनो। Topic खाली रखो तो global news चुनेगा; अपना topic भी लिख सकते हो।
7. Run पूरा होने पर नीचे Artifacts → `WTB-Studio-...` download करो। `documentary.mp4`, `thumbnail.jpg`, `review.html` और `quality_report.json` देखो। Manual upload के लिए अगली run में **publish** चुनो। अभी preview के बाद publish नई production run बनाता है।

**Automatic schedule चालू है:** रोज 11:30 AM और 11:30 PM IST। एक documentary और valid होने पर एक Short। Default successful scheduled upload public है। जाँच के दौरान repository Variable `WTB_PRIVACY=unlisted` रख सकते हो। GitHub schedule में देरी हो सकती है।

Source/credit links के लिए Settings → Pages में अपनी default branch का `/docs` folder enabled रखो। Workflow नई credits pages के लिए rebuild request भेजेगा; failure हो तो Summary में warning दिखेगी।

## मुख्य सुधार

- Narration के हिसाब से scene plan; random keyword देखकर chart नहीं।
- Sourced numbers के बिना chart नहीं; stock/archive footage की पहचान screen पर।
- Real moving footage का minimum हिस्सा; zoom की हुई photo को real video नहीं गिनेगा।
- Consistent narrator; voice fail होने पर silent video upload नहीं।
- साफ़ documentary design, timeline, charts, mechanism diagrams और चुने हुए 3D illustrations।
- Thumbnail/title की भी facts से जाँच, source list, license records और confirmed upload IDs।

## Run रुक जाए तो

Actions Summary और artifact में `run_report.json` देखो। “Too little real video footage” मतलब सही footage नहीं मिला। “Evidence” error का मतलब research/storyboard जाँच में समस्या। “TTS” error में voice key/quota देखो। “pending receipt” में पहले YouTube Studio देखो—पिछला upload हो सकता है।

**साफ बात:** Premium voice और live upload का test तुम्हारे GitHub Secrets वाले run में होगा। साथ दिया sample केवल graphics का demo है; उसमें fictional data है और narration नहीं है। Views या Think School/BBC जैसी human-team quality की guarantee नहीं है।
