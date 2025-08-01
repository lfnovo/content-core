# Changelog

All notable changes to Content Core will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Pure Python file type detection via the new `FileDetector` class
- Comprehensive file signature detection for 25+ file formats
- Smart detection for ZIP-based formats (DOCX, XLSX, PPTX, EPUB)

### Changed
- File type detection now uses pure Python implementation instead of libmagic
- Improved cross-platform compatibility - no system dependencies required

### Removed
- Dependency on `python-magic` and `python-magic-bin`
- System requirement for libmagic library

### Technical Details
- Replaced libmagic dependency with custom `FileDetector` implementation
- File detection based on binary signatures and content analysis
- Maintains same API surface - no breaking changes for users
- Significantly simplified installation process across all platforms

## Previous Releases

For releases prior to this changelog, please see the [GitHub releases page](https://github.com/lfnovo/content-core/releases).