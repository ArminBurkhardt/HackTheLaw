import io
import wave

from .schemas import Language
from .settings import Settings, load_settings


RECEIVE_SAMPLE_RATE = 24_000


class LiveAudioUnavailable(RuntimeError):
    pass


class GeminiLiveAudioService:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or load_settings()

    async def synthesize(self, text: str, language: Language = Language.english) -> bytes:
        if not self._settings.google_api_key:
            raise LiveAudioUnavailable("GOOGLE_API_KEY must be set for Gemini Live audio.")
        if not text.strip():
            raise LiveAudioUnavailable("Text is required for Gemini Live audio.")

        try:
            from google import genai
            from google.genai import types
        except ModuleNotFoundError as error:
            raise LiveAudioUnavailable("google-genai must be installed for Gemini Live audio.") from error

        client = genai.Client(
            http_options={"api_version": "v1beta"},
            api_key=self._settings.google_api_key,
        )
        config = types.LiveConnectConfig(
            responseModalities=["AUDIO"],
            speechConfig=types.SpeechConfig(
                languageCode=language_code(language),
                voiceConfig=types.VoiceConfig(
                    prebuiltVoiceConfig=types.PrebuiltVoiceConfig(
                        voiceName=self._settings.live_audio_voice,
                    )
                )
            ),
        )

        audio = bytearray()
        async with client.aio.live.connect(model=self._settings.live_audio_model, config=config) as session:
            await session.send_client_content(turns=types.Content(role="user", parts=[types.Part(text=text)]))
            async for response in session.receive():
                if response.data:
                    audio.extend(response.data)
                if response.server_content and response.server_content.turn_complete:
                    break

        if not audio:
            raise LiveAudioUnavailable("Gemini Live returned no audio.")
        return pcm_to_wav(bytes(audio))


def language_code(language: Language) -> str:
    return "de-DE" if language == Language.german else "en-US"


def pcm_to_wav(pcm: bytes) -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(RECEIVE_SAMPLE_RATE)
        wav.writeframes(pcm)
    return output.getvalue()
