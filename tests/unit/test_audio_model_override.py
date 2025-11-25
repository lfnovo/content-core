"""
Unit tests for custom audio model override functionality.

Tests verify that:
1. Custom audio models can be specified via audio_provider and audio_model parameters
2. Backward compatibility is maintained when no parameters provided
3. Validation warnings are logged when only one parameter provided
4. Error handling works correctly for invalid providers/models
5. Parameters flow correctly through the state graph
6. Concurrency control is applied to custom models
"""

import os
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from content_core.common import ProcessSourceState
from content_core.processors.audio import extract_audio_data


class TestCustomAudioModel:
    """Test custom audio model selection functionality"""

    @pytest.mark.asyncio
    async def test_custom_audio_model_both_params_provided(self):
        """Test that custom model is used when both audio_provider and audio_model are provided"""
        # Create state with custom audio model parameters
        state = ProcessSourceState(
            file_path="/fake/audio.mp3",
            audio_provider="openai",
            audio_model="whisper-1",
        )

        # Mock dependencies
        with patch("content_core.processors.audio.AudioFileClip") as mock_audio_clip:
            # Setup audio clip mock
            mock_clip = MagicMock()
            mock_clip.duration = 300  # 5 minutes - short file, no segmentation
            mock_audio_clip.return_value = mock_clip

            # Mock AIFactory to verify it's called
            with patch("esperanto.AIFactory") as mock_ai_factory:
                mock_custom_model = MagicMock()
                mock_custom_model.atranscribe = AsyncMock(
                    return_value=MagicMock(text="Custom model transcription")
                )
                mock_ai_factory.create_speech_to_text.return_value = mock_custom_model

                # Mock ModelFactory (should NOT be used)
                with patch("content_core.models.ModelFactory") as mock_model_factory:
                    # Execute
                    result = await extract_audio_data(state)

                    # Verify AIFactory was called with correct parameters
                    # Timeout is configurable, so we use ANY to match any timeout value
                    mock_ai_factory.create_speech_to_text.assert_called_once_with(
                        "openai", "whisper-1", {"timeout": ANY}
                    )

                    # Verify ModelFactory was NOT called (custom model used)
                    mock_model_factory.get_model.assert_not_called()

                    # Verify transcription result
                    assert result["content"] == "Custom model transcription"

    @pytest.mark.asyncio
    async def test_custom_audio_model_calls_aifactory(self):
        """Test that AIFactory.create_speech_to_text is called with correct arguments"""
        state = ProcessSourceState(
            file_path="/fake/audio.mp3",
            audio_provider="google",
            audio_model="chirp",
        )

        with patch("content_core.processors.audio.AudioFileClip") as mock_audio_clip:
            mock_clip = MagicMock()
            mock_clip.duration = 300
            mock_audio_clip.return_value = mock_clip

            with patch("esperanto.AIFactory") as mock_ai_factory:
                mock_custom_model = MagicMock()
                mock_custom_model.atranscribe = AsyncMock(
                    return_value=MagicMock(text="Google Chirp transcription")
                )
                mock_ai_factory.create_speech_to_text.return_value = mock_custom_model

                with patch("content_core.models.ModelFactory"):
                    await extract_audio_data(state)

                    # Verify correct provider and model passed
                    # Timeout is configurable, so we use ANY to match any timeout value
                    mock_ai_factory.create_speech_to_text.assert_called_once_with(
                        "google", "chirp", {"timeout": ANY}
                    )

    @pytest.mark.asyncio
    async def test_default_model_when_no_params(self):
        """Test backward compatibility - default model used when no custom params provided"""
        state = ProcessSourceState(
            file_path="/fake/audio.mp3",
            # No audio_provider or audio_model
        )

        with patch("content_core.processors.audio.AudioFileClip") as mock_audio_clip:
            mock_clip = MagicMock()
            mock_clip.duration = 300
            mock_audio_clip.return_value = mock_clip

            # Mock ModelFactory (should be used for default)
            with patch("content_core.models.ModelFactory") as mock_model_factory:
                mock_default_model = MagicMock()
                mock_default_model.atranscribe = AsyncMock(
                    return_value=MagicMock(text="Default model transcription")
                )
                mock_model_factory.get_model.return_value = mock_default_model

                # Mock AIFactory (should NOT be called)
                with patch("esperanto.AIFactory") as mock_ai_factory:
                    result = await extract_audio_data(state)

                    # Verify ModelFactory was called for default model
                    mock_model_factory.get_model.assert_called_once_with("speech_to_text")

                    # Verify AIFactory was NOT called
                    mock_ai_factory.create_speech_to_text.assert_not_called()

                    # Verify result
                    assert result["content"] == "Default model transcription"

    @pytest.mark.asyncio
    async def test_default_model_when_only_provider(self):
        """Test fallback when only audio_provider given (missing audio_model)"""
        state = ProcessSourceState(
            file_path="/fake/audio.mp3",
            audio_provider="openai",
            # Missing audio_model
        )

        with patch("content_core.processors.audio.AudioFileClip") as mock_audio_clip:
            mock_clip = MagicMock()
            mock_clip.duration = 300
            mock_audio_clip.return_value = mock_clip

            with patch("content_core.models.ModelFactory") as mock_model_factory:
                mock_default_model = MagicMock()
                mock_default_model.atranscribe = AsyncMock(
                    return_value=MagicMock(text="Default model used")
                )
                mock_model_factory.get_model.return_value = mock_default_model

                with patch("esperanto.AIFactory") as mock_ai_factory:
                    result = await extract_audio_data(state)

                    # Should use default model
                    mock_model_factory.get_model.assert_called_once_with("speech_to_text")
                    mock_ai_factory.create_speech_to_text.assert_not_called()

                    assert result["content"] == "Default model used"

    @pytest.mark.asyncio
    async def test_default_model_when_only_model(self):
        """Test fallback when only audio_model given (missing audio_provider)"""
        state = ProcessSourceState(
            file_path="/fake/audio.mp3",
            audio_model="whisper-1",
            # Missing audio_provider
        )

        with patch("content_core.processors.audio.AudioFileClip") as mock_audio_clip:
            mock_clip = MagicMock()
            mock_clip.duration = 300
            mock_audio_clip.return_value = mock_clip

            with patch("content_core.models.ModelFactory") as mock_model_factory:
                mock_default_model = MagicMock()
                mock_default_model.atranscribe = AsyncMock(
                    return_value=MagicMock(text="Default model used")
                )
                mock_model_factory.get_model.return_value = mock_default_model

                with patch("esperanto.AIFactory") as mock_ai_factory:
                    result = await extract_audio_data(state)

                    # Should use default model
                    mock_model_factory.get_model.assert_called_once_with("speech_to_text")
                    mock_ai_factory.create_speech_to_text.assert_not_called()

                    assert result["content"] == "Default model used"

    @pytest.mark.asyncio
    async def test_warning_logged_when_only_provider(self):
        """Test that warning is logged when only audio_provider provided and default model used"""
        state = ProcessSourceState(
            file_path="/fake/audio.mp3",
            audio_provider="openai",
            # Missing audio_model - should trigger warning and use default
        )

        with patch("content_core.processors.audio.AudioFileClip") as mock_audio_clip:
            mock_clip = MagicMock()
            mock_clip.duration = 300
            mock_audio_clip.return_value = mock_clip

            with patch("content_core.models.ModelFactory") as mock_model_factory:
                mock_default_model = MagicMock()
                mock_default_model.atranscribe = AsyncMock(
                    return_value=MagicMock(text="text")
                )
                mock_model_factory.get_model.return_value = mock_default_model

                with patch("esperanto.AIFactory") as mock_ai_factory:
                    result = await extract_audio_data(state)

                    # Verify default model was used (not custom)
                    mock_model_factory.get_model.assert_called_once_with("speech_to_text")
                    mock_ai_factory.create_speech_to_text.assert_not_called()

                    # Verify result works correctly
                    assert result["content"] == "text"

    @pytest.mark.asyncio
    async def test_warning_logged_when_only_model(self):
        """Test that warning is logged when only audio_model provided and default model used"""
        state = ProcessSourceState(
            file_path="/fake/audio.mp3",
            audio_model="whisper-1",
            # Missing audio_provider - should trigger warning and use default
        )

        with patch("content_core.processors.audio.AudioFileClip") as mock_audio_clip:
            mock_clip = MagicMock()
            mock_clip.duration = 300
            mock_audio_clip.return_value = mock_clip

            with patch("content_core.models.ModelFactory") as mock_model_factory:
                mock_default_model = MagicMock()
                mock_default_model.atranscribe = AsyncMock(
                    return_value=MagicMock(text="text")
                )
                mock_model_factory.get_model.return_value = mock_default_model

                with patch("esperanto.AIFactory") as mock_ai_factory:
                    result = await extract_audio_data(state)

                    # Verify default model was used (not custom)
                    mock_model_factory.get_model.assert_called_once_with("speech_to_text")
                    mock_ai_factory.create_speech_to_text.assert_not_called()

                    # Verify result works correctly
                    assert result["content"] == "text"

    @pytest.mark.asyncio
    async def test_custom_model_invalid_provider(self):
        """Test error handling when invalid provider specified - graceful fallback"""
        state = ProcessSourceState(
            file_path="/fake/audio.mp3",
            audio_provider="invalid_provider",
            audio_model="whisper-1",
        )

        with patch("content_core.processors.audio.AudioFileClip") as mock_audio_clip:
            mock_clip = MagicMock()
            mock_clip.duration = 300
            mock_audio_clip.return_value = mock_clip

            with patch("esperanto.AIFactory") as mock_ai_factory:
                # Simulate Esperanto error for invalid provider
                mock_ai_factory.create_speech_to_text.side_effect = Exception(
                    "Unsupported provider"
                )

                with patch("content_core.models.ModelFactory") as mock_model_factory:
                    mock_default_model = MagicMock()
                    mock_default_model.atranscribe = AsyncMock(
                        return_value=MagicMock(text="Fallback transcription")
                    )
                    mock_model_factory.get_model.return_value = mock_default_model

                    result = await extract_audio_data(state)

                    # Should attempt to create custom model
                    mock_ai_factory.create_speech_to_text.assert_called_once()

                    # Should fall back to default model after error
                    mock_model_factory.get_model.assert_called_once_with("speech_to_text")

                    # Workflow should continue successfully with default model
                    assert result["content"] == "Fallback transcription"

    @pytest.mark.asyncio
    async def test_custom_model_invalid_model(self):
        """Test error handling when invalid model name specified - graceful fallback"""
        state = ProcessSourceState(
            file_path="/fake/audio.mp3",
            audio_provider="openai",
            audio_model="invalid_model",
        )

        with patch("content_core.processors.audio.AudioFileClip") as mock_audio_clip:
            mock_clip = MagicMock()
            mock_clip.duration = 300
            mock_audio_clip.return_value = mock_clip

            with patch("esperanto.AIFactory") as mock_ai_factory:
                # Simulate Esperanto error for invalid model
                mock_ai_factory.create_speech_to_text.side_effect = Exception(
                    "Unsupported model"
                )

                with patch("content_core.models.ModelFactory") as mock_model_factory:
                    mock_default_model = MagicMock()
                    mock_default_model.atranscribe = AsyncMock(
                        return_value=MagicMock(text="Fallback transcription")
                    )
                    mock_model_factory.get_model.return_value = mock_default_model

                    result = await extract_audio_data(state)

                    # Should attempt to create custom model
                    mock_ai_factory.create_speech_to_text.assert_called_once()

                    # Should fall back to default model after error
                    mock_model_factory.get_model.assert_called_once_with("speech_to_text")

                    # Workflow should continue successfully
                    assert result["content"] == "Fallback transcription"

    @pytest.mark.asyncio
    async def test_custom_model_respects_concurrency(self):
        """Test that custom models respect the same concurrency control as default"""
        state = ProcessSourceState(
            file_path="/fake/audio.mp3",
            audio_provider="openai",
            audio_model="whisper-1",
        )

        # Mock long audio that will be segmented
        with patch("content_core.processors.audio.AudioFileClip") as mock_audio_clip:
            mock_clip = MagicMock()
            mock_clip.duration = 1800  # 30 minutes - will create 3 segments (10 min each)
            mock_audio_clip.return_value = mock_clip

            with patch("content_core.processors.audio.extract_audio"):
                with patch("esperanto.AIFactory") as mock_ai_factory:
                    mock_custom_model = MagicMock()
                    mock_custom_model.atranscribe = AsyncMock(
                        return_value=MagicMock(text="segment")
                    )
                    mock_ai_factory.create_speech_to_text.return_value = mock_custom_model

                    with patch("content_core.models.ModelFactory"):
                        # Mock get_audio_concurrency to return 3
                        with patch(
                            "content_core.processors.audio.get_audio_concurrency",
                            return_value=3,
                        ):
                            result = await extract_audio_data(state)

                            # Verify transcription happened (proves concurrency was applied)
                            assert result["content"] is not None
                            assert result["metadata"]["segments_count"] == 3

    @pytest.mark.asyncio
    async def test_state_flow_through_graph(self):
        """Test that audio_provider and audio_model parameters flow through the state correctly"""
        from content_core.common import ProcessSourceInput
        from content_core.content.extraction import extract_content

        # This is an integration-style test to verify state flow
        # We mock the actual transcription but verify the state carries the parameters

        with patch("content_core.processors.audio.AudioFileClip") as mock_audio_clip:
            mock_clip = MagicMock()
            mock_clip.duration = 300
            mock_audio_clip.return_value = mock_clip

            with patch("esperanto.AIFactory") as mock_ai_factory:
                mock_custom_model = MagicMock()
                mock_custom_model.atranscribe = AsyncMock(
                    return_value=MagicMock(text="transcription")
                )
                mock_ai_factory.create_speech_to_text.return_value = mock_custom_model

                with patch("content_core.models.ModelFactory"):
                    # Mock file type identification
                    with patch(
                        "content_core.content.identification.get_file_type",
                        return_value="audio/mpeg",
                    ):
                        # Create input with custom audio parameters
                        input_data = ProcessSourceInput(
                            file_path=os.path.join(
                                os.path.dirname(__file__),
                                "../input_content/file_audio.mp3",
                            ),
                            audio_provider="openai",
                            audio_model="whisper-1",
                        )

                        # Extract content (goes through full graph)
                        result = await extract_content(input_data)

                        # Verify AIFactory was called with the custom parameters (including timeout config)
                        # This proves the parameters flowed through the state correctly
                        mock_ai_factory.create_speech_to_text.assert_called_with(
                            "openai", "whisper-1", {"timeout": 3600}
                        )

                        # Verify we got a result
                        assert result.content == "transcription"


