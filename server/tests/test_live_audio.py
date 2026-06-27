from app.live_audio import pcm_to_wav


def test_pcm_to_wav_wraps_live_audio_bytes() -> None:
    wav = pcm_to_wav(b"\x00\x00\x01\x00")

    assert wav.startswith(b"RIFF")
    assert b"WAVE" in wav[:16]
    assert len(wav) > 40
