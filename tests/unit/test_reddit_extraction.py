"""Unit tests for Reddit post extraction."""
from unittest.mock import AsyncMock, patch

import pytest

from content_core.config import ContentCoreConfig
from content_core.processors.url.reddit import (
    _format_comment,
    _format_reddit_post,
    extract_reddit,
    is_reddit_post,
)


# Sample Reddit JSON response structure
SAMPLE_REDDIT_JSON = [
    {
        "data": {
            "children": [
                {
                    "kind": "t3",
                    "data": {
                        "title": "Test Post Title",
                        "author": "testuser",
                        "subreddit": "testsubreddit",
                        "score": 42,
                        "selftext": "This is the post body.",
                        "is_self": True,
                        "url": "",
                    },
                }
            ]
        }
    },
    {
        "data": {
            "children": [
                {
                    "kind": "t1",
                    "data": {
                        "author": "commenter1",
                        "body": "Great post!",
                        "score": 10,
                        "replies": {
                            "data": {
                                "children": [
                                    {
                                        "kind": "t1",
                                        "data": {
                                            "author": "replier1",
                                            "body": "I agree.",
                                            "score": 5,
                                            "replies": "",
                                        },
                                    }
                                ]
                            }
                        },
                    },
                },
                {
                    "kind": "t1",
                    "data": {
                        "author": "commenter2",
                        "body": "Thanks for sharing.",
                        "score": 3,
                        "replies": "",
                    },
                },
            ]
        }
    },
]


class TestIsRedditPost:
    def test_standard_url(self):
        assert is_reddit_post("https://www.reddit.com/r/python/comments/abc123/some_title/")

    def test_without_trailing_slash(self):
        assert is_reddit_post("https://www.reddit.com/r/python/comments/abc123/some_title")

    def test_without_slug(self):
        assert is_reddit_post("https://www.reddit.com/r/python/comments/abc123")

    def test_old_reddit(self):
        assert is_reddit_post("https://old.reddit.com/r/python/comments/abc123/title/")

    def test_new_reddit(self):
        assert is_reddit_post("https://new.reddit.com/r/python/comments/abc123/title/")

    def test_subreddit_listing_is_not_post(self):
        assert not is_reddit_post("https://www.reddit.com/r/python/")

    def test_homepage_is_not_post(self):
        assert not is_reddit_post("https://www.reddit.com/")

    def test_non_reddit_url(self):
        assert not is_reddit_post("https://example.com/r/python/comments/abc123")

    def test_user_profile_is_not_post(self):
        assert not is_reddit_post("https://www.reddit.com/u/someuser")


class TestFormatRedditPost:
    def test_formats_title(self):
        title, content = _format_reddit_post(SAMPLE_REDDIT_JSON)
        assert title == "Test Post Title"
        assert "# Test Post Title" in content

    def test_formats_metadata(self):
        _, content = _format_reddit_post(SAMPLE_REDDIT_JSON)
        assert "r/testsubreddit" in content
        assert "u/testuser" in content
        assert "score: 42" in content

    def test_formats_body(self):
        _, content = _format_reddit_post(SAMPLE_REDDIT_JSON)
        assert "This is the post body." in content

    def test_formats_comments(self):
        _, content = _format_reddit_post(SAMPLE_REDDIT_JSON)
        assert "## Comments" in content
        assert "u/commenter1" in content
        assert "Great post!" in content
        assert "u/commenter2" in content
        assert "Thanks for sharing." in content

    def test_formats_nested_replies(self):
        _, content = _format_reddit_post(SAMPLE_REDDIT_JSON)
        assert "u/replier1" in content
        assert "I agree." in content

    def test_link_post_includes_url(self):
        data = [
            {
                "data": {
                    "children": [
                        {
                            "kind": "t3",
                            "data": {
                                "title": "Link Post",
                                "author": "poster",
                                "subreddit": "sub",
                                "score": 1,
                                "selftext": "",
                                "is_self": False,
                                "url": "https://example.com/article",
                            },
                        }
                    ]
                }
            },
            {"data": {"children": []}},
        ]
        _, content = _format_reddit_post(data)
        assert "https://example.com/article" in content


class TestFormatComment:
    def test_skips_deleted(self):
        comment = {
            "kind": "t1",
            "data": {"author": "[deleted]", "body": "[deleted]", "score": 0, "replies": ""},
        }
        assert _format_comment(comment) == ""

    def test_skips_removed(self):
        comment = {
            "kind": "t1",
            "data": {"author": "mod", "body": "[removed]", "score": 0, "replies": ""},
        }
        assert _format_comment(comment) == ""

    def test_skips_non_comment_kinds(self):
        assert _format_comment({"kind": "more", "data": {}}) == ""


class TestExtractReddit:
    @pytest.fixture
    def config(self):
        return ContentCoreConfig()

    async def test_successful_extraction(self, config):
        with patch(
            "content_core.processors.url.reddit._fetch_reddit_json",
            new_callable=AsyncMock,
            return_value=SAMPLE_REDDIT_JSON,
        ):
            result = await extract_reddit(
                "https://www.reddit.com/r/test/comments/abc123/title/", config
            )
            assert result is not None
            assert result.title == "Test Post Title"
            assert "This is the post body." in result.content
            assert "Great post!" in result.content
            assert result.source_type == "url"
            assert result.identified_type == "reddit"

    async def test_returns_none_on_failure(self, config):
        with patch(
            "content_core.processors.url.reddit._fetch_reddit_json",
            new_callable=AsyncMock,
            side_effect=Exception("403 Forbidden"),
        ):
            result = await extract_reddit(
                "https://www.reddit.com/r/test/comments/abc123/title/", config
            )
            assert result is None
