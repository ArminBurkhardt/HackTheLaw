"""Gemini implementation of the ModelClient protocol."""
from __future__ import annotations

from google import genai
from google.genai import errors, types

from crucible.agents.base import ModelClientError


class GeminiModelClient:
    def __init__(self, settings) -> None:
        if settings.google_api_key:
            self._client = genai.Client(api_key=settings.google_api_key)
            return

        if settings.google_cloud_project:
            self._client = genai.Client(
                vertexai=True,
                project=settings.google_cloud_project,
                location=settings.google_cloud_location,
            )
            return

        raise RuntimeError("GOOGLE_API_KEY or GOOGLE_CLOUD_PROJECT must be configured.")

    def generate(self, *, model: str, system: str, messages: list[dict], **kw) -> str:
        wants_json = "JSON" in system or "valid json" in system.lower()
        try:
            response = self._client.models.generate_content(
                model=model,
                contents=_to_contents(messages),
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    temperature=float(kw.get("temperature", 0.2)),
                    max_output_tokens=kw.get("max_output_tokens"),
                    response_mime_type="application/json" if wants_json else None,
                ),
            )
        except errors.APIError as error:
            status_code = int(getattr(error, "status_code", 503) or 503)
            raise ModelClientError(f"Gemini model request failed: {error}", status_code=status_code) from error
        text = _response_text(response)
        if not text:
            raise RuntimeError(f"Gemini returned an empty response: {_finish_summary(response)}")
        return text


def _to_contents(messages: list[dict]) -> list[types.Content]:
    contents: list[types.Content] = []
    for message in messages:
        content = str(message.get("content", "")).strip()
        if not content:
            continue
        role = "model" if message.get("role") == "assistant" else "user"
        contents.append(
            types.Content(
                role=role,
                parts=[types.Part.from_text(text=content)],
            )
        )
    return contents


def _response_text(response) -> str:
    if response.text:
        return response.text

    chunks: list[str] = []
    for candidate in response.candidates or []:
        content = candidate.content
        if content is None:
            continue
        for part in content.parts or []:
            text = getattr(part, "text", None)
            if text:
                chunks.append(text)
    return "".join(chunks)


def _finish_summary(response) -> str:
    summaries: list[str] = []
    for candidate in response.candidates or []:
        finish_reason = getattr(candidate, "finish_reason", None)
        safety = getattr(candidate, "safety_ratings", None)
        summaries.append(f"finish_reason={finish_reason}, safety_ratings={safety}")
    return "; ".join(summaries) or "no candidates"
