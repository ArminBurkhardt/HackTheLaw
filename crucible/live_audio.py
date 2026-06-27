from __future__ import annotations

import io
import logging
import time
import wave
from dataclasses import dataclass
from uuid import uuid4

from crucible.config import Settings, get_settings


RECEIVE_SAMPLE_RATE = 24_000
LOG_PREVIEW_CHARS = 180

logger = logging.getLogger("uvicorn.error")


class LiveAudioUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class LiveUtterance:
    transcript: str
    wav: bytes


class GeminiLiveAudioService:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def generate_utterance(self, *, system: str, prompt: str, language: str = "en") -> LiveUtterance:
        if not self._settings.google_api_key:
            raise LiveAudioUnavailable("GOOGLE_API_KEY must be set for Gemini Live audio.")
        cleaned_prompt = prompt.strip()
        if not cleaned_prompt:
            raise LiveAudioUnavailable("Prompt is required for Gemini Live audio.")

        try:
            from google import genai
            from google.genai import types
        except ModuleNotFoundError as error:
            raise LiveAudioUnavailable("google-genai must be installed for Gemini Live audio.") from error

        started = time.perf_counter()
        request_id = uuid4().hex[:8]
        self._log_start(request_id, cleaned_prompt, language)
        client = genai.Client(http_options={"api_version": "v1beta"}, api_key=self._settings.google_api_key)
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription=types.AudioTranscriptionConfig(),
            system_instruction=system,
            temperature=0.7,
            speech_config=types.SpeechConfig(
                language_code=language_code(language),
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=self._settings.live_audio_voice)
                ),
            ),
        )

        audio = bytearray()
        transcript_parts: list[str] = []
        try:
            async with client.aio.live.connect(model=self._settings.live_audio_model, config=config) as session:
                await session.send_client_content(
                    turns=types.Content(role="user", parts=[types.Part(text=cleaned_prompt)])
                )
                async for response in session.receive():
                    if response.data:
                        audio.extend(response.data)
                    if response.text:
                        transcript_parts.append(response.text)
                    content = response.server_content
                    if content and content.output_transcription and content.output_transcription.text:
                        transcript_parts.append(content.output_transcription.text)
                    if content and content.turn_complete:
                        break
        except Exception as error:
            raise LiveAudioUnavailable(f"Gemini Live audio failed: {error}") from error

        transcript = compact_transcript("".join(transcript_parts))
        if not audio:
            raise LiveAudioUnavailable("Gemini Live returned no audio.")
        if not transcript:
            raise LiveAudioUnavailable("Gemini Live returned no output transcript.")

        wav = pcm_to_wav(bytes(audio))
        self._log_done(request_id, transcript, language, wav, time.perf_counter() - started)
        return LiveUtterance(transcript=transcript, wav=wav)

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

    def _log_done(self, request_id: str, text: str, language: str, wav: bytes, elapsed: float) -> None:
        if self._settings.live_audio_debug:
            logger.info(
                "live_audio.done request_id=%s language=%s chars=%s text_sha=%s wav_bytes=%s elapsed_ms=%s",
                request_id,
                language,
                len(text),
                text_hash(text),
                len(wav),
                round(elapsed * 1000),
            )


def language_code(language: str) -> str:
    return "de-DE" if language == "de" else "en-US"


def text_hash(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def text_preview(text: str) -> str:
    cleaned = " ".join(text.split())
    return cleaned if len(cleaned) <= LOG_PREVIEW_CHARS else f"{cleaned[:LOG_PREVIEW_CHARS]}..."


def compact_transcript(text: str) -> str:
    return " ".join(text.split())


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
