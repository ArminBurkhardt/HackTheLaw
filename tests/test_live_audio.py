from crucible.live_audio import audio_cache_key, language_code, pcm_to_wav, text_preview, wav_duration_seconds


def test_pcm_to_wav_wraps_live_audio_bytes():
    wav = pcm_to_wav(b"\x00\x00\x01\x00")

    assert wav.startswith(b"RIFF")
    assert b"WAVE" in wav[:16]
    assert len(wav) > 40
    assert wav_duration_seconds(wav) > 0


def test_live_audio_language_code_tracks_session_language():
    assert language_code("en") == "en-US"
    assert language_code("de") == "de-DE"


def test_live_audio_cache_key_ignores_edge_whitespace():
    left = audio_cache_key(" Speak this. ", "en", "model-a", "voice-a")
    right = audio_cache_key("Speak this.", "en", "model-a", "voice-a")

    assert left == right


def test_live_audio_text_preview_compacts_whitespace():
    assert text_preview("One\n\n  two\tthree") == "One two three"
    assert text_preview("x" * 200).endswith("...")