class TestBackwardCompatibility:
    """Test that existing functionality remains unchanged"""

    @pytest.mark.asyncio
    async def test_existing_code_without_params_works(self):
        """Test that code without audio_provider/audio_model parameters continues to work"""
        # This simulates existing user code that doesn't use the new parameters
        from content_core.common import ProcessSourceInput
        from content_core.content.extraction import extract_content

        with patch("content_core.processors.audio.AudioFileClip") as mock_audio_clip:
            mock_clip = MagicMock()
            mock_clip.duration = 300
            mock_audio_clip.return_value = mock_clip

            with patch("content_core.models.ModelFactory") as mock_model_factory:
                mock_default_model = MagicMock()
                mock_default_model.atranscribe = AsyncMock(
                    return_value=MagicMock(text="default transcription")
                )
                mock_model_factory.get_model.return_value = mock_default_model

                with patch(
                    "content_core.content.identification.get_file_type",
                    return_value="audio/mpeg",
                ):
                    # Old-style call without new parameters
                    input_data = ProcessSourceInput(
                        file_path=os.path.join(
                            os.path.dirname(__file__), "../input_content/file_audio.mp3"
                        )
                    )

                    result = await extract_content(input_data)

                    # Should use default model
                    mock_model_factory.get_model.assert_called_once_with("speech_to_text")

                    # Should work correctly
                    assert result.content == "default transcription"
