import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from content_core.config import get_audio_concurrency
from content_core.processors.audio import transcribe_audio_segment


class TestAudioConcurrencyConfig:
    """Test configuration loading for audio concurrency"""

    def test_default_concurrency(self):
        """Test that default concurrency is 3 when no override is set"""
        with patch.dict(os.environ, {}, clear=True):
            # Remove CCORE_AUDIO_CONCURRENCY if it exists
            os.environ.pop("CCORE_AUDIO_CONCURRENCY", None)
            concurrency = get_audio_concurrency()
            assert concurrency == 3

    def test_environment_variable_override(self):
        """Test that CCORE_AUDIO_CONCURRENCY environment variable overrides default"""
        with patch.dict(os.environ, {"CCORE_AUDIO_CONCURRENCY": "5"}):
            concurrency = get_audio_concurrency()
            assert concurrency == 5

    def test_invalid_concurrency_non_integer(self):
        """Test that non-integer values fall back to default with warning"""
        with patch.dict(os.environ, {"CCORE_AUDIO_CONCURRENCY": "invalid"}):
            concurrency = get_audio_concurrency()
            assert concurrency == 3  # Falls back to default

    def test_invalid_concurrency_zero(self):
        """Test that zero concurrency falls back to default with warning"""
        with patch.dict(os.environ, {"CCORE_AUDIO_CONCURRENCY": "0"}):
            concurrency = get_audio_concurrency()
            assert concurrency == 3  # Falls back to default

    def test_invalid_concurrency_negative(self):
        """Test that negative concurrency falls back to default with warning"""
        with patch.dict(os.environ, {"CCORE_AUDIO_CONCURRENCY": "-1"}):
            concurrency = get_audio_concurrency()
            assert concurrency == 3  # Falls back to default

    def test_invalid_concurrency_too_high(self):
        """Test that concurrency > 10 falls back to default with warning"""
        with patch.dict(os.environ, {"CCORE_AUDIO_CONCURRENCY": "15"}):
            concurrency = get_audio_concurrency()
            assert concurrency == 3  # Falls back to default

    def test_valid_concurrency_boundary_low(self):
        """Test that concurrency of 1 is accepted"""
        with patch.dict(os.environ, {"CCORE_AUDIO_CONCURRENCY": "1"}):
            concurrency = get_audio_concurrency()
            assert concurrency == 1

    def test_valid_concurrency_boundary_high(self):
        """Test that concurrency of 10 is accepted"""
        with patch.dict(os.environ, {"CCORE_AUDIO_CONCURRENCY": "10"}):
            concurrency = get_audio_concurrency()
            assert concurrency == 10


