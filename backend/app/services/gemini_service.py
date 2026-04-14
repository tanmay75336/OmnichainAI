import json

import requests


GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def gemini_is_configured(config):
    return bool((config.get("GEMINI_API_KEY") or "").strip())


def _extract_text(payload):
    candidates = payload.get("candidates") or []
    if not candidates:
        return ""

    content = candidates[0].get("content") or {}
    parts = content.get("parts") or []
    return "".join(part.get("text", "") for part in parts).strip()


def _safe_json_parse(text):
    if not text:
        return None

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        fenced = None
        if "```json" in text:
            fenced = text.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in text:
            fenced = text.split("```", 1)[1].split("```", 1)[0].strip()

        if not fenced:
            return None

        try:
            return json.loads(fenced)
        except json.JSONDecodeError:
            return None


def generate_json(prompt, config, logger, *, temperature=0.2):
    api_key = (config.get("GEMINI_API_KEY") or "").strip()
    if not api_key:
        return None

    model = (config.get("GEMINI_MODEL") or "gemini-2.0-flash").strip()
    url = GEMINI_API_URL.format(model=model)

    try:
        response = requests.post(
            url,
            params={"key": api_key},
            json={
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": prompt}],
                    }
                ],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "temperature": temperature,
                },
            },
            timeout=config["REQUEST_TIMEOUT_SECONDS"],
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Gemini request failed: %s", exc)
        return None

    return _safe_json_parse(_extract_text(payload))
