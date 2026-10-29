import os
import json
import urllib.request
import urllib.error
import time
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("GOOGLE_API_KEY", "").strip()

print(f"API Key present: {bool(api_key)}")

configured_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash").strip().removeprefix("models/")
if not configured_model or configured_model == "gemini-2.5-flash":
    configured_model = "gemini-3.5-flash"

candidates = [configured_model]
for fallback in ["gemini-3.5-flash-lite", "gemini-3-flash-preview", "gemini-3.1-flash-lite"]:
    if fallback not in candidates:
        candidates.append(fallback)

prompt = "Explain in one sentence what customer due diligence is under banking regulations."
payload = {
    "contents": [{"parts": [{"text": prompt}]}],
    "generationConfig": {"temperature": 0.1, "maxOutputTokens": 256}
}

success = False
for model in candidates:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    for attempt in range(2):
        print(f"Trying model: {model} (attempt {attempt + 1})...")
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                result = json.loads(res.read().decode("utf-8"))
            text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
            print(f"SUCCESS with {model}:\n{text}")
            success = True
            break
        except urllib.error.HTTPError as e:
            print(f"HTTPError {e.code} on {model}")
            if e.code == 404:
                break
            if e.code in (503, 429) and attempt == 0:
                time.sleep(1.5)
                continue
            break
        except Exception as e:
            print(f"Exception on {model}: {e}")
            break
    if success:
        break
