"""Narration with Gemini TTS on Vertex AI. Writes docs/video/audio/<scene>.wav. Usage: python tts.py [voice]"""
import json
import os
import subprocess
import sys
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from google import genai
from google.genai import types
from google.oauth2.credentials import Credentials

HERE = Path(__file__).parent
OUT = HERE / "audio"
VOICE = sys.argv[1] if len(sys.argv) > 1 else "Charon"
token = subprocess.run("gcloud auth print-access-token", shell=True, capture_output=True, text=True).stdout.strip()
client = genai.Client(vertexai=True, project=os.environ.get("GOOGLE_CLOUD_PROJECT", "gen-lang-client-0324574000"),
                      location="global", credentials=Credentials(token))
MODELS = ["gemini-3.8-flash-tts", "gemini-3.1-flash-tts-preview", "gemini-2.5-pro-preview-tts"]


def say(item):
    name, text = item
    prompt = text  # only the words to speak; any instruction here gets read aloud
    for m in MODELS:
        try:
            r = client.models.generate_content(model=m, contents=prompt, config=types.GenerateContentConfig(
                response_modalities=["AUDIO"], speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=VOICE)))))
            pcm = r.candidates[0].content.parts[0].inline_data.data
            with wave.open(str(OUT / f"{name}.wav"), "wb") as w:
                w.setnchannels(1), w.setsampwidth(2), w.setframerate(24000), w.writeframes(pcm)
            return f"{name} {m} {len(pcm) / 48000:.1f}s"
        except Exception as e:
            print(name, m, "failed", str(e)[:120], flush=True)
    return f"{name} FAILED"


OUT.mkdir(exist_ok=True)
with ThreadPoolExecutor(6) as ex:
    only = set(sys.argv[2:])
    for line in ex.map(say, [i for i in json.loads((HERE / "narration.json").read_text(encoding="utf-8")) if not only or i[0] in only]):
        print(line, flush=True)
