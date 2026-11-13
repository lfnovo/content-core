"""Offline checks for credential isolation, ordered uploads and billed retries."""

import asyncio
import shutil
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from content_core.common.exceptions import ExternalServiceError
from content_core.config import ContentCoreConfig
from content_core.processors.media import audio


def test_secrets_not_serialized():
    first = ContentCoreConfig(stt_config={"api_key": "secret-one"})
    second = ContentCoreConfig()
    assert "secret-one" not in repr(first)
    assert "stt_config" not in first.model_dump()
    assert second.stt_config == {}


@pytest.mark.asyncio
async def test_timeout_not_retried():
    model = SimpleNamespace(atranscribe=AsyncMock(side_effect=TimeoutError("timeout")))
    with pytest.raises(ExternalServiceError, match="already have been billed"):
        await audio.transcribe_audio_segment(
            "unused.wav", model, asyncio.Semaphore(1)
        )
    assert model.atranscribe.await_count == 1


@pytest.mark.asyncio
async def test_language_forwarded():
    model = SimpleNamespace(
        atranscribe=AsyncMock(return_value=SimpleNamespace(text="hello"))
    )
    assert (
        await audio.transcribe_audio_segment(
            "unused.wav", model, asyncio.Semaphore(1), max_attempts=1, language="hi"
        )
        == "hello"
    )
    model.atranscribe.assert_awaited_once_with("unused.wav", language="hi")


@pytest.mark.asyncio
@pytest.mark.parametrize("segment_minutes", [0, 5])
async def test_long_audio_order_and_byte_limit(tmp_path, monkeypatch, segment_minutes):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("ffmpeg and ffprobe required")
    path = tmp_path / "lecture.wav"
    # Twelve minutes, 44.1 kHz PCM: > 25 MB. Each minute has its own
    # sample value so the actual decoded upload order can be checked.
    with wave.open(str(path), "wb") as wav:
        wav.setparams((1, 2, 44100, 0, "NONE", "not compressed"))
        for minute in range(12):
            wav.writeframes((minute + 1).to_bytes(2, "little") * (44100 * 60))
    assert path.stat().st_size > 25_000_000
    active = peak = 0
    completed = []
    uploaded_samples = []
    settings = []

    async def transcribe(filename, **kwargs):
        nonlocal active, peak
        assert Path(filename).stat().st_size <= 24_000_000
        assert kwargs == {"language": "hi"}
        with wave.open(filename, "rb") as wav:
            frames = wav.readframes(wav.getnframes())
        first = int.from_bytes(frames[:2], "little")
        uploaded_samples.append((first, frames))
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.15 if first == 1 else 0.005)
        active -= 1
        completed.append(first)
        return SimpleNamespace(text=str(first))

    def create(provider, name, config):
        settings.append((provider, name, config))
        return SimpleNamespace(atranscribe=transcribe)

    monkeypatch.setattr(audio, "_create_stt_model", create)
    result = await audio.transcribe_audio(
        str(path),
        ContentCoreConfig(
            audio_provider="openai-compatible",
            audio_model="kapture-v3",
            stt_config={
                "api_key": "test-only",
                "base_url": "https://adapter.example/v1",
            },
            audio_segment_minutes=segment_minutes,
            audio_concurrency=2,
            audio_max_upload_bytes=24_000_000,
            audio_language="hi",
            audio_transcription_attempts=1,
        ),
    )
    assert peak == 2
    assert completed != sorted(completed)
    assert result.content == " ".join(str(i) for i in sorted(completed))
    assert result.metadata["segments_count"] == len(completed)
    assert settings[0][2]["api_key"] == "test-only"
    # No missing or duplicated audio at boundaries after real ffmpeg splits.
    ordered = b"".join(frames for _, frames in sorted(uploaded_samples))
    with wave.open(str(path), "rb") as wav:
        assert ordered == wav.readframes(wav.getnframes())


@pytest.mark.asyncio
async def test_compatible_provider_wire_contract(tmp_path):
    import httpx
    from esperanto import AIFactory

    path = tmp_path / "interview.wav"
    path.write_bytes(b"synthetic audio")
    captured = []

    async def handler(request):
        captured.append(
            (str(request.url), request.headers["authorization"], await request.aread())
        )
        return httpx.Response(200, json={"text": "Interview transcript"})

    model = AIFactory.create_speech_to_text(
        "openai-compatible",
        "kapture-v3",
        {
            "api_key": "test-only",
            "base_url": "https://adapter.example/v1",
        },
    )
    await model.async_client.aclose()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        model.async_client = client
        result = await audio.transcribe_audio_segment(
            str(path), model, asyncio.Semaphore(1), max_attempts=1, language="hi"
        )
    assert result == "Interview transcript"
    url, auth, body = captured[0]
    assert url == "https://adapter.example/v1/audio/transcriptions"
    assert auth == "Bearer test-only"
    assert b"kapture-v3" in body
    assert b'name="language"\r\n\r\nhi' in body
    assert len(captured) == 1


@pytest.mark.asyncio
async def test_failure_drains_other_uploads_before_cleanup(tmp_path, monkeypatch):
    monkeypatch.setattr(audio, "get_audio_duration", AsyncMock(return_value=720))

    def extract(source, target, start, end):
        Path(target).write_bytes(b"audio")

    monkeypatch.setattr(audio, "extract_audio", extract)
    finished = []

    async def transcribe(path):
        if "001" in path:
            await asyncio.sleep(0.005)
            raise ValueError("invalid key")
        await asyncio.sleep(0.01)
        assert Path(path).exists()
        finished.append(path)
        return SimpleNamespace(text="partial")

    monkeypatch.setattr(
        audio,
        "_create_stt_model",
        lambda *args: SimpleNamespace(atranscribe=transcribe),
    )
    with pytest.raises(ExternalServiceError):
        await audio.transcribe_audio(
            str(tmp_path / "interview.wav"),
            ContentCoreConfig(audio_segment_minutes=5, audio_transcription_attempts=1),
        )
    assert len(finished) == 2
    assert all(not Path(path).exists() for path in finished)
