from app.live_audio import language_code, pcm_to_wav
from app.schemas import Language


def test_pcm_to_wav_wraps_live_audio_bytes() -> None:
    wav = pcm_to_wav(b"\x00\x00\x01\x00")

    assert wav.startswith(b"RIFF")
    assert b"WAVE" in wav[:16]
    assert len(wav) > 40


def test_live_audio_language_code_tracks_session_language() -> None:
    assert language_code(Language.english) == "en-US"
    assert language_code(Language.german) == "de-DE"
