import http.cookiejar
import os
import re
import ssl

import aiohttp
import requests
from bs4 import BeautifulSoup
import youtube_transcript_api as yta  # type: ignore
from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore
from youtube_transcript_api.formatters import TextFormatter  # type: ignore
from youtube_transcript_api.proxies import GenericProxyConfig  # type: ignore

from content_core.common.exceptions import (
    ConfigurationError,
    ContentCoreError,
    ExternalServiceError,
    InvalidInputError,
    NoTranscriptFound,
)
from content_core.common.retry import retry_youtube
from content_core.config import ContentCoreConfig
from content_core.logging import logger
from content_core.common.state import ExtractionOutput

ssl._create_default_https_context = ssl._create_unverified_context


@retry_youtube()
async def _fetch_video_title(video_id, proxy=None):
    """Internal function that fetches video title - wrapped with retry logic.

    ``proxy`` (``youtube_proxy``) takes precedence over the env-var proxies
    that ``trust_env`` honors.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    async with aiohttp.ClientSession(trust_env=True) as session:
        async with session.get(url, proxy=proxy) as response:
            html = await response.text()

    # BeautifulSoup doesn't support async operations
    soup = BeautifulSoup(html, "html.parser")

    # YouTube stores title in a meta tag
    title = soup.find("meta", property="og:title")["content"]
    return title


async def get_video_title(video_id, proxy=None):
    """Get video title from YouTube, with retry logic for transient failures."""
    try:
        return await _fetch_video_title(video_id, proxy)
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
        r"|/live/"  # Livestream URL (active or ended)
        r"|/shorts/"  # Shorts URL
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


def _build_transcript_api(config: ContentCoreConfig) -> YouTubeTranscriptApi:
    """Build the youtube-transcript-api client from the YouTube settings.

    Neither ``youtube_cookies_file`` nor ``youtube_proxy`` set -> a bare
    ``YouTubeTranscriptApi()`` (anonymous, env-var proxies still honored).

    Raises:
        ConfigurationError: ``youtube_cookies_file`` is set but the file is
            missing, unreadable or not a Netscape cookies.txt.
    """
    kwargs = {}

    if config.youtube_cookies_file:
        path = os.path.expanduser(config.youtube_cookies_file)
        # Cookies are credentials: log the path only, never the jar/session.
        logger.debug(f"Using YouTube cookies file {path}")
        jar = http.cookiejar.MozillaCookieJar(path)
        try:
            jar.load(ignore_discard=True, ignore_expires=True)
        except http.cookiejar.LoadError:
            # LoadError messages quote the offending line, which may hold a
            # cookie value -- drop both the message and the chained cause.
            raise ConfigurationError(
                f"youtube_cookies_file {path!r} is not a valid Netscape "
                "cookies.txt file"
            ) from None
        except OSError as e:
            raise ConfigurationError(
                f"youtube_cookies_file {path!r} cannot be read: {e.strerror}"
            ) from None
        session = requests.Session()
        session.cookies = jar  # type: ignore[assignment]
        kwargs["http_client"] = session

    if config.youtube_proxy:
        kwargs["proxy_config"] = GenericProxyConfig(
            http_url=config.youtube_proxy, https_url=config.youtube_proxy
        )

    return YouTubeTranscriptApi(**kwargs)


# youtube-transcript-api outcomes that mean "this video has no usable
# transcript", as opposed to a failed request.
_NO_TRANSCRIPT_ERRORS = (yta.NoTranscriptFound, yta.TranscriptsDisabled)


@retry_youtube()
async def _fetch_best_transcript(
    video_id, preferred_langs=["en", "es", "pt"], api=None
):
    """Internal function that fetches transcript - wrapped with retry logic.

    Uses youtube-transcript-api v1.0+ instance-based API. Only "no
    transcript" outcomes become ``NoTranscriptFound``; any other failure of a
    lookup (e.g. ``IpBlocked`` on ``fetch()``) is re-raised once every lookup
    has been tried.
    """
    if api is None:
        api = YouTubeTranscriptApi()
    try:
        transcript_list = api.list(video_id)
    except _NO_TRANSCRIPT_ERRORS as e:
        raise NoTranscriptFound(f"No transcript available for video {video_id}") from e

    last_error = None

    # First try: Manual transcripts in preferred languages
    try:
        transcript = transcript_list.find_manually_created_transcript(preferred_langs)
        return transcript.fetch()
    except _NO_TRANSCRIPT_ERRORS:
        pass
    except Exception as e:
        last_error = e

    # Second try: Auto-generated transcripts in preferred languages
    try:
        transcript = transcript_list.find_generated_transcript(preferred_langs)
        return transcript.fetch()
    except _NO_TRANSCRIPT_ERRORS:
        pass
    except Exception as e:
        last_error = e

    # Third try: Any transcript in preferred languages (manual or generated)
    try:
        transcript = transcript_list.find_transcript(preferred_langs)
        return transcript.fetch()
    except _NO_TRANSCRIPT_ERRORS:
        pass
    except Exception as e:
        last_error = e

    # Last try: Direct fetch with language fallback
    try:
        return api.fetch(video_id, languages=preferred_langs)
    except _NO_TRANSCRIPT_ERRORS:
        pass
    except Exception as e:
        last_error = e

    if last_error is not None:
        raise last_error
    raise NoTranscriptFound("No suitable transcript found for this video")


async def get_best_transcript(
    video_id, preferred_langs=["en", "es", "pt"], api=None
):
    """Get best available transcript with retry logic for transient failures.

    ``api`` is a preconfigured ``YouTubeTranscriptApi`` (see
    ``_build_transcript_api``); ``None`` means an anonymous client.

    Raises ``NoTranscriptFound`` when the video has no usable transcript, or
    the provider's error (e.g. ``IpBlocked``) once retries are exhausted.
    """
    try:
        return await _fetch_best_transcript(video_id, preferred_langs, api)
    except Exception as e:
        logger.debug(
            f"Failed to get transcript for video {video_id} after retries: {e}"
        )
        raise


@retry_youtube()
def _fetch_transcript_pytubefix(url, languages=["en", "es", "pt"], proxy=None):
    """Internal function that fetches transcript via pytubefix - wrapped with retry logic."""
    from pytubefix import YouTube

    # Without an explicit proxy, pytubefix still respects the HTTP_PROXY env
    # var. It has no clean cookies-file support, so youtube_cookies_file only
    # applies to the youtube-transcript-api path; the proxy applies to both.
    if proxy:
        yt = YouTube(url, proxies={"http": proxy, "https": proxy})
    else:
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


def extract_transcript_pytubefix(url, languages=["en", "es", "pt"], proxy=None):
    """Extract transcript via pytubefix with retry logic for transient failures.

    Returns ``(None, None)`` when the video has no captions; raises the
    pytubefix error once retries are exhausted.
    """
    try:
        return _fetch_transcript_pytubefix(url, languages, proxy)
    except Exception as e:
        logger.debug(f"Failed to extract transcript via pytubefix after retries: {e}")
        raise


def _transcript_failure(video_id, errors):
    """Type a total transcript failure from the errors of both paths.

    Returns ``(exception, cause)``. Only "no transcript" on every path is
    ``NoTranscriptFound``; any other failure (blocked IP, provider error)
    wins, and an untyped one becomes ``ExternalServiceError``.
    """
    failures = [e for e in errors if not isinstance(e, NoTranscriptFound)]
    if not failures:
        cause = errors[0] if errors else None
        return NoTranscriptFound(f"No transcript found for video {video_id}"), cause
    first = failures[0]
    if isinstance(first, ContentCoreError):
        return first, first.__cause__
    return (
        ExternalServiceError(
            f"YouTube transcript extraction failed for video {video_id}: {first!r}"
        ),
        first,
    )


async def extract_youtube(url: str, config: ContentCoreConfig) -> ExtractionOutput:
    """Extract transcript from a YouTube video.

    youtube-transcript-api is tried first and pytubefix is the fallback; if
    neither yields a transcript, the failure raises.

    Raises:
        InvalidInputError: no video ID could be read from the URL.
        ConfigurationError: ``youtube_cookies_file`` cannot be used.
        NoTranscriptFound: the video has no usable transcript.
        ExternalServiceError: YouTube refused or failed the request on every
            path (e.g. ``IpBlocked``).
    """
    logger.debug(f"Extracting transcript from URL: {url}")
    languages = config.youtube_languages
    # Built first: an unusable cookies file is a configuration error and must
    # raise, not degrade to an anonymous request.
    api = _build_transcript_api(config)

    video_id = await _extract_youtube_id(url)
    if not video_id:
        raise InvalidInputError(f"Could not find a YouTube video ID in {url}")

    try:
        title = await get_video_title(video_id, proxy=config.youtube_proxy or None)
    except Exception as e:
        logger.critical(f"Failed to get video title for video_id: {video_id}")
        logger.exception(e)
        title = ""

    formatted_content = ""
    transcript_raw = None
    errors = []

    # Primary: youtube-transcript-api
    try:
        transcript = await get_best_transcript(video_id, languages, api=api)
    except Exception as e:
        logger.debug(f"youtube-transcript-api failed for {video_id}: {e}")
        errors.append(e)
        transcript = None
    if transcript:
        logger.debug("Found transcript via youtube-transcript-api")
        formatter = TextFormatter()

        try:
            formatted_content = formatter.format_transcript(transcript)
        except Exception as e:
            logger.error(f"Failed to format transcript for video_id: {video_id}")
            logger.exception(e)
            errors.append(e)

        try:
            transcript_raw = [
                {"text": s.text, "start": s.start, "duration": s.duration}
                for s in transcript.snippets
            ]
        except Exception as e:
            logger.error(f"Failed to get raw transcript for video_id: {video_id}")
            logger.exception(e)

    # Fallback: pytubefix
    if not formatted_content:
        logger.debug("Falling back to pytubefix for transcript extraction")
        try:
            formatted_content, transcript_raw = extract_transcript_pytubefix(
                url, languages, proxy=config.youtube_proxy
            )
        except Exception as e:
            errors.append(e)

    if not formatted_content:
        failure, cause = _transcript_failure(video_id, errors)
        raise failure from cause

    return ExtractionOutput(
        content=formatted_content or "",
        title=title or "",
        source_type="url",
        identified_type="youtube",
        metadata={"video_id": video_id, "transcript": transcript_raw},
    )
