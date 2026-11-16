import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from content_core.config import ContentCoreConfig
from content_core.common.exceptions import (
    ConfigurationError,
    ExternalServiceError,
    FileOperationError,
)
from content_core.processors.media import audio
from content_core.processors.media.checkpoint import AudioCheckpoint


@pytest.fixture
def setup(tmp_path, monkeypatch):
    source = tmp_path / "lecture.wav"
    source.write_bytes(b"original audio")
    monkeypatch.setattr(audio, "get_audio_duration", AsyncMock(return_value=180))
    monkeypatch.setattr(
        audio,
        "extract_audio",
        lambda src, dst, start, end: Path(dst).write_bytes(str(start).encode()),
    )
    config = ContentCoreConfig(
        audio_segment_minutes=1,
        audio_concurrency=1,
        audio_checkpoint_dir=str(tmp_path / "checkpoints"),
        audio_transcription_attempts=1,
        stt_config={"api_key": "private-key"},
    )
    return source, config


@pytest.mark.asyncio
async def test_resume_only_unfinished_chunks_in_order(setup, monkeypatch):
    source, config = setup
    calls = []
    fail = True

    async def transcribe(path):
        value = Path(path).read_text()
        calls.append(value)
        if fail and value == "60":
            raise RuntimeError("HTTP 502")
        return SimpleNamespace(text=value)

    monkeypatch.setattr(
        audio,
        "_create_stt_model",
        lambda *args: SimpleNamespace(atranscribe=transcribe),
    )
    with pytest.raises(ExternalServiceError):
        await audio.transcribe_audio(str(source), config)
    assert calls == ["0", "60"]  # queued third chunk was not billed
    fail = False
    calls.clear()
    result = await audio.transcribe_audio(str(source), config)
    assert calls == ["60", "120"]
    assert result.content == "0 60 120"
    assert result.metadata["segments_reused"] == 1
    calls.clear()
    assert (await audio.transcribe_audio(str(source), config)).content == "0 60 120"
    assert calls == []
    for path in Path(config.audio_checkpoint_dir).rglob("*.json"):
        assert "private-key" not in path.read_text()
        assert path.stat().st_mode & 0o077 == 0


@pytest.mark.asyncio
async def test_changed_language_and_audio_do_not_reuse(setup, monkeypatch):
    source, config = setup
    transcribe = AsyncMock(return_value=SimpleNamespace(text="text"))
    monkeypatch.setattr(
        audio,
        "_create_stt_model",
        lambda *args: SimpleNamespace(atranscribe=transcribe),
    )
    await audio.transcribe_audio(str(source), config)
    config.audio_language = "en"
    await audio.transcribe_audio(str(source), config)
    source.write_bytes(b"changed audio")
    await audio.transcribe_audio(str(source), config)
    assert transcribe.await_count == 9


def test_lock_released_and_corrupt_checkpoint_fails_closed(tmp_path):
    source = tmp_path / "audio.wav"
    source.write_bytes(b"audio")
    checkpoint = AudioCheckpoint(str(tmp_path / "cache"), str(source), {})
    with pytest.raises(ConfigurationError, match="already running"):
        AudioCheckpoint(str(tmp_path / "cache"), str(source), {})
    key, value = checkpoint.read(0, str(source))
    assert value is None
    checkpoint.save(key, "success")
    checkpoint.close()
    resumed = AudioCheckpoint(str(tmp_path / "cache"), str(source), {})
    assert resumed.read(0, str(source))[1] == "success"
    (resumed.directory / f"{key}.json").write_text("broken")
    with pytest.raises(FileOperationError, match="unreadable"):
        resumed.read(0, str(source))
    resumed.close()


@pytest.mark.asyncio
async def test_inflight_success_saved_after_other_chunk_fails(setup, monkeypatch):
    source, config = setup
    config.audio_concurrency = 2
    calls = []
    fail = True

    async def transcribe(path):
        value = Path(path).read_text()
        calls.append(value)
        if fail and value == "60":
            await asyncio.sleep(0.005)
            raise RuntimeError("HTTP 502")
        await asyncio.sleep(0.02)
        assert Path(path).exists()
        return SimpleNamespace(text=value)

    monkeypatch.setattr(
        audio,
        "_create_stt_model",
        lambda *args: SimpleNamespace(atranscribe=transcribe),
    )
    with pytest.raises(ExternalServiceError):
        await audio.transcribe_audio(str(source), config)
    assert calls == ["0", "60"]
    fail = False
    calls.clear()
    result = await audio.transcribe_audio(str(source), config)
    assert calls == ["60", "120"]
    assert result.content == "0 60 120"
    assert result.metadata["segments_reused"] == 1


