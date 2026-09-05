"""Tests for the exception taxonomy and its public surface (#52)."""

import inspect

import pytest

import content_core
from content_core.common import exceptions as exc_module

# The exact taxonomy the library commits to: every failure that can escape
# extract_content is one of these, and nothing else lives in the module.
PUBLIC_EXCEPTIONS = (
    "ContentCoreError",
    "UnsupportedTypeException",
    "InvalidInputError",
    "ConfigurationError",
    "NotFoundError",
    "NoTranscriptFound",
    "NetworkError",
    "ExternalServiceError",
    "FileOperationError",
)

def _module_exceptions():
    return {
        name
        for name, obj in vars(exc_module).items()
        if inspect.isclass(obj) and issubclass(obj, BaseException)
    }


def test_module_defines_exactly_the_taxonomy():
    """Nothing more, nothing less.

    This is what keeps the pruned classes (a database error, and separate
    auth/rate-limit classes folded into ExternalServiceError) from coming
    back, and any new one from landing without a raise site.
    """
    assert _module_exceptions() == set(PUBLIC_EXCEPTIONS)


@pytest.mark.parametrize("name", PUBLIC_EXCEPTIONS)
def test_exported_from_package_root(name):
    assert name in content_core.__all__
    assert getattr(content_core, name) is getattr(exc_module, name)


@pytest.mark.parametrize("name", PUBLIC_EXCEPTIONS)
def test_exported_from_common(name):
    from content_core import common

    assert name in common.__all__
    assert getattr(common, name) is getattr(exc_module, name)


@pytest.mark.parametrize(
    "name", [n for n in PUBLIC_EXCEPTIONS if n != "ContentCoreError"]
)
def test_every_exception_derives_from_the_base(name):
    assert issubclass(getattr(content_core, name), content_core.ContentCoreError)


def test_base_docstring_does_not_mention_open_notebook():
    assert "Open Notebook" not in (content_core.ContentCoreError.__doc__ or "")


def test_catching_the_base_catches_a_subtype():
    with pytest.raises(content_core.ContentCoreError):
        raise content_core.ConfigurationError("docling not installed")


def test_extract_content_documents_what_it_raises():
    doc = content_core.extract_content.__doc__ or ""
    assert "Raises:" in doc
    for name in PUBLIC_EXCEPTIONS:
        if name == "ContentCoreError":
            continue
        assert name in doc
