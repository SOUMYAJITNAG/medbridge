"""
Gemma 4 AI service for MedBridge Ukraine.

Gemma 4 is a native multimodal model — it handles:
  - Medical image understanding (prescriptions, medicine strips, lab reports)
  - Multilingual text (Ukrainian, Russian, English, Polish, etc.)
  - Handwritten document OCR
  - Voice note transcription and understanding
  - Medical terminology extraction and translation

No separate OCR, TTS, or translation libraries are needed.
"""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types as gtypes

load_dotenv()

_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY", "")
_GEMMA_MODEL = os.getenv("GEMMA_MODEL", "gemma-4-31b-it")

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=_API_KEY)
    return _client


def _build_parts(text_prompt: str, file_paths: list[str] | None = None) -> list:
    """Build content parts for Gemma 4 multimodal request."""
    parts = []

    if file_paths:
        for fp in file_paths:
            path = Path(fp)
            if not path.exists():
                continue
            mime_type, _ = mimetypes.guess_type(str(path))
            if mime_type is None:
                ext = path.suffix.lower()
                mime_map = {
                    ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                    ".png": "image/png", ".gif": "image/gif",
                    ".webp": "image/webp", ".bmp": "image/bmp",
                    ".pdf": "application/pdf",
                    ".mp3": "audio/mpeg", ".wav": "audio/wav",
                    ".ogg": "audio/ogg", ".m4a": "audio/mp4",
                    ".mp4": "video/mp4",
                }
                mime_type = mime_map.get(ext, "application/octet-stream")

            with open(path, "rb") as f:
                data = f.read()

            # Gemma 4 supports image and audio natively
            if mime_type.startswith("image/") or mime_type.startswith("audio/") or mime_type == "application/pdf":
                parts.append(
                    gtypes.Part(
                        inline_data=gtypes.Blob(mime_type=mime_type, data=data)
                    )
                )

    parts.append(gtypes.Part(text=text_prompt))
    return parts


def call_gemma(prompt: str, file_paths: list[str] | None = None, max_tokens: int = 2000) -> str:
    """Call Gemma 4 with optional multimodal inputs. Returns plain text."""
    client = _get_client()
    parts = _build_parts(prompt, file_paths)

    response = client.models.generate_content(
        model=_GEMMA_MODEL,
        contents=gtypes.Content(parts=parts, role="user"),
        config=gtypes.GenerateContentConfig(
            max_output_tokens=max_tokens,
            temperature=0.2,
        ),
    )
    return (response.text or "").strip()


def call_gemma_json(prompt: str, file_paths: list[str] | None = None, max_tokens: int = 3000) -> dict[str, Any]:
    """Call Gemma 4 and parse response as JSON. Returns parsed dict."""
    json_prompt = (
        prompt
        + "\n\nIMPORTANT: Respond with ONLY a valid JSON object. "
          "No markdown fences, no explanation. Pure JSON only."
    )
    text = call_gemma(json_prompt, file_paths=file_paths, max_tokens=max_tokens)

    # Strip markdown fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    text = re.sub(r"```\s*$", "", text.strip(), flags=re.MULTILINE)
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON object from text
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {"raw_text": text, "parse_error": True}
