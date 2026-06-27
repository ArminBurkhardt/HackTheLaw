from __future__ import annotations

import hashlib
import io
import logging
import time
import wave
from uuid import uuid4

from crucible.config import Settings, get_settings


RECEIVE_SAMPLE_RATE = 24_000
LOG_PREVIEW_CHARS = 180
LIVE_AUDIO_SYSTEM_INSTRUCTION = (
    "You are a voice renderer for a legal negotiation training app. "
    "Speak exactly the text the user provides, verbatim. Do not answer it, summarize it, "
    "paraphrase it, translate it, add an introduction, add commentary, or change the language. "
    "Use natural pacing and the configured voice."
)

logger = logging.getLogger("uvicorn.error")


class LiveAudioUnavailable(RuntimeError):
    pass


class GeminiLiveAudioService:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._cache: dict[tuple[str, str, str, str], bytes] = {}

    async def synthesize(self, text: str, language: str = "en") -> bytes:
        if not self._settings.google_api_key:
            raise LiveAudioUnavailable("GOOGLE_API_KEY must be set for Gemini Live audio.")
        cleaned = text.strip()
        if not cleaned:
            raise LiveAudioUnavailable("Text is required for Gemini Live audio.")

        started = time.perf_counter()
        request_id = uuid4().hex[:8]
        key = audio_cache_key(cleaned, language, self._settings.live_audio_model, self._settings.live_audio_voice)
        if cached := self._cache.get(key):
            self._log_done(request_id, cleaned, language, cached, time.perf_counter() - started, cache_hit=True)
            return cached

        try:
            from google import genai
            from google.genai import types
        except ModuleNotFoundError as error:
            raise LiveAudioUnavailable("google-genai must be installed for Gemini Live audio.") from error

        self._log_start(request_id, cleaned, language)
        client = genai.Client(http_options={"api_version": "v1beta"}, api_key=self._settings.google_api_key)
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=LIVE_AUDIO_SYSTEM_INSTRUCTION,
            temperature=0,
            speech_config=types.SpeechConfig(
                language_code=language_code(language),
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=self._settings.live_audio_voice)
                ),
            ),
        )

        audio = bytearray()
        try:
            async with client.aio.live.connect(model=self._settings.live_audio_model, config=config) as session:
                await session.send_client_content(turns=types.Content(role="user", parts=[types.Part(text=cleaned)]))
                async for response in session.receive():
                    if response.data:
                        audio.extend(response.data)
                    if response.server_content and response.server_content.turn_complete:
                        break
        except Exception as error:
            raise LiveAudioUnavailable(f"Gemini Live audio failed: {error}") from error

        if not audio:
            raise LiveAudioUnavailable("Gemini Live returned no audio.")
        wav = pcm_to_wav(bytes(audio))
        self._cache[key] = wav
        self._log_done(request_id, cleaned, language, wav, time.perf_counter() - started, cache_hit=False)
        return wav

    def _log_start(self, request_id: str, text: str, language: str) -> None:
        if self._settings.live_audio_debug:
            logger.info(
                "live_audio.start request_id=%s model=%s voice=%s language=%s chars=%s text_sha=%s text_preview=%r",
                request_id,
                self._settings.live_audio_model,
                self._settings.live_audio_voice,
                language,
                len(text),
                text_hash(text),
                text_preview(text),
            )

    def _log_done(self, request_id: str, text: str, language: str, wav: bytes, elapsed: float, cache_hit: bool) -> None:
        if self._settings.live_audio_debug:
            logger.info(
                "live_audio.done request_id=%s language=%s cache_hit=%s chars=%s text_sha=%s wav_bytes=%s elapsed_ms=%s",
                request_id,
                language,
                cache_hit,
                len(text),
                text_hash(text),
                len(wav),
                round(elapsed * 1000),
            )


def language_code(language: str) -> str:
    return "de-DE" if language == "de" else "en-US"


def audio_cache_key(text: str, language: str, model: str, voice: str) -> tuple[str, str, str, str]:
    return (text_hash(text.strip()), language, model, voice)


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def text_preview(text: str) -> str:
    cleaned = " ".join(text.split())
    return cleaned if len(cleaned) <= LOG_PREVIEW_CHARS else f"{cleaned[:LOG_PREVIEW_CHARS]}..."


def pcm_to_wav(pcm: bytes) -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(RECEIVE_SAMPLE_RATE)
        wav.writeframes(pcm)
    return output.getvalue()


def wav_duration_seconds(wav_bytes: bytes) -> float:
    with wave.open(io.BytesIO(wav_bytes), "rb") as wav:
        return wav.getnframes() / wav.getframerate()
