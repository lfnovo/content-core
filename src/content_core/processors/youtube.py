import re
import ssl

import aiohttp
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore
from youtube_transcript_api.formatters import TextFormatter  # type: ignore

from content_core.common import ProcessSourceState
from content_core.common.exceptions import NoTranscriptFound
from content_core.common.retry import retry_youtube
from content_core.config import CONFIG
from content_core.logging import logger

ssl._create_default_https_context = ssl._create_unverified_context


@retry_youtube()
async def _fetch_video_title(video_id):
    """Internal function that fetches video title - wrapped with retry logic."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    async with aiohttp.ClientSession(trust_env=True) as session:
        async with session.get(url) as response:
            html = await response.text()

    # BeautifulSoup doesn't support async operations
    soup = BeautifulSoup(html, "html.parser")

    # YouTube stores title in a meta tag
    title = soup.find("meta", property="og:title")["content"]
    return title


async def get_video_title(video_id):
    """Get video title from YouTube, with retry logic for transient failures."""
    try:
        return await _fetch_video_title(video_id)
    except Exception as e:
        logger.error(f"Failed to get video title after retries: {e}")
        return None


async def _extract_youtube_id(url):
    """
    Extract the YouTube video ID from a given URL using regular expressions.

    Args:
    url (str): The YouTube URL from which to extract the video ID.

    Returns:
    str: The extracted YouTube video ID or None if no valid ID is found.
    """
    # Define a regular expression pattern to capture the YouTube video ID
    youtube_regex = (
        r"(?:https?://)?"  # Optional scheme
        r"(?:www\.)?"  # Optional www.
        r"(?:"
        r"youtu\.be/"  # Shortened URL
        r"|youtube\.com"  # Main URL
        r"(?:"  # Group start
        r"/embed/"  # Embed URL
        r"|/v/"  # Older video URL
        r"|/watch\?v="  # Standard watch URL
        r"|/watch\?.+&v="  # Other watch URL
        r")"  # Group end
        r")"  # End main group
        r"([\w-]{11})"  # 11 characters (YouTube video ID)
    )

    # Search the URL for the pattern
    match = re.search(youtube_regex, url)

    # Return the video ID if a match is found
    return match.group(1) if match else None


@retry_youtube()
async def _fetch_best_transcript(video_id, preferred_langs=["en", "es", "pt"]):
    """Internal function that fetches transcript - wrapped with retry logic."""
    # youtube-transcript-api uses requests which respects HTTP_PROXY env var
    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

    # First try: Manual transcripts in preferred languages
    manual_transcripts = []
    try:
        for transcript in transcript_list:
            if not transcript.is_generated and not transcript.is_translatable:
                manual_transcripts.append(transcript)

        if manual_transcripts:
            # Sort based on preferred language order
            for lang in preferred_langs:
                for transcript in manual_transcripts:
                    if transcript.language_code == lang:
                        return transcript.fetch()
            # If no preferred language found, return first manual transcript
            return manual_transcripts[0].fetch()
    except NoTranscriptFound:
        pass

    # Second try: Auto-generated transcripts in preferred languages
    generated_transcripts = []
    try:
        for transcript in transcript_list:
            if transcript.is_generated and not transcript.is_translatable:
                generated_transcripts.append(transcript)

        if generated_transcripts:
            # Sort based on preferred language order
            for lang in preferred_langs:
                for transcript in generated_transcripts:
                    if transcript.language_code == lang:
                        return transcript.fetch()
            # If no preferred language found, return first generated transcript
            return generated_transcripts[0].fetch()
    except NoTranscriptFound:
        pass

    # Last try: Translated transcripts in preferred languages
    translated_transcripts = []
    try:
        for transcript in transcript_list:
            if transcript.is_translatable:
                translated_transcripts.append(transcript)

        if translated_transcripts:
            # Sort based on preferred language order
            for lang in preferred_langs:
                for transcript in translated_transcripts:
                    if transcript.language_code == lang:
                        return transcript.fetch()
            # If no preferred language found, return translation to first preferred language
            translation = translated_transcripts[0].translate(preferred_langs[0])
            return translation.fetch()
    except NoTranscriptFound:
        pass

    raise NoTranscriptFound("No suitable transcript found for this video")


async def get_best_transcript(video_id, preferred_langs=["en", "es", "pt"]):
    """Get best available transcript with retry logic for transient failures."""
    try:
        return await _fetch_best_transcript(video_id, preferred_langs)
    except Exception as e:
        logger.error(
            f"Failed to get transcript for video {video_id} after retries: {e}"
        )
        return None


@retry_youtube()
def _fetch_transcript_pytubefix(url, languages=["en", "es", "pt"]):
    """Internal function that fetches transcript via pytubefix - wrapped with retry logic."""
    from pytubefix import YouTube

    # pytubefix uses requests which respects HTTP_PROXY env var
    yt = YouTube(url)
    logger.debug(f"Captions: {yt.captions}")

    # Try to get captions in the preferred languages
    if yt.captions:
        for lang in languages:
            if lang in yt.captions:
                caption = yt.captions[lang]
                break
            elif f"a.{lang}" in yt.captions:
                caption = yt.captions[f"a.{lang}"]
                break
        else:  # No preferred language found, use the first available
            caption_key = list(yt.captions.keys())[0]
            caption = yt.captions[caption_key.code]

        srt_captions = caption.generate_srt_captions()
        txt_captions = caption.generate_txt_captions()
        return txt_captions, srt_captions

    return None, None


def extract_transcript_pytubefix(url, languages=["en", "es", "pt"]):
    """Extract transcript via pytubefix with retry logic for transient failures."""
    try:
        return _fetch_transcript_pytubefix(url, languages)
    except Exception as e:
        logger.error(f"Failed to extract transcript via pytubefix after retries: {e}")
        return None, None


async def extract_youtube_transcript(state: ProcessSourceState):
    """
    Parse the text file and print its content.

    Proxy is configured via standard HTTP_PROXY/HTTPS_PROXY environment variables.
    """

    assert state.url, "No URL provided"
    logger.debug(f"Extracting transcript from URL: {state.url}")
    languages = CONFIG.get("youtube_transcripts", {}).get(
        "preferred_languages", ["en", "es", "pt"]
    )

    # quick fix since transcripts api is not working for now
    engine = "pytubefix"
    video_id = await _extract_youtube_id(state.url)

    try:
        title = await get_video_title(video_id)
    except Exception as e:
        logger.critical(f"Failed to get video title for video_id: {video_id}")
        logger.exception(e)
        title = ""

    if engine == "pytubefix":
        formatted_content, transcript_raw = extract_transcript_pytubefix(
            state.url, languages
        )
    if engine == "transcripts-api":
        transcript = await get_best_transcript(video_id, languages)

        logger.debug(f"Found transcript: {transcript}")
        formatter = TextFormatter()

        try:
            formatted_content = formatter.format_transcript(transcript)
        except Exception as e:
            logger.critical(f"Failed to format transcript for video_id: {video_id}")
            logger.exception(e)
            formatted_content = ""

        try:
            transcript_raw = transcript.to_raw_data()
        except Exception as e:
            logger.critical(f"Failed to get raw transcript for video_id: {video_id}")
            logger.exception(e)
            transcript_raw = ""

    return {
        "content": formatted_content,
        "title": title,
        "metadata": {"video_id": video_id, "transcript": transcript_raw},
    }