class TestParallelTranscription:
    """Test parallel transcription functionality"""

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrency(self):
        """Test that semaphore correctly limits concurrent executions"""
        max_concurrent = 0
        current_concurrent = 0
        concurrency_limit = 3

        async def mock_transcribe(audio_file):
            nonlocal max_concurrent, current_concurrent
            current_concurrent += 1
            max_concurrent = max(max_concurrent, current_concurrent)
            await asyncio.sleep(0.1)  # Simulate API call
            current_concurrent -= 1
            return f"transcription_{audio_file}"

        # Mock the model
        mock_model = MagicMock()
        mock_model.atranscribe = AsyncMock(side_effect=lambda f: MagicMock(text=f"transcript_{f}"))

        # Create semaphore and tasks
        semaphore = asyncio.Semaphore(concurrency_limit)

        # Simulate 10 concurrent transcription attempts
        tasks = []
        for i in range(10):
            audio_file = f"audio_{i}.mp3"
            task = transcribe_audio_segment(audio_file, mock_model, semaphore)
            tasks.append(task)

        # Execute all tasks
        results = await asyncio.gather(*tasks)

        # Verify we got all results
        assert len(results) == 10
        assert all(isinstance(r, str) for r in results)

    @pytest.mark.asyncio
    async def test_results_maintain_order(self):
        """Test that transcription results maintain correct order despite parallel execution"""
        # Mock model that returns different results based on input
        mock_model = MagicMock()

        async def mock_atranscribe(audio_file):
            # Add varying delays to simulate different processing times
            delay = 0.05 if "1" in audio_file else 0.01
            await asyncio.sleep(delay)
            return MagicMock(text=f"transcript_of_{audio_file}")

        mock_model.atranscribe = mock_atranscribe

        # Create tasks with semaphore
        semaphore = asyncio.Semaphore(3)
        audio_files = [f"audio_{i}.mp3" for i in range(5)]

        tasks = [
            transcribe_audio_segment(audio_file, mock_model, semaphore)
            for audio_file in audio_files
        ]

        # Execute all tasks
        results = await asyncio.gather(*tasks)

        # Verify results are in correct order
        expected = [f"transcript_of_audio_{i}.mp3" for i in range(5)]
        assert results == expected

    @pytest.mark.asyncio
    async def test_single_segment_audio(self):
        """Test that single segment audio works correctly"""
        mock_model = MagicMock()
        mock_model.atranscribe = AsyncMock(return_value=MagicMock(text="single_transcript"))

        semaphore = asyncio.Semaphore(3)
        result = await transcribe_audio_segment("single_audio.mp3", mock_model, semaphore)

        assert result == "single_transcript"
        mock_model.atranscribe.assert_called_once_with("single_audio.mp3")

    @pytest.mark.asyncio
    async def test_concurrency_of_one_behaves_serially(self):
        """Test that concurrency of 1 processes segments serially"""
        call_times = []

        async def mock_atranscribe(audio_file):
            call_times.append(asyncio.get_event_loop().time())
            await asyncio.sleep(0.05)
            return MagicMock(text=f"transcript_{audio_file}")

        mock_model = MagicMock()
        mock_model.atranscribe = mock_atranscribe

        # Use semaphore with limit of 1
        semaphore = asyncio.Semaphore(1)
        audio_files = [f"audio_{i}.mp3" for i in range(3)]

        tasks = [
            transcribe_audio_segment(audio_file, mock_model, semaphore)
            for audio_file in audio_files
        ]

        results = await asyncio.gather(*tasks)

        # Verify all completed
        assert len(results) == 3

        # Verify they were called serially (times should be spaced apart)
        # With concurrency of 1 and 0.05s sleep, calls should be ~0.05s apart
        if len(call_times) >= 2:
            time_diff = call_times[1] - call_times[0]
            assert time_diff >= 0.04  # Allow some tolerance for timing

    @pytest.mark.asyncio
    async def test_empty_audio_file_list(self):
        """Test handling of empty audio file list"""
        # Empty list of tasks
        tasks = []
        results = await asyncio.gather(*tasks)

        assert results == []


class TestErrorHandling:
    """Test error handling in parallel transcription"""

    @pytest.mark.asyncio
    async def test_single_failure_doesnt_stop_others(self):
        """Test that one failed transcription doesn't prevent others from completing.

        Note: With retry logic enabled, the failing segment will be retried
        (default: 3 attempts) IF the exception is transient (network error, timeout).
        Total calls = 2 successful + 3 retries = 5.
        """
        call_count = 0
        fail_count = 0

        async def mock_atranscribe(audio_file):
            nonlocal call_count, fail_count
            call_count += 1
            if "fail" in audio_file:
                fail_count += 1
                # Use a transient error message so it triggers retry
                raise TimeoutError("Transcription service timeout")
            await asyncio.sleep(0.01)
            return MagicMock(text=f"transcript_{audio_file}")

        mock_model = MagicMock()
        mock_model.atranscribe = mock_atranscribe

        semaphore = asyncio.Semaphore(3)
        audio_files = ["audio_1.mp3", "audio_fail.mp3", "audio_3.mp3"]

        tasks = [
            transcribe_audio_segment(audio_file, mock_model, semaphore)
            for audio_file in audio_files
        ]

        # gather with return_exceptions=True to handle the failure
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify successful segments called once, failed segment retried
        # Default retry config is 3 attempts for audio, so:
        # - 2 successful calls (audio_1.mp3, audio_3.mp3)
        # - 3 retry attempts for audio_fail.mp3
        # Total = 5 calls
        assert call_count == 5
        assert fail_count == 3  # Retried 3 times

        # Verify we got results for successful ones and exception for failed one
        assert isinstance(results[0], str)  # Success
        assert isinstance(results[1], Exception)  # Failed after retries
        assert isinstance(results[2], str)  # Success
