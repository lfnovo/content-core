# Audio & Video Transcription

Content Core transcribes audio and video files using speech-to-text models with parallel processing for improved performance.

## Supported Formats

### Audio
- MP3, WAV, M4A, FLAC, OGG

### Video
- MP4, AVI, MOV, MKV
- Audio is automatically extracted before transcription

## How It Works

1. **Automatic Segmentation:** Files longer than 10 minutes are split into segments
2. **Parallel Transcription:** Multiple segments transcribed concurrently
3. **Concurrency Control:** Semaphore prevents API rate limiting
4. **Result Assembly:** Transcriptions joined in correct order

## Configuration

### Default Model

By default, Content Core uses OpenAI Whisper:

```yaml
speech_to_text:
  provider: openai
  model_name: whisper-1
  timeout: 3600  # 1 hour for long files
```

### Concurrency

Control parallel transcription:

```bash
# Environment variable
export CCORE_AUDIO_CONCURRENCY=3  # 1-10, default: 3
```

```yaml
# YAML configuration
extraction:
  audio:
    concurrency: 5
```

```python
# Python
from content_core.config import set_audio_concurrency
set_audio_concurrency(5)
```

**Recommendations:**

| Concurrency | Best For |
|-------------|----------|
| 1-2 | Conservative, batch processing |
| 3-5 | Most use cases (recommended) |
| 6-10 | Very long files, premium API |

### Custom Audio Model

Override the speech-to-text model per request:

```python
from content_core.common import ProcessSourceInput
import content_core as cc

result = await cc.extract(ProcessSourceInput(
    file_path="interview.mp3",
    audio_provider="openai",
    audio_model="whisper-1"
))
```

**Note:** Both `audio_provider` and `audio_model` must be specified together.

## Performance

**Processing Times (60-minute audio file):**

| Concurrency | Approximate Time |
|-------------|------------------|
| 1 | ~15-20 minutes |
| 3 | ~5-7 minutes |
| 10 | ~2-3 minutes |

## Timeout Configuration

Audio transcription uses longer timeouts due to file size:

```bash
export ESPERANTO_STT_TIMEOUT=3600  # 1 hour default
```

```yaml
speech_to_text:
  provider: openai
  model_name: whisper-1
  timeout: 3600
```

## Retry Configuration

Automatic retry on transient failures:

```bash
export CCORE_AUDIO_MAX_RETRIES=3
export CCORE_AUDIO_BASE_DELAY=2
export CCORE_AUDIO_MAX_DELAY=30
```

## Use Cases

### Podcast Transcription

```python
from content_core.config import set_audio_concurrency
import content_core as cc

# Higher concurrency for long podcasts
set_audio_concurrency(7)
result = await cc.extract({"file_path": "podcast_2h.mp3"})
```

### Batch Processing

```python
from content_core.config import set_audio_concurrency
import content_core as cc

# Lower concurrency for batch jobs
set_audio_concurrency(2)

for audio_file in audio_files:
    result = await cc.extract({"file_path": audio_file})
```

### Video Transcription

```python
import content_core as cc

# Audio extracted automatically
result = await cc.extract({"file_path": "conference_talk.mp4"})
print(result.content)  # Full transcript
```

## Supported Providers

Content Core uses [Esperanto](https://github.com/lfnovo/esperanto) for model abstraction:

| Provider | Models |
|----------|--------|
| OpenAI | whisper-1 |
| Google | chirp (if available) |

## Gotchas

1. **API costs:** Long files = more API calls
2. **Rate limits:** Higher concurrency may hit limits
3. **Memory:** Large files need adequate RAM
4. **Video extraction:** Uses moviepy for audio extraction

## Error Handling

Content Core handles errors gracefully:

- Invalid provider/model: Falls back to default
- API failures: Automatic retry with backoff
- Partial failures: Other segments continue

```python
# If only one parameter provided, warning logged
result = await cc.extract(ProcessSourceInput(
    file_path="audio.mp3",
    audio_provider="openai"  # Missing audio_model
))
# Logs: "audio_provider provided without audio_model. Falling back to default."
```

## Dependencies

Audio/video processing requires:

```bash
# Included by default
pip install content-core

# For video support (included)
# moviepy is used for video-to-audio conversion
```