@pytest.mark.asyncio
async def test_request_pacing_and_cached_resume(setup, monkeypatch):
    source, config = setup
    config.audio_request_interval_seconds = 0.03
    config.audio_concurrency = 3
    started = []

    async def transcribe(path):
        started.append(asyncio.get_running_loop().time())
        return SimpleNamespace(text=Path(path).read_text())

    monkeypatch.setattr(
        audio,
        "_create_stt_model",
        lambda *args: SimpleNamespace(atranscribe=transcribe),
    )
    await audio.transcribe_audio(str(source), config)
    assert len(started) == 3
    assert all(b - a >= 0.025 for a, b in zip(started, started[1:]))
    # Pacing changes must not invalidate already billed successes.
    config.audio_request_interval_seconds = 10
    result = await audio.transcribe_audio(str(source), config)
    assert result.metadata["segments_reused"] == 3
    assert len(started) == 3


@pytest.mark.asyncio
async def test_provider_status_and_saved_progress_survive_wrapping(setup, monkeypatch):
    from content_core.common.exceptions import AudioTranscriptionError

    source, config = setup

    async def transcribe(path):
        if Path(path).read_text() == "60":
            error = RuntimeError("private upstream body")
            error.status_code = 502
            raise error
        return SimpleNamespace(text="saved")

    monkeypatch.setattr(
        audio,
        "_create_stt_model",
        lambda *args: SimpleNamespace(atranscribe=transcribe),
    )
    with pytest.raises(AudioTranscriptionError) as result:
        await audio.transcribe_audio(str(source), config)
    assert (
        result.value.chunk,
        result.value.total,
        result.value.saved,
        result.value.status,
    ) == (2, 3, 1, 502)
    assert "private" not in str(result.value)


@pytest.mark.asyncio
async def test_corrupt_later_checkpoint_blocks_all_paid_calls(setup, monkeypatch):
    source, config = setup
    transcribe = AsyncMock(return_value=SimpleNamespace(text="saved"))
    monkeypatch.setattr(
        audio,
        "_create_stt_model",
        lambda *args: SimpleNamespace(atranscribe=transcribe),
    )
    await audio.transcribe_audio(str(source), config)
    entries = sorted(Path(config.audio_checkpoint_dir).rglob("*.json"))
    entries[0].unlink()  # unfinished first chunk, corrupt later saved chunk
    entries[-1].write_text("invalid JSON")
    transcribe.reset_mock()
    with pytest.raises(FileOperationError):
        await audio.transcribe_audio(str(source), config)
    transcribe.assert_not_awaited()


@pytest.mark.asyncio
async def test_cancellation_releases_lock_and_closes_clients(setup, monkeypatch):
    import httpx

    source, config = setup
    entered = asyncio.Event()

    async def transcribe(path):
        entered.set()
        await asyncio.Event().wait()

    client = httpx.Client()
    async_client = httpx.AsyncClient()
    model = SimpleNamespace(
        atranscribe=transcribe, client=client, async_client=async_client
    )
    monkeypatch.setattr(audio, "_create_stt_model", lambda *args: model)
    task = asyncio.create_task(audio.transcribe_audio(str(source), config))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert client.is_closed and async_client.is_closed
    model.atranscribe = AsyncMock(return_value=SimpleNamespace(text="resumed"))
    result = await audio.transcribe_audio(str(source), config)
    assert result.content == "resumed resumed resumed"


def test_checkpoint_disk_error_is_permanent(tmp_path, monkeypatch):
    source = tmp_path / "audio.wav"
    source.write_bytes(b"audio")
    checkpoint = AudioCheckpoint(str(tmp_path / "cache"), str(source), {})

    def no_space(*args):
        raise OSError("disk full with private path")

    monkeypatch.setattr(checkpoint, "_save", no_space)
    with pytest.raises(FileOperationError, match="already be billed") as error:
        checkpoint.save("chunk", "transcript")
    assert "private path" not in str(error.value)
    checkpoint.close()
